# 詳細設計（Windows推論 + Mac入力）

## 1. 目的と範囲
- 目的:
  - Macで取得した音声をWindows(WSL2)上のvLLM Realtime APIへ送信し、逐次文字起こし結果を受け取る。
  - `final`（確定結果）のみを任意アプリへ貼り付ける。
- 本設計で扱う範囲:
  - Macクライアント（CLIベース）
  - Windows側のvLLM起動・公開方式
  - LAN内通信、再接続、ログ、評価
- 非対象:
  - インターネット公開
  - クラウド運用
  - GUIのリッチ化

## 2. 全体アーキテクチャ
- Mac:
  - `AudioCapture`: マイク取得
  - `AudioResampler`: PCM16/16kHz/monoへ変換
  - `FrameChunker`: 20msまたは40msフレーム化
  - `RealtimeClient`: WebSocket接続とイベント送受信
  - `TranscriptStore`: partial/final状態管理
  - `PasteController`: finalのみ貼り付け
  - `ReconnectController`: 切断検知と再接続
  - `AppConfig`: 設定読み込み
  - `Logger`: 構造化ログ出力
- Windows(WSL2):
  - `vLLM Server`: `/v1/realtime` 提供
  - `Launcher`: 起動引数固定
  - `Network Bridge`: `portproxy` または `mirrored` モード
  - `Firewall Rule`: Mac IPのみ許可
- Windows本体（検証用）:
  - `Windows Test Client`: WSL上 `/v1/realtime` への疎通確認用CLI
  - 目的: Mac依存を外した段階的検証（WSL <-> Windows本体）

## 3. ディレクトリ設計（提案）
- `server/`
  - `start_vllm.sh`（WSL2内起動スクリプト）
  - `env.example`
  - `README.md`
- `client/`
  - `src/audio_capture.*`
  - `src/audio_resampler.*`
  - `src/frame_chunker.*`
  - `src/realtime_client.*`
  - `src/transcript_store.*`
  - `src/paste_controller.*`
  - `src/reconnect_controller.*`
  - `src/config.*`
  - `src/logger.*`
  - `src/main.*`
- `docs/`
  - `task-breakdown.md`
  - `detailed-design.md`（本書）
  - `micro-tasks.md`

## 4. 通信プロトコル設計（MVP）
- 前提:
  - 仕様名は「vLLM Realtime APIイベント仕様」。
  - 厳密なイベント名・必須項目は `T01` で確定する。
- 送信方針:
  - 音声フレームをbase64化しappendイベントとして送る。
  - 発話区切りでcommit相当イベントを送る。
  - 必要に応じてresponse生成要求イベントを送る。
- 受信方針:
  - `partial` 相当: 画面上の暫定表示を更新
  - `final` 相当: 確定バッファへ追加
  - `error` 相当: 通知し再接続制御へ連携

## 5. セッション状態遷移
- 状態:
  - `IDLE`
  - `CONNECTING`
  - `STREAMING`
  - `RECONNECT_WAIT`
  - `ERROR`
  - `STOPPED`
- 主な遷移:
  - `IDLE -> CONNECTING`: Start操作
  - `CONNECTING -> STREAMING`: ハンドシェイク成功
  - `STREAMING -> RECONNECT_WAIT`: 切断検知
  - `RECONNECT_WAIT -> CONNECTING`: バックオフ経過
  - `STREAMING -> ERROR`: 復旧不能エラー
  - `STREAMING -> STOPPED`: Stop操作

## 6. 音声パイプライン設計
- 入力:
  - デバイス: 既定マイク（将来は選択可能化）
  - サンプルレート: 実デバイス依存
- 変換:
  - 出力フォーマット: PCM16 / 16kHz / mono
- フレーミング:
  - 初期値: 20ms
  - 代替: 40ms（帯域を減らす）
- バッファ:
  - 送信キュー上限（例）: 200フレーム
  - 上限超過時: 古いpartial向けフレーム破棄ではなく、送信遅延警告を優先

## 7. partial/final表示設計
- `partial`:
  - 1行上書き表示
  - 新しいpartialで置換
- `final`:
  - セグメント単位で確定ログへ追記
  - `segment_id` で重複防止
- 画面表示:
  - 上段: 接続状態
  - 中段: partial
  - 下段: final履歴（直近N件）

## 8. 貼り付け設計
- トリガ:
  - `final` 到着時のみ
- 手順:
  - `pbcopy` へ確定テキスト渡し
  - `osascript` でペーストキー送出
- 安全策:
  - Auto Paste初期値はOFF
  - 連続貼り付け最小間隔（例: 700ms）
  - 空文字・同一連続文字は貼り付け抑止

## 9. 再接続設計
- 切断検知:
  - WebSocket close/error
  - heartbeat timeout（必要なら追加）
- バックオフ:
  - 1s, 2s, 4s, 8s, 10s（上限10s）
  - 成功時にリセット
- 再接続時の扱い:
  - partialは破棄
  - final履歴は保持
  - 録音は継続し、接続復帰後に新フレームから送信

## 10. 設定設計
- 設定キー（必須）:
  - `SERVER_URL`
  - `API_KEY`（未使用なら空許容）
  - `AUDIO_CHUNK_MS`（20/40）
  - `TRANSCRIPTION_DELAY_MS`（初期480）
  - `AUTO_PASTE`（true/false）
  - `PASTE_MIN_INTERVAL_MS`
  - `LOG_LEVEL`
  - `LOG_TO_FILE`
- 読み込み順:
  - `.env` -> 環境変数 -> CLI引数

## 11. ログ/メトリクス設計
- ログ形式:
  - JSON Lines（1行1イベント）
- 最低記録項目:
  - timestamp
  - session_id
  - event_type
  - latency_ms
  - queue_depth
  - reconnect_count
  - error_code / message
- 集計指標:
  - 体感遅延中央値/95p
  - 欠落率（final欠損）
  - 再接続回数

## 12. セキュリティ設計（LAN限定）
- Windows Firewallで送信元をMac IPに限定
- ルータでポート開放しない
- 認証無し運用時はLAN外到達性ゼロを確認
- ログに生音声データを保存しない

## 13. テスト設計
- 単体テスト:
  - 音声変換（サンプル数・ビット深度）
  - chunk分割（境界値）
  - transcript重複防止
  - 再接続バックオフ計算
- 結合テスト:
  - ローカル接続（WSL内）
  - LAN接続（Mac -> Windows）
  - final貼り付け
- 耐久テスト:
  - 30〜60分連続運転
  - 一時切断から復帰

## 14. 受け入れ基準
- 逐次認識がCLIで継続表示される
- finalのみ貼り付けられる
- 30〜60分運転で重大停止なし
- 体感遅延0.3〜0.8秒を目標レンジとする

## 15. リスクと設計対策
- 誤貼り付け:
  - final限定 + レート制限 + 重複抑止
- WSL2到達性:
  - `portproxy`/`mirrored` のどちらかを手順化
- 遅延増:
  - `AUDIO_CHUNK_MS` と `TRANSCRIPTION_DELAY_MS` を調整可能化
- VRAM圧迫:
  - `max-model-len` を初期4096で開始し実測で調整

## 16. Windows検証クライアント設計（追加）
- 位置づけ:
  - 本番クライアントはMacだが、検証初期はWindows本体クライアントも用意する。
  - 目的はWSL公開設定とRealtime接続性の切り分け。
- 最小機能:
  - WAV入力（PCM16/16kHz/mono、不足時は変換またはエラー）
  - Realtime API接続
  - append/commit送信
  - partial/final/error表示
- 検証経路:
  - `localhost`
  - `WSL IP`
  - `Windows host IP`
- 成果:
  - 採用経路を1つ固定し、再現手順を文書化
