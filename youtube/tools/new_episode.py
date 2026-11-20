"""新しいエピソードの台本ファイルをテンプレートから作る。

  python tools/new_episode.py shogyomujo          → episodes/004_shogyomujo.yaml（番号は自動）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ep_dir = ROOT / "episodes"
if len(sys.argv) < 2 or not re.fullmatch(r"[a-z0-9_]+", sys.argv[1]):
    sys.exit("使い方: python tools/new_episode.py <ローマ字のslug>  例: saiougauma")
nums = [int(p.name[:3]) for p in ep_dir.glob("[0-9][0-9][0-9]_*.yaml")]
n = max(nums, default=0) + 1
out = ep_dir / f"{n:03d}_{sys.argv[1]}.yaml"
text = (ep_dir / "_template.yaml").read_text(encoding="utf-8")
text = text.split("id: ", 1)[1]
out.write_text(f'id: "{n:03d}"' + text[text.index("\n"):], encoding="utf-8")
print(out)
