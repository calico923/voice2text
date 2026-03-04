# vLLMサーバ起動（T04）

## 1. 前提
- `docs/wsl2-setup.md` のセットアップ完了後に実行する。
- 仮想環境を有効化する。

```bash
cd /path/to/voice2text
source .venv/bin/activate
```

## 2. 事前設定
- 必要に応じて設定ファイルを作成:

```bash
cp server/env.example server/.env
```

- 主な設定値:
  - `MODEL_ID`: 推論モデルID
  - `HOST` / `PORT`: 待受アドレス
  - `MAX_MODEL_LEN`: 初期 `4096`
  - `DTYPE`: 初期 `bfloat16`
  - `VLLM_EXTRA_ARGS`: 追加引数

## 3. 起動
```bash
bash server/start_vllm.sh
```

- 標準出力: `server/logs/vllm-<timestamp>.out.log`
- 標準エラー: `server/logs/vllm-<timestamp>.err.log`

## 4. 最低限の確認
- 起動ログに致命エラーが出ていないこと
- サーバが待受ポートで起動していること（例: `ss -ltnp | grep :8000`）

## 5. 停止
- フォアグラウンド実行中は `Ctrl+C` で停止する。
