# Windows検証クライアント（T07/T08）

## 1. 目的
- Windows本体から WSL 上の Realtime API へ接続できるかを確認する。
- `localhost` / `WSL IP` / `Windows host IP` の経路を比較して採用経路を決める。
- 可能な限り本番に近い形で、Windows実マイク入力の realtime 動作を確認する。

## 2. ファイル
- `windows-client/realtime_wav_client.py`
  - WAVまたはマイク入力を realtime 送信し、partial/final/error を表示
- `windows-client/route_matrix.py`
  - 3経路を順番に試験し、結果を JSON で保存

## 3. 前提
- Python 3.10+（推奨 3.11）
- `pip install websockets==11.0.3`
- テスト音声: `server/testdata/test_en_hello_16k.wav`
- Windows実マイク試験では `ffmpeg` を `PATH` に通す

## 4. 単発実行（1経路）
```bash
python windows-client/realtime_wav_client.py \
  --url ws://127.0.0.1:8000/v1/realtime \
  --wav server/testdata/test_en_hello_16k.wav \
  --chunk-ms 20
```

## 5. Windows実マイク試験
- `realtime_wav_client.py` は `--mic` で有限秒キャプチャを送信できる
- 送信と受信は並列で進むため、partial を取りこぼしにくい
- mic モードは既定で会話向けの VAD 分割を有効にする
  - `chunk-ms=20`
  - `vad-silence-ms=600`
  - `min-utterance-ms=400`
  - `max-utterance-ms=6000`
  - `pre-roll-ms=200`
  - `vad-rms-threshold=700`
- `--mic-seconds` は「連続キャプチャする全体時間」。既定は `30` 秒
- partial UI の 120ms デバウンスはアプリ層の設定で、CLI は受信イベントをそのまま表示する

PowerShell でマイク名を確認:
```powershell
ffmpeg -list_devices true -f dshow -i dummy
```

PowerShell で会話向けの既定設定をそのまま使って realtime 送信:
```powershell
python .\windows-client\realtime_wav_client.py `
  --url ws://127.0.0.1:8000/v1/realtime `
  --mic `
  --mic-device "Microphone Array (Realtek(R) Audio)" `
  --mic-seconds 30 `
  --chunk-ms 20
```

短い smoke test に落としたい場合だけ `--mic-seconds 5` を付ける。

`ffmpeg` を使わず独自コマンドを使いたい場合は `--capture-cmd` を指定する。`{device}` を埋め込みに使える。

```powershell
python .\windows-client\realtime_wav_client.py `
  --url ws://127.0.0.1:8000/v1/realtime `
  --mic `
  --mic-device "Microphone Array (Realtek(R) Audio)" `
  --capture-cmd 'ffmpeg -nostdin -hide_banner -loglevel error -f dshow -i audio="{device}" -ac 1 -ar 16000 -f s16le -acodec pcm_s16le pipe:1'
```

詳細な初期値と運用意図は `docs/realtime-conversation-defaults.md` を参照。

## 6. 経路マトリクス実行（3経路）
```bash
python windows-client/route_matrix.py \
  --localhost-url ws://127.0.0.1:8000/v1/realtime \
  --wsl-ip-url ws://<WSL_IP>:8000/v1/realtime \
  --host-ip-url ws://<WINDOWS_HOST_IP>:8000/v1/realtime
```

- 結果: `docs/windows-route-test-result.json`
  - 各経路の `partial_count / final_count / error_count` を含む

## 7. 判定
- `return_code=0` かつ `passed=true` の経路を候補にする。
- 複数候補がある場合は再現性（3回連続成功）で最終決定する。
