# Windows推論サーバー + Mac入力クライアント方針（改訂）

## 結論（先に）
- 方向性は正しい。Mac軽量化の目的に合っている。
- ただし初期構成は `WSL2 + vLLM + 公式BF16` を第一候補に固定する。
- 量子化（GGUF/コミュニティ実装）は「BF16で問題が出た時の第2段階」に回す。

## 目的
- Macのメモリ負荷を下げるため、推論本体はWindows PCで実行する。
- Macはマイク入力とUIのみ担当し、LAN内ストリーミングで文字起こし結果を受け取る。
- ローカル運用を維持しつつ、必要に応じて省メモリ化を行う。

## 前提スペック（今回）
- Windows: `RTX 4070 Ti SUPER (VRAM 16GB)`
- モデル: `mistralai/Voxtral-Mini-4B-Realtime-2602`（BF16）
- VRAM見積もり:
  - モデル本体（BF16, 4B）: 約8GB
  - KVキャッシュ・ランタイム: 残り約8GBで運用
  - 長時間運用時の余裕は T14 で実測して判断する
- 補足:
  - vLLMはWindowsネイティブ非対応のため、WindowsではWSL2前提。
  - 公式モデルカードでは 16GB GPU 1枚での実行が案内されている。

## 構成
1. Macクライアント
   - マイク入力
   - WebSocket送信
   - 受信した逐次結果を表示し、確定結果のみ貼り付け

2. Windowsサーバー（WSL2）
   - `vllm serve` で `/v1/realtime` を提供
   - セッションごとに逐次文字起こしを返却
   - LAN内クライアントのみ許可

## 実行方式
1. 推奨初期（本線）
- `WSL2 + vLLM + 公式BF16`
- 理由: 公式で realtime 運用が明示され、検証コストが最小

2. 代替（第2段階）
- 量子化モデルまたはコミュニティ実装
- 理由: VRAM削減は期待できるが、精度・安定性・実装差分の再検証が必要

## vLLM運用で先にやる省メモリ調整
1. `--max-model-len` を用途に合わせて縮小（推奨初期値: `4096`）
   - リアルタイム文字起こし用途では長コンテキストは不要。
   - 長時間会議が不要なら、既定値より下げてメモリ確保を優先する。

2. `transcription_delay_ms` はまず 480ms
- 低遅延と精度のバランスが取りやすい初期値。

3. 負荷計測
- 連続30-60分でVRAM推移、遅延、欠落率を記録する。

## プロトコル注意（重要）
- vLLMのRealtime APIは「独自のJSONイベント」を使う。
- 音声は「base64化したPCM16 16kHz mono」を `input_audio_buffer.append` で送る。
- つまり、素のバイナリPCMをそのまま送る独自WebSocket仕様とは互換がない。
- Mac側は最初から vLLM Realtimeイベント仕様に合わせる。

## WSL2ネットワーク設定
- WSL2はデフォルトでNATモードのため、MacからWSL2内サーバに直接到達できない場合がある。
- 対処方法（いずれかを選択）:
  - `netsh interface portproxy` でホスト側ポートをWSL2へ転送
  - WSL2の `networkingMode=mirrored`（Windows 11 22H2以降）を有効化
- 選択した方式を起動手順書（T04）に含める。

## セキュリティ最低ライン
- 外部公開しない（ルータのポート開放なし）
- Firewallで送信元をMacのIPに限定
- 認証なしで運用する場合はLAN限定を厳守

## 段階的手順（実行順）
1. WSL2上で `vllm serve mistralai/Voxtral-Mini-4B-Realtime-2602` を起動
2. ローカル（Windows/WSL内）で `/v1/realtime` 接続確認
3. MacクライアントをvLLM Realtimeイベント仕様で実装
4. LAN越し接続確認
5. VRAM・遅延・安定性を計測して本番設定を固定
6. 問題が出た時のみ量子化ルートを検証

## BF16継続 or 量子化移行の判断基準
- BF16継続:
  - OOMなし
  - 体感遅延が 0.3〜0.8秒以内
  - 30〜60分の連続運用で安定
- 量子化移行:
  - OOMまたは体感遅延が 0.8秒超
  - 他アプリ併用時に不安定
  - 長時間運用でVRAM空き容量が 2GB未満に低下

## 参照
- 公式モデル: https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602
- vLLM Realtime API: https://docs.vllm.ai/en/latest/serving/openai_compatible_server/#realtime-api
- vLLM GPUインストール要件: https://docs.vllm.ai/en/latest/getting_started/installation/gpu/
- vLLM量子化: https://docs.vllm.ai/en/latest/features/quantization/
