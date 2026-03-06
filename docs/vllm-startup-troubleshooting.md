# vLLM起動失敗トラブルシュート

## 1. 対象事象
- 発生日: `2026-03-06`
- 対象モデル: `mistralai/Voxtral-Mini-4B-Realtime-2602`
- 代表エラー:

```text
OSError: .../torch_c_dlpack_ext/libtorch_c_dlpack_addon_torch26-cuda.so:
undefined symbol: _ZNK3c106Device3strB5cxx11Ev
```

- 併発しやすいログ:
  - `` `torch_dtype` is deprecated! Use `dtype` instead! ``
  - `RuntimeError: Engine core initialization failed. See root cause above.`
  - `AttributeError: 'VoxtralRealtimeConfig' object has no attribute 'vocab_size'`
  - `ImportError: \`soundfile\` is not installed.`
  - `fatal error: Python.h: No such file or directory`
  - `RuntimeError: Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't exist`

## 2. 結論
- 根本原因は `flashinfer -> apache-tvm-ffi -> torch_c_dlpack_ext` のネイティブ拡張が、現在の `torch 2.6.0+cu124` と ABI 整合していないこと。
- このプロジェクトでは `torch_c_dlpack_ext` は必須ではないため、`TVM_FFI_DISABLE_TORCH_C_DLPACK=1` で無効化して起動する。
- 安全な起動経路は `bash server/start_vllm.sh`。直接 `vllm serve ...` を叩かない。
- その後の追加調査で、`vllm 0.8.5` は `mistralai/Voxtral-Mini-4B-Realtime-2602` を正しくロードできず、モデルカードどおり `vllm nightly` が必要なことを確認した。
- さらに WSL では、repo を `/mnt/*` 上に置いた `.venv` から起動すると `p9_client_rpc` 待ちで止まりやすい。runtime venv は `/tmp` か `~/...` の ext4 側に置く。
- `mistral-common[soundfile]` が無いと Voxtral の audio dummy input 生成で落ちる。
- `python3.11-dev` や CUDA toolkit (`nvcc`) が無い環境では、`VLLM_EXTRA_ARGS="--enforce-eager --max-num-seqs 1"` を付けて Triton / FlashInfer のビルド経路を避けるのが最短。

## 3. ローカル調査で確認した事実

### 3.1 実際の依存関係
- `torch==2.6.0+cu124`
- `vllm==0.8.5`
- `flashinfer-python==0.6.4`
- `apache-tvm-ffi==0.1.9`
- `torch_c_dlpack_ext==0.1.5`

### 3.2 vLLM 0.8.5 の要求
- ローカルの `vllm-0.8.5.dist-info/METADATA` では以下を要求している。
  - `torch==2.6.0`
  - `torchaudio==2.6.0`
  - `torchvision==0.21.0`
  - `xformers==0.0.29.post2`

つまり、既存の `torch 2.5.1` 前提ドキュメントは現状と合っていない。

### 3.2.1 Voxtral Realtime との互換性
- ローカルログでは、`vllm 0.8.5` が `VoxtralRealtimeForConditionalGeneration` に対して vLLM 実装を持たず、Transformers fallback に落ちている。
- その直後に `AttributeError: 'VoxtralRealtimeConfig' object has no attribute 'vocab_size'` でモデルロードが失敗する。
- Hugging Face のモデルカードでも `vllm (recommended)` / `transformers (WIP)` とされ、`vllm nightly` の利用が案内されている。

### 3.2.2 WSL / runtime 環境の追加要件
- `/mnt/f/Code/voice2text/.venv` 上の `vllm serve` は、実 GPU では `p9_client_rpc` 待ちで停止した。
- `/tmp/voice2text-vllm-venv311-clean` 上の nightly venv では、同じモデルが GPU にロードされ `Starting vLLM server on http://0.0.0.0:8000` まで到達した。
- その時点の `nvidia-smi` では RTX 4070 Ti SUPER の VRAM 使用量が `15815 MiB / 16376 MiB` だった。
- ただし追加依存の不足があると、次の順で失敗した:
  - `soundfile` 未導入: Voxtral の audio dummy input 生成で失敗
  - `python3.11-dev` 未導入: Triton sampler が `Python.h` で失敗
  - `nvcc` 未導入: FlashInfer sampler が CUDA toolkit を見つけられず失敗
- `--max-num-seqs 1` に下げると dummy sampler batch が小さくなり、Triton sampler 経路を避けて起動できた。

### 3.3 何が壊れているか
- `torch._C._GLIBCXX_USE_CXX11_ABI` は `False`
- `torch_c_dlpack_ext` が要求している未解決シンボル:

```text
_ZNK3c106Device3strB5cxx11Ev
```

- 現在の `torch/lib/libc10.so` が実際に公開しているシンボル:

```text
_ZNK3c106Device3strEv
```

この差分は `torch_c_dlpack_ext` 側が期待している C++ ABI と、実際の `torch` ホイールの ABI が一致していないことを示す。

## 4. 再現と切り分け

### 4.1 失敗する最小再現
```bash
source .venv/bin/activate
TVM_FFI_DISABLE_TORCH_C_DLPACK=0 python - <<'PY'
import tvm_ffi
print("unexpected: import succeeded")
PY
```

- 期待結果: `undefined symbol: _ZNK3c106Device3strB5cxx11Ev` で失敗する。

### 4.2 回避できることの確認
```bash
source .venv/bin/activate
TVM_FFI_DISABLE_TORCH_C_DLPACK=1 python - <<'PY'
import tvm_ffi
print("tvm_ffi import: OK")
PY
```

- 期待結果: `tvm_ffi import: OK`

## 5. このリポジトリでの推奨対処

### 5.0 前提バージョン
- `mistralai/Voxtral-Mini-4B-Realtime-2602` を使う場合、`vllm 0.8.5` ではなく `vllm nightly` を使う。
- 参考:
  - https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602
  - https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html

### 5.1 起動方法
```bash
source .venv/bin/activate
bash server/start_vllm.sh
```

- `server/start_vllm.sh` は既定で `TVM_FFI_DISABLE_TORCH_C_DLPACK=1` を export する。
- `server/env.example` でも同値を既定化している。

### 5.2 WSL の安定起動設定
```bash
RUNTIME_VENV=/tmp/voice2text-vllm-venv311-clean \
LOG_DIR=/tmp/voice2text-vllm-logs \
VLLM_EXTRA_ARGS="--enforce-eager --max-num-seqs 1" \
bash server/start_vllm.sh
```

- `RUNTIME_VENV` は ext4 側の venv を指す。`/mnt/*` 上の `.venv` を直接使わない。
- `--enforce-eager` は `torch.compile` / CUDAGraph を止める。
- `--max-num-seqs 1` は profiling の dummy sampler batch を小さくし、Triton sampler の JIT を避ける。
- これで throughput は保守的になるが、`python3.11-dev` と `nvcc` を入れずに起動確認できる。

### 5.3 音声依存
```bash
uv pip install --python /tmp/voice2text-vllm-venv311-clean/bin/python "mistral-common[soundfile]"
```

- `soundfile` が無いと Voxtral の audio dummy input 生成で失敗する。

### 5.4 直接起動する必要がある場合
```bash
source .venv/bin/activate
export TVM_FFI_DISABLE_TORCH_C_DLPACK=1
vllm serve mistralai/Voxtral-Mini-4B-Realtime-2602 --dtype bfloat16 --host 0.0.0.0 --port 8000 --max-model-len 4096
```

- `torch_dtype` ではなく `dtype` を使う。
- `TVM_FFI_DISABLE_TORCH_C_DLPACK=1` を付け忘れると、同じ ABI エラーに戻る。
- WSL では追加で `--enforce-eager --max-num-seqs 1` を付ける方が安全。

## 6. 恒久対応の考え方
- 現時点では「`torch_c_dlpack_ext` を使わない」が最も安全。
- `torch_c_dlpack_ext` の高速経路が本当に必要になるまで、既定値は `TVM_FFI_DISABLE_TORCH_C_DLPACK=1` のまま維持する。
- 将来この値を `0` に戻す条件は次の両方を満たしたときだけ:
  - 同じ `.venv` 上で `TVM_FFI_DISABLE_TORCH_C_DLPACK=0 python -c "import tvm_ffi"` が成功する
  - `bash server/start_vllm.sh` で `torch_c_dlpack_ext` 起因の起動失敗が再発しない

## 7. 注意点
- `pip check` が成功していても、この種の ABI 不整合は検出できない。
- `torch_dtype` 警告は今回の根本原因ではない。ただし、現行スクリプト外の起動経路を使っている兆候ではある。
- 既存環境が崩れている場合は、部分アップグレードより `.venv` 再作成の方が安全。
