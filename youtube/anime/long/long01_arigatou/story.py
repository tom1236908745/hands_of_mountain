"""長編01『ありがとう』— 絵とタイムライン（横長 1920x1080・仕様は spec.md）。

場面（シーン）ごとに描く関数を分け、render(t) が時刻で切りかえる。
場面のつなぎ目は、白・紺・紙色などへの「ディップ」（いったん色に溶けて、次の場面が出てくる）でなめらかにつなぐ。
"""
from __future__ import annotations

import math
import random
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ANIME = HERE.parent.parent
sys.path[:0] = [str(HERE), str(ANIME), str(ANIME / "cast")]

import daylight as dl  # noqa: E402
import kit  # noqa: E402
import neko  # noqa: E402
import snail  # noqa: E402  (ハート)
import turtle as tt  # noqa: E402
from engine import (GOTHIC, MINCHO, SS, Cam, Caption, Frame, Light, Track, clamp, draw_captions, ease_in_out,  # noqa: E402
                    ease_out, font, lerp, pulse, seg)

import pace  # noqa: E402  （テンポ調整：お話の時間 → 動画の時間）

FPS = 30
SIZE = (1920, 1080)
W, H = SIZE
DURATION = round(pace.OUT_END * FPS) / FPS          # 動画の長さ（つめたあと）
STORY_DURATION = 310.0                               # お話の時間（この中の時刻はすべてこちら）

INK = (84, 62, 54)
PAPER = (252, 246, 232)
TITLE_FONT = "MPLUSRounded1c-ExtraBold.ttf"

# ---------------------------------------------------------------- 場面の時間割
OPEN, BOOK, PAGE, DEEP, SURF, RISE, MEET, SUTRA, BACK, THANK, END = (
    0.0, 15.0, 23.0, 50.5, 112.0, 160.0, 176.0, 198.0, 230.0, 264.0, 292.0)
DIPS = [  # (つなぎ目の時刻, 色, 長さ)
    (BOOK + 8.0, (255, 250, 236), 2.4),   # 本が光って ページへ（白）
    (DEEP, (12, 34, 66), 2.2),            # ページ → 海の底（紺）
    (SURF, (210, 232, 246), 2.0),         # 海の底 → 海の上（明るい水色）
    (RISE, (20, 60, 100), 2.0),           # 海の上 → 水の中
    (MEET, (255, 255, 255), 1.4),         # 水面へ（白い光）
    (SUTRA, (6, 10, 24), 2.4),            # 夜へ
    (BACK, (255, 250, 236), 2.4),         # 野原へ もどる（白）
    (END, PAPER, 2.0),                    # ことば帖のページへ
]


def C(t0, t1, text, **kw):
    """横長の字幕：画面の下。"""
    kw.setdefault("size", 50)
    kw.setdefault("y", 0.885)
    return Caption(t0, t1, text, **kw)


def P(t0, t1, text, y, size, fnt=GOTHIC, color=INK):
    """紙の上の文字（影なし・こげ茶）。"""
    return Caption(t0, t1, text, size=size, y=y, font=fnt, color=color, shadow=False, rise=14, fade_out=0.6)


CAPTIONS = [
    # オープニング
    C(0.6, 4.2, "ある 晴れた朝。"),
    C(4.4, 9.4, "子ねこが、お魚クッキーを 分けてくれました。"),
    C(15.4, 20.6, "…「ありがとう」って、どういう 意味だろう？"),
    # ことば帖のページ
    P(24.6, 48.7, "ありがとう", 0.22, 96, TITLE_FONT),
    P(27.6, 48.7, "もとは", 0.34, 40),
    P(28.6, 48.7, "有り難し", 0.47, 150, MINCHO, (150, 70, 50)),
    P(30.6, 48.7, "ありがたし", 0.585, 40, MINCHO, (150, 110, 90)),
    P(33.6, 48.7, "有ることが 難しい", 0.675, 54),
    P(37.2, 48.7, "＝ めったに ない", 0.765, 62, TITLE_FONT, (150, 70, 50)),
    C(25.4, 31.6, "「ありがとう」は、もともと「有り難し」という ことば。", y=0.935, size=46),
    C(34.0, 41.0, "「有ることが 難しい」――めったに ない、という 意味です。", y=0.935, size=46),
    C(42.0, 48.6, "その「めったに ない」を たとえた、むかしの お話が あります。", y=0.935, size=46),
    # 海の底
    C(52.6, 57.0, "広い 広い 海の 底に、"),
    C(57.4, 63.6, "目の見えない、一匹の 年老いた 亀が すんでいました。"),
    C(64.2, 70.3, "亀は、いつもは 海の底で しずかに くらし、"),
    C(70.6, 76.6, "百年に 一度だけ、海の上に 顔を出します。"),
    C(86.0, 90.0, "春が来て、"),
    C(91.0, 95.0, "夏が来て、"),
    C(96.0, 100.0, "秋が来て、"),
    C(101.0, 104.8, "冬が来て……"),
    C(105.4, 110.6, "それを、百回 くりかえして。"),
    # 海の上
    C(113.4, 118.0, "海の上には、穴のあいた 丸太が 一本。"),
    C(118.6, 124.6, "百年の あいだ、ずっと ただよっていました。"),
    C(128.0, 131.8, "風が吹けば、東へ。"),
    C(132.2, 136.6, "波が来れば、西へ。"),
    C(140.2, 145.0, "嵐の日も、"),
    C(151.6, 155.8, "凪の日も。"),
    C(156.0, 159.9, "広い 広い 海の、どこかで。"),
    # 水の中 → 出会い
    C(161.4, 165.8, "百年目の、その日。"),
    C(166.2, 172.2, "亀は、ゆっくりと 海の上へ のぼっていきました。"),
    C(172.6, 175.4, "――そして。"),
    C(178.6, 183.2, "顔を出した、ちょうど そこに――"),
    C(184.6, 189.4, "丸太の 穴が ありました。"),
    C(190.4, 197.0, "それくらい、めったに ない こと。"),
    # 夜：法句経
    Caption(200.4, 213.4, "人の生を受くるは難く、", size=66, font=MINCHO, y=0.17, fade_in=1.2, fade_out=1.0),
    Caption(202.6, 213.4, "やがて死すべきものの、", size=66, font=MINCHO, y=0.26, fade_in=1.2, fade_out=1.0),
    Caption(204.8, 213.4, "いま生命あるは 有り難し", size=66, font=MINCHO, y=0.35, fade_in=1.2, fade_out=1.0),
    Caption(207.0, 213.4, "―― 『法句経』", size=40, font=MINCHO, y=0.445, fade_in=1.0, fade_out=1.0),
    C(214.4, 219.0, "人として 生まれ、いま 生きていることは、"),
    C(219.4, 224.4, "それよりも もっと、めったに ないこと。"),
    C(224.8, 229.2, "お釈迦さまは、そう たとえました。"),
    # 野原へ
    C(231.0, 236.6, "ことにゃんは、野原に もどってきました。"),
    C(236.8, 241.8, "子ねこと、おいしい ごはんが あること。"),
    C(243.2, 248.2, "くろが いること。"),
    C(250.2, 254.6, "今日も、空が 晴れていること。"),
    C(256.2, 263.0, "どれも ほんとうは、めったに ないこと。"),
    C(282.0, 286.2, "「ありがとう」は、"),
    C(286.6, 291.6, "めったに ない しあわせに、気づいた ときの ことば。"),
    # エンディング
    P(293.8, 309.0, "有り難い", 0.3, 150, MINCHO, (150, 70, 50)),
    P(296.0, 309.0, "めったに ない。だから、ありがたい。", 0.46, 58),
    P(302.0, 309.0, "ことにゃんのありがた言葉", 0.56, 34, GOTHIC, (150, 110, 90)),
]


# ================================================================ 共通の小道具
def dip_alpha(t):
    for t0, col, ln in DIPS:
        if abs(t - t0) < ln / 2:
            return col, 1 - abs(t - t0) / (ln / 2)
    return None, 0.0


def fish_cookie(cv, x, y, s, rot=0.0):
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def Pt(lx, ly):
        return x + (lx * cr - ly * sr) * s, y + (lx * sr + ly * cr) * s
    body = [Pt(0.6 * math.cos(a), 0.36 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24)]
    cv.poly(body, (226, 170, 104))
    cv.poly([Pt(0.5, 0), Pt(0.95, -0.32), Pt(0.95, 0.32)], (226, 170, 104))
    cv.line(body + body[:1], INK, 0.07 * s)
    cv.circle(*Pt(-0.3, -0.05), 0.07 * s, INK)
    for k in (-0.05, 0.15):
        cv.line([Pt(k, -0.18), Pt(k + 0.1, 0.18)], (196, 140, 80), 0.05 * s)


# ---------------------------------------------------------------- 横長の野原
GROUND = 830


def ground_at(x):
    return GROUND + 10 * math.sin(x * 0.004) + 4 * math.sin(x * 0.017)


@lru_cache(maxsize=1)
def _land_trees():
    rnd = random.Random(31)
    layers = []
    for layer in range(3):
        trees = []
        x = -300
        while x < 2300:
            top = [520, 560, 610][layer] - rnd.uniform(0, 120)
            blobs = [(x + rnd.uniform(-110, 110), top + rnd.uniform(0, 180), rnd.uniform(80, 140) * (1 + layer * 0.15))
                     for _ in range(7)]
            trees.append((x, top, rnd.uniform(20, 32) * (1 + layer * 0.3), blobs))
            x += rnd.uniform(200, 330)
        layers.append(trees)
    return layers


def meadow(fr, t, th, sun_xy=(1580, 190)):
    dl.sky(fr, th)
    dl.stars(fr, t, th.get("stars", 0))
    dl.sun(fr, *sun_xy, r=80)
    dl.clouds(fr, t, th, alpha=0.9)
    for layer, trees in enumerate(_land_trees()):
        cv = fr.base(parallax=[0.35, 0.55, 0.78][layer])
        col = th["trees"][layer]
        for x, top, tw, blobs in trees:
            sway = math.sin(t * 0.5 + x * 0.01) * 4
            cv.poly([(x - tw, 1400), (x + tw, 1400), (x + tw * 0.5 + sway, top + 160), (x - tw * 0.5 + sway, top + 160)], col)
            for bx, by, br in blobs:
                cv.circle(bx + sway, by, br, col)
        gy = [760, 800, 840][layer]
        cv.poly([(-900, gy), (2800, gy - 20), (2800, 1900), (-900, 1900)], col)
    cv = fr.base()
    top = [(x, ground_at(x)) for x in range(-800, 2800, 40)]
    cv.poly(top + [(2800, 2000), (-800, 2000)], th["ground"])
    cv.line(top, th["ground_top"], 9)
    rnd = random.Random(5)
    for _ in range(60):
        x = rnd.uniform(-600, 2600)
        y = ground_at(x) + 2
        for k in (-1, 0, 1):
            sway = math.sin(t * 1.1 + x) * 3
            cv.poly([(x + k * 7 - 4, y), (x + k * 7 + 4, y), (x + k * 12 + sway, y - rnd.uniform(16, 32))],
                    th["ground_top"])


def meadow_grass(fr, t, th):
    cv = fr.base(parallax=1.25)
    rnd = random.Random(3)
    for i in range(130):
        x = -300 + i * 20 + rnd.uniform(-8, 8)
        hgt = rnd.uniform(50, 140)
        sway = math.sin(t * 1.2 + i * 0.7) * 10
        cv.poly([(x - 9, 1120), (x + 9, 1120), (x + rnd.uniform(-30, 30) + sway, 1085 - hgt)], th["grass"])


# ---------------------------------------------------------------- 本のページ
def paper_scene(fr, t, cat_expr="happy", cat_xy=(1500, 905), cat_s=230, flip_k=0.0):
    """机の上に、大きなことば帖のページ。flip_k: 0〜1 でページがめくれて消える。"""
    bv = fr.base()
    bv.poly([(-50, -50), (W + 50, -50), (W + 50, H + 50), (-50, H + 50)], (214, 196, 166))
    for k in range(9):                                     # 木目
        y = 40 + k * 130
        bv.line([(-20, y), (W + 20, y + 20 * math.sin(k))], (200, 180, 150), 4)
    sx = 1 - ease_in_out(flip_k)                          # めくれる（横につぶれる）
    x0, x1 = W / 2 - 640 * sx, W / 2 + 640 * sx
    y0, y1 = 70, 960
    if sx > 0.02:
        bv.poly([(x0 + 14, y0 + 16), (x1 + 14, y0 + 16), (x1 + 14, y1 + 16), (x0 + 14, y1 + 16)], (150, 126, 100))
        bv.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], PAPER)
        bv.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], INK, 6)
        for k in range(1, 8):                              # うすい罫線
            y = y0 + k * (y1 - y0) / 8
            bv.line([(x0 + 40 * sx, y), (x1 - 40 * sx, y)], (236, 226, 204), 2)
    if cat_expr and flip_k < 0.98:                         # ページといっしょに消える
        neko.draw(fr, cat_xy[0], cat_xy[1], cat_s, cat_expr, item="book", alpha=1 - ease_in_out(flip_k))


# ---------------------------------------------------------------- 海（水の中）
SURFACE_Y = -1500
FLOOR_Y = 930


def depth_color(y):
    u = clamp((y - SURFACE_Y) / (FLOOR_Y - SURFACE_Y))
    top, bot = np.array((70, 150, 196)), np.array((10, 30, 62))
    return tuple(int(v) for v in top + (bot - top) * u ** 0.8)


@lru_cache(maxsize=6)
def _water_img(top, bot):
    y = np.linspace(0, 1, H * SS, dtype=np.float32)[:, None]
    t, b = np.array(top, np.float32), np.array(bot, np.float32)
    col = np.repeat(t + (b - t) * y[..., None], W * SS, axis=1)
    return Image.fromarray(col.astype(np.uint8))


def water_bg(fr, tint=(0, 0, 0), tint_k=0.0):
    cx, cy, z = fr.cam.cx, fr.cam.cy, fr.cam.zoom
    top = depth_color(cy - H / 2 / z)
    bot = depth_color(cy + H / 2 / z)
    q = lambda c: tuple(int(lerp(a, b, tint_k)) // 4 * 4 for a, b in zip(c, tint))  # noqa: E731
    fr.base_img.paste(_water_img(q(top), q(bot)), (0, 0))


@lru_cache(maxsize=1)
def _sea_life():
    rnd = random.Random(8)
    weeds = [(rnd.uniform(-400, 2400), rnd.uniform(120, 300), rnd.uniform(0, 6)) for _ in range(22)]
    rocks = [(rnd.uniform(-400, 2400), rnd.uniform(40, 110)) for _ in range(12)]
    bubbles = [(rnd.uniform(-300, 2300), rnd.uniform(0, 1), rnd.uniform(3, 9), rnd.uniform(0.04, 0.09)) for _ in range(40)]
    fish = [(rnd.uniform(0, 1), rnd.uniform(-600, 700), rnd.uniform(14, 24), rnd.uniform(0.02, 0.05), rnd.choice((1, -1)))
            for _ in range(10)]
    return weeds, rocks, bubbles, fish


def sea_floor(fr, t, light=1.0):
    bv, ev = fr.base(), fr.emit()
    weeds, rocks, bubbles, fish = _sea_life()
    # 光の筋
    for k in range(7):
        x = -200 + k * 380 + 60 * math.sin(t * 0.2 + k)
        a = 5 * light * (0.6 + 0.4 * math.sin(t * 0.5 + k * 1.7))
        if a > 0.5:
            ev.poly([(x, SURFACE_Y), (x + 90, SURFACE_Y), (x + 420, FLOOR_Y), (x + 260, FLOOR_Y)],
                    (int(a), int(a * 1.8), int(a * 2.2)))
    # 砂の底
    floor = [(x, FLOOR_Y + 14 * math.sin(x * 0.006)) for x in range(-600, 2700, 60)]
    bv.poly(floor + [(2700, 2000), (-600, 2000)], (60, 70, 82))
    bv.line(floor, (86, 98, 108), 6)
    for x, r in rocks:
        bv.ellipse(x, FLOOR_Y + 10, r, r * 0.55, (44, 52, 64))
        bv.ellipse(x - r * 0.2, FLOOR_Y - r * 0.15, r * 0.5, r * 0.2, (64, 74, 86))
    # 海藻
    for x, hgt, ph in weeds:
        pts = []
        for i in range(9):
            u = i / 8
            pts.append((x + math.sin(t * 0.9 + ph + u * 2.5) * 22 * u, FLOOR_Y - hgt * u))
        bv.line(pts, (44, 96, 84), 18)
        bv.line(pts, (60, 120, 100), 9)
    # 泡
    for x, ph, r, sp in bubbles:
        u = (ph + t * sp) % 1.0
        y = lerp(FLOOR_Y, SURFACE_Y, u)
        bv.circle(x + math.sin(t * 2 + ph * 9) * 10, y, r, (180, 220, 240, 90))
        bv.circle(x - r * 0.3 + math.sin(t * 2 + ph * 9) * 10, y - r * 0.3, r * 0.3, (230, 245, 255, 140))
    # 小さな魚
    fv = fr.base(parallax=0.7)
    for ph, y, s, sp, d in fish:
        u = (ph + t * sp) % 1.0
        x = lerp(-300, 2200, u) if d > 0 else lerp(2200, -300, u)
        fv.ellipse(x, y + math.sin(t * 3 + ph * 7) * 8, s, s * 0.45, (110, 150, 170, 200))
        fv.poly([(x - d * s, y), (x - d * s * 1.7, y - s * 0.5), (x - d * s * 1.7, y + s * 0.5)], (110, 150, 170, 200))


def falling(fr, t, t0, t1, kind):
    """季節のもの（花びら・木の葉・雪）が 水の中に ゆっくり しずんでくる。"""
    if not t0 <= t <= t1:
        return
    a = pulse(t, t0, t1, 0.8)
    bv = fr.base(parallax=0.9)
    rnd = random.Random({"petal": 1, "leaf": 2, "snow": 3, "sun": 4}[kind])
    cx, cy, z = fr.cam.cx, fr.cam.cy, fr.cam.zoom
    for i in range(36):
        x0, ph, sp = rnd.uniform(-0.1, 1.1), rnd.random(), rnd.uniform(0.08, 0.16)
        u = (ph + (t - t0) * sp) % 1.0
        x = cx - W / 2 / z + x0 * W / z + math.sin(t * 1.3 + i) * 30
        y = cy - H / 2 / z + u * H / z * 1.1
        if kind == "petal":
            bv.ellipse(x, y, 10, 6, (250, 190, 205, int(220 * a)), rot=t * 60 + i * 30)
        elif kind == "leaf":
            bv.ellipse(x, y, 14, 7, ((230, 150, 80), (210, 110, 70), (236, 190, 90))[i % 3] + (int(220 * a),),
                       rot=t * 50 + i * 40)
        elif kind == "snow":
            bv.circle(x, y, 5 + (i % 3), (250, 252, 255, int(230 * a)))
        elif kind == "sun":
            bv.circle(x, y, 3, (255, 250, 210, int(150 * a)))


# ---------------------------------------------------------------- 海の上
HORIZON = 470
SEA_DAY = dict(sky_top=(120, 182, 232), sky_bot=(214, 236, 240), sea_far=(110, 170, 205), sea_near=(46, 110, 160),
               foam=(230, 244, 250), cloud=(255, 255, 255), trees=[(0, 0, 0)] * 3, stars=0.0)
SEA_STORM = dict(sky_top=(70, 80, 96), sky_bot=(120, 130, 140), sea_far=(70, 96, 112), sea_near=(30, 56, 76),
                 foam=(200, 210, 216), cloud=(110, 116, 128), trees=[(0, 0, 0)] * 3, stars=0.0)
SEA_DUSK = dict(sky_top=(94, 96, 160), sky_bot=(250, 180, 130), sea_far=(200, 140, 130), sea_near=(70, 80, 130),
                foam=(255, 220, 200), cloud=(255, 206, 186), trees=[(0, 0, 0)] * 3, stars=0.1)
SEA_NIGHT = dict(sky_top=(8, 12, 36), sky_bot=(24, 50, 84), sea_far=(30, 56, 90), sea_near=(10, 22, 46),
                 foam=(120, 150, 190), cloud=(40, 50, 80), trees=[(0, 0, 0)] * 3, stars=1.0)


def mix_theme(a, b, u):
    return dl.blend(a, b, u)


def wave_y(x, t, row, amp):
    return (math.sin(x * 0.006 + t * (0.9 + row * 0.25) + row * 1.7) * amp
            + math.sin(x * 0.017 - t * 1.3 + row) * amp * 0.35)


def sea_surface(fr, t, th, amp=1.0, front=True):
    """水平線から手前へ、波の帯を重ねる。front=False なら いちばん手前の帯を描かない（丸太の手前用に後で）。"""
    bv = fr.base()
    rows = 7
    for r in range(rows if front else rows - 1):
        k = r / (rows - 1)
        y0 = lerp(HORIZON, 1150, k ** 1.6)
        col = tuple(int(lerp(a, b, k)) for a, b in zip(th["sea_far"], th["sea_near"]))
        a = (4 + 26 * k) * amp
        pts = [(x, y0 + wave_y(x, t, r, a)) for x in range(-400, 2400, 40)]
        bv.poly(pts + [(2400, 1600), (-400, 1600)], col)
        bv.line(pts, th["foam"] + (int(90 + 80 * k),), 2 + 3 * k)


def sea_front(fr, t, th, amp=1.0):
    bv = fr.base()
    r, k = 6, 1.0
    y0 = lerp(HORIZON, 1150, 1.0)
    a = 30 * amp
    pts = [(x, y0 + wave_y(x, t, r, a)) for x in range(-400, 2400, 40)]
    bv.poly(pts + [(2400, 1600), (-400, 1600)], th["sea_near"])
    bv.line(pts, th["foam"] + (170,), 5)


def log_pos(t):
    """丸太のx（風で東へ、波で西へ）。"""
    x = 960 + 60 * math.sin(t * 0.21)
    x += 360 * seg(t, 128.0, 131.8) - 640 * seg(t, 132.2, 136.6) + 280 * seg(t, 151.0, 158.0)
    return x


def driftwood(cv, x, y, s, rot=0.0, hole=True):
    """穴のあいた丸太（少し上から見た形）。"""
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def Pt(lx, ly):
        return x + (lx * cr - ly * sr) * s, y + (lx * sr + ly * cr) * s
    body = [Pt(-1, -0.2), Pt(1, -0.2), Pt(1, 0.2), Pt(-1, 0.2)]
    cv.poly(body, (150, 108, 72))
    cv.poly([Pt(-1, -0.2), Pt(1, -0.2), Pt(1, -0.06), Pt(-1, -0.06)], (176, 132, 92))
    for k in (-0.6, -0.1, 0.45):                                     # 木目
        cv.line([Pt(k, -0.12), Pt(k + 0.3, -0.1)], (120, 84, 56), 0.03 * s)
    cv.line(body + body[:2], (104, 74, 50), 0.05 * s)
    end = [Pt(1 + 0.08 * math.cos(a), 0.2 * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, 12)]
    cv.poly([Pt(1, -0.2)] + end + [Pt(1, 0.2)], (214, 176, 130))
    cv.line([Pt(1, -0.2)] + end, (104, 74, 50), 0.04 * s)
    if hole:
        hp = [Pt(0.17 * math.cos(a), -0.08 + 0.09 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24)]
        cv.poly(hp, (34, 62, 92))
        cv.line(hp + hp[:1], (104, 74, 50), 0.035 * s)
    return Pt(0, -0.08)


def log_front_lip(cv, x, y, s, rot=0.0):
    """頭が穴から出たとき、丸太の手前のふちを上から重ねる。"""
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def Pt(lx, ly):
        return x + (lx * cr - ly * sr) * s, y + (lx * sr + ly * cr) * s
    lip = [Pt(0.17 * math.cos(a), -0.08 + 0.09 * math.sin(a)) for a in np.linspace(0, math.pi, 14)]
    cv.poly(lip + [Pt(-0.3, 0.2), Pt(0.3, 0.2)], (150, 108, 72))
    cv.line(lip, (104, 74, 50), 0.035 * s)


# ================================================================ 各場面
def scene_open(t):
    """0〜23秒：朝の野原 → ことば帖が光る。"""
    th = dl.THEMES["day"]
    if t < BOOK:
        cam = Track([(0, (900, 640, 1.25)), (15, (940, 660, 1.35))])(t)
    else:
        bx, by = 820, ground_at(820) - 300 * 0.2
        u = seg(t, BOOK + 1.5, BOOK + 8.0, ease_in_out)
        cam = (lerp(940, bx, u), lerp(660, by, u), lerp(1.35, 4.2, u ** 1.3))
    fr = Frame(SIZE, Cam(*cam))
    fr.light_cap = 1.25
    meadow(fr, t, th)
    bv, ev = fr.base(), fr.emit()
    cat_x, cat_s, kit_s = 820, 300, 200
    # 子ねこ：右から来て、クッキーを分けてくれる
    kx, kg, ksq = kit.walk(t, 2.6, 5.4, 1500, 1060, ground_at)
    kexpr = "happy" if t > 5.4 else "normal"
    neko.shadow(bv, kx, ground_at(kx), kit_s, alpha=60)
    neko.draw(fr, kx, kg, kit_s, kexpr, palette="kitten", squash=ksq, flip=True)
    # ことにゃん
    if t < 6.4:
        expr = "normal"
    elif t < 11.0:
        expr = "happy"
    elif t < 15.0:
        expr = "thinking"
    else:
        expr = "thinking" if t < 18.6 else "surprised"
    item = "book" if t > 12.6 else None
    blink = (t % 3.7) < 0.12 and expr == "normal"
    neko.shadow(bv, cat_x, ground_at(cat_x), cat_s, alpha=60)
    neko.draw(fr, cat_x, ground_at(cat_x), cat_s, expr, item=item, blink=blink)
    # クッキー：子ねこの手元 → ことにゃんへ ふわっと
    hand = (kx - 70, kg - 70)
    if t < 6.2:
        fish_cookie(bv, hand[0], hand[1], 26, -10)
    elif t < 7.4:
        u = seg(t, 6.2, 7.4, ease_in_out)
        fish_cookie(bv, lerp(hand[0], cat_x + 60, u), lerp(hand[1], ground_at(cat_x) - 90, u) - 90 * math.sin(math.pi * u),
                    26, -10 + 360 * u)
    elif t < 12.6:
        fish_cookie(bv, cat_x + 60, ground_at(cat_x) - 90, 26, -10)
    if 7.4 < t < 9.2:
        snail.heart(bv, (cat_x + kx) / 2, ground_at(cat_x) - 250 - 40 * seg(t, 7.4, 9.2), 16, alpha=pulse(t, 7.4, 9.2, 0.3))
    # ことば帖が光る
    if t > BOOK + 2.0:
        g = seg(t, BOOK + 2.0, BOOK + 7.5)
        bx, by = cat_x, ground_at(cat_x) - cat_s * 0.2
        ev.glow(bx, by, 60 + 260 * g, (255, 236, 170), strength=min(1.0, g * 1.2))
        fr.lights.append(Light(bx, by, 200 + 300 * g, 0.8 * g))
    meadow_grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    img = Image.fromarray(fr.compose())
    if 8.0 < t < 10.6:
        img = kit.speech_bubble(img, cam, SIZE, cat_x + 30, ground_at(cat_x) - cat_s * 0.5, "ありがとう！",
                                alpha=pulse(t, 8.0, 10.6, 0.25), fsize=44, dx=-cat_s * 0.6)
    return img


def scene_page(t):
    """23〜50.5秒：ことば帖のページ「有り難し」。"""
    fr = Frame(SIZE, Cam(W / 2, H / 2, lerp(1.0, 1.03, seg(t, PAGE, DEEP))))
    expr = "happy" if t < 37.2 else ("surprised" if t < 39.0 else "happy")
    if t > 44.0:
        expr = "calm"
    paper_scene(fr, t, cat_expr=expr, flip_k=seg(t, 48.6, 49.9))
    draw_captions(fr, CAPTIONS, t)
    return Image.fromarray(fr.compose())


TURTLE_HOME = (880, 884)


def turtle_state(t):
    """海の底の亀：休む → 百年後に泳ぎ出す。"""
    x, y = TURTLE_HOME
    swim, rot, neck = None, 0.0, 0.25 + 0.05 * math.sin(t * 0.6)
    if t > 106.0:
        u = seg(t, 106.0, 112.0, lambda v: clamp(v) ** 1.6)
        swim = t * 4.0
        rot = -lerp(0, 32, seg(t, 106, 108))
        x, y = lerp(TURTLE_HOME[0], 1500, u), lerp(TURTLE_HOME[1], 0, u)
        neck = 0.8
    return x, y, swim, rot, neck


def years_text(t):
    if t < 85.5 or t > 111.0:
        return None
    if t < 105.4:
        return "1年"                                      # 春・夏・秋・冬で 1年
    return f"{max(1, int(lerp(1, 100, seg(t, 105.4, 108.8, lambda v: clamp(v) ** 1.3))))}年"


def scene_deep(t):
    """50.5〜112秒：海の底の亀と、めぐる季節。"""
    if t < 58.5:
        cy = lerp(-900, 680, seg(t, DEEP, 58.5, ease_in_out))
    else:
        cy = 680 - 30 * math.sin((t - 58.5) * 0.15) * seg(t, 58.5, 62)
    z = 1.0 + 0.25 * seg(t, 60, 68, ease_in_out) - 0.25 * seg(t, 82, 86, ease_in_out)
    cx = 960 + 40 * math.sin(t * 0.07)
    if t > 106:
        cy = lerp(cy, 300, seg(t, 106, 112, ease_in_out))
    fr = Frame(SIZE, Cam(cx, cy, z))
    # 季節で水の色を少し変える（春：桃・夏：明るい・秋：だいだい・冬：白っぽい）
    tint, tk = (0, 0, 0), 0.0
    for t0, t1, col, k in ((85.5, 90.5, (120, 90, 120), 0.18), (90.5, 95.5, (90, 180, 210), 0.22),
                           (95.5, 100.5, (150, 100, 60), 0.2), (100.5, 105.5, (170, 190, 210), 0.25)):
        if t0 - 0.6 <= t <= t1 + 0.6:
            tint, tk = col, k * pulse(t, t0 - 0.6, t1 + 0.6, 0.9)
    flick = 0.0
    if 104.8 < t < 108.6:                                 # 百年が 早送りで過ぎていく（光がまたたく）
        flick = 0.5 + 0.5 * math.sin(t * 22)
        tint, tk = (200, 220, 240), 0.15 * flick * pulse(t, 104.8, 108.6, 0.6)
    water_bg(fr, tint, tk)
    sea_floor(fr, t, light=1.0 + 0.6 * flick)
    falling(fr, t, 85.5, 90.6, "petal")
    falling(fr, t, 90.5, 95.6, "sun")
    falling(fr, t, 95.5, 100.6, "leaf")
    falling(fr, t, 100.5, 105.6, "snow")
    x, y, swim, rot, neck = turtle_state(t)
    bv = fr.base()
    if t <= 106:
        bv.ellipse(x, FLOOR_Y + 6, 190, 22, (20, 26, 36, 120))
    breathe = 1 + 0.012 * math.sin(t * 1.2)
    tt.draw(bv, x, y, 175 * breathe, swim=swim, rot=rot, neck=neck)
    if swim is None and 60 < t < 104:                     # ゆっくり あがる 小さな泡
        for i in range(3):
            u = ((t * 0.25 + i / 3) % 1.0)
            hx, hy = tt.head_world(x, y, 175, neck)
            bv.circle(hx + 20 + math.sin(t + i) * 6, hy - 40 - u * 240, 5 + i * 2, (200, 230, 250, int(160 * (1 - u))))
    draw_captions(fr, CAPTIONS, t)
    img = Image.fromarray(fr.compose())
    yt = years_text(t)
    if yt:
        d = ImageDraw.Draw(img)
        f = font(MINCHO, 64)
        a = pulse(t, 85.5, 111.0, 0.6)
        col = tuple(int(255 * a + c * (1 - a)) for c in (40, 60, 90))
        d.text((W - 90 - f.getlength(yt), 70), yt, font=f, fill=col)
    return img


def surf_theme(t):
    if t < 137.5:
        return SEA_DAY
    if t < 140.0:
        return mix_theme(SEA_DAY, SEA_STORM, seg(t, 137.5, 140.0))
    if t < 149.5:
        return SEA_STORM
    if t < 152.5:
        return mix_theme(SEA_STORM, SEA_DUSK, seg(t, 149.5, 152.5))
    return SEA_DUSK


def scene_surface(t):
    """112〜160秒：海の上をただよう丸太。風・波・嵐・凪。"""
    th = surf_theme(t)
    storm = seg(t, 138.0, 140.5) * (1 - seg(t, 149.0, 151.5))
    cam = Track([(SURF, (960, 560, 1.0)), (124, (960, 600, 1.25)), (138, (960, 560, 1.0)), (160, (980, 560, 1.05))])(t)
    fr = Frame(SIZE, Cam(*cam), ambient=1.0 - 0.18 * storm)
    fr.light_cap = 1.25
    dl.sky(fr, th)
    sx, sy = (1500, 200) if t < 150 else (lerp(1500, 1300, seg(t, 150, 160)), lerp(300, 440, seg(t, 150, 160)))
    dl.sun(fr, sx, sy, r=80, alpha=1 - storm, color=(255, 236, 170) if t < 150 else (255, 180, 120))
    dl.clouds(fr, t * (1 + 4 * storm), th, alpha=0.95, dark=0.3 * storm)
    amp = 1.0 + 1.6 * storm
    sea_surface(fr, t, th, amp)
    bv = fr.base()
    lx = log_pos(t)
    ly = HORIZON + 230 + wave_y(lx, t, 4, 18 * amp)
    rot = 4 * math.sin(t * 0.9) * amp
    driftwood(bv, lx, ly, 130, rot)
    sea_front(fr, t, th, amp)
    if 127.6 < t < 132.0:                                 # 風
        for i in range(6):
            u = ((t - 127.6) * 0.6 + i / 6) % 1.0
            y = 230 + i * 50
            bv.line([(lerp(-200, 2100, u), y), (lerp(-200, 2100, u) + 180, y - 10)], (255, 255, 255, int(150 * (1 - u))), 4)
    dl.rain(fr, t, storm)
    draw_captions(fr, CAPTIONS, t)
    img = Image.fromarray(fr.compose())
    for tl in (141.6, 146.1):                             # かみなり
        if tl < t < tl + 0.35:
            a = 0.55 * (1 - (t - tl) / 0.35)
            img = Image.blend(img, Image.new("RGB", SIZE, (240, 244, 255)), a)
    return img


def scene_rise(t):
    """160〜176秒：水の中から見上げる。水面に丸太のかげ。亀がのぼっていく。"""
    u = seg(t, RISE, MEET, lambda v: clamp(v))
    fr = Frame(SIZE, Cam(960, lerp(620, 420, ease_in_out(u)), 1.0))
    q = lambda c: tuple(int(v) // 4 * 4 for v in c)  # noqa: E731
    fr.base_img.paste(_water_img(q((140, 200, 226)), q((24, 70, 110))), (0, 0))
    bv, ev = fr.base(), fr.emit()
    surf = 120
    pts = [(x, surf + 10 * math.sin(x * 0.01 + t * 1.5)) for x in range(-300, 2300, 30)]
    bv.poly([(-300, -400), (2300, -400)] + pts[::-1], (200, 232, 246))
    bv.line(pts, (240, 250, 255), 6)
    for k in range(8):                                    # 水面のゆらめき
        x = -100 + k * 300 + 40 * math.sin(t * 0.8 + k)
        ev.poly([(x, surf), (x + 80, surf), (x + 260, 1300), (x + 140, 1300)], (6, 10, 12))
    # 水面に浮かぶ丸太のかげ（穴から 光がさしこむ）
    lx = 960 + 20 * math.sin(t * 0.5)
    bv.poly([(lx - 150, surf - 14), (lx + 150, surf - 14), (lx + 150, surf + 22), (lx - 150, surf + 22)], (40, 52, 60, 230))
    ev.ellipse(lx, surf + 6, 22, 12, (120, 140, 140))
    ev.poly([(lx - 18, surf + 10), (lx + 18, surf + 10), (lx + 70, 900), (lx - 70, 900)], (10, 12, 10))
    # のぼっていく亀
    tx = lerp(1250, lx - 240, ease_in_out(u))
    ty = lerp(1120, surf + 260, ease_in_out(u))
    tt.draw(bv, tx, ty, 150, swim=t * 4.2, rot=-58, neck=0.9)
    for i in range(6):
        v = ((t * 0.7 + i / 6) % 1.0)
        bv.circle(tx - 40 + math.sin(t * 3 + i) * 10, ty - v * 360, 4 + i % 3 * 2, (220, 240, 250, int(170 * (1 - v))))
    draw_captions(fr, CAPTIONS, t)
    return Image.fromarray(fr.compose())


POP_T = 183.6


def scene_meet(t):
    """176〜198秒：丸太の穴に、すぽっ。"""
    th = SEA_DAY
    cam = Track([(MEET, (960, 640, 1.9)), (POP_T, (960, 630, 2.15)), (189, (960, 630, 2.15)), (198, (960, 600, 1.5))])(t)
    fr = Frame(SIZE, Cam(*cam))
    fr.light_cap = 1.25
    dl.sky(fr, th)
    dl.sun(fr, 1400, 260, r=80)
    dl.clouds(fr, t, th, alpha=0.9)
    sea_surface(fr, t, th, 0.6)
    bv, ev = fr.base(), fr.emit()
    lx, ly = 960, HORIZON + 230 + wave_y(960, t, 4, 8)
    rot = 2 * math.sin(t * 0.8)
    hole = driftwood(bv, lx, ly, 150, rot)
    if t > POP_T:                                         # 頭が穴から ぴょこっ
        k = seg(t, POP_T, POP_T + 0.45, ease_out)
        over = 1 + 0.12 * math.sin(math.pi * seg(t, POP_T + 0.3, POP_T + 0.9))
        hx, hy = hole[0], hole[1] - 46 * k * over
        hs = 150 * 0.55 * (0.6 + 0.4 * k)
        nw = 150 * 0.13                                   # 首（穴の中から 頭まで）
        bv.poly([(hx - nw, hole[1] + 6), (hx + nw, hole[1] + 6), (hx + nw * 0.9, hy + hs * 0.1),
                 (hx - nw * 0.9, hy + hs * 0.1)], tt.SKIN)
        bv.line([(hx - nw, hole[1] + 6), (hx - nw * 0.9, hy + hs * 0.1)], tt.LINE, 5)
        bv.line([(hx + nw, hole[1] + 6), (hx + nw * 0.9, hy + hs * 0.1)], tt.LINE, 5)
        bv.line([(hx - nw * 0.7, hole[1] - 10), (hx + nw * 0.7, hole[1] - 12)], tt.LINE + (110,), 3)   # しわ
        tt.head_only(bv, hx, hy, hs, smile=seg(t, POP_T + 0.8, POP_T + 2.0))
        log_front_lip(bv, lx, ly, 150, rot)
        for i in range(10):                               # しぶき
            v = seg(t, POP_T, POP_T + 0.9)
            a = i / 10 * math.pi
            if v < 1:
                bv.circle(hx + math.cos(a) * 90 * v * (1 if i % 2 else -1), hy + 30 - math.sin(a) * 70 * v + 120 * v * v,
                          6 * (1 - v), (230, 244, 250, 220))
        g = pulse(t, POP_T + 0.2, POP_T + 4.5, 0.8)       # きらめき
        for i in range(12):
            a = i / 12 * 2 * math.pi + t * 0.4
            r = 150 + 90 * seg(t, POP_T, POP_T + 2.0, ease_out)
            ev.glow(hx + math.cos(a) * r, hy + math.sin(a) * r * 0.6, 14, (255, 236, 170), strength=g)
        ev.glow(hx, hy + 40, 260, (255, 240, 190), strength=0.12 * g)
    sea_front(fr, t, th, 0.6)
    draw_captions(fr, CAPTIONS, t)
    return Image.fromarray(fr.compose())


@lru_cache(maxsize=1)
def _night_stars():
    rnd = random.Random(17)
    return [(rnd.uniform(-100, 2020), rnd.uniform(-60, 440), rnd.uniform(1.2, 3.4), rnd.uniform(0, 6.3)) for _ in range(260)]


def scene_sutra(t):
    """198〜230秒：夜の海。法句経のことば。"""
    th = SEA_NIGHT
    fr = Frame(SIZE, Cam(960, lerp(520, 560, seg(t, SUTRA, BACK)), 1.0))
    dl.sky(fr, th)
    ev = fr.emit(parallax=0.1)
    for x, y, r, ph in _night_stars():
        a = 0.55 + 0.45 * math.sin(t * 1.3 + ph)
        ev.circle(x, y, r, tuple(int(c * a) for c in (230, 236, 255)))
    dl.moon(fr, 1500, 210, r=70)
    sea_surface(fr, t, th, 0.5)
    bv, ev2 = fr.base(), fr.emit()
    for i in range(10):                                   # 月の道
        y = HORIZON + 30 + i * 46
        w = 40 + i * 22
        ev2.line([(1500 - w + 30 * math.sin(t + i), y), (1500 + w + 30 * math.sin(t + i), y)], (60, 60, 50), 6)
    # 遠くに、丸太と亀（小さく）
    lx, ly = 520, HORIZON + 120 + wave_y(520, t, 2, 6)
    driftwood(bv, lx, ly, 50, 0)
    tt.head_only(bv, lx, ly - 20, 18, smile=1.0)
    sea_front(fr, t, th, 0.5)
    draw_captions(fr, CAPTIONS, t)
    return Image.fromarray(fr.compose())


def scene_back(t):
    """230〜292秒：野原に もどって、みんなに「ありがとう」。"""
    th = dl.blend("day", "morning", 0.3)
    cam = Track([(BACK, (960, 600, 1.25)), (235.6, (960, 600, 1.3)),
                 (237.6, (560, 640, 1.7)), (242.2, (560, 640, 1.7)),
                 (244.0, (1400, 610, 1.6)), (248.6, (1400, 610, 1.6)),
                 (250.6, (1100, -10, 1.25)), (254.8, (1100, -10, 1.25)),
                 (257.0, (960, 600, 1.15)), (263.6, (960, 600, 1.15)),
                 (266.4, (760, 640, 1.55)), (270.4, (760, 640, 1.55)),
                 (272.6, (1240, 620, 1.5)), (281.0, (1240, 620, 1.5)),
                 (283.0, (960, 600, 1.2)), (292.0, (960, 600, 1.2))])(t)
    fr = Frame(SIZE, Cam(*cam))
    fr.light_cap = 1.25
    meadow(fr, t, th, sun_xy=(1350, 160))
    bv, ev = fr.base(), fr.emit()
    CAT_S, KIT_S, KURO_S = 280, 190, 360
    KIT_X, KURO_X = 560, 1420
    # 子ねこ：クッキーをもぐもぐ
    kexpr = "happy" if (t % 2.2) < 1.6 else "calm"
    if 267.0 < t < 270.4:
        kexpr = "surprised" if t < 267.8 else "happy"
    neko.shadow(bv, KIT_X, ground_at(KIT_X), KIT_S, alpha=60)
    neko.draw(fr, KIT_X, ground_at(KIT_X), KIT_S, kexpr, palette="kitten", squash=1 - 0.03 * abs(math.sin(t * 5)))
    for i in range(3):                                    # お皿とクッキー
        fish_cookie(bv, KIT_X - 130 + i * 34, ground_at(KIT_X) - 16 - (i % 2) * 8, 22, 8 * i)
    bv.ellipse(KIT_X - 96, ground_at(KIT_X) - 2, 80, 14, (240, 236, 226))
    # くろ：お昼寝 → 起きて照れて「…ありがとう」
    if t < 274.0:
        kuro = "sleepy"
    elif t < 275.0:
        kuro = "surprised"
    elif t < 277.8:
        kuro = "blank"
    elif t < 284.0:
        kuro = "shy"
    else:
        kuro = "happy"
    neko.shadow(bv, KURO_X, ground_at(KURO_X), KURO_S, alpha=60)
    neko.draw(fr, KURO_X, ground_at(KURO_X), KURO_S, kuro, palette="kuro", flip=True,
              squash=1 - 0.02 * math.sin(t * 1.6) * (t < 274))
    # ことにゃん：まんなか → 子ねこへ → くろへ → まんなかへ
    if t < 264.4:
        cx, cg, csq = 960, ground_at(960), 1.0
    elif t < 271.0:
        cx, cg, csq = kit.walk(t, 264.4, 266.6, 960, 740, ground_at)
    elif t < 283.0:
        cx, cg, csq = kit.walk(t, 271.0, 273.8, 740, 1180, ground_at)
    else:
        cx, cg, csq = kit.walk(t, 283.0, 285.6, 1180, 960, ground_at)
    if t < 236.0:
        cexpr = "normal"
    elif t < 263.6:
        cexpr = "calm" if (t % 6) > 4 else "happy"
    elif t < 284.0:
        cexpr = "happy"
    else:
        cexpr = "calm"
    neko.shadow(bv, cx, ground_at(cx), CAT_S, alpha=60)
    neko.draw(fr, cx, cg, CAT_S, cexpr, item="book", squash=csq, flip=(271.0 < t < 283.0) is False and t > 264.4 and t < 271.0)
    for t0, x in ((268.0, (cx + KIT_X) / 2), (279.0, (cx + KURO_X) / 2), (286.0, 960)):
        if t0 < t < t0 + 2.4:
            snail.heart(bv, x, ground_at(x) - 300 - 50 * seg(t, t0, t0 + 2.4), 18, alpha=pulse(t, t0, t0 + 2.4, 0.4))
    if 250.0 < t < 255.0:                                 # 空がきらきら
        for i in range(6):
            ev.glow(700 + i * 160, 180 + 50 * math.sin(i), 16, (255, 240, 190), strength=pulse(t, 250, 255, 0.8) * 0.7)
    meadow_grass(fr, t, th)
    draw_captions(fr, CAPTIONS, t)
    img = Image.fromarray(fr.compose())
    bubbles = [((266.8, 269.8), cx, CAT_S, "ありがとう", -0.6), ((274.6, 277.4), cx, CAT_S, "ありがとう", -0.6),
               ((278.0, 281.0), KURO_X, KURO_S, "…ありがとう", 0.55)]
    for (b0, b1), bx, bs, text, side in bubbles:
        if b0 <= t <= b1:
            img = kit.speech_bubble(img, cam, SIZE, bx + side * bs * 0.2, ground_at(bx) - bs * 0.5, text,
                                    alpha=pulse(t, b0, b1, 0.25), fsize=44, dx=side * bs * 0.6)
    return img


def scene_end(t):
    """292〜310秒：ことば帖のページ「有り難い」。"""
    fr = Frame(SIZE, Cam(W / 2, H / 2, 1.0))
    expr = "happy" if t < 305 else "calm"
    paper_scene(fr, t, cat_expr=expr, cat_xy=(1480, 905), cat_s=240)
    fr.fade = seg(t, 308.6, STORY_DURATION)
    draw_captions(fr, CAPTIONS, t)
    img = Image.fromarray(fr.compose())
    if 299.0 < t < 308.0:
        img = kit.speech_bubble(img, (W / 2, H / 2, 1.0), SIZE, 1480 - 50, 905 - 120, "見てくれて、ありがとう",
                                alpha=pulse(t, 299.0, 308.0, 0.3), fsize=42, dx=-200)
    return img


SCENES = [(OPEN, scene_open), (PAGE, scene_page), (DEEP, scene_deep), (SURF, scene_surface), (RISE, scene_rise),
          (MEET, scene_meet), (SUTRA, scene_sutra), (BACK, scene_back), (END, scene_end)]


def render(t_out):
    """動画の時刻 → お話の時刻に直して描く。"""
    return render_story(pace.to_story(t_out))


def render_story(t):
    fn = SCENES[0][1]
    for t0, f in SCENES:
        if t >= t0:
            fn = f
    img = fn(t)
    col, a = dip_alpha(t)
    if a > 0:
        img = Image.blend(img, Image.new("RGB", SIZE, col), clamp(a) ** 0.8)
    return img
