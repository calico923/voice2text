#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "${repo_root}"

chmod +x \
  .githooks/pre-commit \
  .githooks/commit-msg \
  scripts/validate-parent-checklist.sh \
  scripts/validate-parent-commit-msg.sh

git config core.hooksPath .githooks

echo "Installed git hooks:"
echo "- core.hooksPath=.githooks"
echo "- pre-commit: checklist format validation"
echo "- commit-msg: Txxコミット時のチェックリスト更新必須化"
