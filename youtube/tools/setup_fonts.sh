#!/usr/bin/env bash
# 動画・スタンプ用のフォント（M PLUS Rounded 1c・しっぽり明朝 / SIL Open Font License・商用利用OK）を取得
set -euo pipefail
cd "$(dirname "$0")/../assets/fonts"
base="https://raw.githubusercontent.com/google/fonts/main/ofl/mplusrounded1c"
for f in MPLUSRounded1c-ExtraBold.ttf MPLUSRounded1c-Bold.ttf; do
  [ -f "$f" ] || { echo "download $f"; curl -fsSL -o "$f" "$base/$f"; }
done
# アニメの「ことば」表示用の明朝体（しっぽり明朝 B1 / SIL Open Font License）
mbase="https://raw.githubusercontent.com/google/fonts/main/ofl/shipporiminchob1"
for f in ShipporiMinchoB1-ExtraBold.ttf; do
  [ -f "$f" ] || { echo "download $f"; curl -fsSL -o "$f" "$mbase/$f"; }
done
echo "OK: $(pwd)"
