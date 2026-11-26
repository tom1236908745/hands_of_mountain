"""年老いた、目の見えない やさしい亀（長編『ありがとう』）。

ことにゃんと同じ絵柄：くすみ色・あたたかい茶の輪郭線・丸いかたち。目は いつも おだやかに閉じている。
ローカル座標：こうらの半分の長さ = 1、右向き。s でワールド座標の大きさ。
  swim : はばたき（ひれ）の位相（ラジアン）。None なら休んでいる
  neck : 0〜1 首の伸び具合
  smile: 0〜1 ほほえみ
"""
from __future__ import annotations

import math

from engine import Local, ellipse_pts

LINE = (104, 82, 74)
SKIN = (176, 196, 150)
SKIN_DARK = (150, 172, 128)
SHELL = (122, 150, 112)
SHELL_DARK = (98, 126, 92)
SHELL_RIM = (196, 178, 132)
CHEEK = (240, 170, 160)
BROW = (250, 248, 240)


def _shape(L, pts, fill, lw=0.05):
    L.poly(pts, fill)
    L.line(pts + pts[:2], LINE, lw)


def _ell(L, cx, cy, rx, ry, fill, rot=0.0, lw=0.05, n=36):
    _shape(L, ellipse_pts(cx, cy, rx, ry, rot, n), fill, lw)


def draw(cv, x, y, s, *, rot=0.0, flip=False, swim=None, neck=0.4, smile=0.6, alpha=1.0):
    L = Local(cv, x, y, s, rot, flip, alpha)
    a = math.sin(swim) if swim is not None else 0.0

    # --- うしろのひれ（奥） ---
    _ell(L, -0.72, 0.24, 0.32, 0.13, SKIN_DARK, rot=25 + a * 18)
    _ell(L, 0.48, 0.26, 0.42, 0.15, SKIN_DARK, rot=30 + a * 24)
    # --- 首と頭 ---
    hx, hy = 1.12 + 0.22 * neck, -0.06 - 0.04 * neck
    neck_pts = [(0.62, -0.10), (hx - 0.12, hy - 0.16), (hx - 0.12, hy + 0.16), (0.62, 0.16)]
    _shape(L, neck_pts, SKIN)
    for k in (0.0, 0.5):                                       # 首のしわ
        nx = 0.75 + k * (hx - 0.9)
        L.arc(nx, hy + 0.0, 0.05, 0.12, -60, 60, LINE + (120,), 0.03)
    _ell(L, hx + 0.1, hy, 0.36, 0.31, SKIN)
    # 閉じた目（おだやかな ∪）・白いまゆ・ほお・口
    L.arc(hx + 0.17, hy - 0.05, 0.09, 0.055, 20, 160, LINE, 0.05)
    L.arc(hx + 0.16, hy - 0.18, 0.1, 0.045, 200, 340, BROW, 0.055)
    L.ellipse(hx + 0.1, hy + 0.1, 0.09, 0.05, CHEEK + (190,))
    L.arc(hx + 0.33, hy + 0.1, 0.06, 0.04 + 0.03 * smile, 20, 160, LINE, 0.035)
    # --- こうら ---
    dome = [(math.cos(math.radians(t)) * 1.0, -math.sin(math.radians(t)) * 0.8) for t in range(0, 181, 6)]
    dome = [(-1.0, 0.16)] + dome[::-1] + [(1.0, 0.16)]
    _shape(L, dome, SHELL, 0.06)
    for cx, cy, rx, ry in ((-0.52, -0.2, 0.2, 0.15), (0.0, -0.36, 0.24, 0.17), (0.52, -0.2, 0.2, 0.15),
                           (-0.27, 0.0, 0.17, 0.09), (0.27, 0.0, 0.17, 0.09)):
        L.ellipse(cx, cy, rx, ry, SHELL_DARK)                 # まるい もよう
    L.ellipse(-0.35, -0.5, 0.25, 0.08, (160, 186, 146, 200), rot=-12)       # つや
    rim = [(-1.04, 0.10), (1.04, 0.10), (0.98, 0.26), (-0.98, 0.26)]
    _shape(L, rim, SHELL_RIM, 0.05)
    # --- 手前のひれ ---
    _ell(L, -0.6, 0.28, 0.3, 0.12, SKIN, rot=18 - a * 20)
    _ell(L, 0.6, 0.3, 0.4, 0.14, SKIN, rot=28 - a * 26)


def head_world(x, y, s, neck=0.4, flip=False):
    """頭の中心（ワールド座標）。"""
    hx, hy = 1.12 + 0.22 * neck + 0.1, -0.06 - 0.04 * neck
    return x + (hx * s) * (-1 if flip else 1), y + hy * s


def head_only(cv, x, y, s, smile=0.8, alpha=1.0):
    """丸太の穴から出た頭だけ（正面から見た形）。x, y = 頭の中心。"""
    L = Local(cv, x, y, s, 0, False, alpha)
    _ell(L, 0, 0, 0.32, 0.30, SKIN)
    for k in (-1, 1):
        L.arc(0.12 * k, -0.04, 0.07, 0.045, 20, 160, LINE, 0.045)
        L.arc(0.12 * k, -0.14, 0.08, 0.035, 200, 340, BROW, 0.045)
        L.ellipse(0.2 * k, 0.07, 0.07, 0.04, CHEEK + (190,))
    L.arc(0, 0.1, 0.07, 0.03 + 0.03 * smile, 20, 160, LINE, 0.035)
