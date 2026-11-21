"""ep07『和顔愛語』— にっこりは、となりへ（仕様は spec.md）。"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIME = HERE.parent.parent
sys.path[:0] = [str(ANIME), str(ANIME / "cast")]

import daylight as dl  # noqa: E402
import kit  # noqa: E402
import neko  # noqa: E402
import snail  # noqa: E402  (ハート)
from engine import Cam, Caption, Frame, Track, draw_captions, ease_out, lerp, pulse, seg  # noqa: E402

FPS = 30
SIZE = (1080, 1920)
DURATION = 36.0

M = dl.Meadow(1500)
G = M.ground_at
CAT_S, KIT_S, MOM_S, KURO_S = 150, 100, 160, 205
KIT_X0, KIT_X1, MOM_X, KURO_X = 300, 445, 600, 850
DULL = dl.blend("rain", "morning", 0.35)

CAM = Track([
    (0.0, (540, 1390, 1.3)), (4.0, (540, 1390, 1.3)),
    (5.2, (240, 1450, 2.3)), (10.6, (240, 1450, 2.3)),
    (12.4, (470, 1450, 2.2)), (16.4, (500, 1450, 2.2)),
    (17.8, (720, 1440, 2.0)), (22.2, (720, 1440, 2.0)),
    (24.0, (540, 1330, 1.3)), (26.6, (540, 1330, 1.3)),
    (29.4, (540, 1120, 1.05)), (36.0, (540, 1120, 1.05)),
])

CAPTIONS = [
    Caption(0.5, 4.0, "なんだか みんな、ごきげんななめな朝。"),
    Caption(5.4, 8.6, "ことにゃんは にっこり「おはよう」。"),
    Caption(9.2, 11.8, "子ねこも つられて、にっこり。"),
    Caption(12.6, 16.6, "にっこりは、となりへ、となりへ。"),
    Caption(17.6, 20.2, "いちばん むすっとしていた 黒ねこまで、"),
    Caption(20.4, 22.4, "…にっこり。"),
    Caption(22.8, 26.4, "やわらかな笑顔と、\nやさしいことば。"),
] + kit.ending(26.8, "和顔愛語", "―― 『仏説無量寿経』", reading="わげん あいご",
               after=["やわらかな笑顔と やさしいことばは、", "となりの人を照らす、", "小さな灯り。"],
               after_t=31.2, end=35.1)

SMILES = [(6.2, 0.2), (9.0, 0.2), (14.2, 0.25), (20.6, 0.35)]   # (にっこりした時刻, 明るくなる量)


def brightness(t):
    return sum(seg(t, t0, t0 + 1.2) * k for t0, k in SMILES)


def theme(t):
    return dl.blend(DULL, "day", brightness(t))


def cat_state(t):
    x, g, sq = kit.walk(t, 4.6, 6.0, -80, 170, G)
    expr = "normal" if t < 6.1 else "happy"
    if t > 24.0:
        expr = "happy" if t < 27 else "calm"
    return dict(x=x, g=g, sq=sq, expr=expr)


def kitten_state(t):
    x, g, sq = kit.hop_path(t, (KIT_X0, G(KIT_X0)), [(11.8, (KIT_X1, G(KIT_X1)))], height=40)
    expr = "angry" if t < 7.8 else ("surprised" if t < 9.0 else "happy")
    if t > 27:
        expr = "calm"
    return dict(x=x, g=g, sq=sq, expr=expr)


def mom_state(t):
    expr = "blank" if t < 13.4 else ("surprised" if t < 14.2 else "happy")
    if t > 27:
        expr = "calm"
    return dict(x=MOM_X, g=G(MOM_X), sq=1.0, expr=expr)


def kuro_state(t):
    expr = "blank" if t < 19.2 else ("shy" if t < 20.6 else "happy")
    if t > 27:
        expr = "calm"
    sq = 1.0 + 0.04 * pulse(t, 20.6, 21.2, 0.2)
    return dict(x=KURO_X, g=G(KURO_X), sq=sq, expr=expr)


HEARTS = [(6.5, lambda t: (cat_state(t)["x"], CAT_S), (KIT_X0, KIT_S)),
          (12.6, (KIT_X1, KIT_S), (MOM_X, MOM_S)),
          (17.9, (MOM_X, MOM_S), (KURO_X, KURO_S))]

_rnd = random.Random(12)
FLOWERS = []
for t0, xs in ((6.4, (120, 230)), (9.1, (250, 380)), (14.3, (480, 680)), (20.7, (760, 960))):
    for _ in range(5):
        FLOWERS.append((_rnd.uniform(*xs), t0 + _rnd.uniform(0, 0.8)))
for _ in range(40):
    FLOWERS.append((_rnd.uniform(-250, 1350), 22.8 + _rnd.uniform(0, 1.8)))
PETALS = [(250, 170, 190), (250, 220, 140), (190, 180, 240), (255, 200, 160)]


def render(t):
    th = theme(t)
    b = brightness(t)
    cx, cy, z = CAM(t)
    fr = Frame(SIZE, Cam(cx, cy, z), ambient=lerp(0.9, 1.0, b))
    fr.light_cap = 1.25
    fr.fade = seg(t, 35.1, 36.0)

    dl.sky(fr, th)
    dl.sun(fr, 830, lerp(700, 420, b), alpha=b)
    dl.clouds(fr, t, th, alpha=0.95, dark=0.35 * (1 - b))
    dl.trees(fr, t, th)
    bv, ev = fr.base(), fr.emit()
    M.draw(bv, t, th)

    for i, (fx, ft) in enumerate(FLOWERS):
        dl.flower(bv, fx, G(fx) + 6, 1.1, (t - ft) / 0.6, petal=PETALS[i % 4])

    for st, size, pal in ((kuro_state(t), KURO_S, "kuro"), (mom_state(t), MOM_S, "mother"),
                          (kitten_state(t), KIT_S, "kitten"), (cat_state(t), CAT_S, None)):
        if st["x"] > -150:
            neko.shadow(bv, st["x"], G(st["x"]), size, alpha=60)
            neko.draw(fr, st["x"], st["g"], size, st["expr"], palette=pal, squash=st["sq"])

    for t0, a, bb in HEARTS:                         # にっこりが となりへ飛んでいく
        u = (t - t0) / 1.0
        if 0 <= u <= 1:
            (ax, asz) = a(t) if callable(a) else a
            bx, bsz = bb
            x = lerp(ax, bx, ease_out(u))
            y = lerp(G(ax) - asz * 0.8, G(bx) - bsz * 0.8, u) - 90 * math.sin(math.pi * u)
            snail.heart(bv, x, y, 16, alpha=min(1, (1 - u) * 3))
            ev.glow(x, y, 30, (255, 200, 200), strength=0.5 * (1 - u))
    if 20.6 < t < 22.4:                              # くろの めずらしい笑顔にキラキラ
        for i in range(5):
            a = i / 5 * 2 * math.pi + t * 2
            ev.glow(KURO_X + math.cos(a) * 140, G(KURO_X) - 110 + math.sin(a) * 80, 12, (255, 236, 170),
                    strength=pulse(t, 20.6, 22.4, 0.3))

    dl.grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
