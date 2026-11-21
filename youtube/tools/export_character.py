"""キャラクター画像を1枚ずつ書き出す（白背景 or 透過）。

  python tools/export_character.py                  # 白背景・1200px → output/character/white/
  python tools/export_character.py --transparent    # 透過PNG → output/character/transparent/
  python tools/export_character.py --size 3000      # 大きさを変える（グッズ用）

書き出すもの：全表情 ＋ ことば帖・ちょうちん・ほたるの着ぐるみ（ほたるにゃん）の版、一覧画像、zip
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mascot  # noqa: E402
from common import ROOT, config, font  # noqa: E402

VARIANTS = [  # (ファイル名, 表情, item, 光の明るさ, 説明)
    ("book_happy", "happy", "book", 0.0, "ことば帖"),
    ("book_normal", "normal", "book", 0.0, "ことば帖"),
    ("lantern_off", "normal", "lantern", 0.0, "ちょうちん"),
    ("lantern_on", "happy", "lantern", 1.0, "ちょうちん（灯り）"),
    ("hotarunyan", "normal", "firefly", 0.0, "ほたるにゃん"),
    ("hotarunyan_strain", "strain", "firefly", 0.4, "ほたるにゃん（力む）"),
    ("hotarunyan_glow", "happy", "firefly", 1.0, "ほたるにゃん（光る）"),
]


def render(expr, size, item, glow, white):
    img = mascot.draw(expr, size, item=item, lantern=glow)
    if not white:
        return img
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.alpha_composite(img)
    return bg.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1200)
    ap.add_argument("--transparent", action="store_true")
    args = ap.parse_args()
    white = not args.transparent
    name = config()["channel"]["character_name"]
    out = ROOT / "output" / "character" / ("white" if white else "transparent")
    out.mkdir(parents=True, exist_ok=True)

    items = [(f"{i + 1:02d}_{e}", e, None, 0.0, mascot.EXPRESSION_LABELS[e]) for i, e in enumerate(mascot.EXPRESSIONS)]
    items += [(f"{len(items) + i + 1:02d}_{n}", e, it, g, lab) for i, (n, e, it, g, lab) in enumerate(VARIANTS)]

    files, thumbs = [], []
    for fname, e, it, g, lab in items:
        img = render(e, args.size, it, g, white)
        p = out / f"{name}_{fname}.png"
        img.save(p, optimize=True)
        files.append(p)
        thumbs.append((img, lab))

    # 一覧（白背景）
    S, cols = 300, 6
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (S * cols, (S + 50) * rows + 20), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    f = font(26, bold=False)
    for i, (img, lab) in enumerate(thumbs):
        x, y = (i % cols) * S, 10 + (i // cols) * (S + 50)
        t = img.convert("RGBA").resize((S, S), Image.LANCZOS)
        sheet.paste(t, (x, y), t)
        d.text((x + (S - f.getlength(lab)) / 2, y + S + 4), lab, font=f, fill=(104, 82, 74))
    sheet_path = out / f"{name}_一覧.png"
    sheet.save(sheet_path)

    zpath = out / f"{name}_{'白背景' if white else '透過'}_{args.size}px.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files + [sheet_path]:
            z.write(p, p.name)
    print(f"{len(files)}枚 → {out}\n一覧 → {sheet_path}\nzip → {zpath}")


if __name__ == "__main__":
    main()
