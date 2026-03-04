# ローカル疎通試験記録（モック）- 2026-03-04

## 実行目的
- `server/realtime_smoke_client.py` の append/commit/受信ロジック検証
- 実サーバ（vLLM）導入前に基本不具合を除去する

## 実行コマンド
```bash
python3 server/mock_realtime_server.py --host 127.0.0.1 --port 18000
```
```bash
python3 server/realtime_smoke_client.py \
  --url ws://127.0.0.1:18000/v1/realtime \
  --wav server/testdata/test_ja_1s.wav \
  --chunk-ms 20 \
  --receive-timeout 5
```

## 結果
```text
partial count: 3
final count: 1
error count: 0
Result: PASS (mock)
```

## 補足
- この結果はモックサーバでの検証結果であり、T05完了判定には使わない。
- T05をDONEにするには、vLLM実サーバで同等の試験記録が必要。
