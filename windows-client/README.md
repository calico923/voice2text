# Windows検証クライアント（T07/T08）

## 1. 目的
- Windows本体から WSL 上の Realtime API へ接続できるかを確認する。
- `localhost` / `WSL IP` / `Windows host IP` の経路を比較して採用経路を決める。

## 2. ファイル
- `windows-client/realtime_wav_client.py`
  - WAV入力を append/commit で送信し、partial/final/error を表示
- `windows-client/route_matrix.py`
  - 3経路を順番に試験し、結果を JSON で保存

## 3. 前提
- Python 3.10+（推奨 3.11）
- `pip install websockets==11.0.3`
- テスト音声: `server/testdata/test_ja_1s.wav`

## 4. 単発実行（1経路）
```bash
python windows-client/realtime_wav_client.py \
  --url ws://127.0.0.1:8000/v1/realtime \
  --wav server/testdata/test_ja_1s.wav \
  --chunk-ms 20 \
  --send-response-create
```

## 5. 経路マトリクス実行（3経路）
```bash
python windows-client/route_matrix.py \
  --localhost-url ws://127.0.0.1:8000/v1/realtime \
  --wsl-ip-url ws://<WSL_IP>:8000/v1/realtime \
  --host-ip-url ws://<WINDOWS_HOST_IP>:8000/v1/realtime
```

- 結果: `docs/windows-route-test-result.json`

## 6. 判定
- `return_code=0` かつ `passed=true` の経路を候補にする。
- 複数候補がある場合は再現性（3回連続成功）で最終決定する。
