# ローカル疎通試験手順（T05）

## 1. 目的
- WSL2内で起動した vLLM Realtime API に対し、最小クライアントで疎通確認する。
- `partial/final/error` を受信できることを確認する。

## 2. 前提
- `T03` のセットアップ完了
- `T04` の起動スクリプト追加済み
- 仮想環境が有効化されている

## 3. 事前準備
```bash
pip install websockets==11.0.3
python server/testdata/generate_test_wav.py
```

## 4. サーバ起動
```bash
bash server/start_vllm.sh
```

## 5. クライアント実行
```bash
python server/realtime_smoke_client.py \
  --url ws://127.0.0.1:8000/v1/realtime \
  --wav server/testdata/test_ja_1s.wav \
  --chunk-ms 20 \
  --receive-timeout 12
```

## 6. 成功判定（T05 DoD）
- `response.output_text.delta` が1回以上出る
- `response.output_text.done` が1回以上出る
- `error` が0回、または原因を説明できる既知エラーのみ
- 実行ログ（コマンド、日時、結果）を記録済み

## 7. 実行記録テンプレート
```text
Date:
Server URL:
WAV:
Chunk ms:
Command:
partial count:
final count:
error count:
Result: PASS / FAIL
Notes:
```
