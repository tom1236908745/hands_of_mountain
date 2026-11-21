"""ep06『雨垂れ石を穿つ』の音楽：のびのび → 失敗（ぽよん）→ しずくの音 → 毎日のリズム（だんだん上へ）→ とどいた！"""
from audio import Mix

DURATION = 37.0


def build() -> Mix:
    m = Mix(DURATION, seed=6)
    m.birds(0, 15, vel=0.035)
    m.birds(24, 36, vel=0.035)
    m.wind(vel=0.025)
    m.chords([(0, 4.3, ["C3", "G3", "E4"]), (4.3, 10, ["A2", "E3", "C4"]), (10, 15.4, ["F3", "C4", "A4"]),
              (15.4, 19.7, ["C3", "G3", "E4"]), (19.7, 24.0, ["D3", "A3", "F4"]), (24.0, 25.1, ["G3", "D4", "B4"]),
              (25.1, 27.9, ["C3", "G3", "C4", "E4", "D5"]), (27.9, 32.3, ["F3", "A3", "C4", "E4"]),
              (32.3, 36.5, ["C3", "G3", "C4", "E4"])], vel=0.5)
    m.melody([("C5", 1), ("E5", 1), ("G5", 2), ("A5", 1), ("G5", 3)], 0.4, 0.4, vel=0.45)
    for t in (4.6, 7.2):                                   # ぴょん → とどかない
        m.arpeggio(["C5", "E5", "G5"], t, 0.08, vel=0.3, decay=0.6)
        m.boing(t + 0.6)
    t = 10.4                                               # しずく ぽたり
    while t < 15.4:
        m.music_box("E6", t, vel=0.25, decay=0.5)
        t += 0.9
    for i in range(4):                                     # 毎日：すこしずつ高く
        t0 = 15.4 + i * 2.15
        base = ["C5", "D5", "E5", "G5"][i]
        m.music_box(base, t0 + 0.55, vel=0.4, decay=1.2)
        m.music_box(["E5", "F5", "G5", "B5"][i], t0 + 0.8, vel=0.35, decay=1.2)
        m.music_box("C6", t0 + 0.2, vel=0.12, decay=0.4)
    m.arpeggio(["G4", "C5", "E5", "G5", "C6", "E6", "G6"], 24.4, 0.08, vel=0.45, decay=1.6)   # とどいた！
    m.shimmer(24.9, dur=1.6, vel=0.12)
    m.melody([("E5", 1), ("G5", 1), ("A5", 2), ("G5", 1), ("E5", 1), ("D5", 1), ("C5", 3)], 28.1, 0.48, vel=0.45,
             decay=2.2)
    for t, n in ((32.5, "G5"), (33.5, "E5"), (34.5, "D5"), (35.5, "C5")):
        m.music_box(n, t, vel=0.35, decay=2.4)
    return m
