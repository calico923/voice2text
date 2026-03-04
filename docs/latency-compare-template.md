# 遅延比較テンプレート（T15）

## 1. 試験条件
```text
Date:
Server URL:
Model:
WAV:
Runs per setting:
```

## 2. 20ms 設定
```bash
AUDIO_CHUNK_MS=20 LOG_TO_FILE=true LOG_FILE=client/logs/chunk20.jsonl \
python3 client/src/main.py --wav server/testdata/test_ja_1s.wav --url <WS_URL>

python3 client/tools/measure_latency.py --log client/logs/chunk20.jsonl
```

## 3. 40ms 設定
```bash
AUDIO_CHUNK_MS=40 LOG_TO_FILE=true LOG_FILE=client/logs/chunk40.jsonl \
python3 client/src/main.py --wav server/testdata/test_ja_1s.wav --url <WS_URL>

python3 client/tools/measure_latency.py --log client/logs/chunk40.jsonl
```

## 4. 比較表

| Setting | count | median_ms | p95_ms | max_ms | Notes |
|---|---:|---:|---:|---:|---|
| chunk=20 |  |  |  |  |  |
| chunk=40 |  |  |  |  |  |

## 5. 推奨値
```text
Recommended AUDIO_CHUNK_MS:
Reason:
```
