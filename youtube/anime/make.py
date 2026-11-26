"""ショートアニメを書き出す。

  python anime/make.py ep01_ichigu                      # 動画（音つき）＋カバー画像＋投稿文
  python anime/make.py ep01_ichigu --stills 2,8.6,21    # 指定秒の静止画を並べた確認シート（速い）
  python anime/make.py ep01_ichigu --range 6,13         # 一部分だけ動画にする（確認用）
  python anime/make.py ep01_ichigu --audio-only         # 音だけ

エピソードのフォルダ（anime/episodes/<名前>/）に必要なもの:
  spec.md   … 制作仕様（人が読む設計書）
  story.py  … 絵とタイムライン（FPS, SIZE, DURATION, CAPTIONS, render(t)）
  score.py  … 音楽・効果音（build() → Mix）
  meta.yaml … 投稿用のタイトル・説明文・ハッシュタグ・カバー画像の秒数
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "cast")]

import yaml  # noqa: E402
from PIL import Image, ImageFont  # noqa: E402

import engine  # noqa: E402

OUT_ROOT = HERE.parent / "output" / "anime"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_glyphs(story):
    """字幕にフォントにない文字（□になる）がないか確認する。"""
    bad = []
    for c in getattr(story, "CAPTIONS", []):
        f = ImageFont.truetype(str(engine.FONT_DIR / c.font), 40)
        tofu = f.getmask("\U0010FFFF").getbbox()
        for ch in set(c.text) - {" ", "\n", "　"}:
            if f.getmask(ch).getbbox() == tofu:
                bad.append((ch, c.text.replace("\n", " ")))
    for ch, text in bad:
        print(f"  ⚠ フォントにない文字「{ch}」: {text}")
    return not bad


def contact_sheet(story, times, out: Path, w=360, story_path=None):
    ims = []
    for t in times:
        t0 = time.time()
        ims.append(engine.render_frame(story, story_path, t) if story_path else story.render(t))
        print(f"  {t:5.1f}s  ({time.time() - t0:.2f}s/frame)")
    W, H = story.SIZE
    h = int(w * H / W)
    sheet = Image.new("RGB", (w * len(ims), h + 40), (20, 20, 24))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(zip(times, ims)):
        sheet.paste(im.resize((w, h)), (i * w, 40))
        d.text((i * w + 10, 8), f"{t:.1f}s", font=engine.font(engine.GOTHIC, 24), fill=(230, 230, 230))
    sheet.save(out)
    return ims


def write_meta(ep_dir: Path, out_dir: Path):
    p = ep_dir / "meta.yaml"
    if not p.exists():
        return
    m = yaml.safe_load(p.read_text(encoding="utf-8"))
    lines = [f"【タイトル】\n{m['title']}\n", "【説明文】", m.get("description", "").strip(), ""]
    if m.get("source"):
        lines += [f"出典：{m['source']}", ""]
    lines += [" ".join(m.get("hashtags", []))]
    (out_dir / "post.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--stills", help="カンマ区切りの秒数")
    ap.add_argument("--range", help="開始,終了（秒）")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--remux", action="store_true", help="映像は作り直さず、音だけ作り直して video.mp4 に入れ替える")
    ap.add_argument("--workers", type=int)
    ap.add_argument("--sound", help="音色スタイル（musicbox/piano/marimba/guitar/koto/lofi/chiptune）。"
                                     "省略時は meta.yaml の sound:、それもなければ musicbox")
    args = ap.parse_args()

    ep_dir = HERE / "episodes" / args.episode
    if not ep_dir.exists():
        sys.exit(f"エピソードがありません: {ep_dir}")
    out_dir = OUT_ROOT / args.episode
    out_dir.mkdir(parents=True, exist_ok=True)
    story_path = ep_dir / "story.py"
    story = load(story_path, "story")
    check_glyphs(story)

    if args.stills:
        times = [float(x) for x in args.stills.split(",")]
        out = out_dir / "stills.png"
        contact_sheet(story, times, out, story_path=story_path)
        print(f"確認シート → {out}")
        return

    audio = out_dir / "audio.wav"
    score_path = ep_dir / "score.py"
    import audio as audio_mod
    meta = {}
    if (ep_dir / "meta.yaml").exists():
        meta = yaml.safe_load((ep_dir / "meta.yaml").read_text(encoding="utf-8")) or {}
    music_key = meta.get("music")
    audio_mod.STYLE = args.sound or meta.get("sound") or ("marimba" if music_key else "musicbox")
    if score_path.exists():
        if music_key:
            # 曲は曲集（tunes.py）から、効果音・環境音はその回の score.py から
            import numpy as np
            import tunes
            print(f"♪ 曲：{tunes.KEYS[music_key][0]}（{audio_mod.STYLES[audio_mod.STYLE]['label']}）＋ この回の効果音")
            audio_mod.MUSIC_ON = False
            sfx_mix = load(score_path, "score").build()
            audio_mod.MUSIC_ON = True
            sfx = sfx_mix.render(fade_out=2.0, normalize=False)
            bgm = tunes.render_tune(music_key, sfx_mix.duration, style=audio_mod.STYLE)
            n = min(len(sfx), len(bgm))
            mix = bgm[:n] * float(meta.get("music_gain", 0.8)) + sfx[:n]
            mix *= 0.89 / (np.abs(mix).max() + 1e-9)
            import wave
            with wave.open(str(audio), "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(audio_mod.SR)
                w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
        else:
            print(f"♪ 音楽を合成中…（音色：{audio_mod.STYLES[audio_mod.STYLE]['label']}）")
            load(score_path, "score").build().write(audio)
        print(f"  → {audio}")
    else:
        audio = None
    if args.audio_only:
        return
    if args.remux:
        import subprocess
        src = out_dir / "video.mp4"
        tmp = out_dir / "video_remux.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-i", str(audio), "-map", "0:v",
                        "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", str(tmp)], check=True)
        tmp.replace(src)
        print(f"音を入れ替えました → {src}")
        return

    t_range = tuple(float(x) for x in args.range.split(",")) if args.range else None
    out = out_dir / ("preview.mp4" if t_range else "video.mp4")
    print(f"🎞 {story.DURATION}s × {story.FPS}fps を描画中…")
    t0 = time.time()
    engine.render_video(story_path, story, out, audio, workers=args.workers, t_range=t_range)
    print(f"動画 → {out}  ({time.time() - t0:.0f}秒かかりました)")

    if not t_range:
        meta = yaml.safe_load((ep_dir / "meta.yaml").read_text(encoding="utf-8")) if (ep_dir / "meta.yaml").exists() else {}
        cover_t = float(meta.get("cover_time", story.DURATION / 2))
        engine.render_frame(story, story_path, cover_t).save(out_dir / "cover.png")
        write_meta(ep_dir, out_dir)
        print(f"カバー画像・投稿文 → {out_dir}")


if __name__ == "__main__":
    main()
