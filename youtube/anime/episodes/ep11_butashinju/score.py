"""ep11『豚に真珠』の効果音・環境音（曲は meta.yaml の music: から）。"""
from audio import Mix

DURATION = 38.5


def build() -> Mix:
    m = Mix(DURATION, seed=11)
    m.birds(0, 37.5, vel=0.035)
    m.wind(vel=0.02)
    m.shimmer(4.8, dur=1.2, vel=0.1)                              # 真珠きらり
    m.notes([(5.0, "E6"), (5.15, "G6"), (5.3, "C7")], vel=0.2, decay=0.8)
    m.pop(9.0, vel=0.15, note="G5")                                # とりかえっこ
    m.pop(9.5, vel=0.15, note="C6")
    for i in range(9):                                             # ころころ
        m.pop(13.6 + i * 0.5, vel=0.08, note=["C6", "E6", "D6", "G6"][i % 4])
    m.notes([(19.8, "G4"), (20.6, "E4"), (21.4, "C4")], vel=0.25, decay=1.6)   # ねむくなる
    m.boing(22.7, vel=0.18)                                        # はっ
    m.pop(25.2, vel=0.15, note="C6")                               # もどす
    m.pop(25.7, vel=0.15, note="G5")
    return m
