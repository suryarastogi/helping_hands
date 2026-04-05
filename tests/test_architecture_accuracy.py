"""Tests that ARCHITECTURE.md stays in sync with the actual codebase.

Catches documentation drift where ARCHITECTURE.md lists file paths that have
been moved or removed, or where new source modules are missing from the key
file paths table. These tests ensure that every path in the "Key file paths"
table actually exists on disk, and that every Python module under ``src/`` is
represented in the table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHITECTURE_MD = REPO_ROOT / "ARCHITECTURE.md"
SRC_ROOT = REPO_ROOT / "src" / "helping_hands"


@pytest.fixture()
def architecture_text() -> str:
    """Read ARCHITECTURE.md content."""
    return ARCHITECTURE_MD.read_text()


@pytest.fixture()
def key_file_paths(architecture_text: str) -> list[str]:
    """Extract all paths from the 'Key file paths' table."""
    # Match backtick-wrapped paths that look like file paths (contain /)
    return [
        p
        for p in re.findall(r"\|\s*`([^`]+)`\s*\|", architecture_text)
        if "/" in p and p.startswith("src/")
    ]


class TestArchitectureFileExists:
    """ARCHITECTURE.md must exist at the repo root."""

    def test_exists(self) -> None:
        assert ARCHITECTURE_MD.is_file()

    def test_has_key_file_paths_section(self, architecture_text: str) -> None:
        assert "## Key file paths" in architecture_text


class TestKeyFilePathsAccuracy:
    """Every path listed in the 'Key file paths' table must exist on disk."""

    def test_all_listed_paths_exist(self, key_file_paths: list[str]) -> None:
        missing = []
        for rel_path in key_file_paths:
            full = REPO_ROOT / rel_path
            if not full.exists():
                missing.append(rel_path)
        assert not missing, f"ARCHITECTURE.md lists paths that do not exist: {missing}"

    def test_at_least_20_paths_listed(self, key_file_paths: list[str]) -> None:
        """Sanity check: the table should have a reasonable number of entries."""
        assert len(key_file_paths) >= 20, (
            f"Expected at least 20 key file paths, found {len(key_file_paths)}"
        )


class TestSourceModuleCoverage:
    """Every non-init Python module under src/ should appear in ARCHITECTURE.md."""

    # Modules that are intentionally not mentioned (e.g., package __init__.py)
    _EXCLUDED: frozenset[str] = frozenset({"__init__.py"})

    @pytest.fixture()
    def source_modules(self) -> list[str]:
        """Collect all .py filenames under src/helping_hands/."""
        modules = []
        for py_file in sorted(SRC_ROOT.rglob("*.py")):
            if py_file.name in self._EXCLUDED:
                continue
            modules.append(py_file.name)
        return modules

    def test_all_source_modules_mentioned(
        self, architecture_text: str, source_modules: list[str]
    ) -> None:
        missing = []
        for mod_name in source_modules:
            if mod_name not in architecture_text:
                missing.append(mod_name)
        assert not missing, (
            f"Source modules not mentioned in ARCHITECTURE.md: {missing}"
        )


class TestLastUpdatedDate:
    """ARCHITECTURE.md should have a recent 'Last updated' date."""

    def test_has_last_updated(self, architecture_text: str) -> None:
        assert "Last updated:" in architecture_text

    def test_last_updated_is_2026(self, architecture_text: str) -> None:
        """The date should be in the current year."""
        match = re.search(r"Last updated:\s*(\d{4})-\d{2}-\d{2}", architecture_text)
        assert match is not None, "Could not parse 'Last updated' date"
        assert match.group(1) == "2026"
