# vLLMサーバ起動（T04）

## 1. 前提
- `docs/wsl2-setup.md` のセットアップ完了後に実行する。
- 実行時の Python は `.venv` を使うか、`RUNTIME_VENV` で別の runtime venv を指定する。

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
  - `RUNTIME_VENV`: 起動時に優先する runtime venv
  - `LOG_DIR`: ログ出力先
  - `VLLM_EXTRA_ARGS`: 追加引数
  - `TVM_FFI_DISABLE_TORCH_C_DLPACK`: 初期 `1`。`torch_c_dlpack_ext` のABI不整合を回避する安全設定。
  - `VLLM_DISABLE_COMPILE_CACHE`: 初期 `1`
  - `COMPILATION_CONFIG`: 初期 `{"cudagraph_mode":"PIECEWISE"}`

## 3. 起動
```bash
source .venv/bin/activate
bash server/start_vllm.sh
```

- WSL で repo が `/mnt/*` 配下にある場合の推奨起動:

```bash
RUNTIME_VENV=/tmp/voice2text-vllm-venv311-clean \
LOG_DIR=/tmp/voice2text-vllm-logs \
VLLM_EXTRA_ARGS="--enforce-eager --max-num-seqs 1" \
bash server/start_vllm.sh
```

- 標準出力: 既定では `server/logs/vllm-<timestamp>.out.log`
- 標準エラー: 既定では `server/logs/vllm-<timestamp>.err.log`
- 直接 `vllm serve ...` を叩かず、このスクリプトを使う。`TVM_FFI_DISABLE_TORCH_C_DLPACK=1` と nightly 推奨フラグを自動で有効化するため。
- GPU利用可否は仮想環境の有無ではなく、WSL上の `torch.cuda.is_available()` で決まる。
- `RUNTIME_VENV` を指定すると、その venv の `python` / `vllm` を優先して使う。`.venv` を activate しなくてもよい。
- `COMPILATION_CONFIG` と `VLLM_DISABLE_COMPILE_CACHE` は Voxtral の model card で案内されている nightly 向け推奨値を既定化している。
- `VLLM_EXTRA_ARGS="--enforce-eager --max-num-seqs 1"` は WSL 上で `python3.11-dev` や `nvcc` が無い環境向けの保守的な起動設定。まずはこれで起動確認し、後で throughput を詰める。
- モデルが既にローカル cache にある場合は、`MODEL_ID` に `~/.cache/huggingface/hub/.../snapshots/<hash>` を指定すると HF への追加問い合わせを減らせる。

## 4. 最低限の確認
- 起動ログに致命エラーが出ていないこと
- 起動前の事前チェックで `cuda_available=True` と GPU名が表示されること
- サーバが待受ポートで起動していること（例: `ss -ltnp | grep :8000`）
- `GET /health` が `200` を返すこと
- `GET /version` が nightly 版の `vllm` バージョンを返すこと

## 5. トラブルシュート
- `undefined symbol: _ZNK3c106Device3strB5cxx11Ev` が出る場合:
  - `torch_c_dlpack_ext` のABI不整合。`docs/vllm-startup-troubleshooting.md` を参照。
- `` `torch_dtype` is deprecated! Use `dtype` instead! `` が出る場合:
  - 現行の `server/start_vllm.sh` は `--dtype` を使うため、別の起動経路を使っている可能性が高い。

## 6. 停止
- フォアグラウンド実行中は `Ctrl+C` で停止する。
