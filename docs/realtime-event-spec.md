# Realtimeイベント仕様メモ（T01）

## 1. 目的
- Mac/Windowsクライアント実装で参照する最小仕様を固定する。
- 「接続 -> 音声append -> commit -> partial/final受信」までの流れを一意にする。

## 2. 前提
- エンドポイント: `/v1/realtime`
- 送信音声: `PCM16 / 16kHz / mono` を base64 化して送る
- 1イベント1JSONで送受信する

## 3. 送信イベント一覧

| Event Type | 用途 | 必須フィールド | 任意フィールド |
|---|---|---|---|
| `input_audio_buffer.append` | 音声フレーム追加 | `type`, `audio` | `event_id` |
| `input_audio_buffer.commit` | 追加済み音声の確定通知 | `type` | `event_id` |
| `response.create` | 応答生成要求 | `type` | `event_id`, `response` |

### 3.1 送信フィールド定義
- `type`:
  - 文字列。イベント種別。
- `audio`:
  - 文字列。PCM16(16kHz/mono)バイト列をbase64化した値。
- `event_id`:
  - 文字列。クライアント側トレース用の任意ID。
- `response`:
  - オブジェクト。応答形式/指示を指定する拡張領域（MVPでは省略可）。

## 4. 受信イベント一覧

| Event Type | 用途 | 必須フィールド | 任意フィールド |
|---|---|---|---|
| `response.output_text.delta` | partial相当の逐次更新 | `type`, `delta` | `response_id`, `segment_id` |
| `response.output_text.done` | final相当の確定テキスト | `type`, `text` | `response_id`, `segment_id` |
| `error` | 失敗通知 | `type`, `error` | `event_id` |

### 4.1 受信フィールド定義
- `delta`:
  - 文字列。partial表示に使う暫定テキスト。
- `text`:
  - 文字列。確定テキスト。貼り付け対象はこの値のみ。
- `response_id`:
  - 文字列。応答単位のID。
- `segment_id`:
  - 文字列または数値。重複final抑止に利用。
- `error`:
  - オブジェクト。`code` と `message` を最低限含む。

## 5. 正常系シーケンス
1. クライアントが `/v1/realtime` へ接続する。
2. 音声フレームごとに `input_audio_buffer.append` を送信する。
3. 発話区切りで `input_audio_buffer.commit` を送信する。
4. 必要に応じて `response.create` を送信する。
5. サーバから `response.output_text.delta` が複数回返る。
6. サーバから `response.output_text.done` が返る。
7. クライアントは `delta` を上書き表示し、`done.text` をfinal履歴へ追記する。

## 6. 異常系シーケンス
1. 接続中に `error` を受信した場合、内容を表示してセッション継続可否を判定する。
2. WebSocket `close` またはネットワーク切断時は再接続制御へ移行する。
3. 再接続成功後は未確定partialを破棄し、新規セグメントとして再開する。

## 7. 送信サンプルJSON

### 7.1 append
```json
{
  "type": "input_audio_buffer.append",
  "event_id": "evt-0001",
  "audio": "AAABAAIAAwAE..."
}
```

### 7.2 commit
```json
{
  "type": "input_audio_buffer.commit",
  "event_id": "evt-0002"
}
```

### 7.3 response.create（任意）
```json
{
  "type": "response.create",
  "event_id": "evt-0003",
  "response": {
    "instructions": "Transcribe Japanese speech."
  }
}
```

## 8. 受信サンプルJSON

### 8.1 partial（delta）
```json
{
  "type": "response.output_text.delta",
  "response_id": "resp-0001",
  "segment_id": "seg-01",
  "delta": "おは"
}
```

### 8.2 final（done）
```json
{
  "type": "response.output_text.done",
  "response_id": "resp-0001",
  "segment_id": "seg-01",
  "text": "おはようございます。"
}
```

### 8.3 error
```json
{
  "type": "error",
  "event_id": "evt-0002",
  "error": {
    "code": "invalid_audio",
    "message": "Unsupported sample rate."
  }
}
```

## 9. 実装上の固定ルール（MVP）
- partial表示ソースは `response.output_text.delta` のみを採用する。
- final確定ソースは `response.output_text.done.text` のみを採用する。
- Auto Paste対象はfinalのみとし、partialは絶対に貼り付けない。
- `error` 受信時はログ保存 + CLI表示を必須にする。
