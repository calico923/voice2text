# 実装進捗サマリ（2026-03-04）

## 1. 概要
- 本サマリは、2026-03-04 時点で実施した実装・検証・コミットをまとめたもの。
- 詳細タスク管理は `docs/parent-checklist.md` を正とする。

## 2. Parent進捗

### DONE
- `T01`: Realtimeイベント仕様メモ作成
- `T02`: 音声I/O仕様確定
- `T03`: WSL2セットアップ手順化
- `T04`: vLLMサーバ起動スクリプト作成

### IN_PROGRESS
- `T05`: ローカル疎通テスト（実vLLMでの最終試験待ち）
- `T06`: LAN設定手順・Windowsネットワーク設定スクリプト追加
- `T07`: Windows検証クライアント実装（実機接続試験待ち）
- `T08`: 経路マトリクス実装（実機3経路試験待ち）
- `T09`: 音声正規化/チャンク分割（WAV入力ベース）
- `T10`: Realtime送信処理（append/commit/response.create）
- `T11`: 受信表示/TranscriptStore
- `T12`: Auto Paste基盤（pbcopy + osascript）
- `T13`: 誤貼り付け防止ガード（空文字/重複/連投）
- `T14`: 再接続バックオフ基盤
- `T15`: 遅延計測スクリプト/比較テンプレート
- `T16`: JSONLログ基盤
- `T17`: 連続運用試験の実行基盤/チェックリスト/レポート雛形
- `T18`: BF16継続判定シート/量子化検証起票テンプレート

## 3. 追加した主な成果物
- 仕様書:
  - `docs/realtime-event-spec.md`
  - `docs/audio-io-spec.md`
  - `docs/wsl2-setup.md`
- サーバ/疎通:
  - `server/start_vllm.sh`
  - `server/realtime_smoke_client.py`
  - `server/mock_realtime_server.py`
  - `docs/local-connectivity-test.md`
  - `docs/lan-connectivity-setup.md`
- Windows検証:
  - `windows-client/realtime_wav_client.py`
  - `windows-client/route_matrix.py`
  - `docs/windows-route-test-template.md`
  - `docs/windows-route-test-result.mock.json`
  - `windows-network/setup-portproxy.ps1`
  - `windows-network/setup-firewall-rule.ps1`
- Macクライアント基盤:
  - `client/src/main.py`
  - `client/src/audio_frame.py`
  - `client/src/realtime_client.py`
  - `client/src/transcript_store.py`
  - `client/src/paste_controller.py`
  - `client/src/reconnect_controller.py`
  - `client/src/logger.py`
  - `client/tools/measure_latency.py`
  - `client/tools/continuous_eval.py`
- 評価/判定ドキュメント:
  - `docs/continuous-operation-checklist.md`
  - `docs/continuous-operation-report-template.md`
  - `docs/continuous-operation-mock-result-2026-03-04.md`
  - `docs/bf16-decision-sheet.md`
  - `docs/quantization-validation-ticket-template.md`

## 4. 検証結果（この環境で確認済み）
- Pythonユニットテスト: `15 tests, OK`
- モックRealtimeサーバでのE2E:
  - `server/realtime_smoke_client.py`: `partial=3, final=1, error=0`
  - `client/src/main.py`: `final=1` を受信、JSONLログ出力確認
  - `windows-client/route_matrix.py`: モック3経路で `passed=true`
  - `client/tools/continuous_eval.py`: モック短時間ドライランで `summary.json` 出力確認

## 5. 未完了理由（主なもの）
- `T05/T07/T08` の `DONE` 判定には、実vLLMサーバ（`/v1/realtime`）での実接続ログが必要。
- 現在はモックによる事前検証まで完了。

## 6. 主要コミット（新しい順）
- `95a7db8` chore: add mock route matrix result sample
- `9c1d7f7` chore: add latency measurement utility and template
- `ed3d302` chore: add reconnect backoff and jsonl logging
- `b9f4b3e` chore: add paste controller with safety guards
- `924eaa0` chore: scaffold mac cli realtime client modules
- `2d2b79f` chore: add mock connectivity test and LAN setup scaffolding
- `74fb42c` chore: add windows validation client and route matrix scaffold
- `a7f695a` chore: scaffold T05 local connectivity smoke test
- `5220299` T04: add vLLM startup script and server docs
- `104a131` T03: add WSL2 setup guide and pinned versions
- `c27919b` T02: add audio io specification
- `bc12aac` T01: add realtime event spec memo

## 7. 次の実施項目
1. 実vLLMサーバ起動（WSL2）で `T05` の本番疎通ログ取得
2. Windows本体から `T07/T08` の3経路実試験と採用経路確定
3. Mac->Windows LAN 実接続で `T06` 完了判定
4. 実機で `client/tools/continuous_eval.py` を 30分/60分実行し `T17` レポート作成
5. `docs/bf16-decision-sheet.md` に結論記入して `T18` 最終判断
