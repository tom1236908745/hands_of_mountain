#!/usr/bin/env bash
# 動画・スタンプ用のフォント（M PLUS Rounded 1c / SIL Open Font License・商用利用OK）を取得
set -euo pipefail
cd "$(dirname "$0")/../assets/fonts"
base="https://raw.githubusercontent.com/google/fonts/main/ofl/mplusrounded1c"
for f in MPLUSRounded1c-ExtraBold.ttf MPLUSRounded1c-Bold.ttf; do
  [ -f "$f" ] || { echo "download $f"; curl -fsSL -o "$f" "$base/$f"; }
done
echo "OK: $(pwd)"
