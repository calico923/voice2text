# ユーザー実施タスク一覧（2026-03-04時点）

## 1. 目的
- 現在 `IN_PROGRESS` の `T05-T08`, `T17-T18` を完了させるために、ユーザー実機で必要な作業を整理する。
- このドキュメントのチェックが埋まれば、最終判定まで進められる。

## 2. 優先順チェックリスト

### Step 1: T05 実vLLMでローカル疎通ログを取得（WSL2）
- [ ] vLLMサーバ起動
```bash
bash server/start_vllm.sh
```
- [ ] スモーククライアント実行
```bash
python server/realtime_smoke_client.py \
  --url ws://127.0.0.1:8000/v1/realtime \
  --wav server/testdata/test_en_hello_16k.wav \
  --chunk-ms 20 \
  --receive-timeout 12
```
- [ ] `partial>=1`, `final>=1`, `error=0` を確認
- [ ] 結果を `docs/local-connectivity-test.md` のテンプレート形式で記録

### Step 2: T07/T08 Windows本体から3経路実試験
- [ ] Windowsで依存導入
```bash
pip install websockets==11.0.3
```
- [ ] 3経路マトリクス実行
```bash
python windows-client/route_matrix.py \
  --localhost-url ws://127.0.0.1:8000/v1/realtime \
  --wsl-ip-url ws://<WSL_IP>:8000/v1/realtime \
  --host-ip-url ws://<WINDOWS_HOST_IP>:8000/v1/realtime
```
- [ ] `docs/windows-route-test-result.json` を確認
- [ ] `docs/windows-route-test-template.md` を埋めて採用経路を決定
- [ ] 採用経路で3回連続成功を確認

### Step 3: T06 Mac -> Windows(LAN) 実接続確認
- [ ] `docs/lan-connectivity-setup.md` に従ってネットワーク方式を設定
- [ ] FirewallをMac IP限定で許可
- [ ] Mac側クライアントで接続確認
```bash
LOG_TO_FILE=true LOG_FILE=client/logs/lan-e2e.jsonl \
python3 client/src/main.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://<WINDOWS_HOST_IP>:8000/v1/realtime
```
- [ ] `final>=1` を確認し、LAN手順書に実測結果を追記

### Step 4: T17 30分/60分 連続運用試験
- [ ] 30分試験
```bash
python3 client/tools/continuous_eval.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://<ADOPTED_ROUTE_IP>:8000/v1/realtime \
  --duration-minutes 30 \
  --chunk-ms 20 \
  --output-dir client/logs/continuous
```
- [ ] 60分試験
```bash
python3 client/tools/continuous_eval.py \
  --wav server/testdata/test_en_hello_16k.wav \
  --url ws://<ADOPTED_ROUTE_IP>:8000/v1/realtime \
  --duration-minutes 60 \
  --chunk-ms 20 \
  --output-dir client/logs/continuous
```
- [ ] `summary.json` の `missing_final_rate_pct`, `latency_metrics_ms`, `vram_metrics` を記録
- [ ] `docs/continuous-operation-report-template.md` を埋める

### Step 5: T18 BF16継続/量子化移行の最終判断
- [ ] `docs/bf16-decision-sheet.md` に実測値を記入
- [ ] 結論を `BF16継続` か `量子化移行` で確定
- [ ] 量子化移行の場合は `docs/quantization-validation-ticket-template.md` を起票

## 3. 完了時に更新するファイル
- `docs/windows-route-test-template.md`（実測値記入）
- `docs/continuous-operation-report-template.md`（30/60分結果）
- `docs/bf16-decision-sheet.md`（最終判定）
- `docs/parent-checklist.md`（`T05/T06/T07/T08/T17/T18` を `DONE` へ）

## 4. 共有してほしい成果物（この順で）
1. `docs/windows-route-test-result.json`
2. `client/logs/continuous/<run_id>/summary.json`（30分・60分）
3. 更新済み `docs/continuous-operation-report-template.md`
4. 更新済み `docs/bf16-decision-sheet.md`
