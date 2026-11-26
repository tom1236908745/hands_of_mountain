"""ことにゃんアニメ共通の道具（ep04〜）。

  hop_path    … ぴょんぴょん移動（ため・空中・着地のぺたん）
  ending      … 結びの「ことば」を明朝で大きく＋出典＋余韻の字幕セット
  PALETTES    … 色違いのねこ（子ねこ・母ねこ・くろ）
"""
from __future__ import annotations

import math

from engine import MINCHO, Caption, ease_out, lerp

KURO = dict(fur=(78, 72, 80), patch_a=(62, 58, 66), patch_b=(46, 42, 50), eye=(250, 214, 110),
            line=(40, 34, 38), ear_in=(196, 150, 150), cheek=(230, 140, 140))


def hop_path(t, start, hops, dur=0.5, height=46):
    """hops = [(開始時刻, (x, 足の高さy)), ...]。戻り値 (x, y, squash)。"""
    x, g = start
    for t0, (nx, ng) in hops:
        if t < t0 - 0.12:
            return x, g, 1.0
        if t < t0:
            return x, g, lerp(1.0, 0.86, (t - (t0 - 0.12)) / 0.12)
        if t < t0 + dur:
            u = (t - t0) / dur
            y = lerp(g, ng, u) - height * math.sin(math.pi * u)
            return lerp(x, nx, ease_out(u) * 0.3 + u * 0.7), y, 1.08 - 0.08 * abs(u - 0.5) * 2
        if t < t0 + dur + 0.14:
            return nx, ng, lerp(0.86, 1.0, (t - t0 - dur) / 0.14)
        x, g = nx, ng
    return x, g, 1.0


def walk(t, t0, t1, x0, x1, ground_fn, bounce=8, steps_per_sec=4):
    """とことこ歩く（小さく上下）。"""
    if t <= t0:
        return x0, ground_fn(x0), 1.0
    if t >= t1:
        return x1, ground_fn(x1), 1.0
    u = (t - t0) / (t1 - t0)
    x = lerp(x0, x1, u)
    ph = (t - t0) * steps_per_sec * math.pi
    return x, ground_fn(x) - abs(math.sin(ph)) * bounce, 1.0 - 0.03 * abs(math.cos(ph))


def ending(t0, word, source, after, reading=None, after_t=None, end=37.6):
    """結びの字幕セット：ことば（明朝・大）→ 出典 → 余韻の3行。"""
    after_t = after_t or t0 + 4.4
    caps = [Caption(t0, after_t - 0.4, word, size=96 if len(word.replace("\n", "")) <= 8 else 84, font=MINCHO,
                    line_gap=1.35, fade_in=1.0, fade_out=0.8, y=0.3)]
    y_src = 0.41 if "\n" in word else 0.37
    if reading:
        caps.append(Caption(t0 + 0.6, after_t - 0.4, reading, size=36, font=MINCHO, y=y_src, fade_in=0.9,
                            fade_out=0.8))
        y_src += 0.035
    caps.append(Caption(t0 + 0.9, after_t - 0.4, source, size=38, font=MINCHO, y=y_src, fade_in=0.9, fade_out=0.8))
    for i, line in enumerate(after):
        caps.append(Caption(after_t + i * 1.0, end, line, size=50, y=0.27 + i * 0.06, fade_out=0.9))
    last = after_t + (len(after) - 1) * 1.0
    if after and end - last < 1.5:
        raise ValueError(f"結びの最後の行「{after[-1]}」が {end - last:.1f} 秒しか表示されません。"
                         f"after_t を {end - 1.5 - (len(after) - 1):.1f} 以下にしてください")
    return caps


def speech_bubble(img, cam_xyz, size, wx, wy, text, alpha=1.0, fsize=40, dx=0.0):
    """完成した画像に吹き出しを描く。wx, wy = 話している口のあたり（ワールド座標）。
    dx（ワールド座標）だけ横にずらして置き、しっぽは話し手を向く（字幕と重ならないように）。"""
    from PIL import Image, ImageDraw
    from engine import GOTHIC, font
    if alpha <= 0.01:
        return img
    cx, cy, z = cam_xyz
    W, H = size
    ax, ay = (wx - cx) * z + W / 2, (wy - cy) * z + H / 2          # しっぽの先
    sx, sy = ax + dx * z, ay - fsize * 1.2                           # 吹き出しの中心
    f = font(GOTHIC, fsize)
    tw = f.getlength(text)
    pad = fsize * 0.55
    half = tw / 2 + pad
    sx = min(max(sx, half + 24), W - half - 24)                     # 画面からはみ出さない
    box = (sx - half, sy - fsize / 2 - pad, sx + half, sy + fsize / 2 + pad)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    line_c, fill_c = (104, 82, 74, 255), (255, 255, 255, 240)
    # しっぽ：話し手の側の下のふちから、話し手のほうへ 短く ずんぐり
    bx = min(max(ax, box[0] + fsize * 0.9), box[2] - fsize * 0.9)
    vx, vy = ax - bx, max(ay - box[3], fsize * 0.9)
    ln = math.hypot(vx, vy)
    L = fsize * 0.95
    tip = (bx + vx / ln * L, box[3] + vy / ln * L)
    hw = fsize * 0.34
    d.rounded_rectangle((box[0], box[1] + 6, box[2], box[3] + 6), radius=fsize * 0.6, fill=(0, 0, 0, 50))
    d.rounded_rectangle(box, radius=fsize * 0.6, fill=fill_c, outline=line_c, width=4)
    # 枠の上から しっぽを重ね、側面だけ線を引く（付け根に すき間や線が出ない）
    base_l, base_r = (bx - hw, box[3] - 5), (bx + hw, box[3] - 5)
    d.polygon([base_l, base_r, tip], fill=fill_c)
    side_l = (bx - hw, box[3] - 1)
    side_r = (bx + hw, box[3] - 1)
    d.line([side_l, tip, side_r], fill=line_c, width=4, joint="curve")
    d.text((sx - tw / 2, sy - fsize * 0.62), text, font=f, fill=(84, 62, 54, 255))
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    out = img.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")
