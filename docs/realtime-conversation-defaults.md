# リアルタイム会話文字起こしの初期値

## 目的
- AI と日常会話する前提で、低遅延と final の安定性のバランスが取れた初期値を固定する。
- Windows 実マイク試験と、その後の本番クライアント実装で同じ判断基準を使う。

## 初期値
- `chunk_ms=20`
- `vad_silence_ms=600`
- `min_utterance_ms=400`
- `max_utterance_ms=6000`
- `pre_roll_ms=200`
- `vad_rms_threshold=700`
- `partial_flush_ms=120`

## 意図
- `20ms`: 音声送信の粒度として遅延と安定性のバランスが良い。
- `600ms` 無音: 会話の切れ目としては短すぎず長すぎない。
- `400ms` 最小発話: 咳払いや瞬間ノイズでの過剰確定を抑える。
- `6000ms` 最大発話: 長い一括 commit による final 不安定化を避ける。
- `200ms` pre-roll: 話し始めの子音欠けを減らす。
- `700` RMS: USB マイクでの初期値。環境次第で `400-1200` の範囲で調整する。
- `120ms` partial flush: UI のみで使う目安。CLI は受信イベントをそのまま表示する。

## 現在の実装との対応
- `client/src/main.py`
  - macOS/Linux の `--mic` でも上記初期値を既定にする
  - `partial` 表示は `120ms` 間隔で更新し、`final` だけを後段入力の候補にする
- `windows-client/realtime_wav_client.py`
  - `--mic` では上記 VAD 初期値を既定にする
  - `--wav` は既存どおり 1 ファイル 1 commit の検証用モード
- `windows-client/route_matrix.py`
  - 経路比較の再現性を優先して、引き続き WAV ベースで固定する

## 運用メモ
- 本番相当の会話試験では `--mic-seconds 30` を起点にする。
- 短い smoke test だけをしたい場合は `--mic-seconds 5` に落とす。
- `15秒` 以上の単一 commit は final が不安定になりやすいので避ける。
- 会話 UX は `partial` を即表示し、`final` だけを AI 応答の入力に渡す前提で考える。
