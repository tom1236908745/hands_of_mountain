"""カタツムリ（子・母）。

ローカル座標：殻の半径 = 1。体は右向き（flip=True で左向き）。
  mood : sad（泣き・目がたれる）/ normal / happy / content（目を閉じて寄り添う）
  stalk: 0〜1 目の柄の立ち具合（0 でしょんぼり垂れる）
  look : -1〜1 目玉の向き（上下）
  tears: 0〜1 涙の量（時間 t で落ちるしずくをアニメ）
"""
from __future__ import annotations

import math

from engine import Local, lerp

CHILD = dict(body=(236, 214, 178), body_dark=(206, 178, 140), shell=(250, 150, 60), shell_dark=(214, 104, 34),
             shell_hi=(255, 196, 120))
MOTHER = dict(body=(218, 200, 170), body_dark=(186, 162, 130), shell=(196, 116, 70), shell_dark=(150, 82, 46),
              shell_hi=(226, 160, 112))
INK = (60, 40, 30)
TEAR = (150, 210, 255)
CHEEK = (255, 130, 130)


def draw(cv, x, y, s, *, palette=CHILD, flip=False, mood="normal", stalk=1.0, look=0.0, tears=0.0, t=0.0,
         crawl=0.0, alpha=1.0, rot=0.0):
    L = Local(cv, x, y, s, rot, flip, alpha)
    P = palette
    w = math.sin(crawl * 2 * math.pi) * 0.05   # はうときの伸び縮み

    # --- 体（足は細長い楕円＋しっぽ、頭は立ち上がった楕円） ---
    L.poly([(-1.95 - w, 0.92), (-1.0, 0.6), (0.5, 0.55), (0.5, 1.02), (-1.0, 1.02)], P["body"])
    L.ellipse(0.35 + w / 2, 0.8, 1.55 + w, 0.24, P["body"])
    L.ellipse(1.5 + w, 0.28, 0.44, 0.7, P["body"], rot=12)
    L.ellipse(1.42 + w, 0.62, 0.3, 0.2, P["body_dark"] + (90,), rot=12)
    L.line([(-1.6, 1.0), (1.6, 1.0)], P["body_dark"], 0.08)

    # --- 目の柄 ---
    head = (1.6 + w, -0.3)
    droop = 1 - stalk
    eyes = []
    for k, (ang0, ln) in enumerate(((-75, 1.0), (-55, 0.9))):
        ang = math.radians(lerp(ang0, 15 + k * 10, droop))
        tip = (head[0] + math.cos(ang) * ln * 1.1, head[1] + math.sin(ang) * ln * 1.1)
        L.line([head, ((head[0] + tip[0]) / 2 + 0.05, (head[1] + tip[1]) / 2 - 0.05 * stalk), tip],
               P["body"], 0.18)
        eyes.append(tip)
    for ex, ey in eyes:
        L.circle(ex, ey, 0.2, P["body"])
        if mood == "content" or mood == "happy":
            L.arc(ex, ey + 0.03, 0.11, 0.08, 200 if mood == "happy" else 20, 340 if mood == "happy" else 160,
                  INK, 0.06)
        else:
            L.circle(ex, ey, 0.15, (255, 255, 255))
            py = ey + (0.05 if mood == "sad" else 0) + look * 0.05
            L.circle(ex + 0.02, py, 0.09, INK)
            L.circle(ex - 0.01, py - 0.035, 0.035, (255, 255, 255))

    # --- 顔（口・ほお） ---
    mx, my = 1.72 + w, 0.32
    if mood == "sad":
        L.arc(mx, my + 0.12, 0.12, 0.08, 200, 340, INK, 0.06)
    elif mood in ("happy", "content"):
        L.arc(mx, my, 0.13, 0.1, 20, 160, INK, 0.06)
        L.ellipse(1.45 + w, 0.36, 0.12, 0.07, CHEEK + (170,))
    else:
        L.line([(mx - 0.08, my + 0.05), (mx + 0.08, my + 0.05)], INK, 0.05)

    # --- 涙 ---
    if tears > 0:
        for i, (ex, ey) in enumerate(eyes):
            ph = (t * 1.3 + i * 0.5) % 1.0
            ty = ey + 0.2 + ph * 0.9
            a = int(230 * tears * (1 - ph))
            L.ellipse(ex + 0.12, ty, 0.07, 0.1, TEAR + (a,))
            L.poly([(ex + 0.05, ty - 0.04), (ex + 0.19, ty - 0.04), (ex + 0.12, ty - 0.2)], TEAR + (a,))

    # --- 殻（うず巻き） ---
    L.circle(0, -0.05, 1.0, P["shell_dark"])
    L.circle(-0.04, -0.09, 0.9, P["shell"])
    sp = []
    for i in range(70):
        a = i / 70 * 2.6 * 2 * math.pi
        r = 0.78 * (1 - i / 75)
        sp.append((-0.02 + math.cos(a) * r, -0.08 + math.sin(a) * r))
    L.line(sp, P["shell_dark"], 0.1)
    L.ellipse(-0.35, -0.5, 0.25, 0.13, P["shell_hi"] + (200,), rot=-35)


def heart(cv, x, y, s, alpha=1.0, col=(255, 130, 150)):
    pts = []
    for i in range(40):
        a = i / 40 * 2 * math.pi
        hx = 16 * math.sin(a) ** 3
        hy = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((x + hx / 16 * s, y + hy / 16 * s))
    cv.poly(pts, col + (int(255 * alpha),))
