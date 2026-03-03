# リアルタイム音声入力方針（参考・旧案）

## ステータス
- この文書は「初期検討時の旧案」を残した参考資料。
- 現在の採用方針ではないため、実装判断には使わない。

## 非採用となった理由
- 本文書の案は `FastAPI + WebSocket + faster-whisper` を前提としている。
- 現行計画は `WSL2 + vLLM Realtime API + Voxtral-Mini-4B-Realtime-2602(BF16)` に統一済み。
- プロトコルが異なるため（独自JSON/binaryとvLLMイベント仕様は非互換）、本案を混在させると実装が破綻する。

## 現行で参照すべき文書
- `docs/sankou/implementation-roadmap.md`
- `docs/windows-streaming-quantization.md`
- `docs/detailed-design.md`
- `docs/task-breakdown.md`
- `docs/micro-tasks.md`

## 備考
- 検討履歴としては価値があるため削除せず保持する。
- 旧案を再採用する場合は、別ブランチで独立検証した上で採否を再評価する。
