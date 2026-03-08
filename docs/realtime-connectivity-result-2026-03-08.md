# Realtime 実機疎通結果（2026-03-08）

## 1. 概要
- WSL 上の vLLM Realtime API に対し、Windows 実マイクと Mac 実マイクの両方で文字起こし成功を確認した。
- 実運用で使えた LAN 経路は `Mac -> Windows host IP -> portproxy -> WSL` だった。

## 2. 接続情報
```text
Date: 2026-03-08
WSL server bind: 0.0.0.0:8000
WSL IP: 172.22.38.155
Windows host IP: 192.168.1.27
Adopted LAN URL: ws://192.168.1.27:8000/v1/realtime
Windows local URL: ws://127.0.0.1:8000/v1/realtime
```

## 3. Windows 実機結果
- 目的: Windows 本体から localhost 経由で realtime 音声入力が通ることを確認
- クライアント: `windows-client/realtime_wav_client.py`
- マイク: `マイク (USB MICROPHONE)`

### 実行コマンド
```powershell
py -3 .\windows-client\realtime_wav_client.py `
  --url ws://127.0.0.1:8000/v1/realtime `
  --mic `
  --mic-device "マイク (USB MICROPHONE)"
```

### 結果
```text
Observed summary (representative):
[summary] {"partial": 73, "final": 1, "error": 0, "other": 1} sent_chunks=250
Result: PASS
Notes:
- partial と final の両方を受信した。
- 認識精度は今後調整余地ありだが、実マイク -> 推論 -> 文字起こし の経路は成立した。
```

## 4. Mac 実機結果
- 目的: Mac から Windows 経由で WSL realtime サーバーへ接続し、WAV と実マイクの両方を通す
- クライアント: `client/src/main.py`

### 事前設定
Windows 管理者 PowerShell:
```powershell
.\windows-network\setup-portproxy.ps1 `
  -ListenAddress 0.0.0.0 `
  -ListenPort 8000 `
  -ConnectAddress 172.22.38.155 `
  -ConnectPort 8000
```

```powershell
.\windows-network\setup-firewall-rule.ps1 `
  -RuleName "voice2text-realtime-8000" `
  -Port 8000 `
  -MacIp <user-local-mac-ip>
```

### WAV 疎通
Mac:
```bash
python3 client/src/main.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://192.168.1.27:8000/v1/realtime
```

結果:
```text
Result: PASS
Notes:
- final を受信し、WAV ベースの LAN 経路が成立した。
```

### 実マイク疎通
Mac:
```bash
ffmpeg -f avfoundation -list_devices true -i ""
python3 client/src/main.py \
  --mic \
  --mic-device <avfoundation-device-index> \
  --url ws://192.168.1.27:8000/v1/realtime
```

結果:
```text
Result: PASS
Notes:
- 実マイクでも realtime 文字起こしできることを確認した。
- Mac 側では conversation defaults (20ms / 600ms silence / 400ms min / 6000ms max) を使用。
```

## 5. 失敗パターンと対処
- `404`:
  - Mac から `ws://127.0.0.1:8000/v1/realtime` を叩くと Mac 自身を見に行く。Windows host IP を使う。
- `TimeoutError: timed out during opening handshake`:
  - Windows host IP で待ち受けていないか、portproxy/firewall が未設定。
- `socket.gaierror: [Errno 8] ...`:
  - URL にプレースホルダ文字列やカンマ区切り IP を入れている。実 IP をドット区切りで指定する。

## 6. 現時点の判断
- `T06`: 実機 LAN 疎通としては PASS
- `T07`: Windows 実機クライアントとしては PASS
- `T08`: 採用経路候補は `Windows host IP + portproxy`。3経路の定量比較記録は未実施
