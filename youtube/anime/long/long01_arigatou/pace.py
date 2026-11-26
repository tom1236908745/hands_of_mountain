"""テンポ調整：お話の時間（story 時間）を、場面ごとの速さで 動画の時間（out 時間）に つめる。

ゆっくりすぎる所は速く、動きのある所はあまり変えない。絵・字幕・効果音・曲の切りかえは
すべて story 時間で書いてあるので、ここで変換するだけで全体のテンポが変わる。
"""
from __future__ import annotations

# (story 時間の区切り, その区間の速さ)
SPEEDS = [
    (0.0, 1.25),     # 朝の野原
    (23.0, 1.45),    # ことば帖のページ
    (50.5, 1.6),     # 海の底
    (85.0, 1.5),     # めぐる季節
    (112.0, 1.55),   # 海の上
    (160.0, 1.3),    # 水の中 → 出会い
    (198.0, 1.4),    # 夜：法句経
    (230.0, 1.5),    # 野原へ
    (264.0, 1.3),    # ありがとう
    (292.0, 1.15),   # エンディング
]
STORY_END = 310.0


def _segments():
    out = []
    o = 0.0
    for i, (s0, sp) in enumerate(SPEEDS):
        s1 = SPEEDS[i + 1][0] if i + 1 < len(SPEEDS) else STORY_END
        out.append((s0, s1, o, sp))
        o += (s1 - s0) / sp
    return out, o


SEGS, OUT_END = _segments()


def to_story(t_out: float) -> float:
    for s0, s1, o0, sp in SEGS:
        if t_out <= o0 + (s1 - s0) / sp:
            return s0 + (t_out - o0) * sp
    return STORY_END


def to_out(t_story: float) -> float:
    for s0, s1, o0, sp in SEGS:
        if t_story <= s1:
            return o0 + (t_story - s0) / sp
    return OUT_END


def fmt(t_story: float) -> str:
    t = int(round(to_out(t_story)))
    return f"{t // 60}:{t % 60:02d}"
