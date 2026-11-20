"""マスコットキャラ「ことにゃん」（三毛猫）の描画モジュール。

デザインの考え方は character/DESIGN_PRINCIPLES.md（親しまれるキャラの条件）。
  ・おもち形のシルエット（頭と体が一体）・角のない形
  ・点目＋ω口のシンプルな顔（見る人が気持ちを重ねられる）
  ・くすみカラー3色＋線の色
  ・少しゆらぐ手描き風の線
  ・しるし：左耳が茶・右耳が黒の三毛／青い「ことば帖」

外部の画像素材を使わず Pillow の図形だけで描くので、どのサイズでもくっきり出力できる。
座標は 1000x1000 の設計キャンバス上の値。4倍で描いて縮小（なめらかな線）。
"""
from __future__ import annotations

import math
from PIL import Image, ImageChops, ImageDraw

# ---- カラーパレット（グッズ化のときもこの値を使う） -------------------------
PALETTE = {
    "fur": (255, 250, 242),       # クリーム白
    "patch_a": (236, 166, 112),   # くすみオレンジ
    "patch_b": (96, 86, 88),      # チャコール
    "line": (104, 82, 74),        # 線（あたたかい茶）
    "ear_in": (247, 200, 192),
    "eye": (54, 46, 46),
    "cheek": (248, 168, 160),
    "mouth_in": (226, 120, 120),
    "book": (126, 158, 182),      # ことば帖（くすみブルー）
    "book_dark": (96, 124, 148),
    "page": (252, 246, 232),
    "eye_white": (255, 255, 255),
    "tear": (140, 196, 236),
    "halo": (255, 220, 130),
    "anger": (232, 112, 100),
    "bubble": (200, 228, 246),
}

SS = 4          # スーパーサンプリング倍率
BASE = 1000     # 設計キャンバスのサイズ
LW = 12         # 線の太さ

EXPRESSIONS = [
    "normal", "happy", "surprised", "thinking", "sad",
    "angry", "wink", "sleepy", "satori", "shy", "blank", "pien",
]

EXPRESSION_LABELS = {
    "normal": "ふつう", "happy": "にっこり", "surprised": "びっくり",
    "thinking": "考え中", "sad": "しょんぼり", "angry": "ぷんすか",
    "wink": "ウインク", "sleepy": "ねむい", "satori": "悟り", "shy": "てれ",
    "blank": "スン…", "pien": "ぴえん",
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


# ---- 形 -----------------------------------------------------------------------
CX, CY = 500, 615            # おもちの中心
RX, RY_TOP, RY_BOT = 350, 255, 270     # 上を低くして、耳と顔を近づける
EYE_L = (390, 585)
EYE_R = (610, 585)
MOUTH = (500, 637)
EAR_DY = 95                  # 耳を下げる量


def _wobble(pts, amp=2.2, seed=0.0):
    """手描き風に線をすこしゆらす（毎回同じ形になるよう決まった揺れ）。"""
    out = []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a = i / max(1, n) * 2 * math.pi
        d = amp * (math.sin(a * 7 + seed) + 0.6 * math.sin(a * 13 + seed * 2.3))
        out.append((x + d, y + d * 0.7))
    return out


def _mochi_pts(n=160):
    """おもち形：上は丸く、下は少し平たい超楕円。"""
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        c, s = math.cos(th), math.sin(th)
        ex = 2 / 2.25
        ey = 2 / (2.2 if s < 0 else 3.0)
        ry = RY_TOP if s < 0 else RY_BOT
        pts.append((CX + RX * math.copysign(abs(c) ** ex, c), CY + ry * math.copysign(abs(s) ** ey, s)))
    return pts


def _outline(pen, pts, c, closed=True, width=LW, seed=0.0):
    p = _wobble(pts, seed=seed)
    if closed:
        p = p + p[:2]
    pen.line(p, c["line"], width)


def _qbez(p0, p1, p2, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def _ear_pts(sx, scale=1.0):
    X = lambda v: 500 + sx * v  # noqa: E731
    return (_qbez((X(325), 330 + EAR_DY), (X(335), 200 + EAR_DY), (X(292), 170 + EAR_DY))
            + _qbez((X(292), 170 + EAR_DY), (X(270), 152 + EAR_DY), (X(240), 172 + EAR_DY))
            + _qbez((X(240), 172 + EAR_DY), (X(190), 205 + EAR_DY), (X(150), 290 + EAR_DY)))


def _ear_inner(sx):
    X = lambda v: 500 + sx * v  # noqa: E731
    return (_qbez((X(292), 310 + EAR_DY), (X(300), 222 + EAR_DY), (X(278), 205 + EAR_DY))
            + _qbez((X(278), 205 + EAR_DY), (X(262), 194 + EAR_DY), (X(246), 210 + EAR_DY))
            + _qbez((X(246), 210 + EAR_DY), (X(212), 240 + EAR_DY), (X(196), 300 + EAR_DY)))


def _tail(pen, c, t_wag=0.0):
    pts = _qbez((780, 830), (960, 860), (905, 690), 20)
    pts += _qbez((905, 690), (880, 610 + t_wag), (835, 650), 10)[1:]
    pen.line(pts, c["line"], 62)
    pen.line(pts, c["patch_a"], 62 - LW * 2)
    pen.line(pts[-8:], c["patch_b"], 62 - LW * 2)


def _body(img, pen, c):
    _tail(pen, c)
    # 耳（体の後ろ）
    for sx, fill in ((-1, c["patch_a"]), (1, c["patch_b"])):
        ear = _ear_pts(sx)
        pen.polygon(ear, fill=fill)
        _outline(pen, ear, c, closed=False, seed=sx)
        pen.polygon(_ear_inner(sx), fill=c["ear_in"])
    # 足（体の後ろから、ぽっちり2つ）
    for x in (405, 595):
        pen.ellipse(x, 884, 52, 26, fill=c["fur"], outline=c["line"], width=LW - 1)
    # おもちの体（模様は体の形で切り抜く）
    shape = _mochi_pts()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lp = type(pen)(layer, pen.s)
    lp.polygon(shape, fill=c["fur"])
    pat = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pp = type(pen)(pat, pen.s)
    pp.ellipse(250, 420, 200, 140, fill=c["patch_a"])      # 左耳から続く茶
    pp.ellipse(740, 385, 120, 75, fill=c["patch_b"])       # 右上の黒
    pp.ellipse(805, 790, 115, 100, fill=c["patch_a"])      # 右下の茶
    pat.putalpha(ImageChops.multiply(pat.getchannel("A"), layer.getchannel("A")))
    layer.alpha_composite(pat)
    img.alpha_composite(layer)
    _outline(pen, shape, c, seed=1.3)


def _book(pen, c):
    """ことば帖（両手で持つ小さな和綴じ本）。"""
    x0, y0, x1, y1 = 405, 690, 595, 845
    pen.polygon([(x0 - 6, y0 + 8), (x1 + 6, y0 + 8), (x1 + 6, y1 + 6), (x0 - 6, y1 + 6)], fill=c["page"])
    pen.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=c["book"])
    _outline(pen, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], c, width=9, seed=4)
    for yy in (725, 765, 805):                         # 和綴じの糸
        pen.line([(x0 + 18, yy), (x0 + 34, yy)], c["page"], 6)
    pen.polygon([(510, y0 + 26), (566, y0 + 26), (566, y0 + 112), (510, y0 + 112)], fill=c["page"])  # 題箋
    for k, ln in ((0, 30), (1, 30), (2, 18)):
        pen.line([(522, y0 + 48 + k * 22), (522 + ln, y0 + 48 + k * 22)], c["book_dark"], 5)
    # 前足（本のふちを持つ・ぽっちり）
    for x in (408, 592):
        pen.ellipse(x, 760, 34, 30, fill=c["fur"], outline=c["line"], width=9)


def _cheeks(pen, c, strong=False):
    a = 235 if strong else 175
    for x in (318, 682):
        pen.ellipse(x, 645, 46 if strong else 40, 24, fill=c["cheek"] + (a,))


def _dot_eye(pen, c, center, look=(0, 0), r=(27, 35), shine=True):
    cx, cy = center[0] + look[0], center[1] + look[1]
    pen.ellipse(cx, cy, r[0], r[1], fill=c["eye"])
    if shine:
        pen.circle(cx - r[0] * 0.25, cy - r[1] * 0.35, r[0] * 0.32, fill=(255, 255, 255))


def _pien_eye(pen, c, center):
    """うるうる（ぴえん）：大きな黒目＋大きなハイライト＋下に涙。"""
    cx, cy = center
    pen.ellipse(cx, cy, 40, 46, fill=c["eye"])
    pen.ellipse(cx - 12, cy - 15, 15, 16, fill=(255, 255, 255))
    pen.circle(cx + 14, cy + 10, 8, fill=(255, 255, 255))
    pen.circle(cx - 4, cy + 22, 5, fill=(255, 255, 255))
    pen.ellipse(cx, cy + 38, 38, 12, fill=c["tear"] + (220,))


def _eye_happy(pen, c, center):     # ∩
    pen.arc(center[0], center[1] + 14, 33, 28, 200, 340, c["eye"], 14)


def _eye_calm(pen, c, center):      # ∪
    pen.arc(center[0], center[1] - 8, 30, 20, 20, 160, c["eye"], 12)


def _eye_line(pen, c, center, w=28):  # ー
    pen.line([(center[0] - w, center[1]), (center[0] + w, center[1])], c["eye"], 12)


def _eye_round(pen, c, center):     # びっくり：白い丸に点
    pen.circle(center[0], center[1], 36, fill=c["eye_white"])
    pen.circle(center[0], center[1], 36, outline=c["eye"], width=8)
    pen.circle(center[0], center[1], 11, fill=c["eye"])


def _eye_angry(pen, c, center, side):
    cx, cy = center
    pen.line([(cx - 26 * side, cy - 18), (cx + 26 * side, cy + 6)], c["eye"], 13)
    pen.ellipse(cx, cy + 12, 14, 16, fill=c["eye"])


def _mouth(pen, c, kind="w", open_=False):
    x, y = MOUTH
    if open_:
        pen.ellipse(x, y + 14, 17, 15, fill=c["mouth_in"])
        pen.arc(x, y + 14, 17, 15, 0, 360, c["line"], 6)
    if kind == "w":
        pen.arc(x - 14, y, 14, 11, 15, 165, c["line"], 7)
        pen.arc(x + 14, y, 14, 11, 15, 165, c["line"], 7)
    elif kind == "flat":
        pen.line([(x - 14, y + 6), (x + 14, y + 6)], c["line"], 7)
    elif kind == "wobble":
        pen.line([(x - 24, y + 8), (x - 12, y), (x, y + 8), (x + 12, y), (x + 24, y + 8)], c["line"], 6)
    elif kind == "o":
        pen.ellipse(x, y + 12, 13, 16, fill=c["mouth_in"])
        pen.arc(x, y + 12, 13, 16, 0, 360, c["line"], 6)
    elif kind == "puff":
        pen.arc(x, y + 14, 18, 10, 200, 340, c["line"], 7)


def _snot_bubble(pen, c):
    """鼻ちょうちん（すぐ寝る、のしるし）。"""
    pen.circle(548, 625, 44, fill=c["bubble"] + (170,))
    pen.arc(548, 625, 44, 44, 0, 360, c["line"] + (160,), 5)
    pen.circle(534, 610, 9, fill=(255, 255, 255, 220))


def _sweat(pen, c, x, y, r=22):
    pen.circle(x, y, r, fill=c["tear"])
    pen.polygon([(x - r * 0.95, y - r * 0.3), (x + r * 0.95, y - r * 0.3), (x, y - r * 2.4)], fill=c["tear"])


def _question(pen, c):
    col = c["line"]
    pen.arc(905, 230, 44, 44, 180, 400, col, 18)
    pen.line([(939, 259), (905, 296), (905, 322)], col, 18)
    pen.circle(905, 362, 12, fill=col)


def _anger_mark(pen, c):
    x, y = 880, 300
    col = c["anger"]
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        pen.arc(x + dx * 36, y + dy * 36, 26, 26,
                {(-1, -1): 0, (1, -1): 90, (-1, 1): 270, (1, 1): 180}[(dx, dy)],
                {(-1, -1): 90, (1, -1): 180, (-1, 1): 360, (1, 1): 270}[(dx, dy)], col, 15)


def _zzz(pen, c):
    col = c["line"]
    for i, (x, y, s) in enumerate(((860, 330, 34), (915, 250, 26), (955, 190, 19))):
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
         blink: bool = False, palette: dict | None = None, item: str | None = None) -> Image.Image:
    """キャラを描いた RGBA 画像（正方形・背景透明）を返す。

    expression: EXPRESSIONS のいずれか
    talking   : 口を開ける（口パク用）
    blink     : 目を閉じる（まばたき用）
    item      : "book" で ことば帖 を持つ
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
    if item == "book":
        _book(pen, c)

    # --- ほっぺ（目より先に） ---
    _cheeks(pen, c, strong=e in ("shy", "happy", "pien"))
    if e == "blank":
        pass

    # --- 目 ---
    L, R = EYE_L, EYE_R
    if blink and e not in ("happy", "satori", "sleepy", "pien"):
        _eye_calm(pen, c, L)
        _eye_calm(pen, c, R)
    elif e in ("normal", "sad"):
        look = (0, 6) if e == "sad" else (0, 0)
        _dot_eye(pen, c, L, look)
        _dot_eye(pen, c, R, look)
    elif e == "happy":
        _eye_happy(pen, c, L)
        _eye_happy(pen, c, R)
    elif e == "surprised":
        _eye_round(pen, c, L)
        _eye_round(pen, c, R)
    elif e == "thinking":
        _dot_eye(pen, c, L, (12, -10))
        _dot_eye(pen, c, R, (12, -10))
    elif e == "angry":
        _eye_angry(pen, c, L, 1)
        _eye_angry(pen, c, R, -1)
    elif e == "wink":
        _dot_eye(pen, c, L)
        _eye_happy(pen, c, R)
    elif e == "sleepy":
        _eye_line(pen, c, L)
        _eye_line(pen, c, R)
    elif e == "satori":
        _eye_calm(pen, c, L)
        _eye_calm(pen, c, R)
    elif e == "shy":
        _dot_eye(pen, c, L, (-8, 8))
        _dot_eye(pen, c, R, (-8, 8))
    elif e == "blank":
        _dot_eye(pen, c, L, r=(10, 12), shine=False)
        _dot_eye(pen, c, R, r=(10, 12), shine=False)
    elif e == "pien":
        _pien_eye(pen, c, L)
        _pien_eye(pen, c, R)

    # --- 口 ---
    kind = {"surprised": "o", "sad": "wobble", "pien": "wobble", "blank": "flat", "angry": "puff",
            "thinking": "flat"}.get(e, "w")
    _mouth(pen, c, kind, open_=(talking or e == "happy") and kind == "w")

    # --- 効果 ---
    if e == "sad":
        _sweat(pen, c, EYE_L[0] - 30, 665, 18)
    elif e == "angry":
        _anger_mark(pen, c)
        for x in (300, 700):                      # ぷくっとふくらんだほっぺ
            pen.ellipse(x, 645, 50, 32, fill=c["cheek"] + (230,))
    elif e == "thinking":
        _question(pen, c)
    elif e == "sleepy":
        _snot_bubble(pen, c)
        _zzz(pen, c)
    elif e == "shy":
        _sweat(pen, c, 805, 460, 22)
        for x in (296, 336, 662, 702):            # 赤面の斜線
            pen.line([(x, 659), (x + 16, 635)], c["anger"], 6)
    elif e in ("happy", "wink"):
        _sparkles(pen, c, [(130, 300, 38), (880, 360, 30)])
    elif e == "satori":
        _sparkles(pen, c, [(120, 220, 34), (890, 250, 42), (110, 780, 26)])
    elif e == "blank":
        for x in (380, 620):                       # 縦線（スン…）
            pen.line([(x, 470), (x, 515)], c["line"] + (120,), 5)

    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    expr = sys.argv[1] if len(sys.argv) > 1 else "normal"
    draw(expr, 800).save(f"mascot_{expr}.png")
