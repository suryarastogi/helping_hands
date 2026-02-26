#!/usr/bin/env bash
set -euo pipefail

echo "smoke_test.sh: begin"
echo "bash: ${BASH_VERSION}"
echo "pwd: $(pwd)"

if [[ ! -f "README.md" ]]; then
  echo "README.md missing from current directory; run from repo root" >&2
  exit 1
fi

echo "README.md lines: $(wc -l < README.md | tr -d ' ')"

if command -v python >/dev/null 2>&1; then
  PY=python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "python not found on PATH" >&2
  exit 1
fi

echo "python: $($PY --version 2>&1)"
echo "smoke_test.sh: ok"

