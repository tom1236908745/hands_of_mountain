"""マスコットキャラ（三毛猫の「ことにゃん」）の描画モジュール。

外部の画像素材を使わず、Pillow の図形だけで描くので
・どんなサイズでもくっきり出力できる（動画 / LINEスタンプ / グッズ用の高解像度）
・表情を足したいときはこのファイルに分岐を足すだけ
という作りになっています。

座標はすべて 1000x1000 の「設計キャンバス」上の値で書き、
4倍の大きさで描いてから指定サイズへ縮小します（＝なめらかな線）。
"""
from __future__ import annotations

import math
from PIL import Image, ImageChops, ImageDraw

# ---- カラーパレット（グッズ化のときもこの値を使う） -------------------------
PALETTE = {
    "fur": (255, 252, 246),       # 白い毛
    "patch_a": (238, 150, 64),    # 三毛の茶
    "patch_b": (72, 58, 52),      # 三毛の黒
    "ear_in": (250, 184, 184),    # 耳の内側
    "line": (112, 80, 68),        # 輪郭線（やわらかい茶）
    "eye": (58, 40, 36),
    "iris": (128, 84, 60),        # 瞳の下のほうの明るい茶
    "nose": (240, 130, 140),
    "mouth_in": (200, 80, 90),
    "cheek": (250, 160, 160),
    "collar": (206, 48, 52),      # 赤い首輪（招き猫）
    "bell": (240, 196, 60),       # 金の鈴
    "bell_dark": (180, 130, 30),
    "eye_white": (255, 255, 255),
    "tear": (120, 190, 240),
    "halo": (255, 214, 102),
    "anger": (230, 70, 60),
}

SS = 4          # スーパーサンプリング倍率
BASE = 1000     # 設計キャンバスのサイズ
LW = 11         # 輪郭線の太さ

EXPRESSIONS = [
    "normal", "happy", "surprised", "thinking", "sad",
    "angry", "wink", "sleepy", "satori", "shy",
]

EXPRESSION_LABELS = {
    "normal": "ふつう", "happy": "にっこり", "surprised": "びっくり",
    "thinking": "考え中", "sad": "しょんぼり", "angry": "ぷんすか",
    "wink": "ウインク", "sleepy": "ねむい", "satori": "悟り", "shy": "てれ",
}


def _opaque(col):
    return None if col is None else tuple(col[:3])


class _Pen:
    """設計座標 → 実ピクセル座標への変換つきの描画ヘルパー。

    半透明色（RGBA で A<255）を渡すと、別レイヤーに描いて合成する
    （ImageDraw は半透明色をそのまま上書きして穴が開くため）。
    """

    def __init__(self, img: Image.Image, scale: float):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.s = scale

    def _alpha_of(self, *cols):
        for col in cols:
            if col is not None and len(col) == 4 and col[3] < 255:
                return col[3]
        return None

    def _via_layer(self, alpha, method, *args, **kw):
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        getattr(_Pen(layer, self.s), method)(*args, **kw)
        a = layer.getchannel("A").point(lambda v: v * alpha // 255)
        layer.putalpha(a)
        self.img.alpha_composite(layer)

    def p(self, *xy):
        return [v * self.s for v in xy]

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=0):
        a = self._alpha_of(fill, outline)
        if a is not None:
            return self._via_layer(a, "ellipse", cx, cy, rx, ry, fill=_opaque(fill),
                                   outline=_opaque(outline), width=width)
        self.d.ellipse(self.p(cx - rx, cy - ry, cx + rx, cy + ry), fill=fill,
                       outline=outline, width=int(width * self.s))

    def circle(self, cx, cy, r, **kw):
        self.ellipse(cx, cy, r, r, **kw)

    def polygon(self, pts, fill=None, outline=None, width=0):
        a = self._alpha_of(fill, outline)
        if a is not None:
            return self._via_layer(a, "polygon", pts, fill=_opaque(fill), outline=_opaque(outline), width=width)
        self.d.polygon([(x * self.s, y * self.s) for x, y in pts], fill=fill,
                       outline=outline, width=int(width * self.s))

    def line(self, pts, fill, width):
        a = self._alpha_of(fill)
        if a is not None:
            return self._via_layer(a, "line", pts, _opaque(fill), width)
        w = int(width * self.s)
        self.d.line([(x * self.s, y * self.s) for x, y in pts], fill=fill,
                    width=w, joint="curve")
        for x, y in (pts[0], pts[-1]):   # 端を丸める
            self.circle(x, y, width / 2, fill=fill)

    def arc(self, cx, cy, rx, ry, start, end, fill, width):
        # Pillow の arc は端が四角いので、点列の太線で描く
        pts = []
        steps = 40
        for i in range(steps + 1):
            t = math.radians(start + (end - start) * i / steps)
            pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
        self.line(pts, fill, width)


# ---- パーツ -------------------------------------------------------------------
# 赤ちゃんっぽく見えるように：頭は大きく横長、目は低め・はなれ気味・大きく
EYE_L = (368, 468)
EYE_R = (632, 468)
HEAD = (500, 415, 350, 268)      # cx, cy, rx, ry


def _tail(pen, c):
    # 体の後ろから右上へ伸びるしっぽ（輪郭→茶→先っぽ黒）
    # 2次ベジェ曲線：体の右下（体に隠れる）→ 右へふくらんで → 上へ
    p0, p1, p2 = (590, 890), (930, 920), (850, 560)
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    pen.line(pts, c["line"], 76)
    pen.line(pts, c["patch_a"], 76 - LW * 2)
    pen.line(pts[-8:], c["patch_b"], 76 - LW * 2)


def _qbez(p0, p1, p2, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def _ear(pen, c, side):
    """先が丸い三角の耳。"""
    sx = -1 if side == "L" else 1
    X = lambda v: 500 + sx * v  # noqa: E731
    outer = (_qbez((X(330), 360), (X(330), 150), (X(262), 118))
             + _qbez((X(262), 118), (X(235), 100), (X(200), 128))
             + _qbez((X(200), 128), (X(150), 170), (X(110), 230)))
    inner = (_qbez((X(292), 320), (X(295), 185), (X(258), 162))
             + _qbez((X(258), 162), (X(232), 150), (X(208), 175))
             + _qbez((X(208), 175), (X(175), 210), (X(160), 250)))
    fill = c["patch_a"] if side == "L" else c["patch_b"]
    pen.polygon(outer, fill=fill, outline=c["line"], width=LW)
    pen.polygon(inner, fill=c["ear_in"])


def _head(img, pen, c):
    cx, cy, rx, ry = HEAD
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lp = type(pen)(layer, pen.s)
    lp.ellipse(cx, cy, rx, ry, fill=c["fur"])
    # 三毛の模様（頭の形で切り抜く）
    pat = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pp = type(pen)(pat, pen.s)
    pp.ellipse(250, 250, 210, 170, fill=c["patch_a"])        # 左上の茶
    pp.ellipse(770, 240, 150, 110, fill=c["patch_b"])        # 右上の黒
    pp.ellipse(500, 175, 70, 45, fill=c["patch_a"])          # おでこの小さな茶
    mask = layer.getchannel("A")
    pat.putalpha(ImageChops.multiply(pat.getchannel("A"), mask))
    layer.alpha_composite(pat)
    img.alpha_composite(layer)
    pen.ellipse(cx, cy, rx, ry, outline=c["line"], width=LW)


def _body(img, pen, c):
    _tail(pen, c)
    # 胴体（座った姿勢）
    pen.ellipse(500, 765, 225, 190, fill=c["fur"], outline=c["line"], width=LW)
    pen.ellipse(355, 760, 62, 82, fill=c["patch_a"])     # 体の茶ぶち
    pen.ellipse(500, 765, 225, 190, outline=c["line"], width=LW)
    # 前足（ころんと丸く）
    for x in (428, 572):
        pen.ellipse(x, 915, 62, 46, fill=c["fur"], outline=c["line"], width=LW)
        for dx in (-16, 16):
            pen.line([(x + dx, 893), (x + dx, 908)], c["line"], 7)
    _ear(pen, c, "L")
    _ear(pen, c, "R")
    _head(img, pen, c)


def _collar(pen, c, with_bell=True):
    pen.arc(500, 590, 200, 92, 32, 148, c["line"], 42)
    pen.arc(500, 590, 200, 92, 34, 146, c["collar"], 27)
    if with_bell:
        bx, by = 500, 712
        pen.circle(bx, by, 34, fill=c["bell"], outline=c["line"], width=8)
        pen.line([(bx - 30, by - 5), (bx + 30, by - 5)], c["bell_dark"], 6)
        pen.circle(bx, by + 12, 7, fill=c["bell_dark"])
        pen.line([(bx, by + 14), (bx, by + 30)], c["bell_dark"], 5)
        pen.circle(bx - 12, by - 16, 8, fill=(255, 255, 255, 230))


def _whiskers(pen, c):
    for side in (-1, 1):
        for dy, ang in ((-10, -8), (12, 5)):
            x0 = 500 + side * 250
            pen.line([(x0, 560 + dy), (x0 + side * 80, 560 + dy + ang)], c["line"] + (150,), 6)


def _cheeks(pen, c, strong=False):
    a = 230 if strong else 170
    for x in (285, 715):
        pen.ellipse(x, 560, 56 if strong else 50, 30, fill=c["cheek"] + (a,))


def _eye_open(pen, c, center, look=(0, 0), r=(58, 68)):
    """うるうるの大きな目：黒目＋下のほうに明るい茶＋大小のハイライト。"""
    cx, cy = center[0] + look[0], center[1] + look[1]
    pen.ellipse(cx, cy, r[0], r[1], fill=c["eye"])
    pen.ellipse(cx, cy + r[1] * 0.42, r[0] * 0.7, r[1] * 0.38, fill=c["iris"] + (170,))
    pen.ellipse(cx - r[0] * 0.28, cy - r[1] * 0.32, r[0] * 0.4, r[1] * 0.36, fill=(255, 255, 255))
    pen.circle(cx + r[0] * 0.38, cy + r[1] * 0.3, r[0] * 0.17, fill=(255, 255, 255))
    pen.circle(cx + r[0] * 0.1, cy - r[1] * 0.6, r[0] * 0.08, fill=(255, 255, 255, 200))


def _eye_surprised(pen, c, center):
    pen.circle(center[0], center[1], 56, fill=c["eye_white"], outline=c["eye"], width=10)
    pen.circle(center[0], center[1], 20, fill=c["eye"])
    pen.circle(center[0] - 6, center[1] - 7, 6, fill=(255, 255, 255))


def _eye_happy(pen, c, center):     # ∩
    pen.arc(center[0], center[1] + 22, 46, 38, 200, 340, c["eye"], 16)


def _eye_calm(pen, c, center):      # ∪
    pen.arc(center[0], center[1] - 12, 44, 28, 20, 160, c["eye"], 15)


def _eye_line(pen, c, center):      # ー
    pen.arc(center[0], center[1] - 8, 44, 22, 25, 155, c["eye"], 14)


def _mouth(pen, c, open_=False, wide=False):
    # 鼻
    pen.ellipse(500, 530, 17, 11, fill=c["nose"])
    pen.line([(500, 538), (500, 552)], c["line"], 6)
    if open_:
        h = 44 if wide else 30
        pen.ellipse(500, 566 + h / 3, 24 if not wide else 21, h / 2 + 5, fill=c["mouth_in"],
                    outline=c["line"], width=6)
    # ω
    pen.arc(482, 552, 18, 14, 10, 170, c["line"], 7)
    pen.arc(518, 552, 18, 14, 10, 170, c["line"], 7)


def _brows(pen, c, kind):
    w = 12
    lx, rx = EYE_L[0], EYE_R[0]
    if kind == "up":
        pen.arc(lx, 370, 45, 20, 200, 340, c["line"], w)
        pen.arc(rx, 370, 45, 20, 200, 340, c["line"], w)
    elif kind == "sad":
        pen.line([(lx - 45, 408), (lx + 40, 388)], c["line"], w)
        pen.line([(rx + 45, 408), (rx - 40, 388)], c["line"], w)
    elif kind == "angry":
        pen.line([(lx - 45, 383), (lx + 45, 413)], c["line"], w)
        pen.line([(rx + 45, 383), (rx - 45, 413)], c["line"], w)
    elif kind == "think":
        pen.line([(lx - 40, 398), (lx + 40, 365)], c["line"], w)
        pen.line([(rx - 40, 380), (rx + 45, 400)], c["line"], w)


def _sweat(pen, c, x, y, r=22):
    pen.circle(x, y, r, fill=c["tear"])
    pen.polygon([(x - r * 0.95, y - r * 0.3), (x + r * 0.95, y - r * 0.3), (x, y - r * 2.4)], fill=c["tear"])


def _question(pen, c):
    col = c["line"]
    pen.arc(865, 190, 48, 48, 180, 400, col, 20)
    pen.line([(902, 222), (865, 262), (865, 290)], col, 20)
    pen.circle(865, 335, 13, fill=col)


def _anger_mark(pen, c):
    x, y = 820, 230
    col = c["anger"]
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        pen.arc(x + dx * 36, y + dy * 36, 26, 26,
                {(-1, -1): 0, (1, -1): 90, (-1, 1): 270, (1, 1): 180}[(dx, dy)],
                {(-1, -1): 90, (1, -1): 180, (-1, 1): 360, (1, 1): 270}[(dx, dy)], col, 15)


def _zzz(pen, c):
    col = c["line"]
    for i, (x, y, s) in enumerate(((800, 260, 40), (870, 180, 30), (920, 115, 22))):
        pen.line([(x - s, y - s), (x + s, y - s), (x - s, y + s), (x + s, y + s)], col, 11)


def _halo(img, pen, c):
    # 後光：放射状の光と輪
    cx, cy = 500, 480
    rays = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rp = _Pen(rays, pen.s)
    for i in range(16):
        a = math.radians(i * 360 / 16)
        a2 = math.radians(i * 360 / 16 + 7)
        rp.polygon([(cx, cy), (cx + 520 * math.cos(a), cy + 520 * math.sin(a)),
                    (cx + 520 * math.cos(a2), cy + 520 * math.sin(a2))], fill=c["halo"] + (110,))
    img.alpha_composite(rays)
    pen.circle(500, 480, 430, outline=c["halo"] + (230,), width=18)


def _sparkles(pen, c, pts):
    for x, y, r in pts:
        pen.polygon([(x, y - r), (x + r * 0.28, y - r * 0.28), (x + r, y), (x + r * 0.28, y + r * 0.28),
                     (x, y + r), (x - r * 0.28, y + r * 0.28), (x - r, y), (x - r * 0.28, y - r * 0.28)],
                    fill=c["halo"])


# ---- 公開API ------------------------------------------------------------------
def draw(expression: str = "normal", size: int = 512, talking: bool = False,
         blink: bool = False, palette: dict | None = None) -> Image.Image:
    """キャラを描いた RGBA 画像（正方形・背景透明）を返す。

    expression: EXPRESSIONS のいずれか
    talking   : 口を開ける（口パク用）
    blink     : 目を閉じる（まばたき用）
    """
    if expression not in EXPRESSIONS:
        raise ValueError(f"unknown expression: {expression} (使えるのは {EXPRESSIONS})")
    c = dict(PALETTE)
    if palette:
        c.update(palette)

    px = size * SS
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    pen = _Pen(img, px / BASE)
    e = expression

    if e == "satori":
        _halo(img, pen, c)
    _body(img, pen, c)
    _collar(pen, c)

    # --- 目 ---
    if blink and e not in ("happy", "satori", "sleepy"):
        _eye_line(pen, c, EYE_L)
        _eye_line(pen, c, EYE_R)
    elif e in ("normal", "angry"):
        _eye_open(pen, c, EYE_L)
        _eye_open(pen, c, EYE_R)
    elif e == "happy":
        _eye_happy(pen, c, EYE_L)
        _eye_happy(pen, c, EYE_R)
    elif e == "surprised":
        _eye_surprised(pen, c, EYE_L)
        _eye_surprised(pen, c, EYE_R)
    elif e == "thinking":
        _eye_open(pen, c, EYE_L, (14, -14), (50, 60))
        _eye_open(pen, c, EYE_R, (14, -14), (50, 60))
    elif e == "sad":
        _eye_open(pen, c, EYE_L, (0, 10), (50, 60))
        _eye_open(pen, c, EYE_R, (0, 10), (50, 60))
    elif e == "wink":
        _eye_open(pen, c, EYE_L)
        _eye_happy(pen, c, EYE_R)
    elif e in ("sleepy", "satori"):
        _eye_calm(pen, c, EYE_L)
        _eye_calm(pen, c, EYE_R)
    elif e == "shy":
        _eye_open(pen, c, EYE_L, (-14, 8), (50, 60))
        _eye_open(pen, c, EYE_R, (-14, 8), (50, 60))

    # --- 口・ほっぺ・ひげ・眉・効果 ---
    _cheeks(pen, c, strong=(e in ("shy", "happy")))
    _whiskers(pen, c)
    _mouth(pen, c, open_=talking or e in ("happy", "surprised"), wide=(e == "surprised"))

    if e == "surprised":
        _brows(pen, c, "up")
    elif e == "sad":
        _brows(pen, c, "sad")
        _sweat(pen, c, EYE_L[0] - 34, 590, 20)   # 涙
    elif e == "angry":
        _brows(pen, c, "angry")
        _anger_mark(pen, c)
    elif e == "thinking":
        _brows(pen, c, "think")
        _question(pen, c)
    elif e == "sleepy":
        _zzz(pen, c)
    elif e == "shy":
        _sweat(pen, c, 820, 330, 24)
        for x in (258, 300, 692, 734):            # 赤面の斜線
            pen.line([(x, 572), (x + 18, 548)], c["anger"], 6)
    elif e in ("happy", "wink"):
        _sparkles(pen, c, [(110, 230, 40), (900, 330, 32)])
    elif e == "satori":
        _sparkles(pen, c, [(120, 200, 36), (890, 220, 44), (110, 760, 28)])

    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    expr = sys.argv[1] if len(sys.argv) > 1 else "normal"
    draw(expr, 800).save(f"mascot_{expr}.png")
