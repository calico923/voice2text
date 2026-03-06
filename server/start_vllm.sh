#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
LOG_DIR_DEFAULT="${SCRIPT_DIR}/logs"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

RUNTIME_VENV="${RUNTIME_VENV:-}"
if [[ -n "${RUNTIME_VENV}" ]]; then
  if [[ ! -x "${RUNTIME_VENV}/bin/python" || ! -x "${RUNTIME_VENV}/bin/vllm" ]]; then
    echo "[start_vllm] ERROR: RUNTIME_VENV must contain bin/python and bin/vllm: ${RUNTIME_VENV}" >&2
    exit 1
  fi
  export VIRTUAL_ENV="${RUNTIME_VENV}"
  export PATH="${RUNTIME_VENV}/bin:${PATH}"
fi

MODEL_ID="${MODEL_ID:-mistralai/Voxtral-Mini-4B-Realtime-2602}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
DTYPE="${DTYPE:-bfloat16}"
LOG_DIR="${LOG_DIR:-${LOG_DIR_DEFAULT}}"
TVM_FFI_DISABLE_TORCH_C_DLPACK="${TVM_FFI_DISABLE_TORCH_C_DLPACK:-1}"
VLLM_DISABLE_COMPILE_CACHE="${VLLM_DISABLE_COMPILE_CACHE:-1}"
DEFAULT_COMPILATION_CONFIG='{"cudagraph_mode":"PIECEWISE"}'
COMPILATION_CONFIG="${COMPILATION_CONFIG:-$DEFAULT_COMPILATION_CONFIG}"
PYTHON_BIN="${PYTHON_BIN:-python}"
VLLM_BIN="${VLLM_BIN:-vllm}"

export TVM_FFI_DISABLE_TORCH_C_DLPACK
export VLLM_DISABLE_COMPILE_CACHE

mkdir -p "${LOG_DIR}"
timestamp="$(date +"%Y%m%d-%H%M%S")"
stdout_log="${LOG_DIR}/vllm-${timestamp}.out.log"
stderr_log="${LOG_DIR}/vllm-${timestamp}.err.log"

cmd=(
  "${VLLM_BIN}"
  serve
  "${MODEL_ID}"
  --host "${HOST}"
  --port "${PORT}"
  --max-model-len "${MAX_MODEL_LEN}"
  --dtype "${DTYPE}"
  --compilation_config "${COMPILATION_CONFIG}"
)

if [[ -n "${VLLM_EXTRA_ARGS:-}" ]]; then
  # VLLM_EXTRA_ARGS='--gpu-memory-utilization 0.9 --max-num-seqs 8'
  read -r -a extra_args <<<"${VLLM_EXTRA_ARGS}"
  cmd+=("${extra_args[@]}")
fi
unset VLLM_EXTRA_ARGS

echo "[start_vllm] MODEL_ID=${MODEL_ID}"
echo "[start_vllm] HOST=${HOST} PORT=${PORT} MAX_MODEL_LEN=${MAX_MODEL_LEN} DTYPE=${DTYPE}"
echo "[start_vllm] TVM_FFI_DISABLE_TORCH_C_DLPACK=${TVM_FFI_DISABLE_TORCH_C_DLPACK}"
echo "[start_vllm] VLLM_DISABLE_COMPILE_CACHE=${VLLM_DISABLE_COMPILE_CACHE}"
echo "[start_vllm] COMPILATION_CONFIG=${COMPILATION_CONFIG}"
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  echo "[start_vllm] VIRTUAL_ENV=${VIRTUAL_ENV}"
else
  echo "[start_vllm] WARN: no active virtualenv detected; activate a venv or set RUNTIME_VENV." >&2
fi
echo "[start_vllm] stdout=${stdout_log}"
echo "[start_vllm] stderr=${stderr_log}"
echo "[start_vllm] cmd=${cmd[*]}"

if ! "${PYTHON_BIN}" - <<'PY'
import sys

import torch

print(
    f"[start_vllm] torch={torch.__version__} "
    f"cuda_available={torch.cuda.is_available()} "
    f"cuda_version={torch.version.cuda}"
)
if not torch.cuda.is_available():
    sys.exit(1)

print(f"[start_vllm] gpu={torch.cuda.get_device_name(0)} count={torch.cuda.device_count()}")
PY
then
  echo "[start_vllm] ERROR: CUDA/GPU is not visible from the current Python environment." >&2
  echo "[start_vllm] ERROR: Verify 'nvidia-smi' in WSL and 'python -c \"import torch; print(torch.cuda.is_available())\"' in the active runtime venv." >&2
  exit 1
fi

"${cmd[@]}" > >(tee -a "${stdout_log}") 2> >(tee -a "${stderr_log}" >&2)
