#!/usr/bin/env bash
set -euo pipefail

CHECKLIST="docs/parent-checklist.md"

if ! git diff --cached --name-only | grep -qx "${CHECKLIST}"; then
  exit 0
fi

staged_content="$(git show ":${CHECKLIST}" 2>/dev/null || true)"
if [[ -z "${staged_content}" ]]; then
  echo "[pre-commit] ${CHECKLIST} をステージ済み内容として取得できません。" >&2
  exit 1
fi

for n in $(seq 1 18); do
  parent="T$(printf '%02d' "${n}")"
  count="$(printf '%s\n' "${staged_content}" | grep -Ec "^\|[[:space:]]*${parent}[[:space:]]*\|")"
  if [[ "${count}" -ne 1 ]]; then
    echo "[pre-commit] ${CHECKLIST} の ${parent} 行は1行だけ必要です（現在: ${count}）。" >&2
    exit 1
  fi
done

invalid_rows="$(printf '%s\n' "${staged_content}" | awk -F'|' '
  /^\|[[:space:]]*T[0-9]{2}[[:space:]]*\|/ {
    s=$3
    gsub(/[[:space:]]/, "", s)
    if (!(s=="TODO" || s=="IN_PROGRESS" || s=="DONE")) {
      print $0
    }
  }'
)"

if [[ -n "${invalid_rows}" ]]; then
  echo "[pre-commit] ${CHECKLIST} の Status は TODO / IN_PROGRESS / DONE のみ利用できます。" >&2
  echo "${invalid_rows}" >&2
  exit 1
fi
