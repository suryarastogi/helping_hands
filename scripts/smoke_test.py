"""Minimal repo-local smoke test.

Safe by design:
- No network calls
- No filesystem writes (beyond normal Python __pycache__ behavior)
- No git operations

Run:
  python scripts/smoke_test.py
"""

from __future__ import annotations

import importlib
import sys


def main() -> int:
    print("[smoke_test.py] python:", sys.version)

    if sys.version_info < (3, 12):
        raise SystemExit("Python >= 3.12 is required")

    pkg = importlib.import_module("helping_hands")
    version = getattr(pkg, "__version__", "<missing>")
    print("[smoke_test.py] helping_hands.__version__ =", version)

    # Ensure key modules import without side effects.
    importlib.import_module("helping_hands.cli.main")
    importlib.import_module("helping_hands.server.app")

    print("[smoke_test.py] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
