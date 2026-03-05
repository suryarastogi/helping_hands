#!/usr/bin/env bash
# Smoke test script for helping_hands bash capability check.
set -euo pipefail

echo "Shell: $SHELL"
echo "Bash version: ${BASH_VERSION:-unknown}"
echo "Working dir: $(pwd)"
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Basic check
VALUE=$((6 * 7))
if [ "$VALUE" -eq 42 ]; then
  echo "Arithmetic check passed: 6 * 7 = $VALUE"
else
  echo "FAIL: expected 42, got $VALUE" >&2
  exit 1
fi

echo "smoke_test.sh: ALL CHECKS PASSED"
