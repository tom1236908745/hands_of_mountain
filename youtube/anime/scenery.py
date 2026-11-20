"""月夜の森の背景パーツ（ほかのエピソードでも使い回せる）。

すべてワールド座標（引きの画 = 1080x1920）で配置。parallax で奥行きを出す。
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image

from engine import SS, bezier, lerp

SKY_TOP = (8, 12, 40)
SKY_BOTTOM = (22, 74, 86)
MOON = (250, 246, 220)
STAR = (230, 236, 255)
TREE_COLORS = [(26, 50, 74), (16, 36, 56), (9, 22, 36)]
LEAF = (46, 104, 84)
LEAF_DARK = (30, 74, 60)
LEAF_VEIN = (84, 150, 118)
VINE = (60, 110, 76)
GRASS = (6, 16, 22)


# ---------------------------------------------------------------- 空
@lru_cache(maxsize=4)
def _sky_img(w, h):
    y = np.linspace(0, 1, h * SS, dtype=np.float32)[:, None]
    y = y ** 0.9
    top, bot = np.array(SKY_TOP, np.float32), np.array(SKY_BOTTOM, np.float32)
    col = top + (bot - top) * y[..., None]
    col = np.repeat(col, w * SS, axis=1)
    return Image.fromarray(col.astype(np.uint8))


def sky(fr):
    w, h = fr.size
    fr.base_img.paste(_sky_img(w, h), (0, 0))


@lru_cache(maxsize=1)
def _stars():
    rnd = random.Random(7)
    return [(rnd.uniform(-200, 1280), rnd.uniform(-300, 1100), rnd.uniform(1.2, 3.2), rnd.uniform(0, 6.28),
             rnd.uniform(0.6, 2.0)) for _ in range(140)]


def stars(fr, t, alpha=1.0):
    ev = fr.emit(parallax=0.06)
    for x, y, r, ph, sp in _stars():
        tw = 0.55 + 0.45 * math.sin(t * sp + ph)
        a = alpha * tw
        ev.circle(x, y, r, tuple(int(c * a) for c in STAR))


def moon(fr, x=790, y=330, r=105):
    ev = fr.emit(parallax=0.1)
    ev.glow(x, y, r * 2.6, (90, 110, 140), strength=0.25, rings=14)
    ev.circle(x, y, r, tuple(int(c * 0.66) for c in MOON))
    # うっすら模様
    ev.circle(x - r * 0.3, y - r * 0.2, r * 0.22, (196, 192, 168))
    ev.circle(x + r * 0.35, y + r * 0.25, r * 0.16, (196, 192, 168))
    ev.circle(x + r * 0.05, y - r * 0.45, r * 0.1, (200, 196, 172))


# ---------------------------------------------------------------- 木々
@lru_cache(maxsize=3)
def _trees(layer):
    rnd = random.Random(100 + layer)
    out = []
    n = [9, 7, 6][layer]
    xs = sorted(rnd.uniform(-250, 1330) for _ in range(n))
    base_y = [1250, 1330, 1420][layer]
    for x in xs:
        top = base_y - rnd.uniform(420, 820) + layer * 60
        blobs = []
        for _ in range(9):
            bx = x + rnd.uniform(-150, 150)
            by = top + rnd.uniform(0, 330)
            br = rnd.uniform(90, 170) * (1 + layer * 0.15)
            blobs.append((bx, by, br))
        trunk_w = rnd.uniform(26, 40) * (1 + layer * 0.3)
        out.append((x, top, trunk_w, blobs))
    return out


def trees(fr, t):
    for layer in range(3):
        par = [0.35, 0.55, 0.78][layer]
        cv = fr.base(parallax=par)
        col = TREE_COLORS[layer]
        for x, top, tw, blobs in _trees(layer):
            sway = math.sin(t * 0.5 + x * 0.01) * 6 * (layer + 1) / 3
            cv.poly([(x - tw, 2300), (x + tw, 2300), (x + tw * 0.5 + sway, top + 200),
                     (x - tw * 0.5 + sway, top + 200)], col)
            for bx, by, br in blobs:
                cv.circle(bx + sway * (1 - (by - top) / 400), by, br, col)
        # 地面（奥の層ほど明るい）
        gy = [1350, 1480, 1620][layer]
        cv.poly([(-600, gy), (1700, gy - 40), (1700, 2400), (-600, 2400)], col)


def grass(fr, t, parallax=1.25):
    cv = fr.base(parallax=parallax)
    rnd = random.Random(3)
    for i in range(70):
        x = -120 + i * 19 + rnd.uniform(-8, 8)
        hgt = rnd.uniform(90, 260)
        base = 1960
        sway = math.sin(t * 1.2 + i * 0.7) * 12
        tip = (x + rnd.uniform(-40, 40) + sway, base - hgt)
        cv.poly([(x - 9, base + 40), (x + 9, base + 40), tip], GRASS)


# ---------------------------------------------------------------- 葉とつる
class Leaf:
    """大きな葉。base（つけね）→ tip（先）。width は最大の半幅。"""

    def __init__(self, base, tip, width, stem_to):
        self.base, self.tip, self.width, self.stem_to = base, tip, width, stem_to
        dx, dy = tip[0] - base[0], tip[1] - base[1]
        self.len = math.hypot(dx, dy)
        self.ux, self.uy = dx / self.len, dy / self.len
        self.nx, self.ny = self.uy, -self.ux          # 上側を向く法線
        if self.ny > 0:
            self.nx, self.ny = -self.nx, -self.ny

    def half(self, u):
        return self.width * math.sin(math.pi * min(1, max(0, u))) ** 0.85 * (1 - 0.25 * u)

    def axis(self, u):
        return self.base[0] + (self.tip[0] - self.base[0]) * u, self.base[1] + (self.tip[1] - self.base[1]) * u

    def top(self, u):
        """葉の上面（キャラを乗せる位置）。"""
        ax, ay = self.axis(u)
        h = self.half(u) * 0.35        # 少し手前に傾いた葉なので、上面は中心線より少し上
        return ax + self.nx * h, ay + self.ny * h

    def draw(self, cv, t):
        sway = math.sin(t * 0.8 + self.base[0]) * 2
        cv.line(bezier(self.stem_to, (self.base[0], self.stem_to[1] - 80), self.base), LEAF_DARK, 12)
        up, lo = [], []
        for i in range(31):
            u = i / 30
            ax, ay = self.axis(u)
            h = self.half(u)
            up.append((ax + self.nx * h, ay + self.ny * h + sway * u))
            lo.append((ax - self.nx * h, ay - self.ny * h + sway * u))
        cv.poly(up + lo[::-1], LEAF)
        cv.poly([(ax, ay + sway * (i / 30)) for i, (ax, ay) in enumerate(self.axis(i / 30) for i in range(31))]
                + lo[::-1], LEAF_DARK)
        cv.line([self.axis(0), self.axis(1)], LEAF_VEIN, 4)
        for k in range(1, 6):
            u = k / 6.5
            ax, ay = self.axis(u)
            h = self.half(u) * 0.8
            ex, ey = self.axis(u + 0.08)
            cv.line([(ax, ay), (ex + self.nx * h, ey + self.ny * h)], LEAF_VEIN + (150,), 3)


class Vine:
    def __init__(self, p0, p1, p2):
        self.p0, self.p1, self.p2 = p0, p1, p2

    def at(self, u):
        (x0, y0), (x1, y1), (x2, y2) = self.p0, self.p1, self.p2
        x = (1 - u) ** 2 * x0 + 2 * (1 - u) * u * x1 + u * u * x2
        y = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * y1 + u * u * y2
        dx = 2 * (1 - u) * (x1 - x0) + 2 * u * (x2 - x1)
        dy = 2 * (1 - u) * (y1 - y0) + 2 * u * (y2 - y1)
        return x, y, math.degrees(math.atan2(dy, dx))

    def draw(self, cv, t):
        pts = [self.at(i / 40)[:2] for i in range(41)]
        cv.line(pts, VINE, 4)
        # 上からたれるつる・小さな葉
        for u, ln in ((0.18, 60), (0.5, 0), (0.8, 50)):
            x, y, _ = self.at(u)
            cv.ellipse(x, y - 6, 9, 4, VINE, rot=-30 + u * 60)
