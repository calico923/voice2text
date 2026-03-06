# vLLM GPU起動調査レポート（2026-03-07）

## 1. 概要
- 対象: `mistralai/Voxtral-Mini-4B-Realtime-2602`
- 目的: WSL2 上で `vllm` の GPU 起動を安定化し、`/v1/realtime` を有効化する。
- 結論: GPU 起動は成功した。`/health=200`、`/version=0.17.0rc1.dev124+g225d1090a`、`/v1/realtime` 公開を確認済み。
- ただし現時点の安定構成は保守設定であり、性能最適化は次段で行う。

## 2. 最終到達点
- `vllm nightly` を WSL ext4 側の runtime venv で起動できた。
- 実行時の GPU は `NVIDIA GeForce RTX 4070 Ti SUPER`。
- `nvidia-smi` で VRAM 使用量 `15815 MiB / 16376 MiB` を確認した。
- API サーバは `http://0.0.0.0:8000` で起動し、`Supported tasks: ['generate', 'transcription', 'realtime']` を出力した。

## 3. 主な原因整理

### 3.1 旧構成の問題
- `vllm 0.8.5` は `Voxtral Realtime` の実装が不足しており、`Transformers fallback` 後に失敗した。
- `flashinfer -> apache-tvm-ffi -> torch_c_dlpack_ext` で ABI 不整合があり、`undefined symbol: _ZNK3c106Device3strB5cxx11Ev` が発生した。
- repo 配下の `.venv` を `/mnt/f/...` 上でそのまま使うと、WSL の `p9_client_rpc` 待ちで停止した。

### 3.2 WSL で追加で見つかった問題
- `soundfile` 未導入だと Voxtral の audio dummy input 生成で失敗した。
- `python3.11-dev` が無いと Triton 補助モジュール生成で `Python.h` エラーになった。
- `nvcc` が無いと FlashInfer sampler の JIT で失敗した。
- profiling 時の dummy sampler batch が大きいと Triton/FlashInfer のビルド経路に入りやすかった。

## 4. 実際に通った構成

### 4.1 runtime venv
- パス: `/tmp/voice2text-vllm-venv311-clean`
- 理由: `/tmp` は WSL ext4 側で、`/mnt/f` より安定していたため。

### 4.2 実行条件
```bash
RUNTIME_VENV=/tmp/voice2text-vllm-venv311-clean \
LOG_DIR=/tmp/voice2text-vllm-logs \
VLLM_EXTRA_ARGS="--enforce-eager --max-num-seqs 1" \
bash server/start_vllm.sh
```

### 4.3 追加で必要だった依存
```bash
uv pip install --python /tmp/voice2text-vllm-venv311-clean/bin/python "mistral-common[soundfile]"
```

### 4.4 モデル指定
- 安定起動時は Hugging Face の repo 名ではなく、ローカル cache の snapshot path を使った。
- 使用パス:
  - `/home/kkato/.cache/huggingface/hub/models--mistralai--Voxtral-Mini-4B-Realtime-2602/snapshots/96acf48bf44a4e0f31d7a73bfcf256acca9cf878`

## 5. 確認結果

### 5.1 API 確認
- `GET /health` -> `200`
- `GET /version` -> `{"version":"0.17.0rc1.dev124+g225d1090a"}`
- `ss -ltnp` で `0.0.0.0:8000` の LISTEN を確認した。

### 5.2 vLLM ログ上の到達点
- `Available KV cache memory` まで到達
- `GPU KV cache size: 2,848 tokens`
- `Starting vLLM server on http://0.0.0.0:8000`
- `Realtime API router attached`
- `Application startup complete`

### 5.3 2026-03-07 の再検証値
- `server/.env` ベースの再起動で `torch=2.10.0+cu128`、`torch.version.cuda=12.8`、`vllm=0.17.0rc1.dev124+g225d1090a` を確認した。
- `nvidia-smi` は `Driver Version 581.57`、`CUDA Version 13.0` を返した。
- 修正後の `bash server/start_vllm.sh` で `GET /health -> 200`、`GET /version -> {"version":"0.17.0rc1.dev124+g225d1090a"}` を再確認した。

## 6. 今回反映したリポジトリ変更
- `server/start_vllm.sh`
  - `RUNTIME_VENV` 対応
  - runtime venv の `python` / `vllm` 優先
  - `VLLM_EXTRA_ARGS` の子プロセス漏れ防止
  - `COMPILATION_CONFIG` の既定値で余分な `}` が付く不具合を修正
- `server/env.example`
  - WSL 安定起動用の例を追加
- `server/README.md`
  - `/tmp` runtime venv と保守起動構成を追記
- `docs/vllm-startup-troubleshooting.md`
  - 失敗原因と回避条件を拡張

## 7. 制約と残課題
- 現在の起動条件 `--enforce-eager --max-num-seqs 1` は安定性優先で、性能は抑えめ。
- `python3.11-dev` と `nvcc` をまだ入れていないため、compile 系の最適化は未評価。
- `/v1/realtime` ルートは起動済みだが、実音声を使った end-to-end セッション確認はまだ未実施。
- Windows 本体や LAN 越しの再接続系評価もこれから。

## 8. 次の実装計画（2026-03-07更新）

### 1st: 安定起動構成の固定化
- [x] `server/.env` に WSL 用の起動値を正式反映した。
- [x] `/tmp/voice2text-vllm-venv311-clean` の作成手順を `docs/wsl2-setup.md` に統合した。
- [x] `server/start_vllm.sh` の `COMPILATION_CONFIG` 不具合を修正し、`.env` ベースで `GET /health=200` / `GET /version` を再確認した。
- [ ] 実機再起動後も同じ手順で `GET /health=200` になることを再確認する。

### 2nd: 性能モード移行の検証
- [ ] `python3.11-dev` 導入後に `--enforce-eager` なしの起動を再試験する。
- [ ] CUDA toolkit / `nvcc` 導入後に sampler 側の compile 経路を再試験する。
- [ ] `--max-num-seqs 1` を段階的に引き上げ、`max-num-seqs 2 -> 4 -> 8` で起動可否と VRAM を測る。
- [ ] eager 構成と compile 構成で、起動時間・VRAM・初回応答時間を比較する。

### 3rd: 実運用経路の疎通確認
- [ ] `server/realtime_smoke_client.py` で `/v1/realtime` のローカル音声試験を行う。
- [ ] Windows 本体からの接続試験を再実施する。
- [ ] 採用経路で 30分 / 60分 の連続試験に進む。

## 9. 現時点の判断
- 「GPU が使えていない」のではなく、「起動前後の複数障害で GPU サーバが最後まで立ち上がっていなかった」が正しい。
- 現在は GPU サーバそのものは起動済みで、次は安定化から性能最適化へ進める段階に入った。

## 10. 続きで反映した内容
- `server/.env`
  - 起動成功時と同じ local snapshot path を `MODEL_ID` に設定した。
  - `RUNTIME_VENV=/tmp/voice2text-vllm-venv311-clean`、`LOG_DIR=/tmp/voice2text-vllm-logs` を固定した。
  - `VLLM_EXTRA_ARGS='--enforce-eager --max-num-seqs 1'` を既定化した。
- `server/start_vllm.sh`
  - `COMPILATION_CONFIG` の既定値で `{"cudagraph_mode":"PIECEWISE"}}` になる不具合を修正した。
  - 修正後に `.env` ベースで再起動し、`/health` と `/version` の到達を確認した。
- `docs/wsl2-setup.md`
  - `/tmp` runtime venv の作成と nightly `vllm` 導入手順を統合した。
  - `mistral-common[soundfile]` の追加、`server/.env` 初期化、`GET /health` / `GET /version` の確認手順を追記した。
  - 実測値に合わせて `torch=2.10.0+cu128`、`torch.version.cuda=12.8`、`vllm=0.17.0rc1.dev124+g225d1090a` に更新した。
- これにより 1st フェーズで残る作業は「実機再起動後の再現確認」のみになった。
