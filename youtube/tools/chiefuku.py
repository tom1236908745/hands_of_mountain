"""ちえふく（マスコットキャラ）の描画モジュール。

外部の画像素材を使わず、Pillow の図形だけで描くので
・どんなサイズでもくっきり出力できる（動画/LINEスタンプ/グッズ用の高解像度）
・表情を足したいときはこのファイルに関数を1つ足すだけ
という作りになっています。

座標はすべて 1000x1000 の「設計キャンバス」上の値で書き、
最後に指定サイズへ縮小します（4倍で描いて縮小＝アンチエイリアス）。
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw

# ---- カラーパレット（グッズ化のときもこの値を使う） -------------------------
PALETTE = {
    "body": (140, 98, 68),        # こげ茶の羽
    "body_dark": (108, 72, 48),   # 翼・耳羽
    "belly": (238, 214, 176),     # おなか
    "belly_mark": (196, 160, 118),
    "face": (252, 240, 216),      # 顔のハート形
    "eye_white": (255, 255, 255),
    "pupil": (40, 30, 26),
    "glasses": (196, 150, 52),    # 金の丸メガネ（トレードマーク）
    "beak": (240, 158, 52),
    "beak_dark": (196, 110, 30),
    "mouth_in": (170, 60, 50),
    "cheek": (246, 160, 150),
    "feet": (240, 158, 52),
    "line": (60, 42, 32),
    "tear": (120, 190, 240),
    "halo": (255, 214, 102),
    "anger": (230, 70, 60),
    "scarf": (196, 52, 52),       # 朱色の首巻き（寺社の朱をイメージ）
}

SS = 4          # スーパーサンプリング倍率
BASE = 1000     # 設計キャンバスのサイズ

EXPRESSIONS = [
    "normal",     # ふつう
    "happy",      # にっこり
    "surprised",  # びっくり
    "thinking",   # 考え中
    "sad",        # しょんぼり
    "angry",      # ぷんすか
    "wink",       # ウインク
    "sleepy",     # ねむい
    "satori",     # 悟り（オチ・まとめ用）
    "shy",        # てれ
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


def _rotated_ellipse(size, cx, cy, rx, ry, angle, fill, scale):
    """回転した楕円（翼など）を別レイヤーに描いて返す。"""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    w, h = int(rx * 2 * scale), int(ry * 2 * scale)
    e = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(e).ellipse((0, 0, w - 1, h - 1), fill=fill)
    e = e.rotate(angle, expand=True, resample=Image.BICUBIC)
    layer.paste(e, (int(cx * scale - e.width / 2), int(cy * scale - e.height / 2)), e)
    return layer


# ---- パーツ -------------------------------------------------------------------
EYE_L = (390, 440)
EYE_R = (610, 440)
EYE_R_WHITE = 88
GLASS_R = 112


def _body(img, pen, c):
    s = pen.s
    # 足
    for x in (420, 580):
        pen.ellipse(x, 925, 52, 26, fill=c["feet"])
    # 耳羽（つの）
    pen.polygon([(250, 330), (225, 175), (370, 265)], fill=c["body_dark"])
    pen.polygon([(750, 330), (775, 175), (630, 265)], fill=c["body_dark"])
    # 翼（胴体の後ろ）
    for cx, ang in ((215, -18), (785, 18)):
        layer = _rotated_ellipse(img.size, cx, 650, 80, 175, ang, c["body_dark"], s)
        img.alpha_composite(layer)
    # 胴体
    pen.ellipse(500, 590, 320, 340, fill=c["body"])
    # おなか
    pen.ellipse(500, 720, 205, 195, fill=c["belly"])
    for row, y in enumerate((690, 770, 850)):
        xs = (440, 560) if row != 1 else (400, 500, 600)
        for x in xs:
            pen.arc(x, y - 20, 26, 20, 20, 160, c["belly_mark"], 9)
    # 顔（ハート形の顔盤）
    pen.circle(EYE_L[0], EYE_L[1], 150, fill=c["face"])
    pen.circle(EYE_R[0], EYE_R[1], 150, fill=c["face"])
    pen.polygon([(262, 500), (738, 500), (500, 655)], fill=c["face"])
    pen.ellipse(500, 520, 210, 110, fill=c["face"])
    # 首巻き（朱）
    pen.arc(500, 560, 250, 110, 35, 145, c["scarf"], 34)
    pen.polygon([(560, 665), (612, 655), (630, 740), (590, 735)], fill=c["scarf"])


def _cheeks(pen, c, strong=False):
    a = 230 if strong else 150
    for x in (285, 715):
        pen.ellipse(x, 560, 50 if strong else 42, 26, fill=c["cheek"] + (a,))


def _eye_open(pen, c, center, look=(0, 0), pupil_r=50, white_r=EYE_R_WHITE):
    cx, cy = center
    pen.circle(cx, cy, white_r, fill=c["eye_white"])
    px, py = cx + look[0], cy + look[1]
    pen.circle(px, py, pupil_r, fill=c["pupil"])
    hr = max(9, pupil_r * 0.34)
    pen.circle(px - pupil_r * 0.35, py - pupil_r * 0.38, hr, fill=(255, 255, 255))
    pen.circle(px + pupil_r * 0.35, py + pupil_r * 0.32, hr * 0.45, fill=(255, 255, 255))


def _eye_white_only(pen, c, center):
    pen.circle(center[0], center[1], EYE_R_WHITE, fill=c["eye_white"])


def _eye_happy(pen, c, center):     # ∩
    _eye_white_only(pen, c, center)
    pen.arc(center[0], center[1] + 22, 46, 40, 200, 340, c["pupil"], 17)


def _eye_calm(pen, c, center):      # ∪（悟り・ねむい）
    _eye_white_only(pen, c, center)
    pen.arc(center[0], center[1] - 10, 46, 30, 20, 160, c["pupil"], 15)


def _eye_line(pen, c, center):      # ー（まばたき）
    _eye_white_only(pen, c, center)
    pen.line([(center[0] - 45, center[1] + 5), (center[0] + 45, center[1] + 5)], c["pupil"], 15)


def _glasses(pen, c):
    for cx, cy in (EYE_L, EYE_R):
        pen.circle(cx, cy, GLASS_R, outline=c["glasses"], width=15)
    # ブリッジ
    pen.arc(500, 430, 18, 16, 200, 340, c["glasses"], 13)
    # レンズの反射
    for cx, cy in (EYE_L, EYE_R):
        pen.arc(cx, cy, GLASS_R - 22, GLASS_R - 22, 200, 235, (255, 255, 255, 200), 9)


def _beak(pen, c, open_=False, wide=False):
    if not open_:
        pen.polygon([(455, 520), (545, 520), (500, 600)], fill=c["beak"])
        pen.polygon([(470, 520), (530, 520), (500, 545)], fill=c["beak_dark"])
        return
    h = 62 if wide else 44
    pen.polygon([(450, 512), (550, 512), (500, 548)], fill=c["beak"])
    pen.ellipse(500, 556 + h / 4, 40, h / 2 + 8, fill=c["mouth_in"])
    pen.polygon([(462, 560 + h / 3), (538, 560 + h / 3), (500, 590 + h / 2)], fill=c["beak"])


def _brows(pen, c, kind):
    w = 13
    if kind == "up":        # びっくり
        pen.arc(EYE_L[0], 300, 60, 25, 200, 340, c["line"], w)
        pen.arc(EYE_R[0], 300, 60, 25, 200, 340, c["line"], w)
    elif kind == "sad":     # ハの字
        pen.line([(320, 318), (440, 295)], c["line"], w)
        pen.line([(680, 318), (560, 295)], c["line"], w)
    elif kind == "angry":   # 逆ハの字
        pen.line([(320, 290), (450, 325)], c["line"], w)
        pen.line([(680, 290), (550, 325)], c["line"], w)
    elif kind == "think":
        pen.line([(330, 305), (450, 300)], c["line"], w)
        pen.line([(560, 285), (680, 310)], c["line"], w)


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
    """ちえふくを描いた RGBA 画像（正方形・背景透明）を返す。

    expression: EXPRESSIONS のいずれか
    talking   : くちばしを開ける（口パク用）
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

    if expression == "satori":
        _halo(img, pen, c)
    _body(img, pen, c)

    # --- 目 ---
    e = expression
    if blink and e not in ("happy", "satori", "sleepy"):
        _eye_line(pen, c, EYE_L)
        _eye_line(pen, c, EYE_R)
    elif e in ("normal", "angry"):
        _eye_open(pen, c, EYE_L, (6, 6))
        _eye_open(pen, c, EYE_R, (-6, 6))
    elif e == "happy":
        _eye_happy(pen, c, EYE_L)
        _eye_happy(pen, c, EYE_R)
    elif e == "surprised":
        _eye_open(pen, c, EYE_L, (0, 0), pupil_r=26, white_r=EYE_R_WHITE + 6)
        _eye_open(pen, c, EYE_R, (0, 0), pupil_r=26, white_r=EYE_R_WHITE + 6)
    elif e == "thinking":
        _eye_open(pen, c, EYE_L, (22, -28), pupil_r=44)
        _eye_open(pen, c, EYE_R, (22, -28), pupil_r=44)
    elif e == "sad":
        _eye_open(pen, c, EYE_L, (0, 22), pupil_r=46)
        _eye_open(pen, c, EYE_R, (0, 22), pupil_r=46)
    elif e == "wink":
        _eye_open(pen, c, EYE_L, (6, 6))
        _eye_happy(pen, c, EYE_R)
    elif e in ("sleepy", "satori"):
        _eye_calm(pen, c, EYE_L)
        _eye_calm(pen, c, EYE_R)
    elif e == "shy":
        _eye_open(pen, c, EYE_L, (-24, 18), pupil_r=46)
        _eye_open(pen, c, EYE_R, (-24, 18), pupil_r=46)

    _glasses(pen, c)

    # --- 口・ほっぺ・眉 ---
    open_ = talking or e in ("happy", "surprised")
    _beak(pen, c, open_=open_, wide=(e == "surprised"))
    _cheeks(pen, c, strong=(e in ("shy", "happy")))

    if e == "surprised":
        _brows(pen, c, "up")
    elif e == "sad":
        _brows(pen, c, "sad")
        _sweat(pen, c, EYE_L[0] - 20, 590, 20)   # 涙
    elif e == "angry":
        _brows(pen, c, "angry")
        _anger_mark(pen, c)
    elif e == "thinking":
        _brows(pen, c, "think")
        _question(pen, c)
    elif e == "sleepy":
        _zzz(pen, c)
    elif e == "shy":
        _sweat(pen, c, 790, 330, 24)
        for x in (255, 300, 700, 745):            # 赤面の斜線
            pen.line([(x, 545), (x + 20, 520)], c["anger"], 7)
    elif e == "happy" or e == "wink":
        _sparkles(pen, c, [(140, 230, 40), (870, 300, 32)])
    elif e == "satori":
        _sparkles(pen, c, [(130, 200, 36), (880, 220, 44), (120, 760, 28)])

    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    expr = sys.argv[1] if len(sys.argv) > 1 else "normal"
    draw(expr, 800).save(f"chiefuku_{expr}.png")
