# Realtimeイベント仕様メモ（T01）

## 1. 目的
- Mac/Windowsクライアント実装で参照する最小仕様を固定する。
- 「接続 -> 音声append -> commit -> partial/final受信」までの流れを一意にする。
- 対象は `vllm 0.17.0rc1.dev124+g225d1090a` の realtime 実装に合わせる。

## 2. 前提
- エンドポイント: `/v1/realtime`
- 送信音声: `PCM16 / 16kHz / mono` を base64 化して送る
- 1イベント1JSONで送受信する

## 3. 送信イベント一覧

| Event Type | 用途 | 必須フィールド | 任意フィールド |
|---|---|---|---|
| `session.update` | 接続セッションのモデル検証 | `type`, `model` | - |
| `input_audio_buffer.append` | 音声フレーム追加 | `type`, `audio` | `event_id` |
| `input_audio_buffer.commit` | 追加済み音声の確定通知 / 生成開始 | `type` | `event_id`, `final` |

### 3.1 送信フィールド定義
- `type`:
  - 文字列。イベント種別。
- `model`:
  - 文字列。`session.update` で送るモデルIDまたはパス。
- `audio`:
  - 文字列。PCM16(16kHz/mono)バイト列をbase64化した値。
- `event_id`:
  - 文字列。クライアント側トレース用の任意ID。現行 vLLM 実装では必須ではない。
- `final`:
  - 真偽値。`true` で音声入力終了を通知する。

## 4. 受信イベント一覧

| Event Type | 用途 | 必須フィールド | 任意フィールド |
|---|---|---|---|
| `session.created` | WebSocket 接続初期化完了 | `type`, `id`, `created` | - |
| `transcription.delta` | partial相当の逐次更新 | `type`, `delta` | - |
| `transcription.done` | final相当の確定テキスト | `type`, `text` | `usage` |
| `error` | 失敗通知 | `type`, `error` | `code` |

### 4.1 受信フィールド定義
- `delta`:
  - 文字列。partial表示に使う暫定テキスト。
- `text`:
  - 文字列。確定テキスト。貼り付け対象はこの値のみ。
- `error`:
  - 文字列。エラーメッセージ。
- `code`:
  - 文字列。エラー種別。

## 5. 正常系シーケンス
1. クライアントが `/v1/realtime` へ接続する。
2. サーバから `session.created` を受信する。
3. クライアントが `session.update` を送信する。
4. 音声フレームごとに `input_audio_buffer.append` を送信する。
5. 生成開始のため `input_audio_buffer.commit` を送信する。
6. 音声終了を示すため `input_audio_buffer.commit` with `final=true` を送信する。
7. サーバから `transcription.delta` が複数回返る。
8. サーバから `transcription.done` が返る。
9. クライアントは `delta` を追記表示し、`done.text` を final 履歴へ追記する。

## 6. 異常系シーケンス
1. 接続中に `error` を受信した場合、内容を表示してセッション継続可否を判定する。
2. WebSocket `close` またはネットワーク切断時は再接続制御へ移行する。
3. 再接続成功後は未確定partialを破棄し、新規セグメントとして再開する。
4. `model_not_validated` を受けた場合は `session.update` が欠けている。

## 7. 送信サンプルJSON

### 7.1 session.update
```json
{
  "type": "session.update",
  "model": "mistralai/Voxtral-Mini-4B-Realtime-2602"
}
```

### 7.2 append
```json
{
  "type": "input_audio_buffer.append",
  "event_id": "evt-0001",
  "audio": "AAABAAIAAwAE..."
}
```

### 7.3 commit
```json
{
  "type": "input_audio_buffer.commit"
}
```

### 7.4 commit final
```json
{
  "type": "input_audio_buffer.commit",
  "final": true
}
```

## 8. 受信サンプルJSON

### 8.1 session.created
```json
{
  "type": "session.created",
  "id": "sess-1234",
  "created": 1772835927
}
```

### 8.2 partial（delta）
```json
{
  "type": "transcription.delta",
  "delta": "おは"
}
```

### 8.3 final（done）
```json
{
  "type": "transcription.done",
  "text": "おはようございます。",
  "usage": {
    "prompt_tokens": 39,
    "completion_tokens": 12,
    "total_tokens": 51
  }
}
```

### 8.4 error
```json
{
  "type": "error",
  "error": "Model not validated. Make sure to validate the model by sending a session.update event.",
  "code": "model_not_validated"
}
```

## 9. 実装上の固定ルール（MVP）
- 接続後すぐに `session.update` を送る。
- partial表示ソースは `transcription.delta` のみを採用する。
- final確定ソースは `transcription.done.text` のみを採用する。
- Auto Paste対象はfinalのみとし、partialは絶対に貼り付けない。
- `error` 受信時はログ保存 + CLI表示を必須にする。
- T05 以降の実接続試験では、tone WAV ではなく spoken WAV を使う。
