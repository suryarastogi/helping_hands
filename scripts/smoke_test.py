"""Smoke test script for helping_hands capability validation."""

import sys
import platform
import datetime


def main() -> None:
    print(f"Python {sys.version}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print("scripts/smoke_test.py: OK")


if __name__ == "__main__":
    main()
