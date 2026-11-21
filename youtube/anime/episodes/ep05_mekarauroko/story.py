"""ep05『目から鱗』— こわそうな黒ねこの葉っぱの傘（仕様は spec.md）。"""
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
from engine import Cam, Caption, Frame, Track, draw_captions, ease_out, lerp, pulse, seg  # noqa: E402

FPS = 30
SIZE = (1080, 1920)
DURATION = 36.0


class Hill(dl.Meadow):
    """右に小さな丘（くろの定位置）。"""

    def ground_at(self, x):
        return super().ground_at(x) - 95 * math.exp(-((x - 870) / 190) ** 2)


M = Hill(1500)
G = M.ground_at
CAT_S, KIT_S, KURO_S = 150, 100, 205
CAT_X, KIT_X, KURO_X0, KURO_X1 = 430, 300, 870, 590
UMB_S = 92

CAM = Track([
    (0.0, (600, 1400, 1.45)), (3.8, (600, 1400, 1.45)),
    (4.8, (850, 1320, 2.5)), (6.2, (850, 1320, 2.5)),
    (7.0, (390, 1450, 2.3)), (13.8, (390, 1450, 2.3)),
    (15.0, (560, 1420, 1.65)), (19.6, (520, 1420, 1.75)),
    (20.6, (440, 1395, 3.0)), (23.6, (440, 1395, 3.0)),
    (25.4, (560, 1380, 1.5)), (27.0, (560, 1380, 1.5)),
    (29.5, (560, 1150, 1.15)), (36.0, (560, 1150, 1.15)),
])

CAPTIONS = [
    Caption(0.5, 3.6, "丘の上の、大きな黒ねこ。"),
    Caption(4.2, 6.2, "いつも むすっとしていて、"),
    Caption(6.4, 8.6, "こわいねこだと 思っていた。"),
    Caption(9.4, 11.4, "とつぜんの 雨。"),
    Caption(11.6, 13.9, "ふたりとも、ずぶぬれ。"),
    Caption(15.2, 17.3, "黒ねこが だまって、"),
    Caption(17.4, 20.0, "葉っぱの傘を さしかけてくれた。"),
    Caption(20.6, 22.6, "そのとき、目から なにかが ポロリ。"),
    Caption(22.8, 25.6, "ほんとうは、やさしいねこだったんだ。"),
] + kit.ending(27.0, "目から鱗が\n落ちる", "―― 新約聖書『使徒言行録』9章18節", reading="めから うろこが おちる",
               after=["思いこみが ポロリと落ちると、", "ほんとうの姿が 見えてくる。"], after_t=31.4, end=35.1)


def rain_amount(t):
    return seg(t, 9.0, 10.0) * (1 - seg(t, 24.0, 25.5))


def theme(t):
    if t < 8.0:
        return dl.THEMES["day"]
    if t < 24.0:
        return dl.blend("day", "rain", seg(t, 8.0, 9.6))
    return dl.blend("rain", "day", seg(t, 24.0, 26.0))


def kuro_state(t):
    x, g, sq = kit.walk(t, 14.4, 17.0, KURO_X0, KURO_X1, G, bounce=6, steps_per_sec=3)
    expr = "blank"
    if 17.2 < t < 22.6:
        expr = "shy"
    elif t >= 22.6:
        expr = "calm"
    return dict(x=x, g=g, sq=sq, expr=expr, flip=t > 14.2)


def cat_state(t):
    x, g, sq, jit = CAT_X, G(CAT_X), 1.0, 0.0
    if t < 4.0:
        x, g, sq = kit.hop_path(t, (CAT_X, G(CAT_X)), [(1.0, (470, G(470))), (2.2, (CAT_X, G(CAT_X)))], height=40)
        expr = "happy"
    elif t < 8.4:
        expr = "normal" if t < 6.3 else "sad"
    elif t < 17.0:
        expr = "pien"
        jit = math.sin(t * 60) * 1.5 * seg(t, 10, 11)
    elif t < 22.6:
        expr = "surprised"
    elif t < 27.0:
        expr = "happy"
    else:
        expr = "calm"
    return dict(x=x + jit, g=g, sq=sq, expr=expr)


def kit_state(t):
    x, g, sq, jit = KIT_X, G(KIT_X), 1.0, 0.0
    if t < 4.0:
        x, g, sq = kit.hop_path(t, (KIT_X, G(KIT_X)), [(1.5, (260, G(260))), (2.7, (KIT_X, G(KIT_X)))], height=30)
        expr = "happy"
    elif t < 8.4:
        expr = "normal" if t < 6.3 else "pien"
    elif t < 17.0:
        expr = "pien"
        jit = math.sin(t * 70 + 1) * 1.2 * seg(t, 10, 11)
    elif t < 22.6:
        expr = "surprised"
    else:
        expr = "happy" if t < 27 else "calm"
    return dict(x=x + jit, g=g, sq=sq, expr=expr)


def umbrella(t, ks):
    """くろの持つ傘：柄の先の位置と傾き。17〜18秒で、ふたりの上へさしかける。"""
    k = seg(t, 17.0, 18.0)
    px = ks["x"] - KURO_S * 0.28 - 70 * k
    py = ks["g"] - KURO_S * 0.42
    return px, py, lerp(0, -24, k)


def scales(cv, ev, t, cs):
    """20.7〜22.4 秒：ことにゃんの目から うろこ がポロリ。"""
    if not 20.6 < t < 22.8:
        return
    for side, ex in ((-1, 390), (1, 610)):
        wx = cs["x"] + (ex - 500) / 1000 * CAT_S
        wy = cs["g"] - 0.91 * CAT_S + 0.585 * CAT_S
        ev.glow(wx, wy, 22, (230, 240, 255), strength=pulse(t, 20.7, 21.4, 0.2))
        for i in range(3):
            t0 = 20.75 + i * 0.18 + (0.08 if side > 0 else 0)
            u = (t - t0) / 1.1
            if 0 <= u <= 1:
                dl.scale_piece(cv, wx + side * (6 + 18 * u) + i * 3, wy + 8 + 90 * u * u, 9,
                               rot=side * 40 * u + i * 30, alpha=1 - u ** 3)


def render(t):
    th = theme(t)
    cx, cy, z = CAM(t)
    ra = rain_amount(t)
    fr = Frame(SIZE, Cam(cx, cy, z), ambient=lerp(1.0, 0.82, ra))
    fr.light_cap = 1.25
    fr.fade = seg(t, 35.1, 36.0)

    dl.sky(fr, th)
    dl.sun(fr, 830, 420, alpha=1 - seg(t, 7.5, 9.0) + seg(t, 25.0, 26.5))
    dl.rainbow(fr, seg(t, 25.3, 27.0), cx=560, cy=1450, r=820)
    dl.clouds(fr, t, th, alpha=0.95, dark=0.4 * ra)
    dl.trees(fr, t, th)
    bv, ev = fr.base(), fr.emit()
    M.draw(bv, t, th)

    ks = kuro_state(t)
    cs = cat_state(t)
    kt = kit_state(t)
    neko.shadow(bv, ks["x"], G(ks["x"]), KURO_S, alpha=60)
    neko.draw(fr, ks["x"], ks["g"], KURO_S, ks["expr"], palette="kuro", squash=ks["sq"], flip=ks["flip"])
    for st, size, pal in ((kt, KIT_S, "kitten"), (cs, CAT_S, None)):
        neko.shadow(bv, st["x"], G(st["x"]), size, alpha=60)
        neko.draw(fr, st["x"], st["g"], size, st["expr"], palette=pal, squash=st["sq"])
    shelter = None
    if t > 14.2:
        ux, uy, tilt = umbrella(t, ks)
        dl.leaf_umbrella(bv, ux, uy, UMB_S, tilt)
        if t > 17.6:
            shelter = (ux - 2.0 * UMB_S, ux + 0.9 * UMB_S, uy - 1.6 * UMB_S)
    scales(bv, ev, t, cs)
    dl.rain(fr, t, ra, shelter=shelter)

    dl.grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
