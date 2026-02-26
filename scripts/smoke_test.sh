#!/usr/bin/env bash
set -euo pipefail

# Minimal smoke test for this repo.
# Intentionally quick, offline, and side-effect free.

echo "smoke_test.sh: start"

python --version
PYTHONPATH="./src${PYTHONPATH:+:$PYTHONPATH}" python -c 'import helping_hands; print(f"import helping_hands: ok ({helping_hands.__file__})")'

echo "smoke_test.sh: ok"
