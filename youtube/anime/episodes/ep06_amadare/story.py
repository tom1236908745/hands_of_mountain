"""ep06『雨垂れ石を穿つ』— 切り株にとどくまで（仕様は spec.md）。"""
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
DURATION = 37.0

M = dl.Meadow(1500)
G = M.ground_at
CAT_S = 150
HOME = 515
STUMP_X, STUMP_W, STUMP_H = 655, 180, 185
ROCK_X, ROCK_W, ROCK_H = 320, 160, 92
DRIP_FROM = (322, 1190)
DAY0, DAY_LEN, DAYS = 15.4, 2.15, 4

CAM = Track([
    (0.0, (575, 1425, 1.95)), (9.8, (575, 1425, 1.95)),
    (11.0, (390, 1415, 2.6)), (14.8, (390, 1415, 2.6)),
    (15.8, (560, 1420, 1.9)), (24.0, (560, 1420, 1.9)),
    (25.2, (640, 1320, 1.9)), (26.4, (620, 1250, 1.45)), (28.0, (620, 1250, 1.45)),
    (30.5, (560, 1120, 1.1)), (37.0, (560, 1120, 1.1)),
])

CAPTIONS = [
    Caption(0.5, 3.6, "切り株の上から見る景色は、\nきっと きれい。"),
    Caption(4.4, 6.8, "ぴょん！ …とどかない。"),
    Caption(7.1, 9.8, "何度やっても、とどかない。"),
    Caption(10.4, 12.6, "そばの岩に、しずくが ぽたり。"),
    Caption(12.8, 15.2, "小さなしずくが、\n岩に くぼみを つくっていた。"),
    Caption(15.7, 17.8, "きょうも、ぴょん。"),
    Caption(18.0, 20.2, "あしたも、ぴょん。"),
    Caption(20.4, 23.7, "毎日、すこしずつ。"),
    Caption(25.0, 27.5, "とどいた！"),
] + kit.ending(27.9, "雨垂れ\n石を穿つ", "―― 『漢書』枚乗伝より", reading="あまだれ いしを うがつ",
               after=["小さな一歩も、", "つづければ、", "大きな力になる。"], after_t=32.3, end=36.1)


def day_phase(t):
    """モンタージュ中の 1日の進み具合（0〜1）。それ以外は None。"""
    if DAY0 <= t < DAY0 + DAY_LEN * DAYS:
        return ((t - DAY0) / DAY_LEN) % 1.0
    return None


def theme(t):
    p = day_phase(t)
    if p is not None:
        if p < 0.2:
            return dl.blend("morning", "day", p / 0.2)
        if p < 0.5:
            return dl.THEMES["day"]
        if p < 0.72:
            return dl.blend("day", "dusk", (p - 0.5) / 0.22)
        if p < 0.85:
            return dl.blend("dusk", "night", (p - 0.72) / 0.13)
        return dl.blend("night", "morning", (p - 0.85) / 0.15)
    if t >= DAY0 + DAY_LEN * DAYS:
        return dl.blend("morning", "day", seg(t, 24.0, 30.0) * 0.5)
    return dl.THEMES["day"]


STUMP_TOP = (STUMP_X, G(STUMP_X) - STUMP_H)


def cat_state(t):
    x, g, sq, rot = HOME, G(HOME), 1.0, 0.0
    expr = "normal"
    if t < 4.3:
        expr = "normal" if t < 2.0 else "happy"
        rot = -5 * pulse(t, 0.6, 3.6, 0.5)
    elif t < 10.2:                                       # とどかない ×2
        hops = [(4.6, (585, G(585))), (5.25, (HOME, G(HOME))), (7.2, (590, G(590))), (7.85, (HOME, G(HOME)))]
        x, g, sq = kit.hop_path(t, (HOME, G(HOME)), hops, dur=0.55, height=135)
        if t > 7.9:
            x, g, sq = kit.hop_path(t, (HOME, G(HOME)), hops, dur=0.55, height=135)
        expr = "strain" if (4.5 < t < 5.2 or 7.1 < t < 7.8) else ("pien" if t > 8.2 else "sad")
    elif t < DAY0:                                       # 岩のそばで気づく
        x, g, sq = kit.walk(t, 10.2, 11.3, HOME, 445, G)
        expr = "sad" if t < 11.8 else ("thinking" if t < 13.4 else ("surprised" if t < 14.4 else "strain"))
        if t > 14.9:
            x, g, sq = kit.hop_path(t, (445, G(445)), [(14.95, (HOME, G(HOME)))], height=40)
    elif t < DAY0 + DAY_LEN * DAYS:                      # 毎日 ぴょん（すこしずつ高く）
        i = int((t - DAY0) // DAY_LEN)
        p = day_phase(t)
        t0 = DAY0 + i * DAY_LEN + 0.55
        h = 120 + i * 18
        x, g, sq = kit.hop_path(t, (HOME, G(HOME)), [(t0, (580, G(580))), (t0 + 0.55, (HOME, G(HOME)))],
                                dur=0.5, height=h)
        expr = "strain" if 0.2 < p < 0.55 else ("calm" if p > 0.8 else "normal")
    else:                                                # とどいた！
        x, g, sq = kit.hop_path(t, (HOME, G(HOME)), [(24.4, STUMP_TOP)], dur=0.7, height=120)
        expr = "strain" if t < 24.6 else ("surprised" if t < 25.3 else ("happy" if t < 31 else "calm"))
    return dict(x=x, g=g, sq=sq, expr=expr, rot=rot)


def branch(cv, t):
    sway = math.sin(t * 0.9) * 3
    pts = [(-80, 1080), (120, 1120), (260, 1160 + sway), (345, 1182 + sway)]
    cv.line(pts, (120, 90, 66), 18)
    for i, (lx, ly) in enumerate([(30, 1085), (110, 1135), (190, 1120), (250, 1180), (300, 1160), (340, 1195)]):
        cv.ellipse(lx, ly + sway * (i / 6), 34, 15, (96, 164, 100), rot=20 + i * 25)


def render(t):
    th = theme(t)
    cx, cy, z = CAM(t)
    p = day_phase(t)
    night = 0.0
    if p is not None:
        night = max(0.0, 1 - abs(p - 0.83) / 0.12) if 0.7 < p < 0.97 else 0.0
    fr = Frame(SIZE, Cam(cx, cy, z), ambient=lerp(1.0, 0.72, night))
    fr.light_cap = 1.25
    fr.fade = seg(t, 36.1, 37.0)

    dl.sky(fr, th)
    dl.stars(fr, t, th["stars"])
    if p is not None:                                    # 太陽と月が空をめぐる
        a = math.pi * min(1, p / 0.72)
        dl.sun(fr, 1100 - 1000 * p / 0.72, 1000 - 650 * math.sin(a), alpha=1 if p < 0.7 else 0)
        if p > 0.68:
            q = (p - 0.68) / 0.32
            dl.moon(fr, 1000 - 700 * q, 700 - 380 * math.sin(math.pi * q), alpha=min(1, night * 2))
    elif t >= 24.0:
        dl.sun(fr, 1010, lerp(980, 700, seg(t, 24.0, 30.0)), r=80, color=(255, 200, 140))
    else:
        dl.sun(fr, 850, 430)
    dl.clouds(fr, t * (6 if p is not None else 1), th, alpha=0.9 * (1 - night))
    dl.trees(fr, t, th)
    bv, ev = fr.base(), fr.emit()
    M.draw(bv, t, th)

    hollow = 0.15 + 0.85 * seg(t, 10.0, 26.0)
    dl.rock(bv, ROCK_X, G(ROCK_X) + 4, ROCK_W, ROCK_H, hollow=hollow)
    branch(bv, t)
    dl.drip(bv, DRIP_FROM[0], DRIP_FROM[1] + 12, G(ROCK_X) + 4 - ROCK_H + 8, t, period=0.9 if p is None else 0.3)
    dl.stump(bv, STUMP_X, G(STUMP_X), STUMP_W, STUMP_H)

    cs = cat_state(t)
    neko.shadow(bv, cs["x"], G(cs["x"]) if cs["x"] < STUMP_X - 80 else STUMP_TOP[1], CAT_S, alpha=60)
    neko.draw(fr, cs["x"], cs["g"], CAT_S, cs["expr"], squash=cs["sq"], rot=cs["rot"])
    if 25.1 < t < 27.0:                                  # とどいたキラキラ
        for i in range(6):
            a = i / 6 * 2 * math.pi + t
            r = 120 + 40 * seg(t, 25.1, 26.0, ease_out)
            ev.glow(cs["x"] + math.cos(a) * r, cs["g"] - 90 + math.sin(a) * r * 0.6, 14, (255, 236, 160),
                    strength=pulse(t, 25.1, 27.0, 0.3))

    dl.grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
