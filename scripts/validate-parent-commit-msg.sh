#!/usr/bin/env bash
set -euo pipefail

msg_file="${1:-}"
if [[ -z "${msg_file}" || ! -f "${msg_file}" ]]; then
  echo "[commit-msg] コミットメッセージファイルを取得できません。" >&2
  exit 1
fi

first_line="$(sed -n '1{s/\r$//;p;q;}' "${msg_file}")"
if [[ ! "${first_line}" =~ ^T([0-9]{2}):[[:space:]].+ ]]; then
  exit 0
fi

parent="T${BASH_REMATCH[1]}"
checklist="docs/parent-checklist.md"

if ! git diff --cached --name-only | grep -qx "${checklist}"; then
  echo "[commit-msg] ${parent} コミットには ${checklist} の更新が必要です。" >&2
  exit 1
fi

if ! git diff --cached -- "${checklist}" | grep -Eq "^[+-].*\|[[:space:]]*${parent}[[:space:]]*\|"; then
  echo "[commit-msg] ${checklist} の ${parent} 行が更新されていません。" >&2
  exit 1
fi

staged_content="$(git show ":${checklist}" 2>/dev/null || true)"
target_row="$(printf '%s\n' "${staged_content}" | grep -E "^\|[[:space:]]*${parent}[[:space:]]*\|" | head -n1 || true)"

if [[ -z "${target_row}" ]]; then
  echo "[commit-msg] ${checklist} に ${parent} 行が見つかりません。" >&2
  exit 1
fi

status="$(printf '%s\n' "${target_row}" | awk -F'|' '{gsub(/[[:space:]]/, "", $3); print $3}')"
reviewed_on="$(printf '%s\n' "${target_row}" | awk -F'|' '{gsub(/[[:space:]]/, "", $4); print $4}')"

if [[ "${status}" != "DONE" ]]; then
  echo "[commit-msg] ${parent} コミット時は ${checklist} の Status を DONE にしてください。" >&2
  exit 1
fi

if [[ ! "${reviewed_on}" =~ ^20[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "[commit-msg] ${parent} コミット時は Reviewed On を YYYY-MM-DD で記入してください。" >&2
  exit 1
fi
