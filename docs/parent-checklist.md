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
| T04 | DONE | 2026-03-07 | vLLM GPU安定起動のWSL手順・トラブルシュート・再検証ログを更新 |
| T05 | DONE | 2026-03-07 | 現行 vLLM realtime protocol に合わせて client を修正し、spoken WAV で local /v1/realtime 疎通を確認 |
| T06 | DONE | 2026-03-08 | Mac -> Windows host IP `192.168.1.27:8000` -> WSL `172.22.38.155:8000` の LAN 疎通を WAV/実マイクで確認し、portproxy 手順を記録 |
| T07 | DONE | 2026-03-08 | Windows クライアントで localhost 経由の WAV/実マイク文字起こしを確認 |
| T08 | IN_PROGRESS | - | 採用経路候補は Windows host IP + portproxy。3経路マトリクスの定量記録は未実施 |
| T09 | IN_PROGRESS | - | WAV入力ベースの音声正規化/チャンク分割に加え、有限秒のマイク取り込み基盤を追加 |
| T10 | IN_PROGRESS | - | Realtime送信クライアントを追加（append/commit/response.create） |
| T11 | IN_PROGRESS | - | TranscriptStoreと受信表示ロジックを追加 |
| T12 | IN_PROGRESS | - | PasteControllerを追加（pbcopy + osascript） |
| T13 | IN_PROGRESS | - | 空文字/重複/連投ガードと単体テストを追加 |
| T14 | IN_PROGRESS | - | 再接続バックオフ制御と単体テストを追加 |
| T15 | IN_PROGRESS | - | 遅延計測スクリプトと比較テンプレートを追加 |
| T16 | IN_PROGRESS | - | JSONLロガーと単体テストを追加 |
| T17 | IN_PROGRESS | - | 連続運用試験チェックリスト・実行基盤・レポート雛形を追加 |
| T18 | IN_PROGRESS | - | BF16判定シートと量子化検証起票テンプレートを追加 |
