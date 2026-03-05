"""Smoke test script for helping_hands capabilities check."""

import sys
import os

print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print(f"Working dir: {os.getcwd()}")

# Simple arithmetic check
result = sum(range(10))
assert result == 45, f"Expected 45, got {result}"
print(f"Arithmetic check passed: sum(range(10)) = {result}")

# Import check
import json
data = json.dumps({"smoke_test": True, "status": "ok"})
parsed = json.loads(data)
assert parsed["status"] == "ok"
print(f"JSON round-trip check passed: {data}")

print("smoke_test.py: ALL CHECKS PASSED")
