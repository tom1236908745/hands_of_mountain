"""ep08『挨拶』— ep07 の映像（にっこりが となりへ伝わる朝）を使い、「おはよう」の連鎖にした回。

絵と動きは ep07_wagenaigo/story.py をそのまま読みこみ、字幕と吹き出しだけを差し替える。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIME = HERE.parent.parent
sys.path[:0] = [str(ANIME), str(ANIME / "cast")]

import kit  # noqa: E402
from engine import Caption, pulse  # noqa: E402

_spec = importlib.util.spec_from_file_location("ep07_story", HERE.parent / "ep07_wagenaigo" / "story.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

FPS, SIZE, DURATION = base.FPS, base.SIZE, base.DURATION

CAPTIONS = [
    Caption(0.5, 4.0, "なんだか みんな、むすっとして見える朝。"),
    Caption(5.4, 8.6, "ことにゃんは「おはよう」と 声をかけた。"),
    Caption(9.2, 12.2, "返ってきた「おはよう」は、\n思ったより 元気だった。"),
    Caption(12.6, 16.6, "ひとこと 交わすたびに、"),
    Caption(17.6, 20.2, "むすっとして見えた 黒ねこの、"),
    Caption(20.4, 22.4, "ほんとうの顔が 見えた。"),
    Caption(22.8, 26.4, "ことばを交わすと、\n心が すこし 見えてくる。"),
] + kit.ending(26.8, "挨拶", "―― 禅のことば「一挨一拶」より", reading="あいさつ",
               after=["もとは 禅のことば。", "ことばを交わして、", "相手の心を たしかめ合うこと。"],
               after_t=31.2, end=35.1)
base.CAPTIONS = CAPTIONS          # ep07 の render() が使う字幕を差し替える

# 吹き出し：(表示する時間, だれの上か, ことば)
BUBBLES = [   # (時間, 話し手, 大きさ, ことば, 横のずらし（大きさに対する割合）)
    ((6.2, 8.2), lambda t: base.cat_state(t), base.CAT_S, "おはよう", 0.55),
    ((9.1, 11.0), lambda t: base.kitten_state(t), base.KIT_S, "おはよう！", 0.9),
    ((14.2, 16.2), lambda t: base.mom_state(t), base.MOM_S, "おはよう", 0.75),
    ((20.7, 22.6), lambda t: base.kuro_state(t), base.KURO_S, "…おはよう", -0.75),
]


def render(t):
    img = base.render(t)
    cam = base.CAM(t)
    for (t0, t1), st_fn, size, text, side in BUBBLES:
        if t0 <= t <= t1:
            st = st_fn(t)
            a = pulse(t, t0, t1, 0.25)
            img = kit.speech_bubble(img, cam, SIZE, st["x"] + side * size * 0.25, st["g"] - size * 0.45, text,
                                    alpha=a, fsize=int(34 + 6 * min(1, cam[2] / 2)), dx=side * size * 0.6)
    return img
