"""ep09『情けは人の為ならず』— 葉っぱの傘が めぐってくる（仕様は spec.md）。"""
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
import snail  # noqa: E402  (ハート)
from engine import Cam, Caption, Frame, Track, draw_captions, ease_in_out, lerp, pulse, seg  # noqa: E402

FPS = 30
SIZE = (1080, 1920)
DURATION = 35.0

M = dl.Meadow(1500)
G = M.ground_at
CAT_S, KIT_S, MOM_S = 150, 100, 165
CAT_X = 420
KIT_X = 600
UMB_CAT, UMB_KIT, UMB_BIG = 78, 62, 160

CAM = Track([
    (0.0, (420, 1440, 2.0)), (3.2, (460, 1440, 2.15)), (9.4, (470, 1440, 2.15)),
    (10.6, (420, 1420, 2.8)), (14.6, (420, 1420, 2.8)),
    (16.0, (560, 1430, 1.8)), (21.6, (540, 1430, 1.9)),
    (23.6, (560, 1320, 1.35)), (25.6, (560, 1320, 1.35)),
    (28.2, (560, 1150, 1.1)), (35.0, (560, 1150, 1.1)),
])

CAPTIONS = [
    Caption(0.5, 3.4, "雨の日。ぬれている 子ねこがいた。"),
    Caption(3.8, 6.6, "ことにゃんは、傘を さしだした。"),
    Caption(7.0, 9.4, "子ねこは にっこり、帰っていった。"),
    Caption(10.2, 12.3, "かわりに、ことにゃんは ずぶぬれ。"),
    Caption(12.6, 14.4, "くしゅん。", size=50, y=0.36),
    Caption(15.2, 17.8, "すると、さっきの子ねこが"),
    Caption(17.9, 21.0, "お母さんと、\n大きな葉っぱを持って 戻ってきた。"),
    Caption(21.4, 25.0, "やさしさが、めぐって\nかえってきた。"),
] + kit.ending(25.6, "情けは\n人の為ならず", "―― ことわざ", reading="なさけは ひとの ためならず",
               after=["人への親切は、", "めぐりめぐって、", "自分に かえってくる。"], after_t=30.0, end=34.2)


def rain_amount(t):
    return seg(t, 0.0, 0.6) * (1 - seg(t, 22.6, 24.2))


def theme(t):
    if t < 22.6:
        return dl.THEMES["rain"]
    return dl.blend("rain", "day", seg(t, 22.6, 24.6))


def cat_state(t):
    x, g, sq = CAT_X, G(CAT_X), 1.0
    jit = 0.0
    if t < 3.6:
        expr = "normal" if t < 2.4 else "surprised"
    elif t < 7.0:
        expr = "happy"
    elif t < 10.0:
        expr = "happy" if t < 8.6 else "calm"
    elif t < 15.4:                                   # ずぶぬれ・くしゃみ
        expr = "pien"
        jit = math.sin(t * 60) * 1.5
        sq = 1.0 - 0.1 * pulse(t, 12.6, 12.95, 0.1) + 0.06 * pulse(t, 12.95, 13.2, 0.08)
        if 12.6 < t < 13.2:
            expr = "strain"
    elif t < 19.0:
        expr = "surprised"
    elif t < 26:
        expr = "happy"
    else:
        expr = "calm"
    return dict(x=x + jit, g=g, sq=sq, expr=expr)


def kit_state(t):
    """子ねこ：その場でぬれている → 傘をもらう → 右へ帰る → 母と戻ってくる。"""
    if t < 8.4:
        x, g, sq = KIT_X, G(KIT_X), 1.0
        expr = "pien" if t < 6.0 else "happy"
    elif t < 15.0:
        x, g, sq = kit.walk(t, 8.4, 10.6, KIT_X, 1300, G, bounce=10)
        expr = "happy"
    else:
        x, g, sq = kit.walk(t, 15.4, 18.0, 1300, 560, G, bounce=10)
        expr = "happy" if t < 26 else "calm"
    return dict(x=x, g=g, sq=sq, expr=expr)


def mom_state(t):
    x, g, sq = kit.walk(t, 15.6, 18.6, 1450, 720, G, bounce=6, steps_per_sec=3)
    expr = "normal" if t < 19.0 else ("happy" if t < 26 else "calm")
    return dict(x=x, g=g, sq=sq, expr=expr, flip=True)


def umbrellas(t, cs, ks, ms):
    """[(柄の先x, y, 大きさ, 傾き)] と、雨よけの範囲。"""
    out, shelters = [], []
    # ことにゃんの傘 → 子ねこへ（3.8〜5.6 秒）
    k = seg(t, 3.9, 5.6, ease_in_out)
    cpx, cpy = cs["x"] + CAT_S * 0.22, cs["g"] - CAT_S * 0.45
    kpx, kpy = ks["x"] - KIT_S * 0.15, ks["g"] - KIT_S * 0.5
    if t < 10.8:
        px, py = lerp(cpx, kpx, k), lerp(cpy, kpy, k) - 40 * math.sin(math.pi * k)
        s = lerp(UMB_CAT, UMB_KIT, k)
        out.append((px, py, s, lerp(0, -8, k)))
        shelters.append((px - 1.3 * s, px + 1.3 * s, py - 1.7 * s))
    # 母ねこの大きな葉っぱ（戻ってきて、みんなの上へ）
    if t > 15.4:
        k2 = seg(t, 18.4, 19.6, ease_in_out)
        px = lerp(ms["x"] - MOM_S * 0.3, (CAT_X + ms["x"]) / 2 - 20, k2)
        py = ms["g"] - MOM_S * 0.5 - 30 * k2
        out.append((px, py, UMB_BIG, lerp(0, -10, k2)))
        if t > 19.4:
            shelters.append((px - 1.5 * UMB_BIG, px + 1.4 * UMB_BIG, py - 1.8 * UMB_BIG))
    return out, shelters


def render(t):
    th = theme(t)
    cx, cy, z = CAM(t)
    ra = rain_amount(t)
    fr = Frame(SIZE, Cam(cx, cy, z), ambient=lerp(1.0, 0.84, ra))
    fr.light_cap = 1.25
    fr.fade = seg(t, 34.2, 35.0)

    dl.sky(fr, th)
    dl.sun(fr, 830, 430, alpha=seg(t, 23.0, 24.6))
    dl.rainbow(fr, seg(t, 23.4, 25.0), cx=560, cy=1460, r=820)
    dl.clouds(fr, t, th, alpha=0.95, dark=0.4 * ra)
    dl.trees(fr, t, th)
    bv = fr.base()
    M.draw(bv, t, th)

    cs, ks, ms = cat_state(t), kit_state(t), mom_state(t)
    if ms["x"] < 1300:
        neko.shadow(bv, ms["x"], G(ms["x"]), MOM_S, alpha=60)
        neko.draw(fr, ms["x"], ms["g"], MOM_S, ms["expr"], palette="mother", squash=ms["sq"], flip=True)
    if ks["x"] < 1250:
        neko.shadow(bv, ks["x"], G(ks["x"]), KIT_S, alpha=60)
        neko.draw(fr, ks["x"], ks["g"], KIT_S, ks["expr"], palette="kitten", squash=ks["sq"])
    neko.shadow(bv, cs["x"], G(cs["x"]), CAT_S, alpha=60)
    neko.draw(fr, cs["x"], cs["g"], CAT_S, cs["expr"], squash=cs["sq"])

    ums, shelters = umbrellas(t, cs, ks, ms)
    for px, py, s, tilt in ums:
        dl.leaf_umbrella(bv, px, py, s, tilt)
    if 19.8 < t < 23.0:                                # ハート
        u = seg(t, 19.8, 23.0)
        snail.heart(bv, CAT_X + 60, G(CAT_X) - 170 - 60 * u, 14, alpha=pulse(t, 19.8, 23.0, 0.4))
    dl.rain(fr, t, ra, shelter=shelters[-1] if shelters else None)

    dl.grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
