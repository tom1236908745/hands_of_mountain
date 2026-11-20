"""LINEスタンプ用の画像一式を作る（LINE Creators Market のガイドライン準拠）。

  python tools/stamps.py                   # stamps/stamps.yaml → output/line_stamps/
  python tools/stamps.py --sheet           # 一覧画像（確認用）も出す
  python tools/stamps.py --hires 2000      # グッズ用の高解像度キャラ画像（全表情）も出す

LINE の主な規定:
  スタンプ 最大 370x320px（幅・高さは偶数）/ 背景透過PNG / 1枚1MB以下 / 余白 約10px
  メイン画像 240x240 / タブ画像 96x74 / 個数 8,16,24,32,40
  提出用 zip: 01.png〜NN.png, main.png, tab.png
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mascot  # noqa: E402
from common import ROOT, config, font, load_yaml, wrap  # noqa: E402

STAMP_W, STAMP_H, MARGIN = 370, 320, 10
DEFAULT_COLOR = (108, 72, 48)
VALID_COUNTS = (8, 16, 24, 32, 40)


def _trim(img: Image.Image) -> Image.Image:
    bbox = img.getchannel("A").getbbox()
    return img.crop(bbox) if bbox else img


def _fit(img: Image.Image, w: int, h: int) -> Image.Image:
    img = _trim(img)
    r = min(w / img.width, h / img.height)
    return img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))), Image.LANCZOS)


def _text_layer(text: str, max_w: int, max_h: int, color) -> Image.Image:
    """縁取り付きの文字を、指定の箱に収まる最大サイズで描いた透過画像。"""
    size = 90
    while size > 16:
        f = font(size)
        stroke = max(4, size // 7)
        lines = wrap(text, f, 10_000)       # 改行は \n の指定どおり
        lh = int(size * 1.12)
        w = max(f.getlength(l) for l in lines) + stroke * 2
        h = lh * (len(lines) - 1) + size * 1.15 + stroke * 2
        if w <= max_w and h <= max_h:
            break
        size -= 2
    layer = Image.new("RGBA", (int(w) + 4, int(h) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = stroke
    for l in lines:
        x = (layer.width - f.getlength(l)) / 2
        d.text((x, y), l, font=f, fill=tuple(color), stroke_width=stroke, stroke_fill=(255, 255, 255))
        y += lh
    return layer


def make_stamp(spec: dict) -> Image.Image:
    canvas = Image.new("RGBA", (STAMP_W, STAMP_H), (0, 0, 0, 0))
    inner_w, inner_h = STAMP_W - MARGIN * 2, STAMP_H - MARGIN * 2
    text = spec.get("text", "")
    text_h = 0
    if text:
        n_lines = text.count("\n") + 1
        text_h = int(inner_h * (0.30 if n_lines == 1 else 0.42))
    ch = _fit(mascot.draw(spec["expression"], 1200), inner_w, inner_h - int(text_h * 0.75))
    top = spec.get("text_pos", "top") == "top"
    cx = (STAMP_W - ch.width) // 2
    cy = STAMP_H - MARGIN - ch.height if top else MARGIN
    canvas.alpha_composite(ch, (cx, cy))
    if text:
        t = _text_layer(text, inner_w, text_h, spec.get("color", DEFAULT_COLOR))
        ty = MARGIN if top else STAMP_H - MARGIN - t.height
        canvas.alpha_composite(t, ((STAMP_W - t.width) // 2, ty))
    return canvas


def make_icon(expression: str, w: int, h: int, margin: int) -> Image.Image:
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ch = _fit(mascot.draw(expression, 1000), w - margin * 2, h - margin * 2)
    canvas.alpha_composite(ch, ((w - ch.width) // 2, (h - ch.height) // 2))
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "stamps" / "stamps.yaml")
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "line_stamps")
    ap.add_argument("--sheet", action="store_true", help="確認用の一覧画像も出す")
    ap.add_argument("--hires", type=int, default=0, help="グッズ用に全表情をこのpxで書き出す")
    args = ap.parse_args()

    spec = load_yaml(args.config)
    stamps = spec["stamps"]
    if len(stamps) not in VALID_COUNTS:
        print(f"⚠ スタンプは {VALID_COUNTS} 個のどれかで申請します（今は {len(stamps)} 個）")
    args.out.mkdir(parents=True, exist_ok=True)

    files = []
    imgs = []
    for i, s in enumerate(stamps, 1):
        img = make_stamp(s)
        p = args.out / f"{i:02d}.png"
        img.save(p, optimize=True)
        files.append(p)
        imgs.append(img)
        if p.stat().st_size > 1_000_000:
            print(f"⚠ {p.name} が1MBを超えています")
    main_img = make_icon(spec.get("main", {}).get("expression", "happy"), 240, 240, 8)
    tab_img = make_icon(spec.get("tab", {}).get("expression", "normal"), 96, 74, 2)
    main_img.save(args.out / "main.png", optimize=True)
    tab_img.save(args.out / "tab.png", optimize=True)
    files += [args.out / "main.png", args.out / "tab.png"]

    with zipfile.ZipFile(args.out / "line_stamps.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.name)
    print(f"LINEスタンプ {len(stamps)}個 → {args.out}/line_stamps.zip（そのまま申請画面にアップロード可）")

    if args.sheet:
        cols = 4
        rows = (len(imgs) + cols - 1) // cols
        sheet = Image.new("RGBA", (STAMP_W * cols, STAMP_H * rows), (236, 240, 246, 255))
        d = ImageDraw.Draw(sheet)
        for i, im in enumerate(imgs):
            x, y = (i % cols) * STAMP_W, (i // cols) * STAMP_H
            d.rectangle((x, y, x + STAMP_W - 1, y + STAMP_H - 1), outline=(200, 205, 215))
            sheet.alpha_composite(im, (x, y))
        sheet.convert("RGB").save(args.out / "_sheet.png")
        print(f"一覧 → {args.out / '_sheet.png'}")

    if args.hires:
        hd = ROOT / "output" / "character_hires"
        hd.mkdir(parents=True, exist_ok=True)
        for e in mascot.EXPRESSIONS:
            mascot.draw(e, args.hires).save(hd / f"{config()["channel"]["character_name"]}_{e}.png")
        print(f"グッズ用高解像度 {args.hires}px → {hd}")


if __name__ == "__main__":
    main()
