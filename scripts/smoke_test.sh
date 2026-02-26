#!/usr/bin/env bash
set -euo pipefail

# Minimal repo-local smoke test.
# Safe by design: no network, no git, no writes (other than possible __pycache__).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python}"

echo "[smoke_test.sh] using: $PY_BIN"

# Tiny inline check (mirrors the 'python.run_code' intent)
PYTHONPATH=src "$PY_BIN" - <<'PY'
import sys
print('[smoke_test.sh] python:', sys.version)
assert sys.version_info[:2] >= (3, 12)
PY

# Script check (mirrors the 'python.run_script' intent)
PYTHONPATH=src "$PY_BIN" scripts/smoke_test.py

echo "[smoke_test.sh] OK"
