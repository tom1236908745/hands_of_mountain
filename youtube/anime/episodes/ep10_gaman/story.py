"""ep10『我慢』— ひとりで運べる！（仕様は spec.md）。"""
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
from engine import Cam, Caption, Frame, Track, draw_captions, ease_in_out, ease_out, lerp, pulse, seg  # noqa: E402

FPS = 30
SIZE = (1080, 1920)
DURATION = 36.0

M = dl.Meadow(1500)
G = M.ground_at
CAT_S, KIT_S, KURO_S = 150, 100, 200
BOOKS = [(126, 158, 182), (236, 166, 112), (150, 190, 140), (220, 140, 150), (190, 170, 220), (240, 210, 120)]
FALL_T = 14.0
LAND = [(430, 8), (470, -14), (560, 20), (605, -6), (650, 12), (505, -24)]   # 落ちた本の位置と傾き
OWNER = ["kit", "kit", "kuro", "kuro", "kuro", "cat"]                     # 拾ったあと、だれが運ぶか

CAM = Track([
    (0.0, (330, 1335, 2.4)), (3.8, (330, 1335, 2.4)),
    (5.0, (300, 1370, 1.9)), (8.8, (300, 1370, 1.9)),
    (10.4, (600, 1360, 1.7)), (13.6, (620, 1360, 1.7)),
    (14.6, (530, 1395, 2.2)), (20.0, (530, 1395, 2.2)),
    (21.0, (560, 1375, 1.7)), (24.6, (560, 1375, 1.7)),
    (28.2, (690, 1375, 1.7)), (28.8, (690, 1375, 1.7)),
    (31.0, (580, 1200, 1.1)), (36.0, (580, 1200, 1.1)),
])

CAPTIONS = [
    Caption(0.4, 3.9, "こんなに たくさん、\nひとりで 運べる？"),
    Caption(4.4, 6.6, "子ねこが「てつだう？」"),
    Caption(6.8, 9.0, "「へいき！ ひとりで できる！」"),
    Caption(9.4, 11.6, "ほんとうは、ちょっと 重い。"),
    Caption(11.8, 13.9, "でも、弱いところは 見せたくない。"),
    Caption(14.6, 16.4, "どさっ。", size=58),
    Caption(16.8, 20.6, "強がるほど、\nひとりぼっちに なっていく。"),
    Caption(21.0, 23.4, "だまって 拾ってくれた、ふたり。"),
    Caption(23.6, 25.6, "「…てつだって くれる？」"),
    Caption(25.8, 28.4, "三つに分けたら、かるくなった。"),
] + kit.ending(28.8, "我慢", "―― 仏教のことば（七慢のひとつ）", reading="がまん",
               after=["もとは、自分を 大きく見せようとする心。", "ときには、", "強がらなくて いいんだよ。"],
               after_t=33.0, end=35.2)

BUBBLES = [((5.0, 6.6), "kit", "てつだう？", 0.9, 0.0), ((6.9, 8.8), "cat", "へいき！", -0.6, 0.0),
           ((23.8, 25.5), "cat", "…てつだって？", 0.15, 0.55)]   # (時間, 話し手, ことば, 横, 上)


# ---------------------------------------------------------------- 動き
def cat_state(t):
    x, g, sq = 330, G(330), 1.0
    rot = 0.0
    if t < 4.4:
        expr = "happy"
    elif t < 6.8:
        expr = "normal"
    elif t < 9.2:
        expr = "angry"                                   # ぷくっと強がる
    elif t < FALL_T:
        x, g, sq = kit.walk(t, 9.2, FALL_T, 330, 520, G, bounce=6, steps_per_sec=3)
        expr = "strain" if (t % 1.6) < 1.0 else "normal"
        rot = 4 * math.sin(t * 5)
    elif t < 14.7:                                       # つまずく
        x, g = 520, G(520)
        u = (t - FALL_T) / 0.7
        rot = 70 * math.sin(math.pi * u)
        expr = "surprised"
        sq = 1 - 0.15 * math.sin(math.pi * u)
    else:
        x, g = 520, G(520)
        expr = "pien" if t < 21.4 else ("surprised" if t < 22.0 else ("shy" if t < 25.6 else "happy"))
        sq = lerp(0.9, 1.0, seg(t, 14.7, 15.2))
        if t > 25.0:
            x, g, sq = kit.walk(t, 25.4, 28.3, 520, 700, G)
        if t > 29:
            expr = "calm"
    return dict(x=x, g=g, sq=sq, expr=expr, rot=rot)


def kit_state(t):
    if t < 5.0:
        x, g, sq = kit.walk(t, 3.8, 5.0, -80, 210, G)
    elif t < 19.6:
        x, g, sq = 210, G(210), 1.0
    elif t < 25.0:
        x, g, sq = kit.walk(t, 19.6, 21.0, 210, 425, G)
    else:
        x, g, sq = kit.walk(t, 25.4, 28.3, 425, 595, G)
    expr = "happy" if t < 6.9 else ("sad" if t < 19.6 else ("normal" if t < 23.8 else "happy"))
    if t > 29:
        expr = "calm"
    return dict(x=x, g=g, sq=sq, expr=expr)


def kuro_state(t):
    if t < 12.4:
        x, g, sq = kit.walk(t, 10.2, 12.4, 1150, 830, G, bounce=5, steps_per_sec=3)
    elif t < 25.0:
        x, g, sq = kit.walk(t, 19.4, 21.0, 830, 640, G, bounce=5, steps_per_sec=3)
    else:
        x, g, sq = kit.walk(t, 25.4, 28.3, 640, 820, G, bounce=5, steps_per_sec=3)
    expr = "blank" if t < 23.8 else ("shy" if t < 25.6 else "happy")
    if t > 29:
        expr = "calm"
    return dict(x=x, g=g, sq=sq, expr=expr, flip=True)


# ---------------------------------------------------------------- 本
def book(cv, x, y, w, h, rot, col):
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    P = lambda lx, ly: (x + lx * cr - ly * sr, y + lx * sr + ly * cr)  # noqa: E731
    cv.poly([P(-w / 2, -h / 2), P(w / 2, -h / 2), P(w / 2, h / 2), P(-w / 2, h / 2)], (104, 82, 74))
    cv.poly([P(-w / 2 + 3, -h / 2 + 3), P(w / 2 - 3, -h / 2 + 3), P(w / 2 - 3, h / 2 - 3), P(-w / 2 + 3, h / 2 - 3)], col)
    cv.poly([P(w / 2 - 12, -h / 2 + 3), P(w / 2 - 3, -h / 2 + 3), P(w / 2 - 3, h / 2 - 3), P(w / 2 - 12, h / 2 - 3)],
            (252, 246, 232))


def head_top(st, size):
    return st["x"], st["g"] - size * 0.55 * st["sq"]


def stack_positions(base_x, base_y, n, size, t, wobble):
    w, h = size * 0.6, size * 0.15
    out = []
    dx = 0.0
    for i in range(n):
        dx += wobble * math.sin(t * 4.0 + i * 0.6) * (i + 1) * 0.6
        rot = wobble * 0.5 * math.sin(t * 4.0 + i * 0.6)
        out.append((base_x + dx, base_y - h * (i + 0.5), w, h, rot))
    return out


def books_now(t, cs, ks, kr):
    """[(x, y, w, h, 傾き, 色)]"""
    out = []
    if t < FALL_T:
        wob = 0.0 if t < 9.2 else lerp(1.5, 5.0, seg(t, 9.2, FALL_T))
        if t < 9.2:
            wob = 1.0 + 0.6 * (t > 6.8)
        hx, hy = head_top(cs, CAT_S)
        for (x, y, w, h, r), col in zip(stack_positions(hx, hy, len(BOOKS), CAT_S, t, wob), BOOKS):
            out.append((x, y, w, h, r + cs["rot"] * 0.5, col))
        return out
    start = stack_positions(520, G(520) - CAT_S * 0.55, len(BOOKS), CAT_S, FALL_T, 5.0)
    carriers = {"kit": (ks, KIT_S), "kuro": (kr, KURO_S), "cat": (cs, CAT_S)}
    counts = {"kit": 0, "kuro": 0, "cat": 0}
    for i, col in enumerate(BOOKS):
        sx, sy, w, h, _ = start[i]
        lx, lr = LAND[i]
        ly = G(lx) - h / 2
        u = seg(t, FALL_T + i * 0.05, FALL_T + 0.7 + i * 0.05, lambda v: min(1.0, max(0.0, v)))
        x = lerp(sx, lx, u)
        y = lerp(sy, ly, u) - 160 * math.sin(math.pi * u) * (0.6 + 0.1 * i)
        rot = lerp(0, lr + 360 * (1 if i % 2 else -1), u)
        # 拾って、運ぶ人の頭へ
        who = OWNER[i]
        st, size = carriers[who]
        k = counts[who]
        counts[who] += 1
        pick0 = 21.2 + i * 0.22
        if t > pick0:
            hx, hy = head_top(st, size)
            bw, bh = size * 0.6, size * 0.15
            tx, ty = hx, hy - bh * (k + 0.5)
            v = seg(t, pick0, pick0 + 0.6, ease_in_out)
            x, y = lerp(lx, tx, v), lerp(ly, ty, v) - 70 * math.sin(math.pi * v)
            rot = lerp(lr, 2 * math.sin(t * 3 + i), v)
            w, h = lerp(w, bw, v), lerp(h, bh, v)
        out.append((x, y, w, h, rot, col))
    return out


def render(t):
    th = dl.THEMES["day"]
    cx, cy, z = CAM(t)
    fr = Frame(SIZE, Cam(cx, cy, z))
    fr.light_cap = 1.25
    fr.fade = seg(t, 35.2, 36.0)

    dl.sky(fr, th)
    dl.sun(fr, 850, 420)
    dl.clouds(fr, t, th)
    dl.trees(fr, t, th)
    bv = fr.base()
    M.draw(bv, t, th)

    cs, ks, kr = cat_state(t), kit_state(t), kuro_state(t)
    for st, size, pal in ((kr, KURO_S, "kuro"), (ks, KIT_S, "kitten"), (cs, CAT_S, None)):
        if -150 < st["x"] < 1250:
            neko.shadow(bv, st["x"], G(st["x"]), size, alpha=60)
            neko.draw(fr, st["x"], st["g"], size, st["expr"], palette=pal, squash=st["sq"], rot=st.get("rot", 0.0),
                      flip=st.get("flip", False))
    for x, y, w, h, r, col in books_now(t, cs, ks, kr):
        book(bv, x, y, w, h, r, col)
    if 9.5 < t < FALL_T:                                  # あせ
        dl_y = cs["g"] - CAT_S * 0.75
        bv.circle(cs["x"] + CAT_S * 0.4, dl_y + 10 * ((t * 1.5) % 1), 6, (140, 196, 236, 200))
    if 26.0 < t < 28.8:
        u = seg(t, 26.0, 28.8)
        snail.heart(bv, cs["x"] + 60, cs["g"] - 230 - 50 * u, 14, alpha=pulse(t, 26.0, 28.8, 0.4))

    dl.grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    img = Image.fromarray(fr.compose())
    cam = CAM(t)
    who = {"cat": (cs, CAT_S), "kit": (ks, KIT_S)}
    for (t0, t1), w, text, side, up in BUBBLES:
        if t0 <= t <= t1:
            st, size = who[w]
            img = kit.speech_bubble(img, cam, SIZE, st["x"] + side * size * 0.25, st["g"] - size * (0.45 + up), text,
                                    alpha=pulse(t, t0, t1, 0.25), fsize=int(34 + 6 * min(1, cam[2] / 2)),
                                    dx=side * size * 0.75)
    return img
