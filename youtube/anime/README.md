# ショートアニメ制作キット

仏教・聖書・故事成語の「ことば」を、**セリフなしの縦型ショートアニメ**（38秒前後）にする仕組みです。
絵・カメラ・光・字幕・音楽まで、すべて Python（Pillow + numpy）と ffmpeg だけで作ります。
画像素材・音源・有料ソフトは不要で、BGMも自動作曲なので著作権の心配がありません。

```
spec.md（制作仕様）  →  story.py（絵とタイムライン）＋ score.py（音楽）  →  make.py  →  video.mp4
```

## 使い方

```bash
cd youtube
pip install -r requirements.txt
./tools/setup_fonts.sh                                  # 丸ゴシック＋明朝（どちらも商用OK）

python anime/make.py ep01_ichigu --stills 2,9,15,21,27,31   # 静止画で確認（数秒）
python anime/make.py ep01_ichigu --range 19,25              # 一部分だけ動画で確認
python anime/make.py ep01_ichigu                            # 本番（4コアで約3分）
```

出力（`output/anime/ep01_ichigu/`）:
`video.mp4`（1080×1920・30fps・H.264+AAC）/ `cover.png`（カバー画像）/ `post.txt`（タイトル・説明文・ハッシュタグ）/ `audio.wav`

## 新しいエピソードの作り方

1. `SPEC_TEMPLATE.md` をコピーして `episodes/epNN_<slug>/spec.md` を書く（ep01 の spec.md が見本）
2. ep01 の `story.py` `score.py` `meta.yaml` をコピーして書き換える
3. `--stills` で確認しながら調整 → 本番書き出し

**Claude Code なら「この仕様書でアニメにして」と spec を渡すだけで 1〜3 をやります**（`.claude/skills/short-anime`）。

## しくみ

| ファイル | 役割 |
|---|---|
| `engine.py` | カメラ（寄り・引き・視差）、ベクター描画、ライティング（月明かり・光源）、ブルーム、字幕、並列書き出し |
| `audio.py` | オルゴール・パッド・アルペジオ・リバーブ・虫の声・夜風・効果音の合成 |
| `scenery.py` | 月夜の森（空・月・星・3層の木・草・葉・つる草） |
| `cast/firefly.py` | ホタル（表情：open/squeeze/closed/wide/happy/sad、光る量、はばたき） |
| `cast/snail.py` | カタツムリ親子（sad/normal/happy/content、目の柄の垂れ、涙）とハート |
| `cast/neko.py` | マスコット「ことにゃん」（tools/mascot.py）をアニメに出す。ちょうちん・ぴょんジャンプ・色違いの子ねこ/母ねこ |
| `make.py` | 書き出し・確認シート・字幕のフォント欠け検査 |

### 絵の3つの層
- **base**：ふつうの絵。月明かり（環境光）で暗くなり、`Light` の近くだけ明るくなる
- **emit**：自分で光るもの（月・ホタルの光）。ぼかしてブルーム（光のにじみ）を足す
- **字幕**：ライティングの影響を受けない

### story.py でよく使う道具
```python
CAM = Track([(0, (540, 960, 1.0)), (8.4, (300, 1390, 3.6))])   # 時刻 → (中心x, 中心y, ズーム)
seg(t, 16.4, 17.6)        # 16.4〜17.6秒で 0→1（イーズ付き）
pulse(t, 8.7, 8.9, 0.05)  # その間だけ 1（チカッと光る）
Caption(0.5, 3.3, "字幕")  # 上から1/3・フェード＋浮き上がり
fr.lights.append(Light(x, y, 半径, 強さ))
```

## エピソード一覧

| ep | タイトル | 出典 | 長さ |
|---|---|---|---|
| 01 | 一隅を照らす（ホタル版） | 最澄『山家学生式』 | 38秒 |
| 02 | 一隅を照らす（ことにゃん・ちょうちん版） | 最澄『山家学生式』 | 38秒 |
| 03 | 一隅を照らす（ほたるにゃん版：ほたるの着ぐるみのことにゃん） | 最澄『山家学生式』 | 38秒 |
