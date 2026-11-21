"""音楽は ep07 と同じ時間割なので共通。"""
import importlib.util
from pathlib import Path

_p = Path(__file__).resolve().parent.parent / "ep07_wagenaigo" / "score.py"
_spec = importlib.util.spec_from_file_location("ep07_score", _p)
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
DURATION = _m.DURATION
build = _m.build
