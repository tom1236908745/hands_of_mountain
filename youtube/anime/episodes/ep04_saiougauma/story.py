"""ep04『塞翁が馬』— ことば帖が飛ばされた日（仕様は spec.md）。"""
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
DURATION = 35.5

M = dl.Meadow(1500)
G = M.ground_at
CAT_S, KIT_S = 150, 100
CAT_X0, CAT_X1, KIT_X = 380, 700, 880

CAM = Track([
    (0.0, (400, 1460, 2.3)), (3.6, (400, 1460, 2.3)),
    (4.6, (500, 1340, 1.6)), (6.9, (500, 1340, 1.6)),
    (8.2, (560, 1460, 2.3)), (10.2, (750, 1460, 2.3)), (13.4, (750, 1460, 2.3)),
    (16.4, (720, 1462, 2.3)), (19.6, (740, 1462, 2.2)),
    (22.0, (700, 1220, 1.4)), (25.2, (700, 1220, 1.4)),
    (28.8, (540, 960, 1.0)), (35.5, (540, 960, 1.0)),
])

Q = dict(size=46, y=0.40, fade_in=0.35)
CAPTIONS = [
    Caption(0.5, 3.4, "ことにゃんの たからもの、ことば帖。"),
    Caption(4.4, 6.6, "風に とばされてしまった。"),
    Caption(5.6, 7.3, "わるいこと…？", **Q),
    Caption(8.4, 11.2, "ひろってくれた子と、"),
    Caption(11.3, 13.4, "友だちに なった。"),
    Caption(12.2, 13.4, "いいこと…？", **Q),
    Caption(14.0, 17.2, "はしゃいで、ころんでしまった。"),
    Caption(17.2, 19.2, "わるいこと…？", **Q),
    Caption(19.6, 21.0, "休んでいたら、"),
    Caption(21.6, 24.4, "空いっぱいの 流れ星。"),
    Caption(23.2, 25.0, "いいこと…？", **Q),
] + kit.ending(25.6, "人間万事\n塞翁が馬", "―― 『淮南子』人間訓の故事より", reading="にんげんばんじ さいおうがうま",
               after=["いいことも、わるいことも、", "まだ お話の とちゅう。", "だから、あわてなくていい。"],
               after_t=30.2, end=34.6)


def theme(t):
    if t < 13.5:
        return dl.THEMES["day"]
    if t < 18.5:
        return dl.blend("day", "dusk", seg(t, 13.5, 18.5))
    return dl.blend("dusk", "night", seg(t, 18.5, 21.5))


def cat_state(t):
    item, rot, flip = "book", 0.0, False
    x, g, sq = CAT_X0, G(CAT_X0), 1.0
    expr = "happy"
    if t < 4.0:
        expr = "happy" if (t % 3.0) > 0.15 else "calm"
    elif t < 7.6:                                    # 本が飛ばされる
        item = None
        expr = "surprised" if t < 5.6 else "pien"
        sq = 1.0 + 0.05 * pulse(t, 4.0, 4.5, 0.2)
    elif t < 11.4:                                   # 探しに行って、見つける
        item = None
        x, g, sq = kit.walk(t, 7.8, 10.0, CAT_X0, CAT_X1, G)
        expr = "sad" if t < 10.0 else "surprised"
    elif t < 15.4:                                   # 返してもらって、あそぶ
        x, g, sq = kit.hop_path(t, (CAT_X1, G(CAT_X1)), [(13.6, (620, G(620))), (14.2, (700, G(700))),
                                                          (14.8, (620, G(620)))], height=60)
        expr = "happy"
    else:                                            # ころぶ → 休む → 流れ星
        if t < 15.95:
            u = (t - 15.4) / 0.55
            x = lerp(620, 705, u)
            g = lerp(G(620), G(705), u) - 70 * math.sin(math.pi * u)
            rot = 360 * ease_out(u)
            expr = "surprised"
        else:
            x, g = 705, G(705)
            sq = lerp(0.8, 1.0, seg(t, 15.95, 16.3))
            expr = "pien" if t < 18.6 else ("sad" if t < 21.2 else ("surprised" if t < 22.3 else "happy"))
            if t > 26.5:
                expr = "calm"
    return dict(x=x, g=g, sq=sq, expr=expr, item=item, rot=rot)


def kit_state(t):
    x, g, sq = KIT_X, G(KIT_X), 1.0
    item = "book" if t < 11.4 else None
    expr = "happy"
    if 9.9 < t < 10.7:
        expr = "surprised"
    if t >= 10.7:
        x, g, sq = kit.hop_path(t, (KIT_X, G(KIT_X)), [(10.8, (800, G(800))), (13.9, (860, G(860))),
                                                       (14.5, (790, G(790)))], height=45)
    if 15.95 < t < 18.6:
        expr = "surprised" if t < 16.6 else "sad"
    elif 18.6 <= t < 21.2:
        expr = "calm"
    elif 21.2 <= t < 22.3:
        expr = "surprised"
    elif t > 26.5:
        expr = "calm"
    return dict(x=x, g=g, sq=sq, expr=expr, item=item)


def book_flight(t):
    """4.0〜7.0 秒：ことば帖が風で右上へ。"""
    if not 4.0 <= t < 7.2:
        return None
    u = (t - 4.0) / 3.2
    sx, sy = CAT_X0, G(CAT_X0) - CAT_S * 0.14
    x = lerp(sx, 1250, u) + math.sin(u * 9) * 30
    y = sy - 520 * math.sin(u * math.pi * 0.8) - 60 * u
    return x, y, t * 18, 40 * math.sin(t * 5)


_rnd = random.Random(2)
LEAVES = [(_rnd.uniform(-200, 200), _rnd.uniform(1150, 1480), _rnd.uniform(0, 6.28), _rnd.uniform(0.8, 1.3))
          for _ in range(16)]


def bandage(cv, x, foot, s):
    hx, hy = x + (365 - 500) / 1000 * s, foot - 0.91 * s + 0.43 * s
    a = math.radians(-28)
    w, h = 0.17 * s, 0.06 * s
    pts = [(hx + dx * math.cos(a) - dy * math.sin(a), hy + dx * math.sin(a) + dy * math.cos(a))
           for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
    cv.poly(pts, (246, 216, 182))
    cv.poly([((p[0] + hx) / 2 + (q[0] - hx) * 0.0, (p[1] + hy) / 2) for p, q in zip(pts, pts)], (232, 196, 160))
    cv.circle(hx, hy, 0.025 * s, (220, 180, 150))


def render(t):
    th = theme(t)
    cx, cy, z = CAM(t)
    fr = Frame(SIZE, Cam(cx, cy, z), ambient=lerp(1.0, 0.78, seg(t, 18.5, 21.5)))
    fr.light_cap = 1.25
    fr.fade = seg(t, 34.6, 35.5)

    dl.sky(fr, th)
    dl.stars(fr, t, th["stars"])
    k = seg(t, 13.5, 20.0)
    dl.sun(fr, lerp(840, 920, k), lerp(430, 1250, k), alpha=1 - seg(t, 18.5, 20.2),
           color=tuple(int(lerp(a, b, k)) for a, b in zip((255, 236, 170), (255, 150, 90))))
    dl.moon(fr, 820, 340, alpha=seg(t, 20.5, 22.0))
    dl.clouds(fr, t, th, alpha=1 - seg(t, 17.5, 20.5))
    if t > 20.8:
        dl.shooting_stars(fr, t, 21.0, n=9)
    dl.trees(fr, t, th)
    bv = fr.base()
    M.draw(bv, t, th)

    ks, cs = kit_state(t), cat_state(t)
    for st, size, pal in ((ks, KIT_S, "kitten"), (cs, CAT_S, None)):
        neko.shadow(bv, st["x"], G(st["x"]), size, alpha=60)
        neko.draw(fr, st["x"], st["g"], size, st["expr"], item=st["item"], palette=pal, squash=st["sq"],
                  rot=st.get("rot", 0.0))
    if t > 16.2:
        bandage(bv, cs["x"], cs["g"], CAT_S)
    if 11.4 < t < 13.4:                              # ハート
        u = seg(t, 11.4, 13.4, ease_out)
        snail.heart(bv, (cs["x"] + ks["x"]) / 2, G(750) - 150 - 60 * u, 14, alpha=pulse(t, 11.4, 13.4, 0.4))

    bf = book_flight(t)
    if bf:
        dl.flying_book(bv, bf[0], bf[1], 42, bf[2], bf[3])
    if 3.6 < t < 7.4:                                # 風で葉っぱが飛ぶ
        for ox, oy, ph, sp in LEAVES:
            u = ((t - 3.6) * 0.45 * sp + ph / 6.28) % 1.0
            lx = CAT_X0 - 300 + ox + u * 1100
            ly = oy - u * 300 + math.sin(t * 4 + ph) * 30
            bv.ellipse(lx, ly, 14, 6, (110, 170, 100, 220), rot=t * 200 + ph * 50)

    dl.grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
