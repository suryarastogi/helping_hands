"""Minimal smoke test for this repo.

Intentionally quick, offline, and side-effect free.

Run:
  python scripts/smoke_test.py
"""

from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path


def _ensure_local_src_on_path() -> None:
    """Prefer importing this repo's package (./src) over any globally-installed one."""

    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    sys.path.insert(0, str(src))


def main() -> int:
    _ensure_local_src_on_path()

    print("smoke_test: start")
    print(f"python: {sys.version.splitlines()[0]}")
    print(f"platform: {platform.platform()}")

    # Basic import check (does not execute app/CLI entrypoints).
    pkg = importlib.import_module("helping_hands")
    print(f"import helping_hands: ok ({pkg.__file__})")

    print("smoke_test: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
