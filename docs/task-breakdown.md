# タスク分解（implementation-roadmap対応）

## 運用ルール
- IDは `Txx` で管理する。
- 各タスクは「依存タスク」が完了してから着手する。
- 完了条件（DoD）を満たした時点で完了とする。
- 詳細設計は `docs/detailed-design.md` を参照する。
- 最小粒度タスクは `docs/micro-tasks.md` を参照する。
- `Parent`（= `Txx`）を1つ完了するたびに、必ず `git commit` を作成する。
- `Txx` 完了の判定は「対応する全 `Mxxx` が完了」かつ「`Txx` の DoD を満たす」の両方を満たした時点とする。
- コミットは原則として1 `Txx` = 1コミット（複数 `Txx` のまとめコミットは禁止）。
- `Parent` の完了記録は `docs/parent-checklist.md` を更新して残す。
- フック導入: `bash scripts/install-git-hooks.sh`

## Phase 1: 仕様固定

### T01 Realtimeイベント仕様メモ作成
- 目的: 実装時の仕様ブレを防ぐ
- 作業:
  - 送信イベント（`input_audio_buffer.append` など）を列挙
  - 受信イベント（partial/final/error相当）を列挙
  - セッション開始/終了/異常系のシーケンスを記述
- 依存: なし
- DoD:
  - サンプルJSON付きで1ファイルに整理されている
  - 実装者レビューで不明点が残らない

### T02 音声I/O仕様確定
- 目的: Mac録音処理とサーバ入力の整合を固定
- 作業:
  - PCM16 / 16kHz / mono を明文化
  - フレーム長（20ms or 40ms）を仮決定
  - 送信間隔とバッファ上限を定義
- 依存: T01
- DoD:
  - 音声フォーマットと送信粒度が文書化されている
  - 実装に必要な数値パラメータが全て決まっている

## Phase 2: Windowsサーバ起動確認

### T03 WSL2環境セットアップ手順化
- 目的: 再現可能な起動基盤を作る
- 作業:
  - Python/vLLM依存のセットアップ手順作成
  - Python / CUDA / torch / vLLM の採用バージョンを固定
  - モデル取得手順（認証含む）整理
- 成果物:
  - `docs/wsl2-setup.md`
- 依存: T01
- DoD:
  - 初回環境構築が手順通りに完了する
  - バージョン不一致時の確認手順が記録されている

### T04 vLLMサーバ起動スクリプト作成
- 目的: 手動ミスをなくして起動を固定化
- 作業:
  - `vllm serve mistralai/Voxtral-Mini-4B-Realtime-2602` 実行コマンド作成
  - 主要引数（`max-model-len` 等）を外出し設定化
- 成果物:
  - `server/start_vllm.sh`
  - `server/env.example`
  - `server/README.md`
- 依存: T03
- DoD:
  - 1コマンドでサーバ起動できる
  - 起動ログに致命エラーがない

### T05 ローカル疎通テスト作成
- 目的: Realtime APIが正しく応答することを検証
- 作業:
  - 最小クライアントで `/v1/realtime` に接続
  - テスト音声を送り逐次応答を確認
- 成果物:
  - `server/realtime_smoke_client.py`
  - `server/testdata/test_ja_1s.wav`
  - `docs/local-connectivity-test.md`
- 依存: T04
- DoD:
  - partial/final相当の逐次結果を取得できる
  - 成功・失敗の判定条件が記録されている

### T06 LAN越し疎通テスト
- 目的: MacからWindows(WSL2)への接続をLAN越しで確認する
- 作業:
  - T08で固定した採用経路に合わせてネットワーク設定を構成
  - MacからWindowsホストIP経由で `/v1/realtime` に接続確認
  - 遅延の簡易計測
- 成果物:
  - `docs/lan-connectivity-setup.md`
  - `windows-network/setup-portproxy.ps1`
  - `windows-network/setup-firewall-rule.ps1`
- 依存: T05, T08
- DoD:
  - MacからLAN越しで逐次文字起こし結果を受信できる
  - 接続手順が記録されている

### T07 Windows検証クライアント実装（WSL接続用）
- 目的: Mac依存を外して、Windows本体からWSL上サーバへの接続可否を先に確認する
- 作業:
  - Windows本体で動くCLIクライアントを作成
  - 音声入力（WAVファイル入力を最低限）をRealtime APIへ送信
  - partial/final/error表示を実装
- 成果物:
  - `windows-client/realtime_wav_client.py`
  - `windows-client/README.md`
- 依存: T05
- DoD:
  - Windows本体からWSL上 `/v1/realtime` に接続できる
  - 1回以上のpartial/final受信が確認できる

### T08 Windows本体 <-> WSL 接続検証
- 目的: WSLネットワーク設定の妥当性をWindowsクライアントで検証する
- 作業:
  - `localhost` / `WSL IP` / `Windows host IP` の各経路を試験
  - 採用経路を1つに固定
  - 実行手順を記録
- 成果物:
  - `windows-client/route_matrix.py`
  - `docs/windows-route-test-template.md`
- 依存: T07
- DoD:
  - 採用経路で再現性ある接続が確認できる
  - 手順書だけで第三者が再実行できる

## Phase 3: Mac CLIクライアント

### T09 録音モジュール実装
- 目的: 安定した音声フレーム供給
- 作業:
  - マイク入力取得
  - PCM16 / 16kHz / mono 変換
  - フレーム分割（20-40ms）
- 成果物:
  - `client/src/audio_frame.py`
  - `client/src/main.py`（WAV入力モード）
- 依存: T02
- DoD:
  - 連続録音で欠落なくフレーム生成できる

### T10 Realtime送信モジュール実装
- 目的: vLLM仕様準拠の送信処理を作る
- 作業:
  - 音声をbase64化してappendイベント送信
  - commit相当イベントを適切タイミングで送信
- 成果物:
  - `client/src/realtime_client.py`
  - `client/src/main.py`
- 依存: T01, T09
- DoD:
  - サーバ側で受理され、推論が進む

### T11 受信表示モジュール実装
- 目的: partial/finalを安全に扱う
- 作業:
  - partialは上書き表示
  - finalは確定バッファへ追記
  - error受信時の通知
- 成果物:
  - `client/src/transcript_store.py`
  - `client/tests/test_transcript_store.py`
- 依存: T10
- DoD:
  - CLI上で逐次表示が崩れない
  - final確定が正しく分離される

## Phase 4: 貼り付け機能

### T12 Auto Paste機能実装
- 目的: finalのみ貼り付ける安全動作
- 作業:
  - `pbcopy` + `osascript` 連携
  - Auto Pasteトグル（デフォルトOFF）
- 依存: T11
- DoD:
  - partialは貼り付けない
  - finalのみ貼り付ける

### T13 誤貼り付け防止ガード
- 目的: 実運用時の事故を減らす
- 作業:
  - 連続貼り付けレート制限
  - 貼り付け先未フォーカス時の扱い定義
- 依存: T12
- DoD:
  - 想定外連打や暴発が再現しない

## Phase 5: 安定化

### T14 再接続処理実装
- 目的: Wi-Fi瞬断への耐性を持たせる
- 作業:
  - 切断検知
  - バックオフ再接続
  - 再接続中ステータス表示
- 依存: T11
- DoD:
  - 短時間切断から自動復帰できる

### T15 設定チューニング
- 目的: 遅延と精度のバランス最適化
- 作業:
  - `transcription_delay_ms` 初期値 480ms で評価
  - チャンクサイズ比較（20ms/40ms）
- 依存: T14
- DoD:
  - 推奨初期値が1セット決まる

### T16 ログ機能実装
- 目的: 障害解析と評価を可能にする
- 作業:
  - ログON/OFF
  - 接続イベント・遅延・エラーを記録
- 依存: T14
- DoD:
  - トラブル発生時に時系列追跡できる

## Phase 6: 評価と分岐

### T17 連続運用試験（30-60分）
- 目的: 実運用の安定性確認
- 作業:
  - 連続使用して遅延/欠落/OOMを計測
  - VRAM推移を記録
- 依存: T15, T16
- DoD:
  - 評価結果がレポート化されている

### T18 BF16継続/量子化移行の最終判断
- 目的: 次フェーズの方針確定
- 作業:
  - 判定基準に沿って継続 or 移行を決定
  - 移行の場合は量子化検証タスクを起票
- 依存: T17
- DoD:
  - 判断理由が文書化され、次アクションが明確

## すぐ着手する順番（推奨）
1. T01
2. T02
3. T03
4. T04
5. T05
6. T07
7. T08
8. T06
9. T09
10. T10
11. T11
12. T12
13. T13
14. T14
15. T15
16. T16
17. T17
18. T18
