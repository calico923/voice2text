# リアルタイム音声入力方針（Mac軽量 + Windows推論）

## 背景
- 旧案の「Mac上で Voxtral Mini 4B Realtime / MLX 実行」は、メモリ不足で継続困難。
- 要件は「Macで話す -> Windowsで変換 -> Macへ戻して入力」。
- 自宅LAN内利用のため、通信遅延は小さい前提でサーバ集中方式が有効。

## 新しい目的
- Macは音声取得と表示/貼り付けだけを担当し、低メモリで安定稼働させる。
- 推論負荷はWindowsに集約する。
- まずは最短で「話す -> 文字になる -> 任意アプリへ貼り付ける」を実現する。

## システム構成
1. Macクライアント
- マイク音声を取得してWebSocketでWindowsへ送信（16kHz, mono, PCM16）。
- サーバから受けた `partial` / `final` テキストを表示。
- `final` のみ貼り付け対象へ送信（`pbcopy` + `osascript`）。

2. Windowsサーバ
- `FastAPI + WebSocket` で音声ストリームを受信。
- VAD（無音検知）で発話区間を切って逐次認識。
- STTエンジンは `faster-whisper` を第一候補とする。

3. モデル方針（Windows）
- 低遅延優先: `small` / `medium`。
- 精度優先: `large-v3` 系（GPU余力がある場合）。
- PoC段階ではまず `small` で動作と遅延を確認し、段階的に上げる。

## 通信仕様（最小）
- Mac -> Windows: バイナリ音声フレーム（20-40ms単位）。
- Windows -> Mac: JSONイベント。
  - `{"type":"partial","text":"..."}`
  - `{"type":"final","text":"...","segment_id":123}`
  - `{"type":"error","message":"..."}`

## マイルストーン
### M1: Windows単体PoC
- WebSocket受信とSTT推論をCLIで確認。
- マイク入力wavで `partial/final` 出力確認。

### M2: Mac送信CLI
- Macマイク音声をリアルタイム送信。
- 返却テキストをターミナル表示。

### M3: 最小アプリ化
- Start/Stop/Clear。
- `partial` 表示と `final` バッファ管理。
- Auto Pasteトグル（既定OFF）。

### M4: 実用化
- 無音閾値とチャンクサイズ調整。
- 再接続処理（Wi-Fi瞬断対策）。
- 誤認識置換辞書、ログ保存ON/OFF。

## 性能目標
- 体感遅延: 0.3-0.8秒以内。
- 部分結果は継続的に更新し、最終確定で置換する。
- Mac側メモリ利用は軽量クライアント相当（推論モデル非搭載）。

## リスクと対策
- リスク: ノイズで誤認識増加
  - 対策: VAD閾値、入力ゲイン、ノイズ抑制の調整
- リスク: 部分結果の誤貼り付け
  - 対策: `final` のみ貼り付け対象
- リスク: LAN切断時の停止
  - 対策: 自動再接続と接続状態表示

## 次の作業
1. Windows推論サーバ（最小）を作る
2. Mac送信CLIを作る
3. `partial/final` 往復の遅延を計測する
4. 最小GUIとAuto Pasteを追加する
