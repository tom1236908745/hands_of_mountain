"""音楽は ep01（ホタル版）と同じ時間割なので、そのまま使う。"""
import importlib.util
from pathlib import Path

_p = Path(__file__).resolve().parent.parent / "ep01_ichigu" / "score.py"
_spec = importlib.util.spec_from_file_location("ep01_score", _p)
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)

DURATION = _m.DURATION
build = _m.build
