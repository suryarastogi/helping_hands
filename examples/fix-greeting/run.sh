#!/usr/bin/env bash
# Run helping-hands against the fix-greeting example.
#
# Usage (from the repo root):
#   ./examples/fix-greeting/run.sh
#
# Requirements:
#   - Python 3.12+ with uv
#   - helping_hands installed (uv sync --dev)
#   - At least one AI provider API key (e.g. OPENAI_API_KEY)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Running helping-hands against examples/fix-greeting"
echo "    The greet() function has a bug — the AI will fix it."
echo ""

uv run helping-hands "$SCRIPT_DIR" \
    --backend basic-langgraph \
    --no-pr \
    --prompt "The greet() function in src/greet.py has a bug: it returns 'Hello, !' instead of including the name argument. Fix the bug so that greet('Alice') returns 'Hello, Alice!'. Then verify the tests in tests/test_greet.py pass."

echo ""
echo "==> Done. Check examples/fix-greeting/src/greet.py to see the fix."
