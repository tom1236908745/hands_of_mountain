"""台本（episodes/*.yaml）から動画一式を作る。

使い方:
  python tools/render.py episodes/001_shogyomujo.yaml            # 横動画
  python tools/render.py episodes/001_shogyomujo.yaml --format shorts
  python tools/render.py episodes/001_shogyomujo.yaml --format both
  python tools/render.py episodes/001_shogyomujo.yaml --preview  # 各シーンの静止画だけ（確認用・速い）
  python tools/render.py episodes/*.yaml                         # まとめて

出力（output/<id>_<slug>/）:
  video.mp4 / shorts.mp4 … 動画
  thumbnail.png          … サムネイル (1280x720)
  subtitles.srt          … YouTube にアップできる字幕
  metadata.txt           … タイトル・概要欄（チャプター付き）・タグ
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chiefuku  # noqa: E402
import voice  # noqa: E402
from common import ROOT, category, config, font, load_yaml, rounded_box, text_block, vertical_gradient  # noqa: E402

WHITE = (255, 255, 255)
INK = (52, 40, 34)

# ---- レイアウト（横動画 / ショート） ----------------------------------------------
LAYOUTS = {
    "landscape": dict(
        size=(1920, 1080),
        pill=(60, 36), pill_font=40,
        board=(60, 120, 1270, 790), heading_h=110,
        char_size=660, char_pos=(1250, 170),
        sub=(60, 830, 1860, 1045), sub_font=58, name_pos=(100, 798),
    ),
    "shorts": dict(
        size=(1080, 1920),
        pill=(50, 150), pill_font=42,
        board=(40, 250, 1040, 1000), heading_h=120,
        char_size=520, char_pos=(280, 960),
        sub=(40, 1440, 1040, 1700), sub_font=56, name_pos=(80, 1408),
    ),
}

SPEAKER_NAMES = {"chiefuku": None, "narration": "ナレーション"}  # None → config のキャラ名


@dataclass
class Line:
    scene_idx: int
    text: str
    say: str
    speaker: str
    expression: str
    wav: Path | None = None
    talk: float = 0.0
    total: float = 0.0
    start: float = 0.0


@dataclass
class Episode:
    path: Path
    data: dict
    lines: list[Line] = field(default_factory=list)

    @property
    def out_dir(self) -> Path:
        return ROOT / "output" / self.path.stem

    @property
    def cat(self) -> dict:
        return category(self.data.get("category", "other"))


# ---- 台本の読み込みとタイミング計算 ----------------------------------------------------
def load_episode(path: Path, use_voice: bool) -> Episode:
    data = load_yaml(path)
    for key in ("title", "category", "term", "scenes"):
        if key not in data:
            raise ValueError(f"{path}: '{key}' がありません")
    ep = Episode(path, data)
    vcfg = config()["video"]
    vdir = ep.out_dir / "voice"
    if use_voice:
        print("  VOICEVOX で音声を作成中…")
    for si, scene in enumerate(data["scenes"]):
        for ln in scene.get("lines", []):
            text = str(ln["text"])
            line = Line(si, text, str(ln.get("say", text)).replace("\n", ""), ln.get("speaker", "chiefuku"),
                        ln.get("expression", scene.get("expression", "normal")))
            if line.expression not in chiefuku.EXPRESSIONS:
                raise ValueError(f"{path}: 表情 '{line.expression}' は使えません {chiefuku.EXPRESSIONS}")
            if use_voice:
                line.wav = voice.synth(line.say, line.speaker, vdir)
            if line.wav:
                line.talk = voice.duration(line.wav)
            else:
                line.talk = max(vcfg["min_line_seconds"] - 0.4, len(line.say) * vcfg["seconds_per_char"])
            line.total = max(vcfg["min_line_seconds"], line.talk + 0.35) + vcfg["gap_seconds"]
            line.total += float(ln.get("pause", 0))
            ep.lines.append(line)
    # フレーム境界にそろえる
    fps = vcfg["fps"]
    t = 0.0
    for line in ep.lines:
        line.total = round(line.total * fps) / fps
        line.start = t
        t += line.total
    return ep


# ---- 画面の組み立て ---------------------------------------------------------------
_char_cache: dict = {}


def char_img(expr, size, talking=False, blink=False):
    key = (expr, size, talking, blink)
    if key not in _char_cache:
        _char_cache[key] = chiefuku.draw(expr, size, talking=talking, blink=blink)
    return _char_cache[key]


def _pill(img, xy, text, color, fsize):
    d = ImageDraw.Draw(img)
    f = font(fsize)
    w = f.getlength(text)
    x, y = xy
    rounded_box(img, (x, y, x + w + fsize * 1.4, y + fsize * 1.7), int(fsize * 0.85), color + (255,), shadow=False)
    d.text((x + fsize * 0.7, y + fsize * 0.3), text, font=f, fill=WHITE)
    return x + w + fsize * 1.4


def _background(ep: Episode, L) -> Image.Image:
    cat = ep.cat
    img = vertical_gradient(L["size"], cat["bg_top"], cat["bg_bottom"]).convert("RGB")
    # 青海波っぽいうっすら模様（RGB 画像に描くと半透明が正しく混ざる）
    d = ImageDraw.Draw(img, "RGBA")
    W, H = L["size"]
    r = 70
    for row, y in enumerate(range(0, H + r, r // 2)):
        off = 0 if row % 2 == 0 else r
        for x in range(-r, W + r, r * 2):
            for k in (1.0, 0.72, 0.44):
                d.arc((x + off - r * k, y - r * k, x + off + r * k, y + r * k), 180, 360,
                      fill=tuple(cat["color"]) + (22,), width=2)
    return img.convert("RGBA")


def _board(img, ep: Episode, scene: dict, L):
    cat = ep.cat
    col = tuple(cat["color"])
    x0, y0, x1, y1 = L["board"]
    d = ImageDraw.Draw(img)
    rounded_box(img, (x0, y0, x1, y1), 36, (255, 253, 247, 255), outline=col, width=6)
    stype = scene.get("type", "talk")
    term = ep.data["term"]
    reading = ep.data.get("reading", "")
    pad = 50

    if stype in ("title", "ending"):
        top = y0 + 40
        if reading:
            text_block(d, (x0 + pad, top, x1 - pad, top + 70), reading, font(46, bold=False), col)
        big = 190 if L["size"][0] > L["size"][1] else 150
        text_block(d, (x0 + pad, top + 80, x1 - pad, top + 80 + int(big * 1.6)), term, font(big), INK,
                   stroke=4, stroke_fill=WHITE)
        sub = ep.data.get("summary", "") if stype == "ending" else ep.data.get("source", "")
        if sub:
            text_block(d, (x0 + pad, y1 - 220, x1 - pad, y1 - 40), sub, font(50, bold=False), INK)
        return

    # talk / quote: 見出し帯 + 本文
    heading = scene.get("heading", "")
    body_top = y0 + 30
    if heading:
        hh = L["heading_h"]
        d.rounded_rectangle((x0 + 6, y0 + 6, x1 - 6, y0 + hh), 30, fill=col)
        d.rectangle((x0 + 6, y0 + hh - 30, x1 - 6, y0 + hh), fill=col)
        text_block(d, (x0 + pad, y0 + 10, x1 - pad, y0 + hh - 4), heading, font(58), WHITE)
        body_top = y0 + hh + 30

    note = scene.get("note", "")
    body_bottom = y1 - (110 if note else 40)
    if note:
        text_block(d, (x0 + pad, y1 - 105, x1 - pad, y1 - 30), note, font(38, bold=False), (120, 104, 92),
                   align="right")

    if scene.get("image"):
        pic = Image.open(ROOT / scene["image"]).convert("RGBA")
        pic.thumbnail((x1 - x0 - pad * 2, body_bottom - body_top))
        img.alpha_composite(pic, (int(x0 + (x1 - x0 - pic.width) / 2), int(body_top + (body_bottom - body_top - pic.height) / 2)))
        return

    board = scene.get("board")
    if board is None:   # 何も指定がなければ用語を大きく
        board = term
    if stype == "quote":
        text_block(d, (x0 + pad + 30, body_top, x1 - pad - 30, body_bottom), f"「{board}」", font(78), INK,
                   line_spacing=1.45)
    else:
        text_block(d, (x0 + pad, body_top, x1 - pad, body_bottom), board, font(92), INK,
                   line_spacing=1.35, stroke=3, stroke_fill=WHITE)


def _subtitle(img, ep: Episode, line: Line, L):
    col = tuple(ep.cat["color"])
    x0, y0, x1, y1 = L["sub"]
    rounded_box(img, (x0, y0, x1, y1), 30, (255, 255, 255, 240), outline=col, width=5)
    d = ImageDraw.Draw(img)
    text_block(d, (x0 + 50, y0 + 40, x1 - 50, y1 - 22), line.text, font(L["sub_font"]), INK,
               line_spacing=1.3)
    name = SPEAKER_NAMES.get(line.speaker) or config()["channel"]["character_name"]
    _pill(img, L["name_pos"], name, col, 36)


def compose_base(ep: Episode, scene: dict, line: Line | None, L, bg) -> Image.Image:
    img = bg.copy()
    cat = ep.cat
    nx = _pill(img, L["pill"], cat["label"], tuple(cat["color"]), L["pill_font"])
    if scene.get("type", "talk") not in ("title",):
        d = ImageDraw.Draw(img)
        d.text((nx + 24, L["pill"][1] + 8), ep.data["term"], font=font(L["pill_font"] + 6), fill=INK,
               stroke_width=3, stroke_fill=WHITE)
    _board(img, ep, scene, L)
    return img


def compose(base: Image.Image, ep: Episode, line: Line | None, L, talking=False, blink=False) -> Image.Image:
    img = base.copy()
    expr = line.expression if line else "normal"
    ch = char_img(expr, L["char_size"], talking=talking, blink=blink)
    x, y = L["char_pos"]
    img.alpha_composite(ch, (x, y - (8 if talking else 0)))
    if line:
        _subtitle(img, ep, line, L)
    return img.convert("RGB")


# ---- 出力 ---------------------------------------------------------------------
def fmt_ts(sec: float, srt=False) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    return f"{int(h)}:{int(m):02d}:{int(s):02d}" if h else f"{int(m)}:{int(s):02d}"


def write_srt(ep: Episode, out: Path):
    rows = []
    for i, ln in enumerate(ep.lines, 1):
        rows.append(f"{i}\n{fmt_ts(ln.start, True)} --> {fmt_ts(ln.start + ln.total - 0.05, True)}\n{ln.text}\n")
    out.write_text("\n".join(rows), encoding="utf-8")


def write_metadata(ep: Episode, out: Path, has_voice: bool):
    ch = config()["channel"]
    d = ep.data
    chapters, seen = [], set()
    for ln in ep.lines:
        sc = d["scenes"][ln.scene_idx]
        name = sc.get("chapter") or sc.get("heading") or {"title": "オープニング", "ending": "まとめ"}.get(sc.get("type"))
        if name and ln.scene_idx not in seen:
            seen.add(ln.scene_idx)
            chapters.append(f"{fmt_ts(ln.start)} {name}")
    if chapters:
        chapters[0] = "0:00" + chapters[0][chapters[0].index(" "):]
    # YouTube のチャプターは「3つ以上・各10秒以上」が条件
    starts = [ln.start for i, ln in enumerate(ep.lines) if i == 0 or ln.scene_idx != ep.lines[i - 1].scene_idx]
    ends = starts[1:] + [ep.lines[-1].start + ep.lines[-1].total]
    if any(e - s < 10 for s, e in zip(starts, ends)) and len(chapters) >= 3:
        print("  ⚠ 10秒未満のシーンがあるため、YouTube でチャプターが無効になる可能性があります")
    tags = list(dict.fromkeys([d["term"], d.get("reading", ""), ep.cat["label"], *d.get("tags", []),
                               ch["character_name"]]))
    desc = [d.get("description") or d.get("summary", ""), ""]
    if d.get("source"):
        desc += [f"■ 出典：{d['source']}", ""]
    if len(chapters) >= 3:
        desc += ["■ チャプター", *chapters, ""]
    if d.get("references"):
        desc += ["■ 参考", *[f"・{r}" for r in d["references"]], ""]
    desc += [ch["outro"], ""]
    if has_voice and config().get("voice", {}).get("credit"):
        desc += [config()["voice"]["credit"], ""]
    desc += [" ".join(ch["hashtags"])]
    text = (f"【タイトル】\n{d['title']}\n\n【概要欄】\n" + "\n".join(desc) +
            f"\n\n【タグ】\n{', '.join(t for t in tags if t)}\n")
    out.write_text(text, encoding="utf-8")


def make_thumbnail(ep: Episode, out: Path):
    W, H = 1280, 720
    cat = ep.cat
    col = tuple(cat["color"])
    th = ep.data.get("thumbnail", {})
    img = vertical_gradient((W, H), cat["bg_top"], cat["bg_bottom"])
    d = ImageDraw.Draw(img)
    # 放射線（集中線）
    import math
    cx, cy = 980, 380
    for i in range(36):
        a, b = math.radians(i * 10), math.radians(i * 10 + 4)
        d.polygon([(cx, cy), (cx + 1600 * math.cos(a), cy + 1600 * math.sin(a)),
                   (cx + 1600 * math.cos(b), cy + 1600 * math.sin(b))], fill=tuple(cat["bg_bottom"]))
    # 用語の帯 → その上にキャラ（顔が隠れないように）
    d.rectangle((0, 500, W, 670), fill=col)
    ch = char_img(th.get("expression", "surprised"), 620)
    img.alpha_composite(ch, (690, 70))
    text_block(d, (40, 510, 760, 660), ep.data["term"], font(130), WHITE, align="left", stroke=6,
               stroke_fill=INK)
    # キャッチコピー
    catch = th.get("catch", ep.data["title"])
    text_block(d, (40, 30, 800, 480), catch, font(104), (255, 236, 80), align="left", line_spacing=1.2,
               stroke=12, stroke_fill=INK)
    _pill(img, (W - 330, 24), cat["label"], col, 40)
    img.convert("RGB").save(out, quality=95)


def render_video(ep: Episode, fmt: str, preview: bool):
    L = LAYOUTS[fmt]
    fps = config()["video"]["fps"]
    mi = config()["video"]["mouth_interval"]
    out_dir = ep.out_dir
    work = out_dir / f"_frames_{fmt}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    bg = _background(ep, L)

    if preview:
        pdir = out_dir / f"preview_{fmt}"
        shutil.rmtree(pdir, ignore_errors=True)
        pdir.mkdir(parents=True)
        done = set()
        for ln in ep.lines:
            if ln.scene_idx in done:
                continue
            done.add(ln.scene_idx)
            sc = ep.data["scenes"][ln.scene_idx]
            compose(compose_base(ep, sc, ln, L, bg), ep, ln, L).save(pdir / f"scene{ln.scene_idx:02d}.png")
        shutil.rmtree(work)
        print(f"  プレビュー → {pdir}")
        return

    concat = []
    use_lines = [ln for ln in ep.lines if not (fmt == "shorts" and ep.data["scenes"][ln.scene_idx].get("shorts") is False)]
    base_cache = {}
    for i, ln in enumerate(use_lines):
        sc = ep.data["scenes"][ln.scene_idx]
        if ln.scene_idx not in base_cache:
            base_cache = {ln.scene_idx: compose_base(ep, sc, ln, L, bg)}
        base = base_cache[ln.scene_idx]
        f_closed = work / f"{i:04d}_c.png"
        f_open = work / f"{i:04d}_o.png"
        f_blink = work / f"{i:04d}_b.png"
        compose(base, ep, ln, L).save(f_closed, compress_level=1)
        compose(base, ep, ln, L, talking=True).save(f_open, compress_level=1)
        compose(base, ep, ln, L, blink=True).save(f_blink, compress_level=1)
        # 口パク → 口を閉じて待つ（途中で1回まばたき）
        step = max(1, round(mi * fps))
        talk_frames = round(ln.talk * fps)
        total_frames = round(ln.total * fps)
        seq, k = [], 0
        while k < talk_frames:
            n = min(step, talk_frames - k)
            seq.append((f_open if (k // step) % 2 == 0 else f_closed, n))
            k += n
        rest = total_frames - k
        if rest > 0:
            blink_at = rest // 2
            if rest > 8:
                seq += [(f_closed, blink_at), (f_blink, 4), (f_closed, rest - blink_at - 4)]
            else:
                seq.append((f_closed, rest))
        for f, n in seq:
            if n > 0:
                concat.append(f"file '{f.name}'\nduration {n / fps:.6f}")
    concat.append(f"file '{f_closed.name}'")
    (work / "frames.txt").write_text("\n".join(concat) + "\n")

    # 音声トラック
    segs = []
    for ln in use_lines:
        segs.append((ln.wav, ln.total))
    voice.concat(segs, work / "audio.wav")

    out = out_dir / ("video.mp4" if fmt == "landscape" else "shorts.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "frames.txt"),
           "-i", str(work / "audio.wav")]
    bgm = config().get("bgm", {}) or {}
    if bgm.get("file"):
        cmd += ["-stream_loop", "-1", "-i", str(ROOT / "assets" / "bgm" / bgm["file"]),
                "-filter_complex", f"[2:a]volume={bgm.get('volume', 0.12)}[b];[1:a][b]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    shutil.rmtree(work)
    total = sum(l.total for l in use_lines)
    print(f"  動画 → {out}  ({fmt_ts(total)})")
    if fmt == "shorts" and total > 180:
        print("  ⚠ ショートは3分以内にしてください（scenes に shorts: false を付けて削れます）")


def main():
    ap = argparse.ArgumentParser(description="台本YAMLから動画を作る")
    ap.add_argument("episodes", nargs="+", type=Path)
    ap.add_argument("--format", choices=["landscape", "shorts", "both"], default="landscape")
    ap.add_argument("--preview", action="store_true", help="シーンごとの静止画だけ出す")
    ap.add_argument("--no-voice", action="store_true", help="VOICEVOXを使わない（無音）")
    args = ap.parse_args()

    use_voice = not args.no_voice and not args.preview and voice.available()
    if not args.no_voice and not args.preview and not use_voice:
        print("※ VOICEVOX エンジンに接続できないため、音声なしで作ります（字幕のみ）")

    for path in args.episodes:
        print(f"▶ {path}")
        ep = load_episode(path, use_voice)
        ep.out_dir.mkdir(parents=True, exist_ok=True)
        fmts = ["landscape", "shorts"] if args.format == "both" else [args.format]
        for fmt in fmts:
            render_video(ep, fmt, args.preview)
        if not args.preview:
            write_srt(ep, ep.out_dir / "subtitles.srt")
            write_metadata(ep, ep.out_dir / "metadata.txt", use_voice)
        make_thumbnail(ep, ep.out_dir / "thumbnail.png")
        print(f"  サムネ・字幕・概要欄 → {ep.out_dir}")


if __name__ == "__main__":
    main()
