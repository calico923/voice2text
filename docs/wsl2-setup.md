# WSL2環境セットアップ手順（T03）

## 1. 目的
- Windows + WSL2 上で vLLM Realtime サーバを再現可能に起動できる基盤を作る。
- Python / CUDA / torch / vLLM の採用バージョンを固定し、差分原因を減らす。

## 2. 採用バージョン（固定）
- 日付: `2026-03-04`
- WSL distro: `Ubuntu 22.04 LTS`
- Python: `3.11.x`
- NVIDIA Driver (Windows): `R550` 以上
- CUDA runtime (driver reported): `12.4` 系
- PyTorch: `2.5.1+cu124`
- vLLM: `0.8.5`
- モデル: `mistralai/Voxtral-Mini-4B-Realtime-2602`

## 3. 互換性確認表

| Component | Fixed Version | 確認コマンド | 合格条件 |
|---|---|---|---|
| WSL2 distro | Ubuntu 22.04 | `cat /etc/os-release` | `VERSION_ID=\"22.04\"` |
| Python | 3.11.x | `python --version` | `Python 3.11.*` |
| NVIDIA + CUDA | Driver R550+, CUDA 12.4系 | `nvidia-smi` | GPU名表示 + CUDA Versionが12.4以上 |
| torch | 2.5.1+cu124 | `python -c \"import torch; print(torch.__version__)\"` | `2.5.1+cu124` |
| torch CUDA可視 | - | `python -c \"import torch; print(torch.cuda.is_available())\"` | `True` |
| vLLM | 0.8.5 | `python -c \"import vllm; print(vllm.__version__)\"` | `0.8.5` |

## 4. 初回セットアップ手順

### 4.1 WSL2ディストリ情報を記録
```bash
wsl -l -v
```
```bash
cat /etc/os-release
uname -r
```

### 4.2 Python環境を作成
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential
python3.11 -m venv .venv
source .venv/bin/activate
python --version
pip install --upgrade pip setuptools wheel
```

### 4.3 torch / vLLM をインストール
```bash
pip install --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1+cu124
pip install vllm==0.8.5
```

### 4.4 CUDA可視を確認
```bash
nvidia-smi
python -c "import torch; print(torch.__version__)"
python -c "import torch; print('cuda_available=', torch.cuda.is_available())"
python -c "import torch; print('gpu=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

### 4.5 Hugging Face 認証
```bash
pip install huggingface_hub
huggingface-cli login
```
- 画面でアクセストークンを入力する。
- トークンは `Read` 権限を付与する。

### 4.6 モデルアクセス確認
```bash
python - <<'PY'
from huggingface_hub import model_info
info = model_info("mistralai/Voxtral-Mini-4B-Realtime-2602")
print(info.id)
PY
```

## 5. バージョン不一致時の確認手順
- Python が `3.11.x` でない場合:
  - `python --version` で実行バイナリを確認し、`.venv` 再作成。
- torch が `+cu124` でない場合:
  - `pip uninstall -y torch` 後、`--index-url` を指定して再インストール。
- `torch.cuda.is_available() == False` の場合:
  - Windows側のGPUドライバ更新、WSL再起動（`wsl --shutdown`）を実施。
- vLLM import 失敗時:
  - `pip show vllm` と `python -c "import sys; print(sys.executable)"` を確認し、仮想環境の取り違えを解消。

## 6. 完了チェック（T03 DoD）
- [ ] 初回セットアップ手順で環境構築できる
- [ ] 固定バージョンがすべて確認コマンドで一致する
- [ ] 不一致時の確認手順で切り分けできる

## 7. 記録テンプレート
```text
Date:
Windows Version:
WSL Distro:
Kernel:
Python:
NVIDIA Driver:
CUDA Version (nvidia-smi):
torch:
vLLM:
HF Login: done / not done
Notes:
```
