# 次にやること（2026-03-06）

## 目的
- `IN_PROGRESS` の `T05/T06/T07/T08/T17/T18` を `DONE` に進める。
- 実機ログを集めて、最終判断（BF16継続 or 量子化移行）まで完了させる。

## 優先順チェックリスト

### 1. T05: 実vLLMでローカル疎通確認（WSL2）
- [ ] `bash server/start_vllm.sh`
- [ ] `python server/realtime_smoke_client.py --url ws://127.0.0.1:8000/v1/realtime --wav server/testdata/test_en_hello_16k.wav --chunk-ms 20 --receive-timeout 12`
- [ ] `partial>=1` / `final>=1` / `error=0` を確認
- [ ] 結果を `docs/local-connectivity-test.md` に記録

### 2. T07/T08: Windows本体から3経路試験
- [ ] `python windows-client/route_matrix.py --localhost-url ws://127.0.0.1:8000/v1/realtime --wsl-ip-url ws://<WSL_IP>:8000/v1/realtime --host-ip-url ws://<WINDOWS_HOST_IP>:8000/v1/realtime`
- [ ] `docs/windows-route-test-result.json` を確認
- [ ] `docs/windows-route-test-template.md` に実測結果を記録し、採用経路を1つ決定
- [ ] 採用経路で3回連続成功を確認

### 3. T06: Mac -> Windows(LAN) 実接続
- [ ] `docs/lan-connectivity-setup.md` の手順でネットワーク設定
- [ ] FirewallをMac IP限定で許可
- [ ] `LOG_TO_FILE=true LOG_FILE=client/logs/lan-e2e.jsonl python3 client/src/main.py --wav server/testdata/test_en_hello_16k.wav --url ws://<WINDOWS_HOST_IP>:8000/v1/realtime`
- [ ] `final>=1` を確認し、`docs/lan-connectivity-setup.md` に実測結果を追記

### 4. T17: 30分/60分 連続運用試験
- [ ] 30分: `python3 client/tools/continuous_eval.py --wav server/testdata/test_en_hello_16k.wav --url ws://<ADOPTED_ROUTE_IP>:8000/v1/realtime --duration-minutes 30 --chunk-ms 20 --output-dir client/logs/continuous`
- [ ] 60分: `python3 client/tools/continuous_eval.py --wav server/testdata/test_en_hello_16k.wav --url ws://<ADOPTED_ROUTE_IP>:8000/v1/realtime --duration-minutes 60 --chunk-ms 20 --output-dir client/logs/continuous`
- [ ] `summary.json` の `missing_final_rate_pct` / `latency_metrics_ms` / `vram_metrics` を記録
- [ ] `docs/continuous-operation-report-template.md` を更新

### 5. T18: 最終判断（BF16継続 or 量子化移行）
- [ ] `docs/bf16-decision-sheet.md` に実測値と結論を記入
- [ ] 量子化移行の場合は `docs/quantization-validation-ticket-template.md` を起票
- [ ] `docs/parent-checklist.md` の `T18` を更新

## 最後に更新するファイル
- `docs/local-connectivity-test.md`
- `docs/windows-route-test-template.md`
- `docs/lan-connectivity-setup.md`
- `docs/continuous-operation-report-template.md`
- `docs/bf16-decision-sheet.md`
- `docs/parent-checklist.md`

## 参照
- `docs/parent-checklist.md`
- `docs/user-action-items-2026-03-04.md`
- `docs/progress-summary-2026-03-04.md`
