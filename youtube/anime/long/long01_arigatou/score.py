"""長編01『ありがとう』の効果音・環境音（曲は meta.yaml の music: で、場面ごとに切りかえ）。"""
import numpy as np

import sys
from pathlib import Path

import audio
from audio import Mix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pace  # noqa: E402

DURATION = pace.OUT_END
T = pace.to_out          # お話の時刻 → 動画の時刻
SR = audio.SR


def _band(m, t0, t1, lo, hi, vel, period=6.0, fade=2.0):
    """帯域をしぼったノイズを、ゆっくり強弱をつけて流す（波・水の中の音）。"""
    n = int((t1 - t0) * SR)
    sig = m._noise(n, lo, hi)
    tt = np.arange(n) / SR
    env = (0.6 + 0.4 * np.sin(2 * np.pi * tt / period)) * np.minimum(1, tt / fade) * np.minimum(1, (t1 - t0 - tt) / fade)
    st = np.stack([sig * env, np.roll(sig, 1500) * env], axis=1) * vel
    m._add(m.dry, t0, st.astype(np.float32))


def _bubble(m, t, vel=0.05, pan=0.0):
    """ぽこっ（泡）。"""
    dur = 0.08
    tt = np.arange(int(dur * SR)) / SR
    f = 500 + 1400 * tt / dur
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / dur)
    m._add(m.dry, t, audio._pan(sig * vel, pan))


def _thunder(m, t, vel=0.35):
    n = int(2.6 * SR)
    sig = m._noise(n, 30, 400)
    tt = np.arange(n) / SR
    env = np.exp(-tt * 1.6) * (1 - np.exp(-tt * 30)) * (1 + 0.5 * np.sin(2 * np.pi * 3 * tt))
    m._add(m.dry, t, audio._pan(sig * env * vel, 0))


def _splash(m, t, vel=0.18):
    n = int(0.7 * SR)
    sig = m._noise(n, 800, 7000)
    tt = np.arange(n) / SR
    m._add(m.dry, t, audio._pan(sig * np.exp(-tt * 7) * vel, 0))


def _swish(m, t, vel=0.08):
    """ページをめくる音。"""
    n = int(0.45 * SR)
    sig = m._noise(n, 1500, 7000)
    tt = np.arange(n) / SR
    m._add(m.dry, t, audio._pan(sig * np.sin(np.pi * tt / 0.45) ** 2 * vel, 0.2))


def _chimes(m, t0, notes, step=0.12, vel=0.18, decay=1.6):
    for i, n in enumerate(notes):
        m._bell(n, t0 + i * step, vel=vel, decay=decay, pan=-0.4 + 0.8 * i / max(1, len(notes) - 1))


def build() -> Mix:
    m = Mix(DURATION, seed=101)
    rng = np.random.default_rng(5)
    # ---- 野原（朝）
    m.birds(T(0.5), T(22), vel=0.035)
    m.wind(vel=0.015)
    m.pop(T(7.4), vel=0.14, note="E6")                       # クッキー
    _chimes(m, T(7.6), ["C6", "E6", "G6"], vel=0.1)
    m.shimmer(T(16.8), dur=5.0, vel=0.12)                    # ことば帖が光る
    _chimes(m, T(20.6), ["C6", "E6", "G6", "C7", "E7"], step=0.1, vel=0.12)
    # ---- ページ
    _swish(m, T(23.6))
    for t in (24.8, 28.8, 37.4):
        m._bell("G6", T(t), vel=0.08, decay=1.2)
    _swish(m, T(48.8))
    # ---- 海の底
    _band(m, T(50.0), T(112.5), 60, 500, 0.06, period=9.0)
    for t in rng.uniform(52, 111, 40):
        _bubble(m, T(float(t)), vel=0.035, pan=float(rng.uniform(-0.7, 0.7)))
    for t, n in ((86.0, "E6"), (91.0, "G6"), (96.0, "D6"), (101.0, "C6")):   # 季節のはじまり
        m._bell(n, T(t), vel=0.1, decay=2.0)
    m.shimmer(T(104.8), dur=4.0, vel=0.1)                    # 百年が過ぎていく
    # ---- 海の上
    _band(m, T(111.5), T(160.5), 200, 1600, 0.06, period=5.5)   # 波
    m.gust(T(127.8), dur=4.0, vel=0.18)                      # 風
    m.rain(T(138.0), T(151.0), vel=0.06)
    _band(m, T(138.0), T(151.0), 80, 900, 0.08, period=2.5)     # 荒れた海
    _thunder(m, T(141.6))
    _thunder(m, T(146.1), vel=0.28)
    # ---- 水の中 → 出会い
    _band(m, T(159.5), T(176.5), 60, 600, 0.05, period=7.0)
    for t in np.arange(161.0, 176.0, 0.55):
        _bubble(m, T(float(t)), vel=0.04, pan=0.3)
    _band(m, T(176.0), T(198.5), 200, 1400, 0.04, period=5.5)
    _splash(m, T(183.6))
    _chimes(m, T(183.9), ["C6", "E6", "G6", "C7", "E7", "G7"], step=0.11, vel=0.13, decay=2.2)
    # ---- 夜の海
    _band(m, T(197.5), T(230.5), 150, 1000, 0.03, period=7.0)
    for t, n in ((200.4, "E5"), (202.6, "G5"), (204.8, "C6")):
        m._bell(n, T(t), vel=0.1, decay=3.0)
    # ---- 野原へ
    m.shimmer(T(229.0), dur=2.4, vel=0.1)
    m.birds(T(231.0), T(308.0), vel=0.035)
    for t in (267.2, 275.0, 278.4):                       # ありがとう
        m.pop(T(t), vel=0.12, note="G6")
    for t in (268.0, 279.0, 286.0):                       # ハート
        _chimes(m, T(t), ["E6", "G6", "C7"], vel=0.08)
    # ---- エンディング
    _swish(m, T(292.4))
    m._bell("C6", T(293.8), vel=0.12, decay=2.6)
    m._bell("G6", T(296.0), vel=0.1, decay=2.6)
    _chimes(m, T(299.2), ["C6", "E6", "G6", "C7"], step=0.14, vel=0.1, decay=2.4)
    return m
