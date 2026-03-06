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
python3 -m pip install websockets==14.2
```

- 実接続の PASS 判定には spoken WAV を使う。
- `server/testdata/test_ja_1s.wav` は 440Hz tone なので、`transcription.done` まで到達しても `text=""` になり得る。
- 現在の推奨 testdata は `server/testdata/test_en_hello_16k.wav`。

## 4. サーバ起動
```bash
bash server/start_vllm.sh
```

## 5. クライアント実行
```bash
python server/realtime_smoke_client.py \
  --url ws://127.0.0.1:8000/v1/realtime \
  --wav server/testdata/test_en_hello_16k.wav \
  --chunk-ms 20 \
  --receive-timeout 12
```

## 6. 成功判定（T05 DoD）
- `transcription.delta` が1回以上出る
- `transcription.done` が1回以上出る
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

## 8. 実行記録（2026-03-07）
```text
Date: 2026-03-07
Server URL: ws://127.0.0.1:8000/v1/realtime
WAV: server/testdata/test_en_hello_16k.wav
Chunk ms: 20
Command: /tmp/voice2text-vllm-venv311-clean/bin/python server/realtime_smoke_client.py --url ws://127.0.0.1:8000/v1/realtime --wav server/testdata/test_en_hello_16k.wav --chunk-ms 20 --receive-timeout 12
partial count: 10
final count: 1
error count: 0
Result: PASS
Notes: 現行 vLLM realtime 実装は session.update / transcription.delta / transcription.done を使う。旧 response.create 前提 client を修正して再試験した。認識結果は「ハローボイストゥーテクト。」。
```

## 9. 補助検証（任意）
- 実vLLMが未導入の段階では `server/mock_realtime_server.py` を使って
  クライアント送受信の単体疎通を先に確認できる。
