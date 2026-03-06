# 連続運用試験チェックリスト（T17 / M090）

## 1. 事前準備
- [ ] vLLMサーバ（WSL2）を起動し、`/v1/realtime` へ接続可能な状態にする
- [ ] テストWAVを固定する（例: `server/testdata/test_en_hello_16k.wav`）
- [ ] 試験中は同条件を維持する（同一モデル、同一`chunk_ms`）
- [ ] `nvidia-smi` が利用可能であることを確認する（VRAM採取用）
- [ ] 試験開始時刻と構成（GPU/モデルURL/設定値）を記録する

## 2. 30分連続試験（M091）
```bash
python3 client/tools/continuous_eval.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://<WSL_OR_HOST_IP>:8000/v1/realtime \
  --duration-minutes 30 \
  --chunk-ms 20 \
  --output-dir client/logs/continuous
```

- [ ] `summary.json` が出力される
- [ ] `successful_runs > 0`
- [ ] `missing_final_rate_pct` を記録する
- [ ] `latency_metrics_ms.median/p95` を記録する

## 3. 60分連続試験（M092）
```bash
python3 client/tools/continuous_eval.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://<WSL_OR_HOST_IP>:8000/v1/realtime \
  --duration-minutes 60 \
  --chunk-ms 20 \
  --output-dir client/logs/continuous
```

- [ ] `summary.json` が出力される
- [ ] `successful_runs > 0`
- [ ] `missing_final_rate_pct` を記録する
- [ ] `latency_metrics_ms.median/p95` を記録する

## 4. VRAM推移確認（M093）
- [ ] `vram_metrics.available=true` を確認
- [ ] `memory_used_mb.max` と `memory_free_mb.min` を記録
- [ ] OOM/クラッシュ有無を記録

## 5. 指標計算（M094/M095）
- [ ] 遅延中央値: `latency_metrics_ms.median`
- [ ] 遅延95p: `latency_metrics_ms.p95`
- [ ] 欠落率: `event_metrics.missing_final_rate_pct`

## 6. レポート化（M096）
- [ ] `docs/continuous-operation-report-template.md` を埋める
- [ ] 30分/60分結果を同一フォーマットで比較する
- [ ] BF16継続/移行判定に必要な根拠が揃っている
