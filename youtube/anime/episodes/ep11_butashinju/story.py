"""ep11『豚に真珠』— とりかえっこした宝物（仕様は spec.md）。"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIME = HERE.parent.parent
sys.path[:0] = [str(ANIME), str(ANIME / "cast")]

import daylight as dl  # noqa: E402
import kit  # noqa: E402
import neko  # noqa: E402
from engine import Cam, Caption, Frame, Track, draw_captions, ease_in_out, lerp, pulse, seg  # noqa: E402

FPS = 30
SIZE = (1080, 1920)
DURATION = 38.5

M = dl.Meadow(1500)
G = M.ground_at
CAT_S, KURO_S = 150, 200
CAT_X, KURO_X = 380, 700
SWAP, SWAP_BACK = (8.8, 9.8), (25.0, 26.0)

CAM = Track([
    (0.0, (380, 1415, 2.9)), (3.8, (380, 1415, 2.9)),
    (5.2, (560, 1370, 1.6)), (12.8, (560, 1370, 1.6)),
    (13.8, (380, 1395, 2.1)), (17.8, (380, 1395, 2.1)),
    (18.8, (690, 1390, 2.1)), (22.8, (690, 1390, 2.1)),
    (23.8, (560, 1370, 1.6)), (28.8, (560, 1370, 1.6)),
    (31.0, (560, 1200, 1.1)), (38.5, (560, 1200, 1.1)),
])

CAPTIONS = [
    Caption(0.6, 4.0, "ことにゃんの宝物は、ことば帖。"),
    Caption(4.6, 8.2, "くろの宝物は、ぴかぴかの 真珠。"),
    Caption(8.6, 12.8, "「とりかえっこ しよう」"),
    Caption(13.6, 17.8, "ことにゃんには、\nころがる ただの玉。"),
    Caption(18.6, 22.8, "くろは、1ページで\nねむくなった。"),
    Caption(23.2, 25.4, "どっちも、相手の宝物の\nよさが わからない。"),
    Caption(25.6, 28.6, "やっぱり、自分の宝物が いちばん。"),
] + kit.ending(28.8, "豚に真珠", "―― 新約聖書『マタイによる福音書』7章6節", reading="ぶたに しんじゅ",
               after=["どんなに すばらしい宝物も、", "そのよさが わからなければ、", "ただの 玉ころ。"],
               after_t=32.6, end=37.7)


# ---------------------------------------------------------------- 動き
def pearl_roll_x(t):
    """13.4〜18 秒：ころがる真珠（左右に行ったり来たり）。"""
    u = t - 13.4
    return CAT_X - 40 + 130 * math.sin(u * 1.7)


def cat_state(t):
    x, g, sq = CAT_X, G(CAT_X), 1.0
    item = "book" if (t < SWAP[0] + 0.2 or t > SWAP_BACK[1] - 0.2) else None
    if t < 4.2:
        expr = "happy"
    elif t < 8.6:
        expr = "surprised" if t < 6.0 else "normal"
    elif t < 13.0:
        expr = "happy" if t < 10.5 else "thinking"
    elif t < 18.0:                                        # 真珠を追いかけて あそぶ
        px = pearl_roll_x(t)
        x = lerp(CAT_X, px + 70 * (1 if math.cos((t - 13.4) * 1.7) < 0 else -1) * 0.5, seg(t, 13.0, 13.6))
        g = G(x) - abs(math.sin(t * 7)) * 14 * seg(t, 13.4, 13.8)
        expr = "happy" if (t % 1.4) < 0.9 else "wink"
    elif t < 23.0:
        x = CAT_X
        expr = "happy"
    elif t < 25.0:
        expr = "surprised" if t < 23.8 else "thinking"
    else:
        expr = "happy" if t < 30 else "calm"
    return dict(x=x, g=g, sq=sq, expr=expr, item=item)


def kuro_state(t):
    x, g, sq = kit.walk(t, 3.8, 5.6, 1150, KURO_X, G, bounce=5, steps_per_sec=3)
    item = "book" if SWAP[1] - 0.2 < t < SWAP_BACK[0] + 0.2 else None
    if t < 8.6:
        expr = "shy" if t > 6.0 else "blank"
    elif t < 18.4:
        expr = "blank"
    elif t < 23.0:                                        # 1ページで ねむくなる
        expr = "blank" if t < 19.6 else ("sleepy" if t < 22.6 else "surprised")
        sq = 1.0 - 0.03 * math.sin(t * 2.5) * (t > 19.6)
    elif t < 25.0:
        expr = "surprised" if t < 23.8 else "shy"
    else:
        expr = "happy" if t < 30 else "calm"
    return dict(x=x, g=g, sq=sq, expr=expr, item=item, flip=True)


def pearl_pos(t, cs, ks):
    """真珠の位置（x, y, 光の強さ）。"""
    held_kuro = (ks["x"] - KURO_S * 0.18, ks["g"] - KURO_S * 0.1)
    held_cat = (cs["x"] + CAT_S * 0.02, cs["g"] - CAT_S * 0.18)
    if t < SWAP[0]:
        return held_kuro[0], held_kuro[1], 1.0
    if t < SWAP[1]:
        u = seg(t, *SWAP, ease_in_out)
        return lerp(held_kuro[0], held_cat[0], u), lerp(held_kuro[1], held_cat[1], u) - 120 * math.sin(math.pi * u), 1.0
    if t < 13.4:
        return held_cat[0], held_cat[1], 0.8
    if t < 18.0:
        return pearl_roll_x(t), G(pearl_roll_x(t)) - 16, 0.6
    if t < SWAP_BACK[0]:
        x = CAT_X - 40 + 130 * math.sin(4.6 * 1.7)
        return x, G(x) - 16, 0.6
    u = seg(t, *SWAP_BACK, ease_in_out)
    x0 = CAT_X - 40 + 130 * math.sin(4.6 * 1.7)
    return lerp(x0, held_kuro[0], u), lerp(G(x0) - 16, held_kuro[1], u) - 140 * math.sin(math.pi * u), 1.0


def book_flight(t, cs, ks):
    """とりかえっこ／もどす瞬間に、ことば帖が飛ぶ。"""
    for (a, b), (fx, fy), (tx, ty) in (
            (SWAP, (cs["x"], cs["g"] - CAT_S * 0.15), (ks["x"], ks["g"] - KURO_S * 0.15)),
            (SWAP_BACK, (ks["x"], ks["g"] - KURO_S * 0.15), (cs["x"], cs["g"] - CAT_S * 0.15))):
        if a + 0.2 <= t <= b - 0.2:
            u = seg(t, a + 0.2, b - 0.2, ease_in_out)
            return lerp(fx, tx, u), lerp(fy, ty, u) - 150 * math.sin(math.pi * u), t * 14
    return None


def pearl(cv, ev, x, y, r, glow, t):
    ev.glow(x, y, r * 3, (255, 240, 250), strength=0.28 * glow)
    cv.circle(x, y + 2, r, (190, 180, 200))
    cv.circle(x, y, r, (246, 240, 250))
    cv.circle(x + r * 0.15, y + r * 0.2, r * 0.75, (232, 222, 240))
    cv.circle(x - r * 0.35, y - r * 0.35, r * 0.3, (255, 255, 255))
    if glow > 0.5:
        k = 0.5 + 0.5 * math.sin(t * 5)
        ev.glow(x + r * 1.3, y - r * 1.2, r * 0.8, (255, 250, 220), strength=k * 0.8)


def render(t):
    th = dl.THEMES["day"]
    cx, cy, z = CAM(t)
    fr = Frame(SIZE, Cam(cx, cy, z))
    fr.light_cap = 1.25
    fr.fade = seg(t, 37.7, 38.5)

    dl.sky(fr, th)
    dl.sun(fr, 850, 420)
    dl.clouds(fr, t, th)
    dl.trees(fr, t, th)
    bv, ev = fr.base(), fr.emit()
    M.draw(bv, t, th)

    cs, ks = cat_state(t), kuro_state(t)
    if ks["x"] < 1250:
        neko.shadow(bv, ks["x"], G(ks["x"]), KURO_S, alpha=60)
        neko.draw(fr, ks["x"], ks["g"], KURO_S, ks["expr"], palette="kuro", item=ks["item"], squash=ks["sq"],
                  flip=True)
    neko.shadow(bv, cs["x"], G(cs["x"]), CAT_S, alpha=60)
    neko.draw(fr, cs["x"], cs["g"], CAT_S, cs["expr"], item=cs["item"], squash=cs["sq"])

    px, py, gl = pearl_pos(t, cs, ks)
    if ks["x"] < 1250:
        pearl(bv, ev, px, py, 15, gl, t)
    bf = book_flight(t, cs, ks)
    if bf:
        dl.flying_book(bv, bf[0], bf[1], 36, bf[2], 0)

    dl.grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
