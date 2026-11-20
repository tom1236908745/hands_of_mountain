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
    "line": (76, 56, 50),         # 輪郭線
    "eye": (52, 40, 36),
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
LW = 13         # 輪郭線の太さ

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
EYE_L = (385, 445)
EYE_R = (615, 445)
HEAD = (500, 420, 330, 255)      # cx, cy, rx, ry


def _tail(pen, c):
    # 体の後ろから右上へ伸びるしっぽ（輪郭→茶→先っぽ黒）
    # 2次ベジェ曲線：体の右下（体に隠れる）→ 右へふくらんで → 上へ
    p0, p1, p2 = (600, 880), (990, 900), (880, 450)
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    pen.line(pts, c["line"], 82)
    pen.line(pts, c["patch_a"], 82 - LW * 2)
    pen.line(pts[-8:], c["patch_b"], 82 - LW * 2)


def _ear(pen, c, side):
    sx = -1 if side == "L" else 1
    outer = [(500 + sx * 300, 330), (500 + sx * 285, 95), (500 + sx * 120, 200)]
    inner = [(500 + sx * 268, 285), (500 + sx * 268, 150), (500 + sx * 165, 215)]
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
    pen.ellipse(500, 735, 255, 215, fill=c["fur"], outline=c["line"], width=LW)
    pen.ellipse(330, 720, 70, 95, fill=c["patch_a"])     # 体の茶ぶち
    pen.ellipse(500, 735, 255, 215, outline=c["line"], width=LW)
    # 前足
    for x in (420, 580):
        pen.ellipse(x, 905, 68, 52, fill=c["fur"], outline=c["line"], width=LW)
        for dx in (-18, 18):
            pen.line([(x + dx, 878), (x + dx, 900)], c["line"], 8)
    _ear(pen, c, "L")
    _ear(pen, c, "R")
    _head(img, pen, c)


def _collar(pen, c, with_bell=True):
    pen.arc(500, 560, 215, 105, 30, 150, c["line"], 46)
    pen.arc(500, 560, 215, 105, 32, 148, c["collar"], 30)
    if with_bell:
        pen.circle(500, 690, 40, fill=c["bell"], outline=c["line"], width=9)
        pen.line([(465, 684), (535, 684)], c["bell_dark"], 7)
        pen.circle(500, 705, 8, fill=c["bell_dark"])
        pen.line([(500, 708), (500, 728)], c["bell_dark"], 6)
        pen.circle(486, 672, 9, fill=(255, 255, 255, 220))


def _whiskers(pen, c):
    for side in (-1, 1):
        for dy, ang in ((-12, -10), (14, 4)):
            x0 = 500 + side * 205
            pen.line([(x0, 530 + dy), (x0 + side * 105, 530 + dy + ang)], c["line"], 7)


def _cheeks(pen, c, strong=False):
    a = 235 if strong else 160
    for x in (300, 700):
        pen.ellipse(x, 525, 50 if strong else 44, 27, fill=c["cheek"] + (a,))


def _eye_open(pen, c, center, look=(0, 0), r=(40, 50)):
    cx, cy = center[0] + look[0], center[1] + look[1]
    pen.ellipse(cx, cy, r[0], r[1], fill=c["eye"])
    pen.circle(cx - r[0] * 0.3, cy - r[1] * 0.35, r[0] * 0.38, fill=(255, 255, 255))
    pen.circle(cx + r[0] * 0.35, cy + r[1] * 0.35, r[0] * 0.16, fill=(255, 255, 255))


def _eye_surprised(pen, c, center):
    pen.circle(center[0], center[1], 52, fill=c["eye_white"], outline=c["eye"], width=10)
    pen.circle(center[0], center[1], 18, fill=c["eye"])


def _eye_happy(pen, c, center):     # ∩
    pen.arc(center[0], center[1] + 22, 44, 38, 200, 340, c["eye"], 16)


def _eye_calm(pen, c, center):      # ∪
    pen.arc(center[0], center[1] - 12, 44, 28, 20, 160, c["eye"], 15)


def _eye_line(pen, c, center):      # ー
    pen.line([(center[0] - 42, center[1] + 5), (center[0] + 42, center[1] + 5)], c["eye"], 14)


def _mouth(pen, c, open_=False, wide=False):
    # 鼻
    pen.polygon([(478, 497), (522, 497), (500, 520)], fill=c["nose"], outline=c["line"], width=5)
    if open_:
        h = 52 if wide else 36
        pen.ellipse(500, 548 + h / 3, 30 if not wide else 26, h / 2 + 6, fill=c["mouth_in"],
                    outline=c["line"], width=7)
    # ω
    pen.arc(477, 530, 23, 18, 10, 170, c["line"], 8)
    pen.arc(523, 530, 23, 18, 10, 170, c["line"], 8)


def _brows(pen, c, kind):
    w = 12
    lx, rx = EYE_L[0], EYE_R[0]
    if kind == "up":
        pen.arc(lx, 370, 45, 20, 200, 340, c["line"], w)
        pen.arc(rx, 370, 45, 20, 200, 340, c["line"], w)
    elif kind == "sad":
        pen.line([(lx - 45, 380), (lx + 40, 360)], c["line"], w)
        pen.line([(rx + 45, 380), (rx - 40, 360)], c["line"], w)
    elif kind == "angry":
        pen.line([(lx - 45, 355), (lx + 45, 385)], c["line"], w)
        pen.line([(rx + 45, 355), (rx - 45, 385)], c["line"], w)
    elif kind == "think":
        pen.line([(lx - 40, 370), (lx + 40, 365)], c["line"], w)
        pen.line([(rx - 40, 352), (rx + 45, 372)], c["line"], w)


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
        _eye_open(pen, c, EYE_L, (14, -14), (36, 44))
        _eye_open(pen, c, EYE_R, (14, -14), (36, 44))
    elif e == "sad":
        _eye_open(pen, c, EYE_L, (0, 10), (36, 44))
        _eye_open(pen, c, EYE_R, (0, 10), (36, 44))
    elif e == "wink":
        _eye_open(pen, c, EYE_L)
        _eye_happy(pen, c, EYE_R)
    elif e in ("sleepy", "satori"):
        _eye_calm(pen, c, EYE_L)
        _eye_calm(pen, c, EYE_R)
    elif e == "shy":
        _eye_open(pen, c, EYE_L, (-14, 8), (36, 44))
        _eye_open(pen, c, EYE_R, (-14, 8), (36, 44))

    # --- 口・ほっぺ・ひげ・眉・効果 ---
    _cheeks(pen, c, strong=(e in ("shy", "happy")))
    _whiskers(pen, c)
    _mouth(pen, c, open_=talking or e in ("happy", "surprised"), wide=(e == "surprised"))

    if e == "surprised":
        _brows(pen, c, "up")
    elif e == "sad":
        _brows(pen, c, "sad")
        _sweat(pen, c, EYE_L[0] - 30, 540, 20)   # 涙
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
        for x in (270, 315, 685, 730):            # 赤面の斜線
            pen.line([(x, 535), (x + 20, 510)], c["anger"], 7)
    elif e in ("happy", "wink"):
        _sparkles(pen, c, [(110, 230, 40), (900, 330, 32)])
    elif e == "satori":
        _sparkles(pen, c, [(120, 200, 36), (890, 220, 44), (110, 760, 28)])

    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    expr = sys.argv[1] if len(sys.argv) > 1 else "normal"
    draw(expr, 800).save(f"mascot_{expr}.png")
