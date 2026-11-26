"""長編01『ありがとう』のあらすじ画像と絵コンテ画像を作る（確認用）。

  python anime/long/long01_arigatou/storyboard.py
  → output/anime/long01_arigatou/あらすじ.png, 絵コンテ.png
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
YT = HERE.parents[2]
sys.path[:0] = [str(YT / "tools")]
import mascot  # noqa: E402

FONT_DIR = YT / "assets" / "fonts"
OUT = YT / "output" / "anime" / "long01_arigatou"
KITTEN = dict(fur=(250, 250, 252), patch_a=(178, 180, 192), patch_b=(112, 114, 126))
KURO = dict(fur=(78, 72, 80), patch_a=(62, 58, 66), patch_b=(46, 42, 50), eye=(250, 214, 110),
            line=(40, 34, 38), ear_in=(196, 150, 150), cheek=(230, 140, 140))
INK = (84, 62, 54)
PAPER = (252, 246, 232)


def F(size, kind="gothic"):
    from PIL import ImageFont
    name = {"gothic": "MPLUSRounded1c-Bold.ttf", "bold": "MPLUSRounded1c-ExtraBold.ttf",
            "mincho": "ShipporiMinchoB1-ExtraBold.ttf"}[kind]
    return ImageFont.truetype(str(FONT_DIR / name), size)


# ---------------------------------------------------------------- 描画の小道具
def grad(w, h, top, bot):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bot)))
    return im.convert("RGBA")


def cat(im, expr, x, foot, size, palette=None, item=None):
    c = mascot.draw(expr, size, palette=palette, item=item)
    im.alpha_composite(c, (int(x - size / 2), int(foot - size * 0.91)))


def meadow(w, h, sky=((140, 196, 236), (226, 240, 240))):
    im = grad(w, h, *sky)
    d = ImageDraw.Draw(im)
    for i, col in enumerate([(150, 196, 170), (118, 172, 140)]):
        for k in range(6):
            x = k * w / 5 + (i * 40)
            d.ellipse((x - 70, h * 0.45 - i * 10 - 60, x + 70, h * 0.45 - i * 10 + 80), fill=col)
    d.rectangle((0, h * 0.55, w, h), fill=(150, 196, 120))
    d.line([(0, h * 0.55), (w, h * 0.55)], fill=(176, 214, 140), width=4)
    d.ellipse((w - 110, 20, w - 50, 80), fill=(255, 244, 200))
    return im


def sea(w, h, deep=False):
    if deep:
        im = grad(w, h, (20, 60, 100), (6, 16, 40)).convert("RGB")
        d = ImageDraw.Draw(im, "RGBA")
        for k in range(5):                                  # 光の筋
            x = 60 + k * w / 5
            d.polygon([(x, 0), (x + 40, 0), (x + 120, h), (x + 60, h)], fill=(160, 210, 240, 22))
        rnd = random.Random(2)
        for _ in range(18):                                 # 泡
            x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(2, 6)
            d.ellipse((x - r, y - r, x + r, y + r), outline=(200, 230, 250, 120), width=2)
        d.rectangle((0, h * 0.86, w, h), fill=(30, 40, 50))
        return im.convert("RGBA")
    im = grad(w, h, (150, 200, 236), (230, 240, 244)).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, h * 0.5, w, h), fill=(60, 130, 180))
    for row in range(5):
        y = h * 0.52 + row * h * 0.1
        for k in range(10):
            x = k * w / 9 + (row % 2) * 30
            d.arc((x - 30, y - 8, x + 30, y + 8), 200, 340, fill=(200, 230, 250, 170), width=3)
    return im.convert("RGBA")


def turtle(d, x, y, s, up=False):
    """目を閉じた、やさしい年寄りの亀（横から見た形）。"""
    sh = (106, 140, 96)
    d.ellipse((x - s * 0.7 + s * 0.95, y - s * 0.18, x + s * 0.2 + s * 0.95, y + s * 0.22), fill=(150, 176, 120))
    d.ellipse((x + s * 0.55, y - s * 0.3, x + s * 1.05, y + s * 0.12), fill=(170, 196, 140))   # 頭
    d.arc((x + s * 0.72, y - s * 0.16, x + s * 0.88, y - s * 0.04), 20, 160, fill=INK, width=max(2, int(s * 0.04)))  # 閉じた目
    for fx in (-0.45, 0.35):                                                                  # ひれ
        d.ellipse((x + s * fx - s * 0.22, y + s * 0.1, x + s * fx + s * 0.22, y + s * 0.32), fill=(150, 176, 120))
    d.chord((x - s * 0.8, y - s * 0.55, x + s * 0.7, y + s * 0.35), 180, 360, fill=sh)          # こうら
    d.line([(x - s * 0.8, y - s * 0.1), (x + s * 0.7, y - s * 0.1)], fill=(80, 110, 76), width=max(2, int(s * 0.04)))
    for k in (-0.4, 0.0, 0.4):
        d.ellipse((x + s * k - s * 0.16, y - s * 0.42, x + s * k + s * 0.16, y - s * 0.18), outline=(80, 110, 76),
                  width=max(2, int(s * 0.03)))


def log(d, x, y, s, rot=0):
    d.rounded_rectangle((x - s, y - s * 0.16, x + s, y + s * 0.16), radius=int(s * 0.14), fill=(150, 108, 70),
                        outline=(104, 74, 50), width=3)
    d.ellipse((x - s * 0.18, y - s * 0.1, x + s * 0.18, y + s * 0.1), fill=(40, 70, 100), outline=(104, 74, 50), width=3)
    d.ellipse((x + s * 0.86, y - s * 0.16, x + s * 1.04, y + s * 0.16), fill=(214, 176, 130))


def bubble(im, x, y, text, size=24):
    d = ImageDraw.Draw(im)
    f = F(size)
    w = f.getlength(text)
    d.rounded_rectangle((x - w / 2 - 14, y - size - 14, x + w / 2 + 14, y + 6), radius=14, fill=(255, 255, 255),
                        outline=INK, width=3)
    d.polygon([(x - 8, y + 5), (x + 8, y + 5), (x, y + 18)], fill=(255, 255, 255))
    d.text((x - w / 2, y - size - 5), text, font=f, fill=INK)


def caption(im, text, size=24):
    d = ImageDraw.Draw(im)
    f = F(size)
    w = f.getlength(text)
    W = im.width
    d.text(((W - w) / 2, 62), text, font=f, fill=(255, 255, 255), stroke_width=4, stroke_fill=(40, 30, 30))


def book_page(w, h, lines):
    im = grad(w, h, (236, 224, 200), (214, 196, 166))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 30, w - 40, h - 30), radius=16, fill=PAPER, outline=INK, width=4)
    d.line([(w / 2, 34), (w / 2, h - 34)], fill=(210, 196, 170), width=3)
    y = 70
    for text, size, kind, col in lines:
        f = F(size, kind)
        tw = f.getlength(text)
        d.text(((w - tw) / 2, y), text, font=f, fill=col)
        y += size * 1.5
    return im


# ---------------------------------------------------------------- 各コマ
W, H = 640, 360


def p_open():
    im = meadow(W, H)
    cat(im, "happy", 250, 300, 170)
    cat(im, "happy", 400, 300, 115, KITTEN)
    d = ImageDraw.Draw(im)
    for k in range(3):                                         # お魚クッキー
        d.ellipse((330 + k * 14, 238 - k * 4, 356 + k * 14, 252 - k * 4), fill=(236, 180, 110), outline=INK)
    bubble(im, 250, 110, "ありがとう")
    return im


def p_question():
    im = meadow(W, H)
    cat(im, "thinking", 320, 310, 210, item="book")
    caption(im, "「ありがとう」って、どういう意味？")
    return im


def p_dive():
    im = grad(W, H, (40, 50, 90), (250, 230, 180))
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((170, 60, 470, 320), fill=(255, 236, 170, 200))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(im)
    d.polygon([(220, 210), (320, 190), (420, 210), (420, 280), (320, 300), (220, 280)], fill=PAPER, outline=INK)
    for k in range(14):
        a = k / 14 * 2 * math.pi
        d.line([(320, 200), (320 + math.cos(a) * 170, 200 + math.sin(a) * 120)], fill=(255, 244, 200), width=2)
    cat(im, "surprised", 320, 190, 120)
    caption(im, "ページが光って、お話の世界へ")
    return im


def p_word():
    return book_page(W, H, [("ありがとう", 46, "bold", INK), ("＝", 30, "gothic", INK),
                            ("有り難し", 64, "mincho", (150, 70, 50)),
                            ("有ることが 難しい ＝ めったにない", 26, "gothic", INK)])


def p_deep():
    im = sea(W, H, deep=True)
    d = ImageDraw.Draw(im)
    turtle(d, 270, 270, 130)
    caption(im, "広い海の底に、目の見えない亀がいた")
    return im


def p_rise():
    im = sea(W, H, deep=True)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, W, 40), fill=(200, 230, 250, 120))
    turtle(d, 300, 150, 90)
    for k in range(5):
        d.ellipse((410 + k * 6, 120 - k * 22, 420 + k * 6, 130 - k * 22), outline=(220, 240, 255), width=2)
    d.text((24, 300), "春・夏・秋・冬 … × 百年", font=F(24), fill=(230, 240, 255))
    caption(im, "百年に一度だけ、海の上に顔を出す")
    return im


def p_log():
    im = sea(W, H)
    d = ImageDraw.Draw(im, "RGBA")
    log(d, 320, 200, 110)
    for k in range(4):
        d.line([(100 + k * 120, 120), (160 + k * 120, 110)], fill=(255, 255, 255, 180), width=3)   # 風
    caption(im, "海の上には、穴のあいた丸太が一本")
    return im


def p_storm():
    im = grad(W, H, (90, 100, 120), (150, 160, 170))
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, H * 0.5, W, H), fill=(50, 90, 120))
    for k in range(40):
        x = (k * 53) % W
        d.line([(x, (k * 37) % H), (x - 10, (k * 37) % H + 30)], fill=(220, 230, 240, 160), width=2)
    log(d, 420, 196, 80)
    d.line([(150, 160), (190, 140), (170, 175), (210, 150)], fill=(255, 240, 160), width=4)
    caption(im, "東へ、西へ。凪の日も、嵐の日も")
    return im


def p_meet():
    im = sea(W, H)
    d = ImageDraw.Draw(im, "RGBA")
    log(d, 320, 196, 120)
    d.ellipse((300, 168, 340, 206), fill=(170, 196, 140))
    d.arc((310, 180, 326, 192), 20, 160, fill=INK, width=3)
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        gd.line([(320, 186), (320 + math.cos(a) * 110, 186 + math.sin(a) * 80)], fill=(255, 240, 170, 200), width=4)
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(3)))
    caption(im, "その穴に、すぽっ。――めったにない、出会い")
    return im


def p_sutra():
    im = grad(W, H, (12, 20, 40), (30, 50, 80))
    d = ImageDraw.Draw(im)
    f = F(34, "mincho")
    for i, line in enumerate(["人の生を受くるは難く、", "やがて死すべきものの、", "いま生命あるは 有り難し"]):
        w = f.getlength(line)
        d.text(((W - w) / 2, 80 + i * 60), line, font=f, fill=(250, 244, 230))
    f2 = F(20, "mincho")
    t = "―― 『法句経』"
    d.text(((W - f2.getlength(t)) / 2, 280), t, font=f2, fill=(220, 210, 190))
    return im


def p_back():
    im = meadow(W, H)
    cat(im, "calm", 170, 300, 150)
    cat(im, "happy", 310, 300, 105, KITTEN)
    cat(im, "blank", 480, 300, 190, KURO)
    d = ImageDraw.Draw(im)
    f = F(20)
    for x, y, t in ((310, 175, "めったにない"), (480, 125, "めったにない"), (560, 110, "")):
        d.text((x - f.getlength(t) / 2, y), t, font=f, fill=(255, 255, 255), stroke_width=3, stroke_fill=INK)
    caption(im, "いま ここに いることも、めったにないこと")
    return im


def p_thanks():
    im = meadow(W, H, sky=((180, 210, 240), (252, 226, 200)))
    cat(im, "happy", 200, 300, 160)
    cat(im, "happy", 330, 300, 105, KITTEN)
    cat(im, "shy", 480, 300, 190, KURO)
    bubble(im, 200, 130, "ありがとう")
    bubble(im, 470, 165, "…ありがとう", 20)
    caption(im, "みんなに「ありがとう」")
    return im


def p_end():
    im = book_page(W, H, [("有り難い", 54, "mincho", (150, 70, 50)), ("めったにない。だから、ありがたい。", 26, "gothic", INK)])
    cat(im, "happy", 320, 340, 120, item="book")
    bubble(im, 470, 250, "見てくれて、ありがとう", 20)
    return im


PANELS = [
    ("0:00", "オープニング", "朝の野原。子ねこがお魚クッキーを分けてくれる。「ありがとう」", p_open),
    ("0:15", "「ありがとう」ってなに？", "ことにゃんが首をかしげて、ことば帖をひらく", p_question),
    ("0:22", "お話の世界へ", "ページが光って、ことにゃんごと吸いこまれる", p_dive),
    ("0:30", "有り難し", "ことば帖のページ：ありがとう＝有り難し＝めったにない", p_word),
    ("0:55", "海の底の亀", "深い海の底。目を閉じた、やさしい年寄りの亀", p_deep),
    ("1:25", "百年に一度", "季節がめぐり月日が流れ、百年に一度だけ海の上へ", p_rise),
    ("1:55", "ただよう丸太", "穴のあいた丸太が、風と波にまかせてただよう", p_log),
    ("2:20", "凪の日も、嵐の日も", "東へ西へ。広い海で、丸太はどこにいるかわからない", p_storm),
    ("2:40", "めったにない出会い", "亀が顔を出す…ちょうど丸太の穴に、すぽっ", p_meet),
    ("3:05", "人として生まれること", "『法句経』のことば。いま生きていることは、もっとめったにない", p_sutra),
    ("3:35", "野原にもどって", "子ねこ、くろ、ごはん、晴れた空。どれも めったにない", p_back),
    ("4:10", "ありがとう", "ひとりひとりに「ありがとう」。くろも照れて「…ありがとう」", p_thanks),
    ("4:35", "エンディング", "「有り難い」のページ。ことにゃん「見てくれて、ありがとう」", p_end),
]


def storyboard():
    cols, pw, ph, cap_h, pad = 3, W, H, 96, 28
    rows = (len(PANELS) + cols - 1) // cols
    sheet = Image.new("RGB", (pad + cols * (pw + pad), 150 + rows * (ph + cap_h + pad)), (246, 242, 234))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 34), "絵コンテ ── 長編01『ありがとう』（横長 16:9・約5分）", font=F(48, "bold"), fill=INK)
    for i, (tc, title, desc, fn) in enumerate(PANELS):
        x = pad + (i % cols) * (pw + pad)
        y = 130 + (i // cols) * (ph + cap_h + pad)
        im = fn().convert("RGB")
        sheet.paste(im, (x, y))
        d.rectangle((x, y, x + pw, y + ph), outline=INK, width=3)
        d.rounded_rectangle((x + 10, y + 10, x + 90, y + 44), radius=10, fill=(84, 62, 54))
        d.text((x + 20, y + 13), tc, font=F(24, "bold"), fill=(255, 255, 255))
        d.text((x, y + ph + 10), f"{i + 1}. {title}", font=F(28, "bold"), fill=INK)
        d.text((x, y + ph + 52), desc, font=F(20), fill=(110, 90, 80))
    return sheet


def synopsis():
    Wd, Hd = 1800, 1500
    im = grad(Wd, Hd, (252, 246, 232), (240, 228, 206))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, Wd - 40, Hd - 40), radius=30, outline=INK, width=5)
    d.text((100, 90), "長編01", font=F(40, "bold"), fill=(150, 70, 50))
    d.text((100, 145), "『ありがとう』", font=F(100, "mincho"), fill=INK)
    d.text((110, 280), "百年に一度の、めったにないこと", font=F(42), fill=(110, 90, 80))
    cat(im, "happy", Wd - 300, 420, 360, item="book")
    info = [("ことば", "ありがとう ＝ 有り難し（有ることが難しい・めったにない）"),
            ("元のお話", "仏教のたとえ話「盲亀浮木」（『雑阿含経』など）／『法句経』"),
            ("形式", "横長 1920×1080・約5分・チャプター付き・セリフなし"),
            ("音楽", "ほのぼのお散歩 → しっとり夕暮れ（海）→ ワルツ（マリンバ）")]
    y = 380
    for k, v in info:
        d.rounded_rectangle((100, y, 290, y + 50), radius=12, fill=INK)
        d.text((118, y + 8), k, font=F(28, "bold"), fill=(255, 255, 255))
        d.text((320, y + 6), v, font=F(32), fill=INK)
        y += 70
    d.text((100, y + 30), "あらすじ", font=F(44, "bold"), fill=(150, 70, 50))
    story = [
        "ある朝、子ねこにおやつを分けてもらったことにゃんは「ありがとう」と言い、ふと思う。",
        "――「ありがとう」って、どういう意味だろう？",
        "ことば帖をひらくと、ページが光り、昔話の海へ。「ありがとう」はもともと「有り難し」――めったにない、という意味。",
        "広い海の底に、目の見えない亀がいる。亀は百年に一度だけ、海の上に顔を出す。",
        "海の上には、穴のあいた丸太が一本、風と波にまかせてただよっている。",
        "亀が顔を出したそこに、ちょうど丸太があって、穴にすぽっと首が入る――それくらい、めったにないこと。",
        "お釈迦さまは、人として生まれ、いま生きていることは、それよりもめったにないことだ、とたとえた。",
        "野原に戻ったことにゃん。子ねこがいて、くろがいて、ごはんがあって、空が晴れている。どれも、めったにないこと。",
        "ことにゃんは、ひとりひとりに「ありがとう」を伝える。最後に画面のこちらへ――「見てくれて、ありがとう」。",
    ]
    f = F(30)
    y += 100
    for line in story:
        # 長い行は折り返す
        buf = ""
        for ch in line:
            if f.getlength(buf + ch) > Wd - 220:
                d.text((110, y), buf, font=f, fill=INK)
                y += 46
                buf = ""
            buf += ch
        d.text((110, y), buf, font=f, fill=INK)
        y += 58
    return im.convert("RGB")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    synopsis().save(OUT / "あらすじ.png")
    storyboard().save(OUT / "絵コンテ.png")
    print(OUT / "あらすじ.png")
    print(OUT / "絵コンテ.png")
