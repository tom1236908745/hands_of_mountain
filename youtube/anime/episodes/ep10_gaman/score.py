"""ep10『我慢』の効果音・環境音（曲は meta.yaml の music: から）。"""
from audio import Mix

DURATION = 37.5


def build() -> Mix:
    m = Mix(DURATION, seed=10)
    m.birds(0, 36.5, vel=0.035)
    m.wind(vel=0.02)
    for t in (9.4, 10.0, 10.6, 11.2, 11.8, 12.4, 13.0, 13.6):     # よろよろ歩き
        m.pop(t, vel=0.06, note="G4")
    m.boing(14.05)                                                 # つまずく
    for i in range(6):                                             # 本が落ちる「ばさっ」
        m.pop(14.7 + i * 0.05, vel=0.12, note=["C4", "E4", "D4", "G4", "F4", "A4"][i])
    for i in range(6):                                             # 拾う
        m.pop(21.4 + i * 0.22, vel=0.1, note=["C6", "D6", "E6", "G6", "A6", "C7"][i])
    m.shimmer(25.8, dur=1.4, vel=0.08)                             # かるくなった
    return m
