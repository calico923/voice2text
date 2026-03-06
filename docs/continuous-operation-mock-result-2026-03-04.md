# 連続運用試験（モック）結果メモ（2026-03-04）

## 1. 目的
- `client/tools/continuous_eval.py` の実行/集計パイプラインが動作することを事前確認する。
- 本結果はモックサーバ検証であり、`T17` 完了判定には使用しない。

## 2. 実行コマンド
```bash
python3 client/tools/continuous_eval.py \
  --wav server/testdata/test_ja_1s.wav \
  --url ws://127.0.0.1:18000/v1/realtime \
  --duration-minutes 0.2 \
  --chunk-ms 20 \
  --max-runs 3 \
  --output-dir client/logs/continuous
```

## 3. 出力サマリ（抜粋）
- run_id: `20260304T114739Z`
- attempted_runs: `1`
- successful_runs: `1`
- success_rate_pct: `100.0`
- latency median/p95: `26.0 / 26.0 ms`
- missing_final_rate_pct: `0.0`
- vram used(max)/free(min): `5242 / 10822 MB`

## 4. 生成物
- `client/logs/continuous/20260304T114739Z/summary.json`
- `client/logs/continuous/20260304T114739Z/events.jsonl`
- `client/logs/continuous/20260304T114739Z/vram.jsonl`

## 5. 注意
- 実運用判定には、実vLLM（`/v1/realtime`）での `30分` / `60分` 試験結果が必要。
