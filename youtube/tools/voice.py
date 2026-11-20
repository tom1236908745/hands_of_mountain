"""音声合成（VOICEVOX）。エンジンが無ければ None を返し、呼び出し側は無音で進める。"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from common import config

SAMPLE_RATE = 24000


def _vv():
    return config().get("voice") or {}


def available() -> bool:
    v = _vv()
    if v.get("engine") != "voicevox":
        return False
    try:
        with urllib.request.urlopen(v["url"].rstrip("/") + "/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def synth(text: str, speaker: str, out_dir: Path) -> Path | None:
    """text を読み上げた wav を作って返す（同じ文はキャッシュを再利用）。"""
    v = _vv()
    spk = v.get("speakers", {}).get(speaker)
    if spk is None:
        return None
    key = hashlib.sha1(f"{spk}|{v.get('speed')}|{text}".encode()).hexdigest()[:16]
    out = out_dir / f"{key}.wav"
    if out.exists():
        return out
    base = v["url"].rstrip("/")
    q = urllib.parse.urlencode({"text": text, "speaker": spk})
    req = urllib.request.Request(f"{base}/audio_query?{q}", method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        query = json.load(r)
    query["speedScale"] = v.get("speed", 1.0)
    query["outputSamplingRate"] = SAMPLE_RATE
    query["outputStereo"] = False
    req = urllib.request.Request(f"{base}/synthesis?speaker={spk}", data=json.dumps(query).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        out_dir.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.read())
    return out


def duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def concat(segments: list[tuple[Path | None, float]], out: Path):
    """[(wavまたはNone, 秒数)] を順につないだ1本の wav を作る。None は無音。"""
    with wave.open(str(out), "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(SAMPLE_RATE)
        for path, sec in segments:
            want = int(round(sec * SAMPLE_RATE))
            data = b""
            if path is not None:
                with wave.open(str(path)) as src:
                    if src.getframerate() != SAMPLE_RATE or src.getnchannels() != 1:
                        raise RuntimeError(f"想定外の wav 形式: {path}")
                    data = src.readframes(src.getnframes())
            data = data[: want * 2]
            data += b"\x00\x00" * (want - len(data) // 2)
            dst.writeframes(data)
