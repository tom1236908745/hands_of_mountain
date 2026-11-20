"""ホタル（ゲンジボタルがモチーフ）。主人公にも、群れのホタルにも使う。

ローカル座標：頭の半径 = 1。s で大きさ（ワールド座標で頭の半径）を決める。
表情パラメータ:
  eyes : open / squeeze(＞＜) / closed(おだやかに閉じる) / wide / happy
  look : (dx, dy) 瞳の向き -1〜1
  mouth: smile / frown / o / line / wobble
  blush: 0〜1 頬の赤み
  glow : 0〜1 お尻の光
  wing : None=たたむ / 数値=はばたきの位相（ラジアン）
"""
from __future__ import annotations

import math

from engine import Local, lerp

BODY = (52, 44, 104)
BODY_HI = (82, 74, 150)
BODY_DARK = (34, 28, 72)
PRONOTUM = (236, 96, 60)
PRONOTUM_HI = (252, 150, 110)
LANTERN_OFF = (240, 232, 196)
LANTERN_ON = (255, 252, 214)
GLOW = (255, 236, 150)
EYE = (255, 255, 255)
PUPIL = (22, 18, 44)
CHEEK = (255, 120, 130)
WING = (200, 220, 255)


def lantern_local():
    return (1.42, 0.98)


def lantern_world(x, y, s, rot=0.0, flip=False):
    lx, ly = lantern_local()
    f = -1 if flip else 1
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    lx *= f
    return x + (lx * cr - ly * sr) * s, y + (lx * sr + ly * cr) * s


def draw(cv, x, y, s, *, rot=0.0, flip=False, eyes="open", look=(0, 0), mouth="smile", blush=0.3,
         glow=0.0, wing=None, legs=True, alpha=1.0):
    L = Local(cv, x, y, s, rot, flip, alpha)

    # --- はね（うしろ） ---
    if wing is None:
        L.ellipse(0.55, -0.55, 0.95, 0.42, WING + (90,), rot=-25)
        L.ellipse(0.35, -0.75, 0.9, 0.38, WING + (70,), rot=-50)
    else:
        a = math.sin(wing)
        for k, base in ((1, -18), (-1, -162)):
            ang = base + k * a * 22
            cx = 0.25 * k + math.cos(math.radians(ang)) * 0.9
            cy = -0.55 + math.sin(math.radians(ang)) * 0.9
            L.ellipse(cx, cy, 0.95, 0.38, WING + (80,), rot=ang)

    # --- おなか（うしろ下） ---
    L.ellipse(0.78, 0.55, 0.85, 0.6, BODY_DARK, rot=28)
    for k in (0.35, 0.7):
        cx, cy = lerp(0.3, 1.25, k), lerp(0.3, 0.8, k)
        L.ellipse(cx, cy, 0.12, 0.5, BODY_HI + (120,), rot=28)
    # 光るところ
    lx, ly = lantern_local()
    col = tuple(int(lerp(a, b, min(1, glow * 1.5))) for a, b in zip(LANTERN_OFF, LANTERN_ON))
    L.ellipse(lx, ly, 0.44, 0.38, col, rot=28)

    # --- あし ---
    if legs:
        for dx in (-0.35, 0.05, 0.4):
            L.line([(dx, 0.8), (dx - 0.08, 1.12), (dx - 0.2, 1.15)], BODY_DARK, 0.09)

    # --- あたま ---
    L.circle(0, 0, 1.0, BODY)
    L.ellipse(-0.3, -0.35, 0.45, 0.3, BODY_HI + (110,), rot=-30)
    # 前胸部（赤橙のかさ）
    cap = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(195, 346, 6)]
    cap += [(0.8, -0.38), (0.4, -0.3), (0, -0.28), (-0.4, -0.3), (-0.8, -0.38)]
    L.poly(cap, PRONOTUM)
    L.ellipse(-0.25, -0.72, 0.3, 0.1, PRONOTUM_HI, rot=-12)
    # しょっかく
    for k in (-1, 1):
        p0 = (0.3 * k, -0.9)
        tip = (0.75 * k, -1.65)
        L.line([p0, (0.45 * k, -1.35), tip], BODY_DARK, 0.08)
        L.circle(tip[0], tip[1], 0.11, BODY_DARK)

    # --- 目 ---
    for k in (-1, 1):
        ex, ey = 0.4 * k, 0.12
        if eyes in ("open", "wide"):
            r = 0.36 if eyes == "wide" else 0.32
            L.circle(ex, ey, r, EYE)
            pr = 0.13 if eyes == "wide" else 0.19
            px, py = ex + look[0] * 0.12, ey + look[1] * 0.12
            L.circle(px, py, pr, PUPIL)
            L.circle(px - pr * 0.4, py - pr * 0.45, pr * 0.42, (255, 255, 255))
        elif eyes == "squeeze":      # ＞＜
            L.line([(ex - 0.2 * k, ey - 0.14), (ex + 0.12 * k, ey), (ex - 0.2 * k, ey + 0.14)], PUPIL, 0.09)
        elif eyes == "closed":       # ∪ おだやか
            L.arc(ex, ey - 0.06, 0.2, 0.14, 20, 160, PUPIL, 0.08)
        elif eyes == "happy":        # ∩
            L.arc(ex, ey + 0.1, 0.2, 0.17, 200, 340, PUPIL, 0.09)
        elif eyes == "sad":
            L.circle(ex, ey, 0.32, EYE)
            px, py = ex + look[0] * 0.1, ey + 0.08 + look[1] * 0.08
            L.circle(px, py, 0.18, PUPIL)
            L.circle(px - 0.07, py - 0.08, 0.075, (255, 255, 255))
            # たれ眉のかわりにまぶた
            L.poly([(ex - 0.36, ey - 0.36), (ex + 0.36, ey - 0.36), (ex + 0.36 * k, ey - 0.12),
                    (ex - 0.36 * k, ey - 0.28)], BODY)

    # --- ほお ---
    if blush > 0:
        for k in (-1, 1):
            L.ellipse(0.66 * k, 0.45, 0.17, 0.09, CHEEK + (int(200 * min(1, blush)),))

    # --- 口 ---
    if mouth == "smile":
        L.arc(0, 0.46, 0.14, 0.1, 20, 160, PUPIL, 0.07)
    elif mouth == "frown":
        L.arc(0, 0.6, 0.13, 0.08, 200, 340, PUPIL, 0.07)
    elif mouth == "o":
        L.ellipse(0, 0.55, 0.08, 0.1, PUPIL)
    elif mouth == "line":
        L.line([(-0.1, 0.55), (0.1, 0.55)], PUPIL, 0.07)
    elif mouth == "wobble":
        L.line([(-0.16, 0.56), (-0.08, 0.5), (0, 0.56), (0.08, 0.5), (0.16, 0.56)], PUPIL, 0.06)


def draw_glow(ev, x, y, s, level, rot=0.0, flip=False):
    """emissive 層に、お尻の光を描く。戻り値＝光の中心（ワールド座標）。"""
    gx, gy = lantern_world(x, y, s, rot, flip)
    if level > 0.01:
        ev.glow(gx, gy, s * (0.8 + 1.5 * level), GLOW, strength=min(0.85, level * 0.85))
        ev.ellipse(gx, gy, s * 0.4, s * 0.34, tuple(int(c * min(1, level) * 0.8) for c in LANTERN_ON))
    return gx, gy


def draw_tiny(bv, ev, x, y, s, level, wing_phase):
    """遠くの群れ用の簡略ホタル（体は小さく、光が主役）。"""
    if s > 0:
        bv.circle(x, y, s, BODY)
        a = math.sin(wing_phase)
        bv.ellipse(x - s * 0.6, y - s * (0.9 + 0.3 * a), s * 0.9, s * 0.4, WING + (80,), rot=-30)
        bv.ellipse(x + s * 0.6, y - s * (0.9 + 0.3 * a), s * 0.9, s * 0.4, WING + (80,), rot=30)
    ev.glow(x + s * 0.6, y + s * 0.9, s * (2.2 + 2.4 * level), GLOW, strength=level)
    ev.circle(x + s * 0.6, y + s * 0.9, s * 0.55, tuple(int(c * level) for c in LANTERN_ON))
