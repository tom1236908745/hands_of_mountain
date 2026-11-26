"""マスコット（tools/mascot.py の猫）をアニメに出すためのラッパー。

mascot.draw() はラスター画像を返すので、カメラのズームに合わせた大きさで描いて
フレームの base 層に貼る（ライティングも受ける）。
  ・ground 基準：足の裏がワールド座標 (x, ground) に来る
  ・squash   ：1 未満でぺたんと縮み（着地）、1 より大きいと伸びる（ジャンプ）
  ・同じ大きさ・表情はキャッシュする
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import mascot  # noqa: E402

FEET = 0.91     # キャンバス上の足の裏の位置（上からの割合）
KITTEN_GREY = dict(fur=(250, 250, 252), patch_a=(178, 180, 192), patch_b=(112, 114, 126))
MOTHER_GREY = dict(fur=(246, 246, 248), patch_a=(158, 160, 172), patch_b=(96, 98, 110))
KURO = dict(fur=(78, 72, 80), patch_a=(62, 58, 66), patch_b=(46, 42, 50), eye=(250, 214, 110),
            line=(40, 34, 38), ear_in=(196, 150, 150), cheek=(230, 140, 140))     # 大きな黒ねこ「くろ」


@lru_cache(maxsize=48)
def _sprite(expr, px, item, lantern_q, palette_key, blink, flap_q, mirror=False):
    palette = {"kitten": KITTEN_GREY, "mother": MOTHER_GREY, "kuro": KURO}.get(palette_key)
    ss = 2 if px < 500 else 1
    return mascot.draw(expr, px, item=item, lantern=lantern_q / 10, palette=palette, ss=ss, blink=blink,
                       flap=flap_q / 4, mirror=mirror)


def draw(fr, x, ground, size, expr="normal", *, item=None, lantern=0.0, palette=None, flip=False,
         squash=1.0, rot=0.0, alpha=1.0, blink=False, flap=0.0):
    """猫を貼る。戻り値は 光の中心（ちょうちん／着ぐるみのお尻）のワールド座標。"""
    view = fr.view()
    px = max(16, int(round(size * view.zoom / 8)) * 8)       # 8px 刻みでキャッシュ
    img = _sprite(expr, px, item, int(round(lantern * 10)), palette, blink, int(round(flap * 4)), bool(flip))
    w = int(px * (1 + (1 - squash) * 0.6))
    h = int(px * squash)
    if (w, h) != (px, px):
        img = img.resize((max(1, w), max(1, h)), Image.BILINEAR)
    if rot:
        img = img.rotate(-rot, resample=Image.BICUBIC, expand=False)
    if alpha < 1:
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    sx, sy = view.pt(x, ground)
    left = int(sx - img.width / 2)
    top = int(sy - img.height * FEET)
    fr.base_img.paste(img, (left, top), img)

    lx, ly = mascot.FIREFLY_LIGHT if item == "firefly" else mascot.LANTERN_CENTER
    k = size / 1000
    wx = x + (lx - 500) * k * (-1 if flip else 1) * (1 + (1 - squash) * 0.6)
    wy = ground - size * squash * FEET + ly * k * squash
    return wx, wy


def shadow(cv, x, ground, size, alpha=90):
    cv.ellipse(x, ground + size * 0.01, size * 0.33, size * 0.05, (0, 0, 0, alpha))
