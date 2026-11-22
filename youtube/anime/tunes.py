"""曲の候補（音色はそのとき選んでいるスタイル。既定はマリンバで聞きくらべ）。

  python anime/tunes.py              # 全曲を output/sound_samples/tunes/ に書き出す（マリンバ）
  python anime/tunes.py --sound lofi # 音色を変えて

楽譜は「音名:拍数」をスペースでつなぐ。休符は "-"。例 "E5:1 G5:0.5 -:0.5"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import audio  # noqa: E402
from audio import Mix  # noqa: E402


def play(m, t0, beat, score, vel=0.5, decay=1.2, pan=0.1):
    t = t0
    for tok in score.split():
        n, d = tok.split(":")
        if n != "-":
            for nn in n.split("+"):                       # "C4+E4" で和音
                m.music_box(nn, t, vel=vel, decay=decay, pan=pan)
        t += float(d) * beat
    return t


def boom_chick(m, t0, beat, chords, bars_per=1, beats=4, vel=0.32):
    """ベースと和音を交互に（ぶん・ちゃっ・ちゃっ）。chords = ["C3 E4+G4", ...]"""
    t = t0
    for ch in chords:
        bass, upper = ch.split(" ")
        for _ in range(bars_per):
            m.music_box(bass, t, vel=vel * 1.2, decay=1.0, pan=-0.2)
            for k in range(1, beats):
                for nn in upper.split("+"):
                    m.music_box(nn, t + k * beat, vel=vel * 0.7, decay=0.7, pan=0.3)
            t += beats * beat
    return t


def shaker(m, t0, t1, step, vel=0.05):
    t = t0
    i = 0
    while t < t1:
        n = int(0.04 * audio.SR)
        sig = m._noise(n, 5000, 12000) * __import__("numpy").exp(-m._env_t(0.04) * 80)
        m._add(m.dry, t, audio._pan(sig * vel * (1.0 if i % 2 == 0 else 0.6), 0.4))
        t += step
        i += 1


# ---------------------------------------------------------------- 曲
def sanpo():
    """① ほのぼのお散歩（ハ長調・120BPM）"""
    b = 60 / 120
    m = Mix(33.0, seed=21)
    prog = ["C3 E4+G4", "G2 D4+B4", "A2 C4+E4", "F2 A3+C4"] * 3 + ["F2 A3+C4", "G2 B3+D4", "C3 E4+G4"]
    boom_chick(m, 0.5, b, prog)
    mel = ("E5:1 G5:1 E5:1 C5:1 D5:1 G4:1 B4:1 D5:1 C5:1 E5:1 A5:1 G5:1 F5:1 E5:1 D5:2 "
           "E5:1 G5:1 C6:1.5 B5:0.5 A5:1 G5:1 E5:2 C5:1 E5:1 G5:1 E5:1 D5:4 "
           "E5:1 G5:1 E5:1 C5:1 D5:1 G4:1 B4:1 D5:1 C5:1 E5:1 A5:1 G5:1 F5:1 A5:1 G5:2 "
           "A5:1 G5:1 F5:1 D5:1 E5:2 D5:2 C5:4")
    play(m, 0.5, b, mel, vel=0.5)
    return m


def wakuwaku():
    """② わくわく ぽんぽこ（ヘ長調・124BPM・シェイカー）"""
    b = 60 / 124
    m = Mix(30.0, seed=22)
    bass = ("F2:1 -:0.5 F2:0.5 C3:1 -:1 " * 2 + "Bb2:1 -:0.5 Bb2:0.5 F2:1 -:1 C3:1 -:0.5 C3:0.5 G2:1 -:1 ") * 3
    play(m, 0.5, b, bass, vel=0.45, decay=0.8, pan=-0.3)
    shaker(m, 0.5, 28.0, b / 2)
    hook = ("C5:0.5 F5:0.5 -:0.5 F5:0.5 A5:0.5 G5:0.5 F5:1 -:0.5 C5:0.5 D5:0.5 F5:0.5 G5:1 -:1 "
            "Bb5:0.5 A5:0.5 G5:0.5 F5:0.5 G5:0.5 A5:0.5 F5:1 E5:0.5 F5:0.5 G5:0.5 C5:0.5 E5:1 -:1 ")
    t = play(m, 0.5 + 4 * b, b, hook, vel=0.5, decay=0.7)
    t = play(m, t, b, hook.replace("C5", "F5").replace("E5:1 -:1", "C6:2"), vel=0.5, decay=0.7)
    play(m, t, b, hook, vel=0.5, decay=0.7)
    for k in range(6):                                   # 和音のぽんっ
        m.music_box("A4", 0.5 + k * 16 * b + 7 * b, vel=0.25)
    return m


def yuugure():
    """③ しっとり夕暮れ（イ短調→ハ長調・72BPM・分散和音）"""
    b = 60 / 72
    m = Mix(32.0, seed=23)
    prog = [("A2", "A3 C4 E4 C4"), ("F2", "F3 A3 C4 A3"), ("C3", "C4 E4 G4 E4"), ("G2", "G3 B3 D4 B3"),
            ("A2", "A3 C4 E4 C4"), ("F2", "F3 A3 C4 A3"), ("G2", "G3 B3 D4 B3"), ("C3", "C4 E4 G4 C5")]
    t = 0.4
    for bass, arp in prog + prog[:1]:
        m.music_box(bass, t, vel=0.4, decay=2.2, pan=-0.2)
        notes = arp.split()
        for k in range(8):
            m.music_box(notes[k % 4], t + k * b / 2, vel=0.22, decay=1.0, pan=0.25)
        t += 4 * b
    mel = ("E5:2 D5:1 C5:1 A4:3 -:1 C5:2 D5:1 E5:1 D5:3 -:1 "
           "E5:2 G5:1 E5:1 C5:3 A4:1 B4:2 C5:1 D5:1 C5:4")
    play(m, 0.4, b, mel, vel=0.45, decay=2.0)
    return m


def wafuu():
    """④ 和風（陽音階 D E G A B・112BPM）"""
    b = 60 / 112
    m = Mix(34.5, seed=24)
    m.pad(["D3", "A3"], 0.3, 32.5, vel=0.45, attack=2.0)
    play(m, 0.5, b, ("D3:2 A2:2 " * 15), vel=0.35, decay=1.4, pan=-0.3)
    mel = ("A4:1 B4:1 D5:2 E5:1 D5:1 B4:2 A4:1 G4:1 A4:1 B4:1 A4:4 "
           "D5:1 E5:1 G5:2 A5:1 G5:1 E5:2 D5:1 E5:1 D5:1 B4:1 A4:4 "
           "B4:1 D5:1 E5:1 G5:1 A5:2 G5:1 E5:1 D5:1 B4:1 A4:1 B4:1 D5:4 "
           "E5:1 D5:1 B4:1 A4:1 G4:2 A4:2 D5:4")
    play(m, 0.5, b, mel, vel=0.5, decay=1.4)
    for t in (0.5, 8 * b + 0.5, 16 * b + 0.5, 24 * b + 0.5, 40 * b + 0.5):
        m._bell("A6", t, vel=0.12, decay=2.0)            # ちりん（風鈴）
    return m


def waltz():
    """⑤ ワルツ（ト長調・3拍子・104BPM）"""
    b = 60 / 104
    m = Mix(31.0, seed=25)
    prog = ["G2 B3+D4", "D3 A3+C4", "E3 G3+B3", "C3 E4+G4", "G2 B3+D4", "C3 E4+G4", "D3 F#3+A3", "G2 B3+D4"] * 2
    boom_chick(m, 0.5, b, prog, beats=3, vel=0.3)
    mel = ("D5:2 B4:1 A4:2 F#4:1 G4:2 B4:1 E5:3 D5:2 G5:1 E5:2 C5:1 A4:3 -:3 "
           "D5:2 B4:1 A4:2 F#4:1 G4:2 B4:1 E5:3 D5:1 E5:1 G5:1 C5:2 A4:1 G4:3 -:3")
    play(m, 0.5, b, mel, vel=0.5, decay=1.6)
    return m


TUNES = [("ほのぼのお散歩", sanpo), ("わくわくぽんぽこ", wakuwaku), ("しっとり夕暮れ", yuugure),
         ("和風（陽音階）", wafuu), ("ワルツ", waltz)]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sound", default="marimba")
    args = ap.parse_args()
    audio.STYLE = args.sound
    out = HERE.parent / "output" / "sound_samples" / "tunes"
    out.mkdir(parents=True, exist_ok=True)
    for i, (name, fn) in enumerate(TUNES, 1):
        wav = out / f"{i:02d}.wav"
        fn().write(wav, fade_out=2.5)
        m4a = out / f"{i:02d}_{name}_{audio.STYLES[args.sound]['label']}.m4a"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "aac", "-b:a", "192k",
                        str(m4a)], check=True)
        wav.unlink()
        print(m4a)
