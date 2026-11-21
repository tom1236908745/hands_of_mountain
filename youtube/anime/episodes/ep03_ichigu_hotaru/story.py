"""ショートアニメ『一隅を照らす』ほたるにゃん版 — 絵とタイムライン（仕様は spec.md）。

ep01（ホタル版）と同じ時間割・同じ音楽で、主人公を「ほたるの着ぐるみを着たことにゃん」にしたもの。
羽があるので、ep01 と同じように飛んで子ねこの上でホバリングし、道を照らす。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIME = HERE.parent.parent
sys.path[:0] = [str(ANIME), str(ANIME / "cast")]

import neko  # noqa: E402
import scenery  # noqa: E402
import snail  # noqa: E402  (ハート)
from engine import (MINCHO, Cam, Caption, Frame, Light, Track, clamp, draw_captions, ease_out, lerp,  # noqa: E402
                    pulse, seg)

FPS = 30
SIZE = (1080, 1920)
DURATION = 38.0

# ---------------------------------------------------------------- 配置
BANKS = scenery.Banks(ground_y=1490, left_edge=470, right_edge=715, water_y=1575)
STONE_PTS = [(528, 1566), (592, 1574), (656, 1566)]
STONES = scenery.Stones(STONE_PTS)
G = BANKS.ground_at

CAT_S, KIT_S, MOM_S = 135, 82, 150
CAT_HOME = 235
KIT_HOME = 405
MOM_X = 905
STONE_TOP = [(x, y - 14) for x, y in STONE_PTS]

# ---------------------------------------------------------------- カメラ（ワールド中心x, y, ズーム）
WIDE = (540, 960, 1.0)
FACE = (250, 1440, 3.4)
TEN1 = (320, 1438, 2.4)
TEN2 = (360, 1375, 2.4)
TOMORU = (600, 1430, 1.5)
KETSU = (700, 1440, 1.6)
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


# ---------------------------------------------------------------- ぴょん（ジャンプ）
def hop_path(t, start, hops, dur=0.5, height=46):
    """hops = [(開始時刻, (x, ground)), ...]。戻り値 (x, ground, squash)。"""
    x, g = start
    for t0, (nx, ng) in hops:
        if t < t0 - 0.12:
            return x, g, 1.0
        if t < t0:                                      # ため（しゃがむ）
            return x, g, lerp(1.0, 0.86, (t - (t0 - 0.12)) / 0.12)
        if t < t0 + dur:                                # 空中
            u = (t - t0) / dur
            y = lerp(g, ng, u) - height * math.sin(math.pi * u)
            return lerp(x, nx, ease_out(u) * 0.3 + u * 0.7), y, 1.08 - 0.08 * abs(u - 0.5) * 2
        if t < t0 + dur + 0.14:                         # 着地でぺたん
            k = (t - t0 - dur) / 0.14
            x, g = nx, ng
            return x, g, lerp(0.86, 1.0, k)
        x, g = nx, ng
    return x, g, 1.0


KIT_HOPS = [(25.0, STONE_TOP[0]), (25.7, STONE_TOP[1]), (26.4, STONE_TOP[2]), (27.1, (765, G(765))),
            (27.75, (840, G(840)))]
HOVER_CHILD = (KIT_HOME - 8, G(KIT_HOME) - 88)       # 子ねこの上（足の位置）
HOVER_END = ((840 + MOM_X) / 2, G(870) - 120)          # 親子の上


def cat_state(t):
    """ほたるにゃん：位置（足の位置）・つぶれ具合・表情・光・羽・飛んでいるか。"""
    x, g, sq = CAT_HOME, G(CAT_HOME), 1.0
    expr, glow, rot, flap, flying = "normal", 0.0, 0.0, 0.0, False
    jit = 0.0
    if t < 6.5:                                             # 起：見上げる → しょんぼり
        rot = -4 * (1 - seg(t, 3.0, 5.0))
        expr = "normal" if t < 3.4 else ("sad" if t < 5.2 else "pien")
        flap = 0.3 * math.sin(t * 2.0) if t < 3.4 else 0.0
    elif t < 12.5:                                          # 承：力む ×2（お尻がチカッ）→ うなだれる
        expr = "sad"
        for a, b, flick, e in ((6.7, 7.5, 8.7, 9.0), (9.2, 9.8, 10.9, 11.2)):
            if a <= t < b:
                expr, sq = "normal", lerp(1.0, 1.05, seg(t, a, a + 0.3))
            elif b <= t < e:
                expr = "strain"
                sq = 0.93 + 0.02 * math.sin(t * 40)
                jit = math.sin(t * 97) * (2 + 2 * (t - b) / (e - b))
                flap = math.sin(t * 55)
                glow = 0.85 * pulse(t, flick, flick + 0.2, 0.05)
        if t >= 11.2:
            expr = "sad" if t < 11.9 else "pien"
            rot = 6 * seg(t, 11.2, 11.9)
            sq = lerp(1.0, 0.95, seg(t, 11.2, 11.9))
    elif t < 16.4:                                          # 転①：気づく
        expr, rot, sq = "pien", 6, 0.95
        if t > 14.1:
            rot, sq = lerp(6, 0, seg(t, 14.1, 14.5)), lerp(0.95, 1.0, seg(t, 14.1, 14.5))
            expr = "sad"
        if t > 14.6:
            expr = "surprised"
    else:                                                   # 転②〜：飛ぶ
        flying = True
        flap = math.sin(t * 34)
        k = seg(t, 16.5, 17.6)
        x = lerp(CAT_HOME, HOVER_CHILD[0], k)
        g = lerp(G(CAT_HOME), HOVER_CHILD[1], k) - math.sin(k * math.pi) * 30
        rot = 10 * math.sin(k * math.pi)
        if t >= 24.4:                                       # 子ねこの少し先を飛んで照らす
            kx, kg, _ = hop_path(t, (KIT_HOME, G(KIT_HOME)), KIT_HOPS, dur=0.5, height=34)
            ahead = (kx + 80, kg - 95)
            k2 = seg(t, 24.4, 25.2)
            x, g = lerp(HOVER_CHILD[0], ahead[0], k2), lerp(HOVER_CHILD[1], ahead[1], k2)
            rot = 6 * math.sin(t * 2)
            if t > 28.0:                                    # 親子の上へ
                k3 = seg(t, 28.0, 29.2)
                x, g = lerp(x, HOVER_END[0], k3), lerp(g, HOVER_END[1], k3)
        g += math.sin(t * 3.1) * 6                          # ふわふわ
        expr = "normal"
        if 18.3 < t < 19.8:
            expr = "calm"
            glow = 0.18 * seg(t, 18.4, 19.7, ease_out) * (0.8 + 0.2 * math.sin(t * 12))
        if t >= 19.8:
            glow = lerp(1.0, 0.85, seg(t, 29, 33))
            if t < 20.4:
                expr = "calm"
            elif t < 21.4:
                expr = "surprised"
            elif t < 23.2:
                expr = "shy"
            elif t < 29:
                expr = "happy"
            else:
                expr = "calm"
    return dict(x=x + jit, g=g, sq=sq, expr=expr, lantern=glow, rot=rot, flap=flap, flying=flying)


def kitten_state(t):
    x, g, sq = KIT_HOME, G(KIT_HOME), 1.0
    if t >= 24.9:
        x, g, sq = hop_path(t, (KIT_HOME, G(KIT_HOME)), KIT_HOPS, dur=0.5, height=34)
    if t < 22.0:
        expr = "pien"
    elif t < 28.3:
        expr = "happy"
    else:
        expr = "calm"
    rot = 7 * seg(t, 28.3, 28.9)
    return dict(x=x, g=g, sq=sq, expr=expr, rot=rot)


def light_radius(t):
    if t < 19.8:
        return 0.0
    r = 440 * seg(t, 19.8, 20.9, ease_out)
    return r * lerp(1, 0.62, seg(t, 29, 33.5))


def ambient_fn(t):
    def f(X, Y):
        import numpy as np
        a = 1.0 - 0.6 * np.clip((Y - 900) / 600, 0, 1)                           # 下ほど暗い
        d = ((X - 900) / 330) ** 2 + ((Y - 1430) / 230) ** 2
        a = a * (1 - 0.96 * np.exp(-d))                                            # 母のいる右岸
        d2 = ((X - 600) / 150) ** 2 + ((Y - 1570) / 70) ** 2
        a = a * (1 - 0.6 * np.exp(-d2))                                            # 小川・飛び石
        return a
    return f


# ---------------------------------------------------------------- 1フレーム
def render(t):
    cx, cy, z = CAM(t)
    amb = lerp(1.0, 0.78, seg(t, 4, 12.5)) * lerp(1.0, 0.82, seg(t, 12.5, 19.8))
    fr = Frame(SIZE, Cam(cx, cy, z), ambient=amb, ambient_map=ambient_fn(t))
    fr.fade = seg(t, 37.0, 38.0)
    fr.light_cap = 1.22

    scenery.sky(fr)
    scenery.stars(fr, t)
    scenery.moon(fr)
    scenery.trees(fr, t)
    scenery.firefly_swarm(fr, t)

    bv, ev = fr.base(), fr.emit()
    fr.lights.append(Light(260, 1440, 280, 0.55, (0.55, 0.68, 1.0)))          # 月明かり
    BANKS.draw(bv, ev, t)
    STONES.draw(bv)

    # 母ねこ
    mom_expr = "calm" if t > 28.3 else ("happy" if t > 22.0 else "normal")
    neko.shadow(bv, MOM_X, G(MOM_X), MOM_S)
    neko.draw(fr, MOM_X, G(MOM_X), MOM_S, mom_expr, palette="mother", rot=-7 * seg(t, 28.3, 28.9),
              blink=(t % 4.1) < 0.12 and mom_expr == "normal")

    # ことにゃん（右岸に渡ったあとは子ねこより奥）と子ねこ
    cs = cat_state(t)
    ks = kitten_state(t)
    appear = seg(t, 12.6, 13.6)

    def draw_cat():
        ground_here = G(cs["x"])
        if cs["flying"]:
            hgt = max(0.0, ground_here - cs["g"])
            neko.shadow(bv, cs["x"], ground_here, CAT_S * max(0.4, 1 - hgt / 300), alpha=45)
        else:
            neko.shadow(bv, cs["x"], cs["g"], CAT_S, alpha=70)
        blink = (t % 3.3) < 0.12 and cs["expr"] in ("normal",)
        return neko.draw(fr, cs["x"], cs["g"], CAT_S, cs["expr"], item="firefly", lantern=cs["lantern"],
                         squash=cs["sq"], rot=cs["rot"], blink=blink, flap=cs["flap"])

    def draw_kit():
        if appear > 0:
            neko.shadow(bv, ks["x"], ks["g"], KIT_S, alpha=int(60 * appear))
            neko.draw(fr, ks["x"], ks["g"], KIT_S, ks["expr"], palette="kitten", squash=ks["sq"], rot=ks["rot"],
                      alpha=appear)

    draw_kit()
    lx, ly = draw_cat()

    # ハート
    if t > 28.6:
        k = seg(t, 28.6, 30.4, ease_out)
        hx = (840 + MOM_X) / 2
        snail.heart(bv, hx + math.sin(t * 3) * 3, G(870) - 150 - 50 * k, 13 + 4 * k, alpha=pulse(t, 28.6, 33.5, 0.6))

    # ちょうちんの光
    lv = cs["lantern"]
    if lv > 0.01:
        ev.glow(lx, ly, CAT_S * (0.14 + 0.32 * lv), (255, 230, 150), strength=min(0.85, lv * 0.85))
    if lv > 0.05 and t < 19.8:
        fr.lights.append(Light(lx, ly, 90, lv * 0.8))
    r = light_radius(t)
    if r > 0:
        fr.lights.append(Light(lx, ly, r, 1.15, falloff=1.0))
        k = clamp((t - 19.8) / 1.4)
        if k < 1:
            a = (1 - k) ** 1.5
            for dr in (0, 10, 20):
                rr = 20 + 430 * ease_out(k) + dr
                ring = [(lx + math.cos(i / 72 * 2 * math.pi) * rr, ly + math.sin(i / 72 * 2 * math.pi) * rr)
                        for i in range(73)]
                ev.line(ring, (255, 230, 150, int(80 * a * (1 - dr / 30))), 5)

    scenery.grass(fr, t)
    draw_captions(fr, CAPTIONS, t)
    from PIL import Image
    return Image.fromarray(fr.compose())
