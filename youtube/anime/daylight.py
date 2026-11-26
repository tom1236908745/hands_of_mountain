"""昼・夕方・夜・雨の野原（時間帯と天気を変えられる舞台セット）。

scenery.py（月夜の森）とちがい、色をテーマ（THEMES）で切り替え・補間できる。
  th = blend("day", "dusk", u)    # 昼→夕方へ u (0〜1) だけ進んだ色
  sky(fr, th); trees(fr, t, th); MEADOW.draw(bv, t, th); grass(fr, t, th)
小道具：太陽・月・星・雲・雨・虹・流れ星・花・岩としずく・切り株・うろこ・本・葉っぱの傘
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image

from engine import SS, bezier, ease_out, lerp

THEMES = {
    "day": dict(sky_top=(120, 182, 232), sky_bot=(214, 236, 240), trees=[(150, 196, 170), (118, 172, 140), (86, 146, 112)],
                ground=(128, 182, 112), ground_top=(160, 206, 132), grass=(84, 140, 86), cloud=(255, 255, 255), stars=0.0),
    "morning": dict(sky_top=(150, 190, 232), sky_bot=(252, 226, 200), trees=[(164, 196, 176), (130, 176, 146), (96, 150, 116)],
                    ground=(132, 184, 118), ground_top=(168, 210, 140), grass=(88, 142, 90), cloud=(255, 246, 240), stars=0.0),
    "dusk": dict(sky_top=(94, 96, 160), sky_bot=(250, 170, 120), trees=[(118, 104, 136), (90, 80, 112), (62, 56, 86)],
                 ground=(96, 110, 96), ground_top=(130, 140, 110), grass=(56, 64, 70), cloud=(255, 200, 180), stars=0.15),
    "night": dict(sky_top=(12, 16, 46), sky_bot=(28, 70, 92), trees=[(26, 50, 74), (16, 36, 56), (9, 22, 36)],
                  ground=(34, 70, 58), ground_top=(58, 108, 84), grass=(8, 18, 24), cloud=(70, 80, 110), stars=1.0),
    "rain": dict(sky_top=(96, 108, 126), sky_bot=(160, 170, 180), trees=[(116, 136, 140), (92, 116, 118), (70, 96, 98)],
                 ground=(96, 138, 104), ground_top=(120, 160, 120), grass=(62, 100, 74), cloud=(150, 156, 166), stars=0.0),
}


def blend(a, b, u):
    A = THEMES[a] if isinstance(a, str) else a
    B = THEMES[b] if isinstance(b, str) else b
    u = max(0.0, min(1.0, u))

    def mix(x, y):
        if isinstance(x, list):
            return [mix(p, q) for p, q in zip(x, y)]
        if isinstance(x, tuple):
            return tuple(int(lerp(p, q, u)) for p, q in zip(x, y))
        return lerp(x, y, u)
    return {k: mix(A[k], B[k]) for k in A}


# ---------------------------------------------------------------- 空・天体
@lru_cache(maxsize=6)
def _sky_img(w, h, top, bot):
    y = np.linspace(0, 1, h * SS, dtype=np.float32)[:, None] ** 0.9
    t, b = np.array(top, np.float32), np.array(bot, np.float32)
    col = np.repeat(t + (b - t) * y[..., None], w * SS, axis=1)
    return Image.fromarray(col.astype(np.uint8))


def sky(fr, th):
    q = lambda c: tuple(int(v) // 3 * 3 for v in c)  # noqa: E731  キャッシュが効くように丸める
    w, h = fr.size
    fr.base_img.paste(_sky_img(w, h, q(th["sky_top"]), q(th["sky_bot"])), (0, 0))


@lru_cache(maxsize=1)
def _stars():
    rnd = random.Random(7)
    return [(rnd.uniform(-200, 1280), rnd.uniform(-300, 1100), rnd.uniform(1.2, 3.2), rnd.uniform(0, 6.28),
             rnd.uniform(0.6, 2.0)) for _ in range(140)]


def stars(fr, t, alpha):
    if alpha <= 0.01:
        return
    ev = fr.emit(parallax=0.06)
    for x, y, r, ph, sp in _stars():
        a = alpha * (0.55 + 0.45 * math.sin(t * sp + ph))
        ev.circle(x, y, r, tuple(int(c * a) for c in (230, 236, 255)))


def sun(fr, x, y, r=95, alpha=1.0, color=(255, 236, 170)):
    if alpha <= 0.01:
        return
    ev = fr.emit(parallax=0.1)
    ev.glow(x, y, r * 2.4, tuple(int(c * 0.5) for c in color), strength=0.15 * alpha, rings=14)
    ev.circle(x, y, r, tuple(int(c * 0.36 * alpha) for c in color))


def moon(fr, x, y, r=90, alpha=1.0):
    if alpha <= 0.01:
        return
    ev = fr.emit(parallax=0.1)
    ev.glow(x, y, r * 2.6, (90, 110, 140), strength=0.25 * alpha, rings=14)
    ev.circle(x, y, r, tuple(int(c * 0.66 * alpha) for c in (250, 246, 220)))
    ev.circle(x - r * 0.3, y - r * 0.2, r * 0.22, tuple(int(c * alpha) for c in (196, 192, 168)))


def shooting_stars(fr, t, t0, n=7, seed=4):
    ev = fr.emit(parallax=0.08)
    rnd = random.Random(seed)
    for i in range(n):
        s0 = t0 + i * 0.55 + rnd.uniform(0, 0.3)
        u = (t - s0) / 0.8
        if not 0 <= u <= 1:
            continue
        x0, y0 = rnd.uniform(200, 1100), rnd.uniform(80, 500)
        x, y = x0 - 420 * u, y0 + 240 * u
        a = math.sin(math.pi * u)
        ev.line([(x, y), (x + 260, y - 150)], (170, 180, 230, int(200 * a)), 7)
        ev.line([(x, y), (x + 110, y - 63)], (255, 250, 230, int(240 * a)), 6)
        ev.glow(x, y, 36, (255, 250, 220), strength=a)


# ---------------------------------------------------------------- 雲・木・地面
@lru_cache(maxsize=1)
def _clouds():
    rnd = random.Random(21)
    return [(rnd.uniform(-300, 1300), rnd.uniform(150, 800), rnd.uniform(0.7, 1.3), rnd.uniform(6, 16)) for _ in range(7)]


def clouds(fr, t, th, alpha=0.9, dark=0.0):
    if alpha <= 0.01:
        return
    cv = fr.base(parallax=0.2)
    col = tuple(int(lerp(c, 120, dark)) for c in th["cloud"])
    for x, y, s, sp in _clouds():
        cx = (x + t * sp + 400) % 1900 - 400
        for dx, dy, r in ((0, 0, 90), (-90, 25, 65), (95, 20, 70), (40, -40, 70)):
            cv.circle(cx + dx * s, y + dy * s, r * s, col + (int(230 * alpha),))


@lru_cache(maxsize=3)
def _trees(layer):
    rnd = random.Random(300 + layer)
    out = []
    xs = sorted(rnd.uniform(-250, 1330) for _ in range([8, 7, 5][layer]))
    base_y = [1300, 1360, 1430][layer]
    for x in xs:
        top = base_y - rnd.uniform(300, 560) + layer * 40
        blobs = [(x + rnd.uniform(-130, 130), top + rnd.uniform(0, 260), rnd.uniform(90, 160) * (1 + layer * 0.12))
                 for _ in range(8)]
        out.append((x, top, rnd.uniform(24, 36) * (1 + layer * 0.3), blobs))
    return out


def trees(fr, t, th):
    for layer in range(3):
        cv = fr.base(parallax=[0.35, 0.55, 0.78][layer])
        col = th["trees"][layer]
        for x, top, tw, blobs in _trees(layer):
            sway = math.sin(t * 0.5 + x * 0.01) * 5 * (layer + 1) / 3
            cv.poly([(x - tw, 2300), (x + tw, 2300), (x + tw * 0.5 + sway, top + 200), (x - tw * 0.5 + sway, top + 200)], col)
            for bx, by, br in blobs:
                cv.circle(bx + sway, by, br, col)
        gy = [1380, 1480, 1560][layer]
        cv.poly([(-600, gy), (1700, gy - 30), (1700, 2400), (-600, 2400)], col)


class Meadow:
    """ゆるやかな野原。ground_at(x) が地面の高さ。"""

    def __init__(self, ground_y=1500):
        self.g = ground_y

    def ground_at(self, x):
        return self.g + 10 * math.sin(x * 0.006) + 4 * math.sin(x * 0.021)

    def draw(self, cv, t, th):
        top = [(x, self.ground_at(x)) for x in range(-500, 1700, 30)]
        cv.poly(top + [(1700, 2600), (-500, 2600)], th["ground"])
        cv.line(top, th["ground_top"], 9)
        rnd = random.Random(5)
        for _ in range(40):
            x = rnd.uniform(-300, 1400)
            y = self.ground_at(x) + 2
            for k in (-1, 0, 1):
                sway = math.sin(t * 1.1 + x) * 3
                cv.poly([(x + k * 7 - 4, y), (x + k * 7 + 4, y), (x + k * 12 + sway, y - rnd.uniform(16, 32))],
                        th["ground_top"])


def grass(fr, t, th, parallax=1.25):
    cv = fr.base(parallax=parallax)
    rnd = random.Random(3)
    for i in range(70):
        x = -120 + i * 19 + rnd.uniform(-8, 8)
        hgt = rnd.uniform(70, 200)
        sway = math.sin(t * 1.2 + i * 0.7) * 12
        cv.poly([(x - 9, 2000), (x + 9, 2000), (x + rnd.uniform(-40, 40) + sway, 1960 - hgt)], th["grass"])


# ---------------------------------------------------------------- 天気
def rain(fr, t, amount=1.0, seed=9, shelter=None):
    """shelter=(x0, x1, y) の範囲（傘の下）には雨を降らせない。"""
    if amount <= 0.01:
        return
    cv = fr.base(parallax=1.0)
    rnd = random.Random(seed)
    cx, cy, z = fr.cam.cx, fr.cam.cy, fr.cam.zoom
    w, h = fr.size[0] / z, fr.size[1] / z
    n = int(160 * amount)
    for i in range(n):
        x0 = rnd.uniform(-0.1, 1.1)
        sp = rnd.uniform(0.9, 1.3)
        ph = rnd.random()
        u = (t * sp * 1.6 + ph) % 1.0
        x = cx - w / 2 + x0 * w - u * 60 / z
        y = cy - h / 2 + u * h * 1.1
        ln = 46 / z ** 0.5
        if shelter and shelter[0] < x < shelter[1] and y > shelter[2]:
            continue
        cv.line([(x, y), (x - ln * 0.25, y + ln)], (210, 226, 240, int(150 * amount)), max(1.5, 3 / z ** 0.3))


def rainbow(fr, alpha, cx=540, cy=1500, r=900):
    if alpha <= 0.01:
        return
    cv = fr.base(parallax=0.25)
    cols = [(240, 120, 120), (246, 180, 110), (246, 226, 130), (140, 210, 140), (120, 180, 230), (150, 140, 220)]
    for i, col in enumerate(cols):
        rr = r - i * 26
        pts = [(cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))) for a in range(180, 361, 4)]
        cv.line(pts, col + (int(120 * alpha),), 26)


# ---------------------------------------------------------------- 小道具
def flower(cv, x, y, s, k, petal=(250, 170, 190), center=(255, 214, 110)):
    """ぽんっと咲く花。k = 0〜1 の咲き具合。"""
    if k <= 0:
        return
    kk = ease_out(min(1, k * 1.3)) * (1 + 0.15 * math.sin(min(1, k) * math.pi))
    cv.line([(x, y), (x, y - 26 * s * min(1, k * 2))], (90, 150, 90), 5 * s)
    fy = y - 30 * s * min(1, k * 2)
    for i in range(5):
        a = i / 5 * 2 * math.pi
        cv.circle(x + math.cos(a) * 11 * s * kk, fy + math.sin(a) * 11 * s * kk, 9 * s * kk, petal)
    cv.circle(x, fy, 7 * s * kk, center)


def rock(cv, x, y, w, h, hollow=0.0):
    """岩（上にくぼみ）。hollow 0〜1 でくぼみが深くなる。"""
    pts = [(x - w / 2, y), (x - w / 2 + 14, y - h * 0.7), (x - w / 4, y - h), (x + w / 4, y - h * 0.98),
           (x + w / 2 - 10, y - h * 0.65), (x + w / 2, y)]
    cv.poly([(px, py + 6) for px, py in pts], (70, 74, 82))
    cv.poly(pts, (150, 156, 164))
    cv.poly([(x - w / 4 + 8, y - h + 6), (x + w / 5, y - h + 4), (x + w / 3, y - h * 0.8), (x - w / 3, y - h * 0.78)],
            (176, 182, 190))
    if hollow > 0:
        cv.ellipse(x, y - h + 10, 26 * (0.4 + hollow), 7 + 6 * hollow, (96, 104, 116))
        cv.ellipse(x, y - h + 8, 20 * (0.4 + hollow), 4 + 3 * hollow, (130, 170, 200, 200))


def drip(cv, x, y_top, y_bottom, t, period=1.2, phase=0.0):
    """ぽたっと落ちるしずく。"""
    u = ((t + phase) % period) / period
    if u < 0.75:
        k = u / 0.75
        y = y_top + (y_bottom - y_top) * k * k
        r = 7
        cv.ellipse(x, y, r * 0.8, r, (170, 210, 240, 230))
        cv.poly([(x - r * 0.7, y - r * 0.3), (x + r * 0.7, y - r * 0.3), (x, y - r * 2.2)], (170, 210, 240, 230))
    else:
        k = (u - 0.75) / 0.25
        for dx in (-1, 1):
            cv.circle(x + dx * 16 * k, y_bottom - 10 * math.sin(k * math.pi), 4 * (1 - k), (170, 210, 240, 200))


def stump(cv, x, y, w, h, th=None):
    bark, top_c, ring = (132, 96, 70), (214, 176, 130), (176, 136, 98)
    cv.poly([(x - w / 2, y + 4), (x + w / 2, y + 4), (x + w / 2 - 6, y - h), (x - w / 2 + 6, y - h)], bark)
    for k in (-0.25, 0.1, 0.32):
        cv.line([(x + k * w, y), (x + k * w + 4, y - h + 10)], (110, 78, 56), 4)
    cv.ellipse(x, y - h, w / 2 - 6, 16, top_c)
    cv.ellipse(x, y - h, w / 4, 8, ring)


def scale_piece(cv, x, y, s, rot, alpha=1.0):
    """目から落ちる「うろこ」（銀色の半月形・きらり）。"""
    pts = []
    for i in range(13):
        a = math.radians(rot + 180 + i * 15)
        pts.append((x + math.cos(a) * s, y + math.sin(a) * s * 0.8))
    cv.poly(pts, (200, 220, 240, int(230 * alpha)))
    cv.line(pts, (120, 150, 180, int(230 * alpha)), 2)


def flying_book(cv, x, y, s, flap, rot=0.0):
    """風に飛ばされる ことば帖（ページがぱたぱた）。"""
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def P(lx, ly):
        return x + (lx * cr - ly * sr) * s, y + (lx * sr + ly * cr) * s
    a = 0.6 + 0.4 * math.sin(flap)
    for sx in (-1, 1):
        cv.poly([P(0, 0), P(sx * 1.0, -0.25 * a), P(sx * 1.0, 0.75), P(0, 0.9)], (126, 158, 182))
        cv.poly([P(0, -0.04), P(sx * 0.9, -0.3 * a), P(sx * 0.9, 0.62), P(0, 0.8)], (255, 250, 232))
    cv.line([P(0, -0.04), P(0, 0.85)], (104, 82, 74), 0.08 * s)


def leaf_umbrella(cv, x, y, s, tilt=0.0):
    """大きな葉っぱの傘（柄の先 = x,y）。"""
    cr, sr = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))

    def P(lx, ly):
        return x + (lx * cr - ly * sr) * s, y + (lx * sr + ly * cr) * s
    cv.line([P(0, 0), P(0, -1.3)], (90, 120, 70), 0.07 * s)
    up = [P(1.3 * math.cos(a), -1.3 - 0.75 * math.sin(a)) for a in np.linspace(0, math.pi, 24)]
    cv.poly(up + [P(-1.25, -1.2), P(-0.6, -1.32), P(0, -1.22), P(0.6, -1.32), P(1.25, -1.2)], (96, 168, 104))
    cv.line([P(0, -1.3), P(0, -2.0)], (150, 206, 150), 0.05 * s)
    for k in (-0.6, 0.6):
        cv.line([P(0, -1.6), P(k * 1.6, -1.45)], (150, 206, 150), 0.04 * s)
