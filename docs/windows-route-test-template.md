# Windows本体 <-> WSL 接続試験テンプレート（T08）

## 1. 試験条件
```text
Date:
Windows Version:
WSL Distro:
Server bind host/port:
WAV:
Chunk ms:
```

## 2. 結果表

| Route | URL | Return Code | Partial Count | Final Count | Error Count | 判定 |
|---|---|---:|---:|---:|---:|---|
| localhost | ws://127.0.0.1:8000/v1/realtime |  |  |  |  | PASS / FAIL |
| WSL IP | ws://<WSL_IP>:8000/v1/realtime |  |  |  |  | PASS / FAIL |
| Windows host IP | ws://<WINDOWS_HOST_IP>:8000/v1/realtime |  |  |  |  | PASS / FAIL |

## 3. 採用経路
```text
Selected route:
Reason:
Repro steps:
```

## 4. 実行コマンド
```bash
python windows-client/route_matrix.py \
  --localhost-url ws://127.0.0.1:8000/v1/realtime \
  --wsl-ip-url ws://<WSL_IP>:8000/v1/realtime \
  --host-ip-url ws://<WINDOWS_HOST_IP>:8000/v1/realtime
```
