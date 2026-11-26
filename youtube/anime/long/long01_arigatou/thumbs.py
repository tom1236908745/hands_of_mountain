"""長編01 サムネイル候補（1280x720）を output/anime/long01_arigatou/thumbs/ に出す。"""
import sys, importlib.util
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
YT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(YT / "anime"), str(YT / "anime" / "cast"), str(YT / "tools")]
import mascot  # noqa: E402
from engine import font  # noqa: E402

sp = importlib.util.spec_from_file_location("s", HERE / "story.py")
m = importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)
m.CAPTIONS.clear()
OUT = YT / "output" / "anime" / "long01_arigatou" / "thumbs"
OUT.mkdir(parents=True, exist_ok=True)
BOLD, MIN = "MPLUSRounded1c-ExtraBold.ttf", "ShipporiMinchoB1-ExtraBold.ttf"
INK = (84, 62, 54)
KURO = dict(fur=(78, 72, 80), patch_a=(62, 58, 66), patch_b=(46, 42, 50), eye=(250, 214, 110),
            line=(40, 34, 38), ear_in=(196, 150, 150), cheek=(230, 140, 140))


def bg(t, blur=0):
    im = m.render_story(t).resize((1280, 720)).convert("RGBA")
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


def txt(im, xy, s, size, fill, f=BOLD, stroke=8, sc=INK, anchor="la"):
    ImageDraw.Draw(im).text(xy, s, font=font(f, size), fill=fill, stroke_width=stroke, stroke_fill=sc, anchor=anchor)


def cat(im, expr, x, y, s, **kw):
    im.alpha_composite(mascot.draw(expr, s, **kw), (int(x), int(y)))


# A：ことにゃんの顔を大きく＋大きな文字（明るい・いちばん目立つ）
a = bg(253.0, 3)
g2 = Image.new("RGBA", a.size, (0, 0, 0, 0))
ImageDraw.Draw(g2).rectangle((0, 600, 1280, 720), fill=(132, 182, 112, 255))
a.alpha_composite(g2.filter(ImageFilter.GaussianBlur(3)))
cat(a, "surprised", 700, 120, 640, item="book")
txt(a, (60, 70), "「ありがとう」", 112, (255, 236, 150), stroke=10)
txt(a, (70, 230), "ほんとうは", 70, (255, 255, 255))
txt(a, (70, 330), "“めったにない”", 98, (255, 255, 255), stroke=10)
txt(a, (70, 470), "って意味だった…！", 64, (255, 236, 150))
a.convert("RGB").save(OUT / "A_ことにゃんどアップ.png")

# B：海の底の亀（しっとり・物語の入り口）
b = bg(75.0)
dark = Image.new("RGBA", b.size, (0, 0, 0, 0))
ImageDraw.Draw(dark).rectangle((0, 0, 1280, 300), fill=(4, 10, 30, 120))
b.alpha_composite(dark.filter(ImageFilter.GaussianBlur(40)))
txt(b, (640, 60), "百年に一度だけ", 72, (255, 255, 255), f=MIN, stroke=0, anchor="ma")
txt(b, (640, 150), "海の上に顔を出す亀の話", 72, (255, 255, 255), f=MIN, stroke=0, anchor="ma")
txt(b, (640, 262), "――「ありがとう」の本当の意味", 40, (255, 230, 170), f=MIN, stroke=0, anchor="ma")
cat(b, "thinking", 1010, 470, 250)
b.convert("RGB").save(OUT / "B_海の底の亀.png")

# C：ことば帖「ありがとう＝有り難し」（クイズ・答え合わせ型）
c = bg(40.0)
c = c.crop((0, 0, 1280, 720))
over = Image.new("RGBA", c.size, (0, 0, 0, 0))
ImageDraw.Draw(over).rectangle((0, 0, 1280, 720), fill=(252, 246, 232, 120))
c.alpha_composite(over)
txt(c, (80, 70), "Q.", 90, (150, 70, 50), stroke=0)
txt(c, (200, 80), "「ありがとう」の語源は？", 72, INK, stroke=0)
txt(c, (120, 260), "有り難し", 190, (150, 70, 50), f=MIN, stroke=0)
txt(c, (130, 520), "＝ めったに ない", 76, INK, stroke=0)
cat(c, "wink", 920, 330, 360, item="book")
c.convert("RGB").save(OUT / "C_ことば帖クイズ.png")

# D：みんなで「ありがとう」（ほっこり・キャラ推し）
d = bg(253.0, 2)                                   # 空と森だけのカット
ground = Image.new("RGBA", d.size, (0, 0, 0, 0))
ImageDraw.Draw(ground).rectangle((0, 560, 1280, 720), fill=(132, 182, 112, 255))
ImageDraw.Draw(ground).line([(0, 560), (1280, 560)], fill=(166, 206, 136), width=6)
d.alpha_composite(ground)
cat(d, "happy", 140, 260, 420, item="book")
cat(d, "happy", 540, 400, 260, palette=dict(fur=(250, 250, 252), patch_a=(178, 180, 192), patch_b=(112, 114, 126)))
cat(d, "shy", 780, 210, 470, palette=KURO, mirror=True)
txt(d, (640, 40), "「ありがとう」って", 84, (255, 255, 255), stroke=10, anchor="ma")
txt(d, (640, 150), "どういう意味？", 84, (255, 236, 150), stroke=10, anchor="ma")
d.convert("RGB").save(OUT / "D_みんなでありがとう.png")

# 一覧
names = ["A_ことにゃんどアップ", "B_海の底の亀", "C_ことば帖クイズ", "D_みんなでありがとう"]
sheet = Image.new("RGB", (1280, 760), (30, 30, 34))
dd = ImageDraw.Draw(sheet)
for i, n in enumerate(names):
    im = Image.open(OUT / f"{n}.png").resize((640, 360))
    x, y = (i % 2) * 640, (i // 2) * 380
    sheet.paste(im, (x, y + 20))
    dd.text((x + 8, y), n, font=font(BOLD, 18), fill=(240, 240, 240))
sheet.save(OUT / "一覧.png")
print(OUT)


# ================================================================ A案の派生（A1〜A4）
def meadow_bg():
    im = bg(253.0, 3)
    g = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).rectangle((0, 600, 1280, 720), fill=(132, 182, 112, 255))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(3)))
    return im


def sea_bg():
    im = bg(191.0, 2)                                     # 海と丸太と亀（めったにない出会い）
    return im


def burst(im, cx, cy, col=(255, 244, 200, 90)):
    import math
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(18):
        a0, a1 = k / 18 * 2 * math.pi, (k + 0.45) / 18 * 2 * math.pi
        d.polygon([(cx, cy), (cx + 1600 * math.cos(a0), cy + 1600 * math.sin(a0)),
                   (cx + 1600 * math.cos(a1), cy + 1600 * math.sin(a1))], fill=col)
    im.alpha_composite(lay)


# A1：Aの言いかえ。「知らなかった…」で共感
a1 = meadow_bg()
burst(a1, 1000, 420)
cat(a1, "surprised", 700, 120, 640, item="book")
txt(a1, (60, 80), "「ありがとう」の", 96, (255, 255, 255), stroke=10)
txt(a1, (60, 220), "本当の意味", 120, (255, 236, 150), stroke=12)
txt(a1, (70, 400), "知らなかった…", 86, (255, 255, 255), stroke=10)
a1.convert("RGB").save(OUT / "A1_知らなかった.png")

# A2：Aの文字＋小さく亀（お話の中身が少し見える）
a2 = meadow_bg()
cat(a2, "surprised", 700, 120, 640, item="book")
import turtle as tt  # noqa: E402
from engine import Frame, Cam  # noqa: E402
tf = Frame((1280, 720), Cam(640, 360, 1.0))
tf.base_img = Image.new("RGBA", (1280 * 2, 720 * 2), (0, 0, 0, 0))
tt.draw(tf.base(), 330, 600, 120, neck=0.6)
tl = tf.base_img.resize((1280, 720), Image.LANCZOS)
a2.alpha_composite(tl)
txt(a2, (60, 60), "「ありがとう」", 112, (255, 236, 150), stroke=10)
txt(a2, (70, 210), "ほんとうは", 70, (255, 255, 255))
txt(a2, (60, 300), "“めったにない”", 98, (255, 255, 255), stroke=10)
txt(a2, (70, 430), "って意味だった…！", 60, (255, 236, 150))
a2.convert("RGB").save(OUT / "A2_亀つき.png")

# A3：海の背景（丸太と亀）×ことにゃんのアップ
a3 = sea_bg()
shade = Image.new("RGBA", a3.size, (0, 0, 0, 0))
ImageDraw.Draw(shade).rectangle((0, 0, 760, 720), fill=(10, 30, 60, 110))
a3.alpha_composite(shade.filter(ImageFilter.GaussianBlur(60)))
cat(a3, "surprised", 720, 150, 600, item="book")
txt(a3, (60, 80), "「ありがとう」", 112, (255, 236, 150), stroke=10)
txt(a3, (70, 230), "百年に一度の", 76, (255, 255, 255))
txt(a3, (60, 330), "めったにない", 110, (255, 255, 255), stroke=12)
txt(a3, (70, 480), "ことだった", 76, (255, 236, 150))
a3.convert("RGB").save(OUT / "A3_海背景.png")

# A4：短く・大きく（スマホで一番読みやすい）
a4 = meadow_bg()
burst(a4, 980, 430, (255, 236, 170, 80))
cat(a4, "surprised", 660, 90, 680, item="book")
txt(a4, (50, 90), "ありがとう", 150, (255, 236, 150), stroke=14)
txt(a4, (60, 290), "の語源", 110, (255, 255, 255), stroke=12)
txt(a4, (60, 450), "知ってる？", 110, (255, 255, 255), stroke=12)
a4.convert("RGB").save(OUT / "A4_短く大きく.png")

names2 = ["A1_知らなかった", "A2_亀つき", "A3_海背景", "A4_短く大きく"]
sheet = Image.new("RGB", (1280, 760), (30, 30, 34))
dd = ImageDraw.Draw(sheet)
for i, n in enumerate(names2):
    im = Image.open(OUT / f"{n}.png").resize((640, 360))
    x, y = (i % 2) * 640, (i // 2) * 380
    sheet.paste(im, (x, y + 20))
    dd.text((x + 8, y), n, font=font(BOLD, 18), fill=(240, 240, 240))
sheet.save(OUT / "一覧_A案.png")
