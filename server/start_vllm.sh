#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
LOG_DIR_DEFAULT="${SCRIPT_DIR}/logs"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

MODEL_ID="${MODEL_ID:-mistralai/Voxtral-Mini-4B-Realtime-2602}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
DTYPE="${DTYPE:-bfloat16}"
LOG_DIR="${LOG_DIR:-${LOG_DIR_DEFAULT}}"

mkdir -p "${LOG_DIR}"
timestamp="$(date +"%Y%m%d-%H%M%S")"
stdout_log="${LOG_DIR}/vllm-${timestamp}.out.log"
stderr_log="${LOG_DIR}/vllm-${timestamp}.err.log"

cmd=(
  vllm
  serve
  "${MODEL_ID}"
  --host "${HOST}"
  --port "${PORT}"
  --max-model-len "${MAX_MODEL_LEN}"
  --dtype "${DTYPE}"
)

if [[ -n "${VLLM_EXTRA_ARGS:-}" ]]; then
  # VLLM_EXTRA_ARGS='--gpu-memory-utilization 0.9 --max-num-seqs 8'
  read -r -a extra_args <<<"${VLLM_EXTRA_ARGS}"
  cmd+=("${extra_args[@]}")
fi

echo "[start_vllm] MODEL_ID=${MODEL_ID}"
echo "[start_vllm] HOST=${HOST} PORT=${PORT} MAX_MODEL_LEN=${MAX_MODEL_LEN} DTYPE=${DTYPE}"
echo "[start_vllm] stdout=${stdout_log}"
echo "[start_vllm] stderr=${stderr_log}"
echo "[start_vllm] cmd=${cmd[*]}"

"${cmd[@]}" > >(tee -a "${stdout_log}") 2> >(tee -a "${stderr_log}" >&2)
