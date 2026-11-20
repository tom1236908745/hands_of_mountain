"""キャラクター表情一覧（設定資料）を character/chiefuku_sheet.png に書き出す。"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chiefuku  # noqa: E402
from common import ROOT, font  # noqa: E402

S, COLS = 360, 5
exprs = chiefuku.EXPRESSIONS
rows = (len(exprs) + COLS - 1) // COLS
sheet = Image.new("RGBA", (S * COLS, (S + 60) * rows + 110), (252, 247, 236, 255))
d = ImageDraw.Draw(sheet)
d.text((30, 26), "ちえふく 表情一覧（tools/chiefuku.py の expression 名）", font=font(46), fill=(80, 56, 40))
for i, e in enumerate(exprs):
    x, y = (i % COLS) * S, 110 + (i // COLS) * (S + 60)
    sheet.alpha_composite(chiefuku.draw(e, S), (x, y))
    label = f"{e}（{chiefuku.EXPRESSION_LABELS[e]}）"
    f = font(30, bold=False)
    d.text((x + (S - f.getlength(label)) / 2, y + S + 6), label, font=f, fill=(80, 56, 40))
out = ROOT / "character" / "chiefuku_sheet.png"
sheet.convert("RGB").save(out)
print(out)
