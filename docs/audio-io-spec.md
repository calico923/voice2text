# 音声I/O仕様書（T02）

## 1. 目的
- 録音処理とRealtime送信処理の前提値を固定し、実装差異をなくす。
- T09/T10 実装で使う定数を先に決める。

## 2. 固定する音声フォーマット
- エンコーディング: `PCM16`（signed 16-bit little-endian）
- サンプルレート: `16000 Hz`
- チャンネル数: `1`（mono）

## 3. フレーム長とサンプル数

### 3.1 計算式
- `samples_per_frame = sample_rate * frame_ms / 1000`
- `bytes_per_sample = 2`（PCM16）
- `bytes_per_frame = samples_per_frame * bytes_per_sample`

### 3.2 20ms
- `samples_per_frame = 16000 * 20 / 1000 = 320`
- `bytes_per_frame = 320 * 2 = 640 bytes`

### 3.3 40ms
- `samples_per_frame = 16000 * 40 / 1000 = 640`
- `bytes_per_frame = 640 * 2 = 1280 bytes`

## 4. 初期値（MVP）
- `AUDIO_CHUNK_MS=20`
- `SEND_INTERVAL_MS=20`
- `SEND_QUEUE_MAX_FRAMES=200`
- `SEND_QUEUE_POLICY=block_with_warning`

## 5. 値選定の理由
- `20ms`:
  - 体感遅延を抑えやすく、逐次認識の更新密度が高い。
- `40ms`:
  - 帯域とイベント数を抑えたい場合の代替値。
- `queue=200`:
  - 20ms運用で約4秒ぶんの吸収バッファ。
  - 一時的なネットワーク揺れを吸収しつつ、無制限成長を防ぐ。
- `block_with_warning`:
  - フレーム破棄による認識欠落より、送信遅延の可視化を優先する。

## 6. 実装ルール
- `AUDIO_CHUNK_MS` は `20` または `40` のみ許可する。
- 送信前に必ず `PCM16/16kHz/mono` へ変換完了させる。
- 送信イベントは1フレーム=1 `input_audio_buffer.append` を基本とする。
- 区切り確定は `input_audio_buffer.commit` を送る。

## 7. 設定キー定義

| Key | Type | Default | Allowed | 用途 |
|---|---|---|---|---|
| `AUDIO_CHUNK_MS` | int | `20` | `20`, `40` | フレーム長 |
| `SEND_INTERVAL_MS` | int | `20` | `>=10` | append送信間隔 |
| `SEND_QUEUE_MAX_FRAMES` | int | `200` | `>=20` | 送信キュー上限 |
| `TRANSCRIPTION_DELAY_MS` | int | `480` | `>=0` | 推論待ち調整 |

## 8. 受け入れ条件（T02 DoD対応）
- フォーマット `PCM16/16kHz/mono` が文書化されている。
- 20ms/40msの計算式と実数値が記載されている。
- 送信間隔、キュー上限、初期値が固定されている。
