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


MINCHO = ROOT / "assets" / "fonts" / "ShipporiMinchoB1-ExtraBold.ttf"
# 短冊にする「古いことば」（シリーズの色 = config.yaml の categories）
CARDS = [("一隅を照らす", "buddhism"), ("目から鱗", "christian"), ("塞翁が馬", "kotowaza")]
SKY_WORDS = ["諸行無常", "一期一会", "狭き門", "地の塩", "蛍雪の功", "井の中の蛙", "和顔愛語", "温故知新", "自灯明",
             "求めよ", "一粒の麦", "雨垂れ"]


def mincho(size):
    from PIL import ImageFont
    return ImageFont.truetype(str(MINCHO), size)


def vertical_text(d, x, y_top, text, f, fill, gap=1.08):
    """縦書き（1文字ずつ下へ）。"""
    y = y_top
    for ch in text:
        w = f.getlength(ch)
        d.text((x - w / 2, y), ch, font=f, fill=fill)
        y += f.size * gap


def tanzaku(text, cat_key, h=330, w=88, fsize=46):
    """光る短冊（上にシリーズの色の帯）。回転して貼れるよう RGBA で返す。"""
    col = tuple(config()["categories"][cat_key]["color"])
    pad = 40
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((pad - 8, pad - 8, pad + w + 8, pad + h + 8), 18, fill=GLOW + (150,))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), 10, fill=(252, 246, 230), outline=(104, 82, 74), width=4)
    d.rounded_rectangle((pad, pad, pad + w, pad + 34), 10, fill=col)
    d.rectangle((pad, pad + 20, pad + w, pad + 34), fill=col)
    d.ellipse((pad + w / 2 - 7, pad + 10, pad + w / 2 + 7, pad + 24), fill=(252, 246, 230))   # ひも穴
    f = mincho(fsize)
    th = len(text) * fsize * 1.08
    vertical_text(d, pad + w / 2, pad + 34 + (h - 34 - th) / 2, text, f, (58, 44, 40))
    return im


def open_book(img, cx, cy, wdt=270):
    """開いたことば帖（ページが光っている）。"""
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((cx - 240, cy - 150, cx + 240, cy + 120), fill=GLOW + (80,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(70)))
    d = ImageDraw.Draw(img)
    hw, hh = wdt / 2, wdt * 0.36
    line = (104, 82, 74)
    cover = (126, 158, 182)
    d.polygon([(cx - hw - 10, cy - hh + 14), (cx, cy - hh + 26), (cx + hw + 10, cy - hh + 14),
               (cx + hw + 10, cy + hh * 0.55 + 10), (cx, cy + hh * 0.55 + 24), (cx - hw - 10, cy + hh * 0.55 + 10)],
              fill=cover, outline=line, width=5)
    for sx in (-1, 1):
        pts = [(cx, cy - hh + 22), (cx + sx * hw, cy - hh), (cx + sx * hw, cy + hh * 0.55), (cx, cy + hh * 0.55 + 16)]
        d.polygon(pts, fill=(255, 250, 232), outline=line)
        for k in range(4):
            yy = cy - hh * 0.62 + k * 22
            d.line([(cx + sx * 22, yy + 6), (cx + sx * (hw - 26), yy)], fill=(200, 184, 160), width=4)
    d.line([(cx, cy - hh + 22), (cx, cy + hh * 0.55 + 16)], fill=line, width=4)
    # 前足（本のふちを持つ）
    for sx in (-1, 1):
        px = cx + sx * (hw - 4)
        d.ellipse((px - 30, cy + 2, px + 30, cy + 48), fill=(255, 250, 242), outline=line, width=5)


def word_stream(img, rnd, p0, p1, n=60):
    """本から短冊へ、光のつぶが立ちのぼる。"""
    pts = []
    for i in range(n):
        u = i / n
        cx = p0[0] + (p1[0] - p0[0]) * u
        cy = p0[1] + (p1[1] - p0[1]) * u - math.sin(u * math.pi) * 160
        pts.append((cx + rnd.uniform(-26, 26), cy + rnd.uniform(-22, 22), rnd.uniform(2.5, 6), rnd.uniform(0.4, 1)))
    big = [(x, y, r * 4, a * 0.3) for x, y, r, a in pts]
    b, _ = glow_layer(img.size, big)
    img.alpha_composite(b)
    _, core = glow_layer(img.size, pts)
    img.alpha_composite(core.filter(ImageFilter.GaussianBlur(1.2)))


def sky_words(img, rnd):
    """夜空にうっすら浮かぶ古いことば（PC・TV で見える部分）。"""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    spots = [(170, 120), (420, 300), (700, 90), (980, 260), (1260, 110), (1540, 300), (1820, 120), (2100, 280),
             (2390, 110), (190, 560), (2380, 560), (300, 760)]
    for (x, y), w in zip(spots, SKY_WORDS):
        f = mincho(int(rnd.uniform(38, 50)))
        x += rnd.uniform(-30, 30)
        if SAFE[0] - 60 < x < SAFE[2] + 60:              # スマホの範囲には入れない
            y = min(y, SAFE[1] - 40 - len(w) * f.size * 1.08)
        vertical_text(d, x, y, w, f, (236, 226, 196, int(rnd.uniform(70, 110))))
    g = lay.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(g)
    img.alpha_composite(lay)


def banner(title, tagline, with_text=True):
    rnd = random.Random(8)
    img = gradient(W, H, SKY_TOP, SKY_BOT)
    d = ImageDraw.Draw(img)
    for _ in range(420):                                  # 星
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, 900), rnd.uniform(1.2, 3.2)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(230, 236, 255, int(rnd.uniform(120, 255))))
    sky_words(img, rnd)
    moon(img, 2230, 640, 92)
    trees(img, rnd)
    fireflies(img, rnd, 30, (0, 120, W, 1000))

    # ことにゃん：ことば帖をひらく
    cs = 470
    cx, foot = 720, 900
    cat = mascot.draw("happy", cs)
    img.alpha_composite(cat, (int(cx - cs / 2), int(foot - cs * 0.91)))
    open_book(img, cx, foot - 22, wdt=210)              # 顔が隠れないよう、胸の下で小さく開く

    # 光る短冊（ことばが本から立ちのぼって、短冊になる）
    card_x = [1760, 1862, 1962] if with_text else [1300, 1420, 1540]
    card_y = [585, 560, 600]
    word_stream(img, rnd, (cx + 30, foot - 60), (card_x[0] - 40, card_y[0] + 120))
    for (text, key), x, y, rot in zip(CARDS, card_x, card_y, (-6, 3, 8)):
        fs = 38
        t = tanzaku(text, key, h=int(34 + len(text) * fs * 1.08 + 34), fsize=fs).rotate(
            rot, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(t, (int(x - t.width / 2), int(y - 40)))

    if with_text:
        tx = 960
        tf = mincho(96)
        while tf.getlength(title) > 1720 - tx and tf.size > 50:
            tf = mincho(tf.size - 2)
        text_glow(img, (tx, 700), title, tf, (255, 252, 240))
        sf = font(36, bold=False)
        while sf.getlength(tagline) > 1730 - tx and sf.size > 22:
            sf = font(sf.size - 1)
        text_glow(img, (tx + 4, 790), tagline, sf, (255, 226, 150), glow=(255, 220, 150, 50))
        bf = font(30, bold=False)
        series = "仏教のことば ・ 聖書のことば ・ 故事成語"
        text_glow(img, (tx + 4, 852), series, bf, (210, 222, 236), glow=(180, 200, 230, 30))
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
    ap.add_argument("--tagline", default="むかしから伝わることばを、小さな物語アニメで。")
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
