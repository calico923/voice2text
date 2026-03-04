# Mac CLI client (T09-T11 scaffold)

## Current scope
- WAV入力ベースで Realtime API 送受信を確認できる最小CLI。
- `partial/final/error` の基本表示と保持ロジックを実装済み。
- マイク入力（リアルタイム録音）は次段階で追加。

## Files
- `client/src/main.py`: CLI entrypoint
- `client/src/audio_frame.py`: PCM16/16kHz/mono正規化 + チャンク分割
- `client/src/realtime_client.py`: WebSocket送受信
- `client/src/transcript_store.py`: partial/final/error状態管理
- `client/src/config.py`: 環境変数設定

## Run
```bash
python3 client/src/main.py \
  --wav server/testdata/test_ja_1s.wav \
  --url ws://127.0.0.1:8000/v1/realtime
```

## Environment variables
- `SERVER_URL` (default: `ws://127.0.0.1:8000/v1/realtime`)
- `API_KEY` (default: empty)
- `AUDIO_CHUNK_MS` (`20` or `40`, default: `20`)
- `TRANSCRIPTION_DELAY_MS` (default: `480`)
- `AUTO_PASTE` (default: `false`)
