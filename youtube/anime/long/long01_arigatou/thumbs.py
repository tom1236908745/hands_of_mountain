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
