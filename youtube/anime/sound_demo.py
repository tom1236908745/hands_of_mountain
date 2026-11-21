"""音色の聞きくらべ用サンプルを作る（映像なし・音だけ）。

  python anime/sound_demo.py                     # ep01（一隅を照らす）の曲で全スタイル
  python anime/sound_demo.py ep04_saiougauma     # ほかの回の曲で

出力：output/sound_samples/<ep>/NN_<スタイル名>.m4a
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "cast")]
import audio  # noqa: E402

ep = sys.argv[1] if len(sys.argv) > 1 else "ep01_ichigu"
out = HERE.parent / "output" / "sound_samples" / ep
out.mkdir(parents=True, exist_ok=True)
for i, (key, st) in enumerate(audio.STYLES.items(), 1):
    audio.STYLE = key
    spec = importlib.util.spec_from_file_location(f"score_{key}", HERE / "episodes" / ep / "score.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    wav = out / f"{i:02d}_{key}.wav"
    mod.build().write(wav)
    m4a = out / f"{i:02d}_{st['label']}.m4a"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "aac", "-b:a", "192k", str(m4a)],
                   check=True)
    wav.unlink()
    print(m4a)
