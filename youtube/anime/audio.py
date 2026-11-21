"""音楽・効果音を numpy だけで合成する（著作権を気にしなくていい自作BGM）。

使い方（エピソードの score.py から）:
    mix = Mix(duration=38)
    mix.music_box("C5", t=1.0, vel=0.8)
    mix.pad(["C4", "E4", "G4"], 0, 6.5)
    mix.crickets(); mix.wind()
    mix.write("audio.wav")
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(note) -> float:
    """'C4' 'F#5' 'Bb3' や MIDI番号 → 周波数"""
    if isinstance(note, (int, float)):
        return 440.0 * 2 ** ((note - 69) / 12)
    n = _NOTE[note[0].upper()]
    rest = note[1:]
    while rest and rest[0] in "#b":
        n += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    midi = 12 * (int(rest) + 1) + n
    return 440.0 * 2 ** ((midi - 69) / 12)


def _pan(sig, pan):
    """pan: -1(左)〜1(右)"""
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([sig * l, sig * r], axis=1)


class Mix:
    def __init__(self, duration: float, seed=1):
        self.n = int(duration * SR) + SR
        self.duration = duration
        self.music = np.zeros((self.n, 2), np.float32)   # リバーブをかけるバス
        self.dry = np.zeros((self.n, 2), np.float32)     # 環境音など（リバーブなし）
        self.rng = np.random.default_rng(seed)

    def _add(self, bus, t, stereo):
        i = int(t * SR)
        if i >= self.n:
            return
        j = min(self.n, i + len(stereo))
        bus[i:j] += stereo[: j - i]

    # ---------------------------------------------------------- 楽器
    def music_box(self, note, t, vel=0.6, decay=1.6, pan=0.0):
        """オルゴール（ベル）の音。倍音を少しずらすと金属っぽくなる。"""
        f = hz(note)
        dur = decay * 3
        tt = np.arange(int(dur * SR)) / SR
        sig = np.zeros_like(tt)
        for mult, amp, dk in ((1.0, 1.0, 1.0), (2.0, 0.35, 1.6), (3.01, 0.18, 2.4), (5.42, 0.1, 3.5),
                              (8.93, 0.05, 5.0)):
            if f * mult < SR / 2:
                sig += amp * np.sin(2 * np.pi * f * mult * tt) * np.exp(-tt * dk / decay)
        sig *= np.minimum(1, tt / 0.002)
        self._add(self.music, t, _pan(sig * vel * 0.22, pan))

    def pad(self, notes, t0, t1, vel=0.5, attack=1.2, release=1.5, bright=0.25):
        """やわらかいパッド（ゆっくり立ち上がる和音）。"""
        dur = t1 - t0 + release
        tt = np.arange(int(dur * SR)) / SR
        env = np.minimum(1, tt / attack) * np.clip((t1 - t0 + release - tt) / release, 0, 1)
        env = np.where(tt < t1 - t0, np.minimum(1, tt / attack), env)
        out = np.zeros((len(tt), 2), np.float32)
        for k, note in enumerate(notes):
            f = hz(note)
            for det, pan in ((-0.004, -0.5), (0.0, 0.0), (0.004, 0.5)):
                ph = self.rng.uniform(0, 6.28)
                s = np.sin(2 * np.pi * f * (1 + det) * tt + ph) + bright * np.sin(4 * np.pi * f * (1 + det) * tt)
                s *= 1 + 0.15 * np.sin(2 * np.pi * 0.3 * tt + k)
                out += _pan(s, pan)
        out *= (env * vel * 0.03 / max(1, len(notes) ** 0.5))[:, None]
        self._add(self.music, t0, out)

    def arpeggio(self, notes, t0, step, vel=0.5, decay=1.2, pan_spread=0.6):
        for i, n in enumerate(notes):
            pan = -pan_spread + 2 * pan_spread * (i / max(1, len(notes) - 1))
            self.music_box(n, t0 + i * step, vel, decay, pan)

    def melody(self, seq, t0, beat, vel=0.6, decay=1.8):
        """seq = [("E5", 拍数), (None, 拍数=休符), ...]"""
        t = t0
        for note, beats in seq:
            if note:
                self.music_box(note, t, vel, decay, pan=0.15)
            t += beats * beat
        return t

    # ---------------------------------------------------------- 効果音
    def blip_down(self, t, f0=1400, f1=520, dur=0.22, vel=0.25):
        """失敗の「ピッ」（音程が下がる）"""
        tt = np.arange(int(dur * SR)) / SR
        f = f0 * (f1 / f0) ** (tt / dur)
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = np.sin(ph) * np.exp(-tt * 9) * np.minimum(1, tt / 0.003)
        self._add(self.music, t, _pan(sig * vel, 0.1))

    def shimmer(self, t, dur=1.6, vel=0.2):
        """光がひろがる「ふわっ」（上がっていくノイズ）"""
        n = int(dur * SR)
        noise = self.rng.standard_normal(n)
        spec = np.fft.rfft(noise)
        freqs = np.fft.rfftfreq(n, 1 / SR)
        spec *= np.exp(-((freqs - 5000) / 3000) ** 2)
        sig = np.fft.irfft(spec, n)
        sig /= np.abs(sig).max() + 1e-9
        tt = np.arange(n) / SR
        env = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2
        self._add(self.music, t, _pan(sig * env * vel, 0))

    # ---------------------------------------------------------- 環境音
    def crickets(self, vel=0.05, t0=0.0, t1=None):
        """コオロギ風の虫の声（左右に2匹）"""
        t1 = t1 or self.duration
        for pan, f, period in ((-0.6, 4300, 0.82), (0.55, 4700, 1.07)):
            t = t0 + self.rng.uniform(0, 0.5)
            while t < t1:
                pulses = self.rng.integers(3, 5)
                dur = pulses / 28
                tt = np.arange(int(dur * SR)) / SR
                am = np.clip(np.sin(2 * np.pi * 28 * tt), 0, 1) ** 2
                sig = np.sin(2 * np.pi * f * tt) * am
                self._add(self.dry, t, _pan(sig * vel, pan))
                t += period * self.rng.uniform(0.85, 1.2)

    def wind(self, vel=0.06):
        """夜風（低いノイズがゆっくり強弱）"""
        n = self.n
        noise = self.rng.standard_normal(n)
        spec = np.fft.rfft(noise)
        freqs = np.fft.rfftfreq(n, 1 / SR)
        spec *= 1 / (1 + (freqs / 300) ** 2)
        sig = np.fft.irfft(spec, n)
        sig /= np.abs(sig).max() + 1e-9
        tt = np.arange(n) / SR
        env = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt) * np.sin(2 * np.pi * 0.031 * tt + 1)
        st = np.stack([sig * env, np.roll(sig, 2000) * env], axis=1)
        self.dry += st.astype(np.float32) * vel

    def _noise(self, n, lo, hi):
        spec = np.fft.rfft(self.rng.standard_normal(n))
        f = np.fft.rfftfreq(n, 1 / SR)
        spec *= ((f > lo) & (f < hi)).astype(float)
        sig = np.fft.irfft(spec, n)
        return sig / (np.abs(sig).max() + 1e-9)

    def rain(self, t0, t1, vel=0.08, fade=1.5):
        """雨音（ざーっ＋ぽつぽつ）。"""
        n = int((t1 - t0) * SR)
        if n <= 0:
            return
        sig = self._noise(n, 800, 9000)
        tt = np.arange(n) / SR
        env = np.minimum(1, tt / fade) * np.minimum(1, (t1 - t0 - tt) / fade)
        st = np.stack([sig, np.roll(sig, 3000)], axis=1) * env[:, None] * vel
        self._add(self.dry, t0, st.astype(np.float32))
        t = t0
        while t < t1:                                    # ぽつぽつ
            self.music_box(int(self.rng.integers(84, 96)), t, vel=0.05, decay=0.25, pan=self.rng.uniform(-0.8, 0.8))
            t += self.rng.uniform(0.08, 0.3)

    def birds(self, t0, t1, vel=0.05):
        """小鳥のさえずり（ちゅんちゅん）。"""
        t = t0 + self.rng.uniform(0, 0.4)
        while t < t1:
            pan = self.rng.uniform(-0.8, 0.8)
            for k in range(int(self.rng.integers(2, 4))):
                dur = 0.07
                tt = np.arange(int(dur * SR)) / SR
                f0 = self.rng.uniform(3200, 4200)
                f = f0 * (1 + 0.35 * np.sin(np.pi * tt / dur))
                ph = 2 * np.pi * np.cumsum(f) / SR
                sig = np.sin(ph) * np.sin(np.pi * tt / dur) ** 2
                self._add(self.dry, t + k * 0.11, _pan(sig * vel, pan))
            t += self.rng.uniform(0.9, 2.2)

    def gust(self, t, dur=2.5, vel=0.2):
        """風がびゅうっと吹く音。"""
        n = int(dur * SR)
        sig = self._noise(n, 200, 2500)
        tt = np.arange(n) / SR
        env = np.sin(np.pi * tt / dur) ** 2
        self._add(self.dry, t, _pan(sig * env * vel, 0.3))

    def boing(self, t, vel=0.25):
        """ころんだ「ぽよん」。"""
        dur = 0.35
        tt = np.arange(int(dur * SR)) / SR
        f = 300 * (1 + 0.6 * np.exp(-tt * 12) * np.sin(2 * np.pi * 14 * tt))
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = np.sin(ph) * np.exp(-tt * 7)
        self._add(self.music, t, _pan(sig * vel, 0))

    def pop(self, t, vel=0.2, note="C6"):
        """花が咲く「ぽんっ」。"""
        self.music_box(note, t, vel=vel, decay=0.5)

    def chords(self, prog, vel=0.55):
        """prog = [(開始, 終了, ["C3","E3","G3"]), ...]"""
        for t0, t1, notes in prog:
            self.pad(notes, t0, t1, vel=vel)

    def notes(self, seq, vel=0.45, decay=1.8):
        """seq = [(時刻, "E5"), ...]"""
        for t, n in seq:
            self.music_box(n, t, vel=vel, decay=decay, pan=0.15)

    # ---------------------------------------------------------- 仕上げ
    def _reverb(self, x, seconds=2.6, wet=0.35):
        n_ir = int(seconds * SR)
        tt = np.arange(n_ir) / SR
        out = np.zeros_like(x)
        size = 1
        while size < len(x) + n_ir:
            size *= 2
        for ch in range(2):
            ir = self.rng.standard_normal(n_ir) * np.exp(-tt * 6.9 / seconds)
            ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
            ir /= np.sqrt((ir ** 2).sum())
            y = np.fft.irfft(np.fft.rfft(x[:, ch], size) * np.fft.rfft(ir, size), size)[: len(x)]
            out[:, ch] = y
        return x * (1 - wet) + out * wet * 2.2

    def render(self, fade_out=2.0):
        music = self._reverb(self.music)
        mix = music + self.dry
        n = int(self.duration * SR)
        mix = mix[:n]
        if fade_out:
            k = int(fade_out * SR)
            mix[-k:] *= np.linspace(1, 0, k)[:, None] ** 1.5
        peak = np.abs(mix).max()
        if peak > 0:
            mix *= 0.89 / peak
        return mix

    def write(self, path: Path, fade_out=2.0):
        data = (np.clip(self.render(fade_out), -1, 1) * 32767).astype("<i2")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(data.tobytes())
