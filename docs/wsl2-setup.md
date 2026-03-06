# WSL2環境セットアップ手順（T03）

## 1. 目的
- Windows + WSL2 上で vLLM Realtime サーバを再現可能に起動できる基盤を作る。
- Python / CUDA / torch / vLLM の採用バージョンを固定し、差分原因を減らす。
- repo が `/mnt/*` 配下でも、vLLM の runtime だけは WSL ext4 側に置いて GPU 起動を安定化する。

## 2. 採用バージョン（固定）
- 日付: `2026-03-07`
- WSL distro: `Ubuntu 22.04 LTS`
- Python: `3.11.x`
- NVIDIA Driver (Windows): `581.57`（R580系）
- CUDA runtime (driver reported): `13.0`
- torch CUDA runtime: `12.8`
- PyTorch: `2.10.0+cu128`
- vLLM: `0.17.0rc1.dev124+g225d1090a`（nightly）
- モデル: `mistralai/Voxtral-Mini-4B-Realtime-2602`
- workspace venv: `<repo>/.venv`（任意。補助ツールや軽い確認用）
- runtime venv: `/tmp/voice2text-vllm-venv311-clean`（vLLM GPU起動用）
- 補足: `vllm 0.8.5` は `torch==2.6.0` / `torchaudio==2.6.0` / `torchvision==0.21.0` を要求するが、Voxtral Realtime の model card は `vllm nightly` を推奨している。
- 補足: `flashinfer -> apache-tvm-ffi -> torch_c_dlpack_ext` のABI不整合を避けるため、起動時は `TVM_FFI_DISABLE_TORCH_C_DLPACK=1` を維持する。

## 3. 互換性確認表

| Component | Fixed Version | 確認コマンド | 合格条件 |
|---|---|---|---|
| WSL2 distro | Ubuntu 22.04 | `cat /etc/os-release` | `VERSION_ID=\"22.04\"` |
| Python | 3.11.x | `python --version` | `Python 3.11.*` |
| NVIDIA + CUDA | Driver 581.57, CUDA 13.0 | `nvidia-smi` | Driver / CUDA Version が一致する |
| runtime venv | `/tmp/voice2text-vllm-venv311-clean` | `ls /tmp/voice2text-vllm-venv311-clean/bin/python` | ファイルが存在する |
| torch | 2.10.0+cu128 | `/tmp/voice2text-vllm-venv311-clean/bin/python -c \"import torch; print(torch.__version__)\"` | `2.10.0+cu128` |
| torch CUDA runtime | 12.8 | `/tmp/voice2text-vllm-venv311-clean/bin/python -c \"import torch; print(torch.version.cuda)\"` | `12.8` |
| torch CUDA可視 | - | `/tmp/voice2text-vllm-venv311-clean/bin/python -c \"import torch; print(torch.cuda.is_available())\"` | `True` |
| vLLM | 0.17.0rc1.dev124+g225d1090a | `/tmp/voice2text-vllm-venv311-clean/bin/python -c \"import vllm; print(vllm.__version__)\"` | `0.17.0rc1.dev124+g225d1090a` |

## 4. 初回セットアップ手順

### 4.1 WSL2ディストリ情報を記録
```bash
wsl -l -v
```
```bash
cat /etc/os-release
uname -r
```

### 4.2 repo用 workspace venv を作成
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential
python3.11 -m venv .venv
source .venv/bin/activate
python --version
pip install --upgrade pip setuptools wheel
```

### 4.3 ext4側の runtime venv を作成
```bash
python3.11 -m venv /tmp/voice2text-vllm-venv311-clean
/tmp/voice2text-vllm-venv311-clean/bin/python -m pip install --upgrade pip setuptools wheel
```

- repo が `/mnt/*` 配下にある場合、vLLM 本体はこの `/tmp` 側 venv で起動する。
- `/mnt/*` 上の `.venv` をそのまま `vllm serve` に使うと、WSL では `p9_client_rpc` 待ちで止まることがある。

### 4.4 runtime venv に nightly vLLM をインストール
```bash
uv pip install --python /tmp/voice2text-vllm-venv311-clean/bin/python -U vllm --extra-index-url https://wheels.vllm.ai/nightly
uv pip install --python /tmp/voice2text-vllm-venv311-clean/bin/python "mistral-common[soundfile]"
```

- Voxtral Realtime では model card 推奨に合わせて nightly を使う。
- `soundfile` が無いと Voxtral の audio dummy input 生成で失敗するため、追加で入れる。
- 既存環境に古い `torch` 系が残っている場合は、新しい runtime venv を作り直してから入れ直す。

### 4.5 runtime venv から CUDA可視を確認
```bash
nvidia-smi
/tmp/voice2text-vllm-venv311-clean/bin/python -c "import torch; print(torch.__version__)"
/tmp/voice2text-vllm-venv311-clean/bin/python -c "import torch; print('cuda_available=', torch.cuda.is_available())"
/tmp/voice2text-vllm-venv311-clean/bin/python -c "import torch; print('gpu=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
/tmp/voice2text-vllm-venv311-clean/bin/python -c "import torch; print('GLIBCXX_USE_CXX11_ABI=', torch._C._GLIBCXX_USE_CXX11_ABI)"
```

- `torch.__version__` は `2.10.0+cu128` を期待値にする。
- `torch.version.cuda` は `12.8` を期待値にする。
- `GLIBCXX_USE_CXX11_ABI` はこの環境では `False` を確認値にする。

### 4.6 Hugging Face 認証
```bash
/tmp/voice2text-vllm-venv311-clean/bin/python -m pip install huggingface_hub
/tmp/voice2text-vllm-venv311-clean/bin/huggingface-cli login
```
- 画面でアクセストークンを入力する。
- トークンは `Read` 権限を付与する。

### 4.7 モデルアクセス確認
```bash
/tmp/voice2text-vllm-venv311-clean/bin/python - <<'PY'
from huggingface_hub import model_info
info = model_info("mistralai/Voxtral-Mini-4B-Realtime-2602")
print(info.id)
PY
```

### 4.8 `server/.env` に安定起動値を入れる
```bash
cp server/env.example server/.env
```

`server/.env` は以下を基準にする。

```dotenv
HOST=0.0.0.0
PORT=8000
MAX_MODEL_LEN=4096
DTYPE=bfloat16
RUNTIME_VENV=/tmp/voice2text-vllm-venv311-clean
LOG_DIR=/tmp/voice2text-vllm-logs
VLLM_EXTRA_ARGS='--enforce-eager --max-num-seqs 1'
TVM_FFI_DISABLE_TORCH_C_DLPACK=1
VLLM_DISABLE_COMPILE_CACHE=1
COMPILATION_CONFIG='{"cudagraph_mode":"PIECEWISE"}'
```

- `server/.env` は git 管理外のローカル設定として扱う。
- モデルが一度 cache 済みなら、`MODEL_ID` は Hugging Face の repo 名よりも `~/.cache/huggingface/hub/.../snapshots/<hash>` のローカル snapshot path を優先すると起動が安定しやすい。

### 4.9 安定起動コマンドでサーバを上げる
```bash
bash server/start_vllm.sh
```

- `server/.env` に `RUNTIME_VENV` を入れてあれば、`.venv` を activate しなくてもよい。
- 起動には数分かかることがある。`Starting vLLM server on http://0.0.0.0:8000` と `Application startup complete` を待つ。

### 4.10 最低限の到達確認
```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/version
ss -ltnp | grep :8000
```

## 5. バージョン不一致時の確認手順
- Python が `3.11.x` でない場合:
  - `python --version` で実行バイナリを確認し、`.venv` 再作成。
- torch が期待値から外れる場合:
  - 依存関係が崩れているため、runtime venv を再作成して nightly の `vllm` から入れ直す。
- `torch.cuda.is_available() == False` の場合:
  - Windows側のGPUドライバ更新、WSL再起動（`wsl --shutdown`）を実施。
- vLLM import 失敗時:
  - `/tmp/voice2text-vllm-venv311-clean/bin/python -c "import sys; print(sys.executable)"` を確認し、runtime venv の取り違えを解消。
- `p9_client_rpc` 待ちで固まる場合:
  - repo が `/mnt/*` 上にあるなら、`RUNTIME_VENV=/tmp/voice2text-vllm-venv311-clean` を使う。
- `undefined symbol: _ZNK3c106Device3strB5cxx11Ev` が出る場合:
  - `flashinfer -> apache-tvm-ffi -> torch_c_dlpack_ext` のABI不整合。
  - `bash server/start_vllm.sh` で起動し、`TVM_FFI_DISABLE_TORCH_C_DLPACK=1` を必ず有効にする。
  - 直接 `vllm serve ...` を叩かない。詳細は `docs/vllm-startup-troubleshooting.md` を参照。
- `AttributeError: 'VoxtralRealtimeConfig' object has no attribute 'vocab_size'` が出る場合:
  - `vllm 0.8.5` では Voxtral Realtime の互換が足りない。
  - nightly の `vllm` に更新し、`bash server/start_vllm.sh` を使う。
- `No module named 'soundfile'` が出る場合:
  - `uv pip install --python /tmp/voice2text-vllm-venv311-clean/bin/python "mistral-common[soundfile]"` を実行する。
- `fatal error: Python.h: No such file or directory` が出る場合:
  - `python3.11-dev` が未導入のまま compile 経路に入っている。まず `--enforce-eager --max-num-seqs 1` の保守起動に戻す。
- `nvcc: command not found` が出る場合:
  - FlashInfer sampler の compile 経路に入っている。CUDA toolkit を入れるか、まずは `--enforce-eager --max-num-seqs 1` で起動確認を優先する。

## 6. 完了チェック（T03 DoD）
- [ ] `/tmp/voice2text-vllm-venv311-clean` を作成し、nightly の `vllm` を import できる
- [ ] 固定バージョンが runtime venv の確認コマンドで一致する
- [ ] `server/.env` に WSL 安定起動値を反映できる
- [ ] `bash server/start_vllm.sh` 実行後に `GET /health` が `200`、`GET /version` が応答する
- [ ] 不一致時の確認手順で切り分けできる

## 7. 記録テンプレート
```text
Date:
Windows Version:
WSL Distro:
Kernel:
Python:
Runtime venv:
NVIDIA Driver:
CUDA Version (nvidia-smi):
torch:
vLLM:
HF Login: done / not done
MODEL_ID:
Health:
Version:
Notes:
```
