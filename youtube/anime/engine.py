"""ショートアニメ用の小さな2Dエンジン（Pillow + numpy だけで動く）。

しくみ
  ・ワールド座標（引きの画 = 1080x1920 の画面と同じ座標）に絵を置く
  ・Camera（中心・ズーム）のキーフレームで、カットを割らずにワンカットで寄り引きする
  ・3つの層を合成して1フレームを作る
      base     … ふつうの絵（月明かりで暗くなり、光源の近くだけ明るくなる）
      emissive … 自分で光るもの（月・ホタルの光など）。ぼかしてブルーム（にじみ）を足す
      overlay  … 字幕など、ライティングの影響を受けないもの
  ・フレームは複数プロセスで並列に描き、ffmpeg にパイプで流して mp4 にする

エピソード側（episodes/<名前>/story.py）は
  DURATION, FPS, SIZE, draw_frame(fx: Frame, t) を用意するだけでよい。
"""
from __future__ import annotations

import math
import os
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent      # youtube/
FONT_DIR = ROOT / "assets" / "fonts"
SS = 2                                              # スーパーサンプリング倍率


# ============================================================================
# 時間・補間
# ============================================================================
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, u):
    return a + (b - a) * u


def ease_in_out(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def ease_in_out_sine(u):
    u = clamp(u)
    return 0.5 - 0.5 * math.cos(math.pi * u)


def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def ease_in(u):
    u = clamp(u)
    return u ** 3


def seg(t, t0, t1, ease=ease_in_out):
    """t が t0→t1 を進む割合（0〜1、イージング付き）。"""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return ease((t - t0) / (t1 - t0))


def pulse(t, t0, t1, fade=0.3):
    """t0〜t1 の間だけ 1 になる（前後 fade 秒でなめらかに）。"""
    return seg(t, t0, t0 + fade) * (1 - seg(t, t1 - fade, t1))


class Track:
    """キーフレーム補間。keys = [(時刻, 値), ...]。値は数値・タプルどちらでも。

    各キーの間はイーズイン・アウト。同じ値が続く区間は静止（ホールド）。
    """

    def __init__(self, keys, ease=ease_in_out_sine):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.ease = ease

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
            if t <= t1:
                u = self.ease((t - t0) / (t1 - t0)) if t1 > t0 else 1
                if isinstance(v0, (tuple, list)):
                    return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
                return lerp(v0, v1, u)
        return ks[-1][1]


# ============================================================================
# カメラと描画
# ============================================================================
@dataclass
class Cam:
    cx: float
    cy: float
    zoom: float


class View:
    """ワールド座標 → スーパーサンプル画像上のピクセル座標。

    parallax < 1 は奥（カメラの動きに対してゆっくり動く）、> 1 は手前。
    """

    def __init__(self, cam: Cam, size, parallax=1.0, home=None):
        w, h = size
        hx, hy = home or (w / 2, h / 2)
        p = parallax
        self.zoom = (1 + (cam.zoom - 1) * p) * SS
        self.cx = hx + (cam.cx - hx) * p
        self.cy = hy + (cam.cy - hy) * p
        self.ox, self.oy = w / 2 * SS, h / 2 * SS

    def pt(self, x, y):
        return ((x - self.cx) * self.zoom + self.ox, (y - self.cy) * self.zoom + self.oy)

    def s(self, v):
        return v * self.zoom


def ellipse_pts(cx, cy, rx, ry, rot=0.0, n=48, a0=0.0, a1=360.0):
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    pts = []
    for i in range(n + 1 if a1 - a0 < 360 else n):
        a = math.radians(a0 + (a1 - a0) * i / n)
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    return pts


def bezier(p0, p1, p2, p3=None, n=24):
    """2次 or 3次ベジェの点列。"""
    pts = []
    for i in range(n + 1):
        u = i / n
        if p3 is None:
            x = (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0]
            y = (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]
        else:
            x = ((1 - u) ** 3 * p0[0] + 3 * (1 - u) ** 2 * u * p1[0] + 3 * (1 - u) * u * u * p2[0]
                 + u ** 3 * p3[0])
            y = ((1 - u) ** 3 * p0[1] + 3 * (1 - u) ** 2 * u * p1[1] + 3 * (1 - u) * u * u * p2[1]
                 + u ** 3 * p3[1])
        pts.append((x, y))
    return pts


class Canvas:
    """1つの層。ワールド座標で図形を描く。色は (r,g,b) か (r,g,b,a)。"""

    def __init__(self, img: Image.Image, view: View):
        self.img = img
        self.view = view
        self.d = ImageDraw.Draw(img, "RGBA")

    def with_view(self, view: View) -> "Canvas":
        c = Canvas.__new__(Canvas)
        c.img, c.view, c.d = self.img, view, self.d
        return c

    def poly(self, pts, fill):
        if len(pts) >= 3:
            self.d.polygon([self.view.pt(x, y) for x, y in pts], fill=_c(fill))

    def ellipse(self, cx, cy, rx, ry, fill, rot=0.0):
        if rot == 0:
            x0, y0 = self.view.pt(cx - rx, cy - ry)
            x1, y1 = self.view.pt(cx + rx, cy + ry)
            if x1 - x0 < 0.5 or y1 - y0 < 0.5:
                return
            self.d.ellipse((x0, y0, x1, y1), fill=_c(fill))
        else:
            self.poly(ellipse_pts(cx, cy, rx, ry, rot), fill)

    def circle(self, cx, cy, r, fill):
        self.ellipse(cx, cy, r, r, fill)

    def line(self, pts, fill, width, round_cap=True):
        w = max(1, int(round(self.view.s(width))))
        sp = [self.view.pt(x, y) for x, y in pts]
        self.d.line(sp, fill=_c(fill), width=w, joint="curve")
        if round_cap and w > 2:
            for x, y in (sp[0], sp[-1]):
                self.d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=_c(fill))

    def glow(self, cx, cy, r, color, strength=1.0, rings=10):
        """やわらかい光の玉（emissive 層向け）。"""
        for i in range(rings, 0, -1):
            k = i / rings
            a = int(255 * strength * (1 - k) ** 1.6 / rings * 2.2)
            if a > 0:
                self.circle(cx, cy, r * k, tuple(color[:3]) + (min(255, a),))


def _c(col):
    if col is None:
        return None
    col = tuple(int(v) for v in col)
    return col if len(col) == 4 else col + (255,)


class Local:
    """キャラクター用のローカル座標（中心 x,y・大きさ s・回転 rot・左右反転 flip）。"""

    def __init__(self, cv: Canvas, x, y, s, rot=0.0, flip=False, alpha=1.0):
        self.cv, self.x, self.y, self.s = cv, x, y, s
        self.cr, self.sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        self.f = -1 if flip else 1
        self.rot = rot
        self.alpha = alpha

    def p(self, lx, ly):
        lx *= self.f
        return (self.x + (lx * self.cr - ly * self.sr) * self.s,
                self.y + (lx * self.sr + ly * self.cr) * self.s)

    def _a(self, col):
        if col is None:
            return None
        a = col[3] if len(col) == 4 else 255
        return tuple(col[:3]) + (int(a * self.alpha),)

    def poly(self, pts, fill):
        self.cv.poly([self.p(x, y) for x, y in pts], self._a(fill))

    def ellipse(self, cx, cy, rx, ry, fill, rot=0.0):
        self.poly(ellipse_pts(cx, cy, rx, ry, rot * self.f, n=40), fill)

    def circle(self, cx, cy, r, fill):
        x, y = self.p(cx, cy)
        self.cv.circle(x, y, r * self.s, self._a(fill))

    def line(self, pts, fill, width):
        self.cv.line([self.p(x, y) for x, y in pts], self._a(fill), width * self.s)

    def arc(self, cx, cy, rx, ry, a0, a1, fill, width, n=20):
        self.line(ellipse_pts(cx, cy, rx, ry, 0, n, a0, a1), fill, width)


# ============================================================================
# フレーム（層の合成・ライティング・ブルーム・字幕）
# ============================================================================
@dataclass
class Light:
    x: float
    y: float
    radius: float
    intensity: float = 1.0
    color: tuple = (1.0, 0.85, 0.55)
    falloff: float = 2.2      # 大きいほど光の縁がはやく暗くなる


@dataclass
class Frame:
    size: tuple
    cam: Cam
    ambient: float = 1.0
    ambient_map: object = None      # (w,h) の numpy 配列（場所による暗さ）。省略可
    lights: list = field(default_factory=list)
    fade: float = 0.0               # 1 で真っ黒
    bloom: float = 1.0
    light_cap: float = 1.6          # 光で明るくなる上限（白いキャラが白飛びするなら下げる）

    def __post_init__(self):
        w, h = self.size
        self.base_img = Image.new("RGB", (w * SS, h * SS), (0, 0, 0))
        self.emit_img = Image.new("RGB", (w * SS, h * SS), (0, 0, 0))
        self.overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.unlit_img = None

    def view(self, parallax=1.0) -> View:
        return View(self.cam, self.size, parallax)

    def base(self, parallax=1.0) -> Canvas:
        return Canvas(self.base_img, self.view(parallax))

    def emit(self, parallax=1.0) -> Canvas:
        return Canvas(self.emit_img, self.view(parallax))

    def screen_xy(self, x, y, parallax=1.0):
        sx, sy = self.view(parallax).pt(x, y)
        return sx / SS, sy / SS

    # ---- 合成 ----
    def compose(self) -> np.ndarray:
        w, h = self.size
        base = np.asarray(self.base_img.reduce(SS), dtype=np.float32) / 255.0
        emit = np.asarray(self.emit_img.reduce(SS), dtype=np.float32) / 255.0

        # ライティング：環境光（場所ごとの暗さ）＋ 光源
        q = 4
        gw, gh = w // q, h // q
        light = np.zeros((gh, gw, 3), np.float32)
        if self.lights:
            ys, xs = np.mgrid[0:gh, 0:gw].astype(np.float32)
            xs = xs * q + q / 2
            ys = ys * q + q / 2
            for L in self.lights:
                sx, sy = self.screen_xy(L.x, L.y)
                r = max(1.0, L.radius * self.cam.zoom)
                d2 = ((xs - sx) ** 2 + (ys - sy) ** 2) / (r * r)
                fall = np.exp(-d2 * L.falloff) * L.intensity
                light += fall[..., None] * np.array(L.color, np.float32)
        amb = np.full((gh, gw), self.ambient, np.float32)
        if self.ambient_map is not None:
            if callable(self.ambient_map):
                # ワールド座標の格子を渡して、場所ごとの明るさを返してもらう
                ys2, xs2 = np.mgrid[0:gh, 0:gw].astype(np.float32)
                wx = self.cam.cx + (xs2 * q + q / 2 - w / 2) / self.cam.zoom
                wy = self.cam.cy + (ys2 * q + q / 2 - h / 2) / self.cam.zoom
                amb = amb * self.ambient_map(wx, wy)
            else:
                amb = amb * self.ambient_map
        lm = amb[..., None] + light
        lm = self.light_cap * (1 - np.exp(-lm / self.light_cap))          # 光が重なっても白飛びしにくいように頭打ち
        lm = np.asarray(Image.fromarray(np.clip(lm * 80, 0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR),
                        dtype=np.float32) / 80.0
        out = base * lm

        # ブルーム：光る層を縮小してぼかし、2段階で足す
        if self.bloom > 0:
            small = self.emit_img.reduce(SS * 4)
            b1 = small.filter(ImageFilter.GaussianBlur(4)).resize((w, h), Image.BILINEAR)
            b2 = small.reduce(2).filter(ImageFilter.GaussianBlur(10)).resize((w, h), Image.BILINEAR)
            bl = (np.asarray(b1, np.float32) * 1.1 + np.asarray(b2, np.float32) * 1.3) / 255.0
            out = out + emit + bl * self.bloom
        else:
            out = out + emit
        # トーン（白飛びをやわらかく）
        out = 1 - np.exp(-out * 1.15)
        out = out / (1 - math.exp(-1.15))
        if self.fade > 0:
            out *= 1 - self.fade
        img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
        img = img.convert("RGBA")
        img.alpha_composite(self.overlay)
        if self.fade > 0:
            dark = Image.new("RGBA", img.size, (0, 0, 0, int(255 * self.fade)))
            img.alpha_composite(dark)
        return np.asarray(img.convert("RGB"))


# ============================================================================
# 字幕
# ============================================================================
@lru_cache(maxsize=None)
def font(name: str, size: int):
    return ImageFont.truetype(str(FONT_DIR / name), size)


GOTHIC = "MPLUSRounded1c-Bold.ttf"
MINCHO = "ShipporiMinchoB1-ExtraBold.ttf"


@dataclass
class Caption:
    t0: float
    t1: float
    text: str
    size: int = 58
    font: str = GOTHIC
    y: float = 0.33          # 画面の上から何割の位置（中心）
    line_gap: float = 1.45
    fade_in: float = 0.5
    fade_out: float = 0.5
    rise: float = 22


CAPTION_MARGIN = 70          # 字幕の左右の余白（px）。この内側に必ず収める
_NO_START = set("、。，．・：；？！ー」』）…‥ぁぃぅぇぉっゃゅょゎァィゥェォッャュョ!?)")


def _split_line(line, f, max_w):
    """1行を2つ以上に分ける。「、」「。」や空白のあとで切れるなら必ずそこで切り（いちばんバランスのよい所）、
    なければ「」の中や小さい文字の前を避けて切る。"""
    if f.getlength(line) <= max_w or len(line) < 2:
        return [line]
    cands = []
    depth = 0
    for i in range(1, len(line)):
        ch = line[i - 1]
        depth += (ch in "「『（") - (ch in "」』）")
        a, b = line[:i].rstrip(), line[i:].lstrip()
        if not a or not b or b[0] in _NO_START:
            continue
        rank = 0 if ch in "、。，！？ 　" else (1 if ch in "」』" else 2)
        wa, wb = f.getlength(a), f.getlength(b)
        cands.append((rank, depth > 0, max(wa, wb) > max_w, abs(wa - wb), a, b))
    if not cands or (min(c[0] for c in cands) == 2 and f.getlength(line) <= max_w / 0.8):
        return [line]          # 自然な切れ目がなく、少しの縮小で収まるなら切らない（呼び出し側で縮小）
    cands.sort(key=lambda c: c[:4])
    _, _, _, _, a, b = cands[0]
    return _split_line(a, f, max_w) + _split_line(b, f, max_w)


def fit_caption(text, font_name, size, max_w):
    """字幕が max_w に収まるよう、少しだけ小さくするか、改行する。戻り値 (行のリスト, 文字サイズ)。"""
    lines = text.split("\n")
    widest = max(font(font_name, size).getlength(l) for l in lines)
    if widest <= max_w:
        return lines, size
    if widest <= max_w / 0.86:                       # すこしはみ出すだけ → 小さくする
        return lines, int(size * max_w / widest)
    f = font(font_name, size)
    out = []
    for l in lines:
        out += _split_line(l, f, max_w)
    widest = max(f.getlength(l) for l in out)
    if widest > max_w:                                # それでも長い行は小さくして必ず収める
        size = int(size * max_w / widest)
    return out, size


def draw_captions(fr: Frame, captions, t):
    W, H = fr.size
    for c in captions:
        if not (c.t0 <= t <= c.t1):
            continue
        a_in = ease_out((t - c.t0) / c.fade_in)
        a_out = 1 - seg(t, c.t1 - c.fade_out, c.t1)
        alpha = a_in * a_out
        if alpha <= 0.01:
            continue
        dy = (1 - a_in) * c.rise
        lines, size = fit_caption(c.text, c.font, c.size, W - CAPTION_MARGIN * 2)
        f = font(c.font, size)
        lh = size * c.line_gap
        total = lh * (len(lines) - 1) + size
        top = H * c.y - total / 2 + dy
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dt, ds = ImageDraw.Draw(txt), ImageDraw.Draw(shadow)
        for i, line in enumerate(lines):
            w = f.getlength(line)
            x = (W - w) / 2
            y = top + i * lh
            ds.text((x, y + 4), line, font=f, fill=(0, 0, 20, 200), stroke_width=4, stroke_fill=(0, 0, 20, 200))
            dt.text((x, y), line, font=f, fill=(255, 255, 255, 255))
        shadow = shadow.filter(ImageFilter.GaussianBlur(9))
        layer = Image.alpha_composite(shadow, txt)
        if alpha < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        fr.overlay.alpha_composite(layer)


# ============================================================================
# 書き出し
# ============================================================================
_STORY = None


def _render_one(args):
    path, t = args
    global _STORY
    if _STORY is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("story", path)
        _STORY = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_STORY)
    return _STORY.render(t).tobytes()


def render_video(story_path: Path, story, out: Path, audio: Path | None = None, workers=None, t_range=None):
    import multiprocessing as mp
    fps = story.FPS
    n = int(round(story.DURATION * fps))
    frames = range(n)
    if t_range:
        frames = range(int(t_range[0] * fps), min(n, int(t_range[1] * fps)))
    W, H = story.SIZE
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-"]
    if audio:
        if t_range:
            cmd += ["-ss", str(t_range[0]), "-t", str(len(frames) / fps)]
        cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "192k", "-ac", "2"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-movflags", "+faststart", "-shortest", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    workers = workers or max(1, (os.cpu_count() or 2))
    ctx = mp.get_context("spawn")
    with ctx.Pool(workers) as pool:
        for i, buf in enumerate(pool.imap(_render_one, [(str(story_path), f / fps) for f in frames], chunksize=2)):
            proc.stdin.write(buf)
            if i % fps == 0:
                print(f"\r  {i / fps:5.1f}s / {len(frames) / fps:.1f}s", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed")
