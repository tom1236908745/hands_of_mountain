"""YouTube チャンネルのバナー（背景画像）とアイコンを作る。

  python tools/make_banner.py                         # config.yaml のチャンネル名で作る
  python tools/make_banner.py --title "WAI" --tagline "古いことばを、小さな物語アニメで。"

出力（output/channel/）:
  banner.png          2560x1440（文字入り）
  banner_notext.png   2560x1440（文字なし）
  banner_preview.png  スマホ・PC・TVでの見え方の確認用
  icon.png            800x800（顔を大きく。丸く切り抜かれても大丈夫な配置）
  banner_phone_view.png  スマホで見える部分だけを切り出したもの

YouTube のバナーの決まり：2560x1440 推奨、すべての端末で見えるのは中央の 1546x423 だけ。
文字とキャラはこの中に収める。
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mascot  # noqa: E402
from common import ROOT, config, font  # noqa: E402

W, H = 2560, 1440
SAFE = (507, 508, 2053, 931)          # すべての端末で見える範囲
DESKTOP = (0, 508, 2560, 931)         # PC で見える範囲
SKY_TOP, SKY_BOT = (14, 18, 52), (26, 78, 92)
GLOW = (255, 230, 150)


def gradient(w, h, top, bot):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    col = np.array(top, np.float32) + (np.array(bot, np.float32) - np.array(top, np.float32)) * y
    return Image.fromarray(np.repeat(col, w, axis=1).astype(np.uint8)).convert("RGBA")


def glow_layer(size, points):
    """points = [(x, y, r, 明るさ)] のやわらかい光。"""
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x, y, r, a in points:
        d.ellipse((x - r, y - r, x + r, y + r), fill=GLOW + (int(255 * a),))
    blur = lay.filter(ImageFilter.GaussianBlur(max(4, int(min(p[2] for p in points) * 1.5)) if points else 4))
    return blur, lay


def fireflies(img, rnd, n, box, rmin=4, rmax=9):
    x0, y0, x1, y1 = box
    pts = [(rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(rmin, rmax), rnd.uniform(0.5, 1.0))
           for _ in range(n)]
    big = [(x, y, r * 4, a * 0.35) for x, y, r, a in pts]
    b, _ = glow_layer(img.size, big)
    img.alpha_composite(b)
    _, core = glow_layer(img.size, pts)
    img.alpha_composite(core.filter(ImageFilter.GaussianBlur(1.5)))


def trees(img, rnd):
    d = ImageDraw.Draw(img, "RGBA")
    for layer, (col, base, hmin, hmax) in enumerate([((22, 48, 70), 960, 150, 250), ((14, 32, 50), 1000, 110, 200),
                                                       ((8, 20, 32), 1040, 80, 150)]):
        x = -100
        while x < W + 100:
            hgt = rnd.uniform(hmin, hmax)
            r = rnd.uniform(90, 160) * (1 + layer * 0.1)
            for _ in range(5):
                bx, by = x + rnd.uniform(-r, r), base - hgt + rnd.uniform(0, hgt * 0.6)
                br = r * rnd.uniform(0.6, 1.0)
                d.ellipse((bx - br, by - br, bx + br, by + br), fill=col)
            d.rectangle((x - 18, base - hgt * 0.4, x + 18, H), fill=col)
            x += rnd.uniform(220, 360)
        d.rectangle((0, base, W, H), fill=col)
    # 手前の丘（キャラが立つ地面）
    pts = [(x, 905 + 18 * math.sin(x / 260)) for x in range(0, W + 1, 20)]
    d.polygon(pts + [(W, H), (0, H)], fill=(30, 66, 56))
    for i in range(12):                                   # 下にいくほど暗く（TVで見える部分）
        y0 = 960 + i * 40
        d.rectangle((0, y0, W, y0 + 40), fill=(6, 16, 20, 18 + i * 6))
    d.line(pts, fill=(58, 108, 84), width=8)
    for _ in range(120):
        gx = rnd.uniform(0, W)
        gy = 905 + 18 * math.sin(gx / 260)
        for k in (-1, 0, 1):
            d.polygon([(gx + k * 8 - 4, gy + 2), (gx + k * 8 + 4, gy + 2), (gx + k * 12, gy - rnd.uniform(14, 30))],
                      fill=(58, 108, 84))


def moon(img, x, y, r):
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2), fill=(140, 160, 190, 70))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(r * 0.8)))
    d = ImageDraw.Draw(img)
    d.ellipse((x - r, y - r, x + r, y + r), fill=(232, 228, 200))
    for dx, dy, rr in ((-0.3, -0.2, 0.22), (0.35, 0.25, 0.16), (0.05, -0.45, 0.1)):
        d.ellipse((x + dx * r - rr * r, y + dy * r - rr * r, x + dx * r + rr * r, y + dy * r + rr * r),
                  fill=(214, 210, 184))


def text_glow(img, xy, text, f, fill, glow=(255, 220, 150, 120), anchor="ls"):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text(xy, text, font=f, fill=glow, anchor=anchor, stroke_width=10, stroke_fill=glow)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(18)))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0], xy[1] + 6), text, font=f, fill=(0, 0, 20, 160), anchor=anchor)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill, anchor=anchor)


def banner(title, tagline, with_text=True):
    rnd = random.Random(8)
    img = gradient(W, H, SKY_TOP, SKY_BOT)
    d = ImageDraw.Draw(img)
    for _ in range(420):                                  # 星
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, 900), rnd.uniform(1.2, 3.2)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(230, 236, 255, int(rnd.uniform(120, 255))))
    moon(img, 2230, 640, 92)
    trees(img, rnd)
    fireflies(img, rnd, 70, (0, 120, W, 1000))
    fireflies(img, rnd, 26, (SAFE[0], SAFE[1], SAFE[2], SAFE[3] - 40), 5, 10)

    # ほたるにゃん（光っている）＋ 子ねこ
    cs = 470
    cx, foot = 760, 920
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lx = cx + (mascot.FIREFLY_LIGHT[0] - 500) / 1000 * cs
    ly = foot - cs * 0.91 + mascot.FIREFLY_LIGHT[1] / 1000 * cs
    ImageDraw.Draw(halo).ellipse((lx - 230, ly - 230, lx + 230, ly + 230), fill=GLOW + (90,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(90)))
    cat = mascot.draw("happy", cs, item="firefly", lantern=1.0, flap=0.3)
    img.alpha_composite(cat, (int(cx - cs / 2), int(foot - cs * 0.91)))
    ks = 230
    kit = mascot.draw("calm", ks, palette=dict(fur=(250, 250, 252), patch_a=(178, 180, 192), patch_b=(112, 114, 126)))
    img.alpha_composite(kit, (int(cx + 305 - ks / 2), int(foot + 6 - ks * 0.91)))
    core = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(core).ellipse((lx - 40, ly - 36, lx + 40, ly + 36), fill=(255, 250, 220, 150))
    img.alpha_composite(core.filter(ImageFilter.GaussianBlur(14)))

    if with_text:
        tx = 1235
        tf = font(118)
        while tf.getlength(title) > SAFE[2] - tx - 20 and tf.size > 50:
            tf = font(tf.size - 4)
        text_glow(img, (tx, 735), title, tf, (255, 252, 240))
        text_glow(img, (tx + 4, 830), tagline, font(54, bold=False), (255, 226, 150), glow=(255, 220, 150, 60))
    return img.convert("RGB")


def preview(img):
    """スマホ / PC / TV でどこまで見えるかを線で示した確認用。"""
    p = img.copy().convert("RGBA")
    d = ImageDraw.Draw(p)
    d.rectangle(DESKTOP, outline=(80, 200, 255), width=6)
    d.rectangle(SAFE, outline=(255, 90, 90), width=8)
    f = font(40)
    d.text((20, 20), "全体 = TV", font=f, fill=(255, 255, 255))
    d.text((20, DESKTOP[1] + 10), "青 = PC", font=f, fill=(80, 200, 255))
    d.text((SAFE[0] + 10, SAFE[1] + 10), "赤 = スマホ（すべての端末で見える）", font=f, fill=(255, 120, 120))
    return p.convert("RGB")


def icon(size=800):
    img = gradient(size, size, (24, 34, 74), (40, 96, 104))
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((size * 0.12, size * 0.18, size * 0.88, size * 0.94), fill=GLOW + (110,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(size * 0.1)))
    rnd = random.Random(3)
    fireflies(img, rnd, 10, (0, 0, size, size * 0.5), 3, 6)
    cs = int(size * 1.12)                         # 顔を大きく（耳まで丸の中に入る大きさ）
    cat = mascot.draw("normal", cs)
    img.alpha_composite(cat, (int(size / 2 - cs / 2), int(size * 0.6 - cs * 0.585)))
    return img.convert("RGB")


def main():
    ch = config()["channel"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default=ch["name"])
    ap.add_argument("--tagline", default="古いことばを、小さな物語アニメで。")
    args = ap.parse_args()
    out = ROOT / "output" / "channel"
    out.mkdir(parents=True, exist_ok=True)
    b = banner(args.title, args.tagline)
    b.save(out / "banner.png", optimize=True)
    banner("", "", with_text=False).save(out / "banner_notext.png", optimize=True)
    preview(b).save(out / "banner_preview.png")
    b.crop(SAFE).save(out / "banner_phone_view.png")
    ic = icon()
    ic.save(out / "icon.png")
    m = Image.new("L", ic.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, ic.width, ic.height), fill=255)
    circ = Image.new("RGBA", ic.size, (255, 255, 255, 0))
    circ.paste(ic, (0, 0), m)
    circ.save(out / "icon_circle_preview.png")
    for p in sorted(out.iterdir()):
        print(p, f"{p.stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()
