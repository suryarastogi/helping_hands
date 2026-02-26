from __future__ import annotations

import platform
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    readme_path = repo_root / "README.md"
    package_init_path = repo_root / "src" / "helping_hands" / "__init__.py"

    print("smoke_test.py: begin")
    print(f"python: {sys.version.split()[0]}")
    print(f"implementation: {platform.python_implementation()}")
    print(f"cwd: {Path.cwd()}")

    if not readme_path.is_file():
        raise FileNotFoundError(readme_path)
    if not package_init_path.is_file():
        raise FileNotFoundError(package_init_path)

    readme_text = readme_path.read_text(encoding="utf-8")
    readme_lines = readme_text.count("\n") + 1 if readme_text else 0
    print(f"README.md: {readme_lines} lines")
    print("smoke_test.py: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

