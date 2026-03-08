# Mac CLI client (T09-T11 scaffold)

## Current scope
- WAV入力ベースで Realtime API 送受信を確認できる最小CLI。
- `--mic` による既定マイクの有限秒キャプチャを追加済み（macOS は `ffmpeg`、Linux は `arecord` 前提）。
- `partial/final/error` の基本表示と保持ロジックを実装済み。
- Auto Paste の基盤（`pbcopy + osascript`）と誤貼り付けガードを実装済み。
- 長時間の常時録音/VAD は次段階で追加。

## Files
- `client/src/main.py`: CLI entrypoint
- `client/src/audio_capture.py`: 既定マイクからの raw PCM16 キャプチャ
- `client/src/audio_frame.py`: PCM16/16kHz/mono正規化 + チャンク分割
- `client/src/realtime_client.py`: WebSocket送受信
- `client/src/transcript_store.py`: partial/final/error状態管理
- `client/src/paste_controller.py`: final貼り付け + ガード
- `client/src/reconnect_controller.py`: 再接続バックオフ計算
- `client/src/logger.py`: JSONLイベントログ
- `client/src/config.py`: 環境変数設定
- `client/tools/measure_latency.py`: JSONLから遅延統計を算出
- `client/tools/continuous_eval.py`: 連続運用試験の反復実行 + 集計 + VRAMサンプリング

## Run
```bash
python3 client/src/main.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://127.0.0.1:8000/v1/realtime
```

```bash
python3 client/src/main.py \
  --mic \
  --mic-seconds 5 \
  --url ws://127.0.0.1:8000/v1/realtime
```

```bash
python3 client/tools/continuous_eval.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://127.0.0.1:8000/v1/realtime \
  --duration-minutes 30
```

## Environment variables
- `SERVER_URL` (default: `ws://127.0.0.1:8000/v1/realtime`)
- `API_KEY` (default: empty)
- `AUDIO_CHUNK_MS` (`20` or `40`, default: `20`)
- `TRANSCRIPTION_DELAY_MS` (default: `480`)
- `AUTO_PASTE` (default: `false`)
- `PASTE_MIN_INTERVAL_MS` (default: `700`)
- `LOG_TO_FILE` (default: `false`)
- `LOG_FILE` (default: `client/logs/events.jsonl`)
- `AUDIO_INPUT_DEVICE` (default: backend default / macOS は `0`)
- `AUDIO_CAPTURE_CMD` (default: empty, set to override capture command)
