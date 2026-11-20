"""設定の読み込み・フォント・文字描画など、各ツールで共通の処理。"""
from __future__ import annotations

import functools
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent   # youtube/


@functools.lru_cache(maxsize=1)
def config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_yaml(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@functools.lru_cache(maxsize=None)
def _font_path(kind: str) -> str:
    for cand in config()["fonts"][kind]:
        p = Path(cand)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            return str(p)
    raise FileNotFoundError(
        f"日本語フォントが見つかりません（fonts.{kind}）。"
        "tools/setup_fonts.sh を実行するか config.yaml の fonts にパスを追加してください。")


@functools.lru_cache(maxsize=None)
def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_font_path("bold" if bold else "regular"), size)


# ---- 文字まわり -------------------------------------------------------------------
_NO_LINE_START = set("、。，．・：；？！ー」』）】〉》〕…‥ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ!?)]")
_NO_LINE_END = set("「『（【〈《〔([")


def wrap(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """日本語向けの折り返し（簡易禁則つき）。\\n は強制改行。"""
    lines: list[str] = []
    for para in str(text).split("\n"):
        cur = ""
        for ch in para:
            if fnt.getlength(cur + ch) <= max_width or not cur:
                cur += ch
                continue
            # 行頭禁則：はみ出す文字が句読点などなら前の行にぶら下げる
            if ch in _NO_LINE_START:
                cur += ch
                continue
            # 行末禁則：開きカッコで終わるなら次行へ送る
            carry = ""
            while cur and cur[-1] in _NO_LINE_END:
                carry = cur[-1] + carry
                cur = cur[:-1]
            lines.append(cur)
            cur = carry + ch
        lines.append(cur)
    return lines


def text_block(draw: ImageDraw.ImageDraw, box, text, fnt, fill, align="center",
               valign="center", line_spacing=1.25, stroke=0, stroke_fill=None, shrink_to_fit=True):
    """box=(x0,y0,x1,y1) の中に折り返して文字を描く。入りきらなければ縮小する。"""
    x0, y0, x1, y1 = box
    size = fnt.size
    while True:
        f = fnt.font_variant(size=size)
        lines = wrap(text, f, x1 - x0 - stroke * 2)
        lh = int(size * line_spacing)
        total = lh * len(lines) - (lh - size)
        if not shrink_to_fit or (total <= y1 - y0 and all(f.getlength(l) <= x1 - x0 for l in lines)) or size <= 14:
            break
        size = int(size * 0.92)
    if valign == "center":
        y = y0 + (y1 - y0 - total) / 2
    elif valign == "bottom":
        y = y1 - total
    else:
        y = y0
    for line in lines:
        w = f.getlength(line)
        if align == "center":
            x = x0 + (x1 - x0 - w) / 2
        elif align == "right":
            x = x1 - w
        else:
            x = x0
        draw.text((x, y), line, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        y += lh
    return size


def vertical_gradient(size, top, bottom) -> Image.Image:
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return grad.resize((w, h)).convert("RGBA")


def rounded_box(img: Image.Image, box, radius, fill, outline=None, width=0, shadow=True):
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        x0, y0, x1, y1 = box
        ImageDraw.Draw(sh).rounded_rectangle((x0 + 8, y0 + 12, x1 + 8, y1 + 12), radius, fill=(0, 0, 0, 40))
        img.alpha_composite(sh)
    ImageDraw.Draw(img).rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)


def category(cat: str) -> dict:
    cats = config()["categories"]
    if cat not in cats:
        raise ValueError(f"category '{cat}' は config.yaml にありません（{list(cats)}）")
    return cats[cat]
