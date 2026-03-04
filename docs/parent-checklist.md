# Parent完了チェックリスト

## 目的
- `Parent`（`Txx`）完了時に、完了根拠を1ファイルで記録する。
- `Txx` 単位でセーブポイント（コミット）を残し、後戻りしやすくする。

## 更新ルール
- `Txx: ...` 形式でコミットする前に、対象 `Txx` の行を必ず更新する。
- `Status` は `TODO` / `IN_PROGRESS` / `DONE` のみ使用する。
- `Txx` 完了コミット時は `Status=DONE` とし、`Reviewed On` を `YYYY-MM-DD` で記入する。
- 同じ `Txx` の追加修正コミット時も、同じ行を更新して履歴を残す。

| Parent | Status | Reviewed On | Notes |
|---|---|---|---|
| T01 | DONE | 2026-03-04 | Realtimeイベント仕様メモを追加 |
| T02 | DONE | 2026-03-04 | 音声I/O仕様書を追加（PCM16/16kHz/mono, 20/40ms） |
| T03 | DONE | 2026-03-04 | WSL2セットアップ手順とバージョン固定を追加 |
| T04 | DONE | 2026-03-04 | vLLM起動スクリプトとserver READMEを追加 |
| T05 | IN_PROGRESS | - | ローカル疎通クライアントと試験手順を追加（実接続試験待ち） |
| T06 | IN_PROGRESS | - | LAN設定手順とWindowsネットワークスクリプトを追加 |
| T07 | IN_PROGRESS | - | Windows WAVクライアント実装を追加（実機接続試験待ち） |
| T08 | IN_PROGRESS | - | 3経路マトリクス実行スクリプトと記録テンプレートを追加 |
| T09 | TODO | - | |
| T10 | TODO | - | |
| T11 | TODO | - | |
| T12 | TODO | - | |
| T13 | TODO | - | |
| T14 | TODO | - | |
| T15 | TODO | - | |
| T16 | TODO | - | |
| T17 | TODO | - | |
| T18 | TODO | - | |
