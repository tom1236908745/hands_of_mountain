"""ショートアニメ『一隅を照らす』— 絵とタイムライン（仕様は spec.md）。

時間 → 状態 を関数で決め、render(t) が 1 フレームを返す。
カメラ・ホタルの動き・字幕などは、spec.md の表の時刻にそろえてある。
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIME = HERE.parent.parent
sys.path[:0] = [str(ANIME), str(ANIME / "cast")]

import firefly  # noqa: E402
import scenery  # noqa: E402
import snail  # noqa: E402
from engine import (MINCHO, Cam, Caption, Frame, Light, Track, clamp, draw_captions, ease_in_out,  # noqa: E402
                    ease_out, lerp, pulse, seg)

FPS = 30
SIZE = (1080, 1920)
DURATION = 38.0

# ---------------------------------------------------------------- 配置
LEAF_L = scenery.Leaf(base=(40, 1560), tip=(445, 1440), width=78, stem_to=(10, 1980))
LEAF_R = scenery.Leaf(base=(1080, 1560), tip=(680, 1452), width=82, stem_to=(1110, 1980))
VINE = scenery.Vine((440, 1440), (560, 1600), (684, 1450))

HERO_S = 20          # 主人公（頭の半径）
CHILD_S = 13         # 子カタツムリ（殻の半径）
MOTHER_S = 19


def _on(leaf, u, lift):
    x, y = leaf.top(u)
    return x, y - lift


HERO_HOME = _on(LEAF_L, 0.5, HERO_S * 1.12)
CHILD_HOME = _on(LEAF_L, 0.86, CHILD_S * 1.0)
MOTHER_POS = _on(LEAF_R, 0.62, MOTHER_S * 1.0)
CHILD_END = (MOTHER_POS[0] - MOTHER_S * 1.6 - CHILD_S * 2.0, _on(LEAF_R, 0.86, CHILD_S)[1])

# ---------------------------------------------------------------- カメラ
WIDE = (540, 960, 1.0)
FACE = (HERO_HOME[0] + 10, HERO_HOME[1] - 20, 3.6)
TEN1 = (HERO_HOME[0] + 70, HERO_HOME[1] - 10, 2.5)
TEN2 = (HERO_HOME[0] + 80, HERO_HOME[1] - 35, 2.5)
TOMORU = (565, 1420, 1.55)
KETSU = (640, 1410, 1.6)

CAM = Track([
    (0.0, WIDE), (5.6, WIDE),
    (8.4, FACE), (12.3, FACE),
    (14.0, TEN1), (16.4, TEN1), (17.6, TEN2), (19.9, TEN2),
    (21.6, TOMORU), (24.4, TOMORU),
    (26.8, KETSU), (29.0, KETSU),
    (33.8, WIDE), (38.0, WIDE),
])

# ---------------------------------------------------------------- 字幕
CAPTIONS = [
    Caption(0.5, 3.3, "仲間たちは 空いっぱいに光る。"),
    Caption(3.5, 6.4, "ぼくも、あんなふうに 輝きたい。"),
    Caption(6.8, 9.5, "遠くまで届く光が ほしくて"),
    Caption(9.7, 12.4, "がんばるほど、光は消えた。"),
    Caption(12.7, 14.5, "そのとき、すぐそばの暗がりで"),
    Caption(14.6, 16.4, "まいごの子が 泣いていた。"),
    Caption(16.6, 18.1, "遠くじゃなくていい。"),
    Caption(18.2, 19.8, "いま ここで、この子を照らしたい。"),
    Caption(20.2, 22.2, "自分の場所で、誰かのために。"),
    Caption(22.3, 24.4, "そう願ったとき、光が灯った。"),
    Caption(24.7, 26.8, "空まで届く光じゃない。"),
    Caption(26.9, 29.0, "でも、この子の道には 十分だった。"),
    Caption(29.6, 33.6, "一隅を照らす、\nこれ則ち国宝なり", size=96, font=MINCHO, line_gap=1.35, fade_in=1.0,
            fade_out=0.8, y=0.3),
    Caption(30.4, 33.6, "―― 最澄『山家学生式』", size=40, font=MINCHO, y=0.41, fade_in=0.9, fade_out=0.8),
    Caption(34.0, 37.6, "大きな光でなくていい。", size=50, y=0.27, fade_out=0.9),
    Caption(35.0, 37.6, "自分の場所で、まごころを尽くす人。", size=50, y=0.33, fade_out=0.9),
    Caption(36.0, 37.6, "その人こそが、国の宝である。", size=50, y=0.39, fade_out=0.9),
]

# ---------------------------------------------------------------- 群れのホタル
_rnd = random.Random(11)
SWARM = []
for i in range(46):
    sx = _rnd.uniform(-40, 1120)
    sy = _rnd.uniform(1660, 1820)
    tx = _rnd.uniform(-20, 1100)
    ty = _rnd.uniform(140, 1050)
    t0 = 0.3 + i * 0.075 + _rnd.uniform(0, 0.5)
    SWARM.append(dict(sx=sx, sy=sy, tx=tx, ty=ty, t0=t0, dur=_rnd.uniform(3.2, 5.0),
                      ph=_rnd.uniform(0, 6.28), sp=_rnd.uniform(0.6, 1.4), s=_rnd.uniform(3.2, 5.0)))


def swarm(fr, t):
    bv, ev = fr.base(), fr.emit()
    for f in SWARM:
        u = clamp((t - f["t0"]) / f["dur"])
        if t < f["t0"] - 0.2:
            continue
        uu = ease_out(u)
        wob = math.sin(t * 2.2 * f["sp"] + f["ph"])
        x = lerp(f["sx"], f["tx"], uu) + wob * 28 * (0.4 + uu) + math.sin(t * 0.4 + f["ph"]) * 20 * uu
        y = lerp(f["sy"], f["ty"], uu) + math.cos(t * 1.7 * f["sp"] + f["ph"]) * 14 * uu
        on = clamp((t - f["t0"]) / 0.6)
        level = on * (0.65 + 0.35 * math.sin(t * 2.5 * f["sp"] + f["ph"]))
        firefly.draw_tiny(bv, ev, x, y, f["s"], level, t * 40 + f["ph"])


# ---------------------------------------------------------------- 主人公の状態
def hero_state(t):
    """位置・表情・光の強さなど。"""
    x, y = HERO_HOME
    st = dict(eyes="open", look=(0, -1), mouth="smile", blush=0.25, glow=0.0, wing=None, rot=0.0, legs=True)
    jitter = (0.0, 0.0)

    # 起：見上げる → だんだんしょんぼり
    if t < 6.5:
        sad = seg(t, 3.0, 5.6)
        st["look"] = (0.2, -1)
        if sad > 0.5:
            st.update(eyes="sad", mouth="frown", blush=0.1, look=(0.2, -0.8))
        elif sad > 0.15:
            st["mouth"] = "line"
        st["rot"] = lerp(-6, 4, sad)

    # 承：見上げて力む ×2 → うつむく
    elif t < 12.5:
        tries = [(6.7, 7.5, 8.7, 9.0), (9.2, 9.8, 10.9, 11.2)]   # 見上げ開始, 力み開始, チカッ, 力み終わり
        st.update(eyes="sad", mouth="frown", blush=0.1, look=(0, 0.4), rot=4)
        for a, b, flick, e in tries:
            if a <= t < b:
                st.update(eyes="open", mouth="line", look=(0.1, -1), rot=-8)
            elif b <= t < e:
                st.update(eyes="squeeze", mouth="wobble", blush=0.7, rot=-4)
                k = (t - b) / (e - b)
                amp = 1.4 + 1.6 * k
                jitter = (math.sin(t * 97) * amp, math.cos(t * 83) * amp * 0.6)
                st["glow"] = 0.85 * pulse(t, flick, flick + 0.2, 0.05)
        if t >= 11.2:
            down = seg(t, 11.2, 12.0)
            st.update(eyes="sad", mouth="frown", look=(0, lerp(0.3, 1, down)), rot=lerp(4, 14, down), blush=0)

    # 転①：子に気づく
    elif t < 16.4:
        st.update(eyes="sad", mouth="frown", look=(0, 1), rot=14, blush=0)
        if t > 13.9:
            turn = seg(t, 13.9, 14.4)
            st.update(look=(lerp(0, 1, turn), lerp(1, 0.2, turn)), rot=lerp(14, 0, turn))
        if t > 14.6:
            st.update(eyes="wide", mouth="o", look=(1, 0.2), rot=-2)

    # 転②：飛んで子の上へ → 目を閉じて願う
    elif t < 19.8:
        fly = seg(t, 16.4, 17.6)
        hover = (CHILD_HOME[0] - 4, CHILD_HOME[1] - 62)
        x = lerp(HERO_HOME[0], hover[0], fly)
        y = lerp(HERO_HOME[1], hover[1], fly) - math.sin(fly * math.pi) * 30 + math.sin(t * 3) * 3 * fly
        st.update(eyes="open", mouth="smile", look=(0.3, 1), wing=t * 45, legs=False, rot=lerp(0, 8, fly),
                  blush=0.3)
        if t > 18.2:
            st.update(eyes="closed", mouth="smile", look=(0, 0), rot=0, blush=0.45)
            st["glow"] = 0.18 * seg(t, 18.4, 19.7, ease_out) * (0.8 + 0.2 * math.sin(t * 12))

    # 灯る〜結：光る → 道を照らしながら一緒に進む
    else:
        st.update(wing=t * 45, legs=False, glow=1.0, look=(0.6, 0.6))
        hx, hy = hero_hover(t)
        x, y = hx, hy
        if t < 20.4:
            st.update(eyes="closed", mouth="smile")
        elif t < 21.4:
            st.update(eyes="wide", mouth="o", blush=0.4, look=(0, 0.3))          # 自分の光に驚く
        elif t < 23.2:
            st.update(eyes="happy", mouth="smile", blush=1.0)                    # 照れる
        elif t < 29:
            st.update(eyes="open", mouth="smile", blush=0.5, look=(0.8, 0.5))
        else:
            st.update(eyes="happy", mouth="smile", blush=0.7)
        st["glow"] = lerp(1.0, 0.85, seg(t, 29, 33))

    st["x"], st["y"] = x + jitter[0], y + jitter[1]
    return st


def child_pos(t):
    """子カタツムリの位置と向き（つる草をわたる）。"""
    if t < 24.6:
        x, y = CHILD_HOME
        return x, y, 0.0, 0.0
    u = seg(t, 24.6, 28.2, ease_in_out)
    if u < 0.12:     # 葉の先からつるへ
        k = u / 0.12
        vx, vy, ang = VINE.at(0.02)
        return lerp(CHILD_HOME[0], vx, k), lerp(CHILD_HOME[1], vy - CHILD_S, k), ang * k, u
    if u < 0.88:
        k = (u - 0.12) / 0.76
        vx, vy, ang = VINE.at(0.02 + 0.96 * k)
        return vx, vy - CHILD_S * 1.0, ang * 0.8, u
    k = (u - 0.88) / 0.12
    vx, vy, ang = VINE.at(0.98)
    return lerp(vx, CHILD_END[0], k), lerp(vy - CHILD_S, CHILD_END[1], k), ang * 0.8 * (1 - k), u


def hero_hover(t):
    """光ったあとの主人公の位置（子の少し先を飛ぶ）。"""
    over_child = (CHILD_HOME[0] - 4, CHILD_HOME[1] - 62)
    if t < 24.4:
        return over_child[0], over_child[1] + math.sin(t * 3) * 3 - seg(t, 19.8, 20.6, ease_out) * 14
    cx, cy, _, _ = child_pos(t)
    ahead = (cx + 70, cy - 70)
    k = seg(t, 24.4, 25.4)
    x = lerp(over_child[0], ahead[0], k)
    y = lerp(over_child[1] - 14, ahead[1], k) + math.sin(t * 3) * 4
    if t > 28.4:          # 親子の上へ
        end = (CHILD_END[0] + 30, CHILD_END[1] - 88)
        k2 = seg(t, 28.4, 29.6)
        x, y = lerp(x, end[0], k2), lerp(y, end[1], k2)
    return x, y


def light_radius(t):
    if t < 19.8:
        return 0.0
    r = 430 * seg(t, 19.8, 20.9, ease_out)
    return r * lerp(1, 0.62, seg(t, 29, 33.5))


# ---------------------------------------------------------------- 1フレーム
def ambient_fn(t):
    def f(X, Y):
        import numpy as np
        a = 1.0 - 0.6 * np.clip((Y - 900) / 600, 0, 1)                          # 下ほど暗い（木の陰）
        d = ((X - 830) / 300) ** 2 + ((Y - 1480) / 150) ** 2
        a = a * (1 - 0.88 * np.exp(-d))                                           # 母のいる右側はとくに暗い
        return a
    return f


def render(t):
    cx, cy, z = CAM(t)
    amb = lerp(1.0, 0.78, seg(t, 4, 12.5)) * lerp(1.0, 0.82, seg(t, 12.5, 19.8))
    fr = Frame(SIZE, Cam(cx, cy, z), ambient=amb, ambient_map=ambient_fn(t))
    fr.fade = seg(t, 37.0, 38.0)

    scenery.sky(fr)
    scenery.stars(fr, t)
    scenery.moon(fr)
    scenery.trees(fr, t)

    hs = hero_state(t)
    swarm(fr, t)

    bv, ev = fr.base(), fr.emit()
    # 月明かり（主人公のいる葉のあたり）
    fr.lights.append(Light(300, 1420, 260, 0.55, (0.55, 0.68, 1.0)))

    LEAF_R.draw(bv, t)
    LEAF_L.draw(bv, t)
    VINE.draw(bv, t)

    # 母カタツムリ
    happy = seg(t, 22.0, 22.6)
    mood_m = "content" if t > 28.4 else ("happy" if happy > 0.5 else "normal")
    snail.draw(bv, MOTHER_POS[0], MOTHER_POS[1], MOTHER_S, palette=snail.MOTHER, flip=True, mood=mood_m,
               stalk=1.0, t=t)

    # 子カタツムリ
    appear = seg(t, 12.6, 13.6)
    if appear > 0:
        x, y, ang, crawl = child_pos(t)
        sees_hero = seg(t, 17.2, 17.8)
        if t < 22.0:
            mood, stalk, tears, look = "sad", lerp(0.25, 0.55, sees_hero), 1.0 - 0.5 * seg(t, 20.0, 21.0), -sees_hero
        elif t < 28.4:
            mood, stalk, tears, look = "happy", 1.0, 0.0, 0
        else:
            mood, stalk, tears, look = "content", 1.0, 0.0, 0
        snail.draw(bv, x, y, CHILD_S, mood=mood, stalk=stalk, tears=tears, look=look, t=t, crawl=crawl * 6,
                   alpha=appear, rot=ang)

    # ハート
    if t > 28.6:
        k = seg(t, 28.6, 30.4, ease_out)
        hx = (CHILD_END[0] + MOTHER_POS[0]) / 2 + 4
        snail.heart(bv, hx + math.sin(t * 3) * 3, CHILD_END[1] - 30 - 40 * k, 9 + 3 * k,
                    alpha=pulse(t, 28.6, 33.5, 0.6))

    # 主人公
    firefly.draw(bv, hs["x"], hs["y"], HERO_S, rot=hs["rot"], eyes=hs["eyes"], look=hs["look"],
                 mouth=hs["mouth"], blush=hs["blush"], glow=hs["glow"], wing=hs["wing"], legs=hs["legs"])
    gx, gy = firefly.draw_glow(ev, hs["x"], hs["y"], HERO_S, hs["glow"], rot=hs["rot"])
    if hs["glow"] > 0.05 and t < 19.8:      # 失敗のチカッ／祈りのかすかな光
        fr.lights.append(Light(gx, gy, 70, hs["glow"] * 0.8))
    r = light_radius(t)
    if r > 0:
        fr.lights.append(Light(gx, gy, r, 1.35, falloff=1.1))
        # 光の輪が広がる
        k = clamp((t - 19.8) / 1.4)
        if k < 1:
            a = (1 - k) ** 1.5
            for dr in (0, 10, 20):
                ring = []
                rr = 20 + 420 * ease_out(k) + dr
                for i in range(73):
                    an = i / 72 * 2 * math.pi
                    ring.append((gx + math.cos(an) * rr, gy + math.sin(an) * rr))
                ev.line(ring, (255, 230, 150, int(80 * a * (1 - dr / 30))), 5)

    scenery.grass(fr, t)

    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
