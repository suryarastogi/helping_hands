"""Tests for v255: consolidated imports and magic number constants in celery_app.py.

The magic numbers (_MAX_UPDATES_VERBOSE/NORMAL, _MAX_LINE_CHARS_VERBOSE/NORMAL,
_FLUSH_CHARS_VERBOSE/NORMAL) control the streaming output behaviour of the
Celery worker. Without named constants these numbers appear three or more times
in the code; a tuning change must update every occurrence or the verbose and
normal paths behave inconsistently.

The consolidated-import check ensures that all constants from server.constants
are imported in a single grouped statement; split imports cause ruff's
combine-as-imports rule to flag violations in CI.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "helping_hands"


def _read_source(relative_path: str) -> str:
    """Read source code from disk without importing the module."""
    return (_SRC_ROOT / relative_path).read_text()


def _count_import_statements_from(source: str, module: str) -> int:
    """Count separate `from <module> import ...` statements in source AST."""
    tree = ast.parse(source)
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            count += 1
    return count


def _find_assignments(source: str, names: set[str]) -> list[ast.Assign]:
    """Find all Assign nodes whose target name is in *names*."""
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    results.append(node)
    return results


# ---------------------------------------------------------------------------
# Import consolidation — celery_app.py (AST-based, no import needed)
# ---------------------------------------------------------------------------


class TestCeleryAppImportConsolidation:
    """Verify celery_app.py uses grouped imports, not single-item statements."""

    @pytest.fixture()
    def _src(self) -> str:
        return _read_source("server/celery_app.py")

    def test_server_constants_single_import(self, _src: str) -> None:
        count = _count_import_statements_from(_src, "helping_hands.server.constants")
        assert count == 1, (
            f"Expected 1 grouped import from server.constants, found {count}"
        )

    def test_github_url_single_import(self, _src: str) -> None:
        count = _count_import_statements_from(_src, "helping_hands.lib.github_url")
        assert count == 1, f"Expected 1 grouped import from github_url, found {count}"

    def test_factory_single_import(self, _src: str) -> None:
        count = _count_import_statements_from(
            _src, "helping_hands.lib.hands.v1.hand.factory"
        )
        assert count == 1, f"Expected 1 grouped import from factory, found {count}"

    def test_constants_import_has_multiple_names(self, _src: str) -> None:
        """The grouped import should contain many names, not just one."""
        tree = ast.parse(_src)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "helping_hands.server.constants"
            ):
                assert len(node.names) >= 10, (
                    f"Expected >=10 names in grouped import, found {len(node.names)}"
                )
                return
        pytest.fail("No import from helping_hands.server.constants found")


# ---------------------------------------------------------------------------
# Import consolidation — app.py (AST-based, no import needed)
# ---------------------------------------------------------------------------


class TestAppImportConsolidation:
    """Verify app.py uses grouped imports, not single-item statements."""

    @pytest.fixture()
    def _src(self) -> str:
        return _read_source("server/app.py")

    def test_server_constants_single_import(self, _src: str) -> None:
        count = _count_import_statements_from(_src, "helping_hands.server.constants")
        assert count == 1, (
            f"Expected 1 grouped import from server.constants, found {count}"
        )

    def test_constants_import_has_multiple_names(self, _src: str) -> None:
        """The grouped import should contain many names, not just one."""
        tree = ast.parse(_src)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "helping_hands.server.constants"
            ):
                assert len(node.names) >= 20, (
                    f"Expected >=20 names in grouped import, found {len(node.names)}"
                )
                return
        pytest.fail("No import from helping_hands.server.constants found")


# ---------------------------------------------------------------------------
# Magic number constants — celery_app.py (AST-based, no import needed)
# ---------------------------------------------------------------------------


class TestMagicNumberConstants:
    """Verify magic numbers are extracted to named constants."""

    @pytest.fixture()
    def _src(self) -> str:
        return _read_source("server/celery_app.py")

    def test_named_constants_defined(self, _src: str) -> None:
        """All six named constants should exist as module-level assignments."""
        expected = {
            "_MAX_UPDATES_VERBOSE",
            "_MAX_UPDATES_NORMAL",
            "_MAX_LINE_CHARS_VERBOSE",
            "_MAX_LINE_CHARS_NORMAL",
            "_FLUSH_CHARS_VERBOSE",
            "_FLUSH_CHARS_NORMAL",
        }
        tree = ast.parse(_src)
        defined = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in expected:
                        defined.add(target.id)
        assert defined == expected, f"Missing constants: {expected - defined}"

    def test_constant_values(self, _src: str) -> None:
        """Named constants should have the expected numeric values."""
        expected_values = {
            "_MAX_UPDATES_VERBOSE": 2000,
            "_MAX_UPDATES_NORMAL": 200,
            "_MAX_LINE_CHARS_VERBOSE": 4000,
            "_MAX_LINE_CHARS_NORMAL": 800,
            "_FLUSH_CHARS_VERBOSE": 40,
            "_FLUSH_CHARS_NORMAL": 180,
        }
        tree = ast.parse(_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in expected_values:
                        assert isinstance(node.value, ast.Constant), (
                            f"{target.id} should be a simple constant assignment"
                        )
                        assert node.value.value == expected_values[target.id], (
                            f"{target.id} should be {expected_values[target.id]}, "
                            f"got {node.value.value}"
                        )

    def test_no_bare_magic_numbers_in_derived_config(self, _src: str) -> None:
        """_MAX_STORED_UPDATES, _MAX_UPDATE_LINE_CHARS, _BUFFER_FLUSH_CHARS
        should reference named constants, not bare numeric literals."""
        bare_magic = {2000, 200, 4000, 800, 40, 180}
        derived = {
            "_MAX_STORED_UPDATES",
            "_MAX_UPDATE_LINE_CHARS",
            "_BUFFER_FLUSH_CHARS",
        }
        for assign in _find_assignments(_src, derived):
            for child in ast.walk(assign.value):
                if isinstance(child, ast.Constant) and isinstance(child.value, int):
                    target_name = assign.targets[0].id  # type: ignore[union-attr]
                    assert child.value not in bare_magic, (
                        f"Bare magic number {child.value} found in "
                        f"{target_name} assignment"
                    )

    def test_verbose_constants_greater_than_normal(self, _src: str) -> None:
        """Verbose limits should be higher than normal limits."""
        tree = ast.parse(_src)
        values: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(
                        node.value, ast.Constant
                    ):
                        values[target.id] = node.value.value
        assert values["_MAX_UPDATES_VERBOSE"] > values["_MAX_UPDATES_NORMAL"]
        assert values["_MAX_LINE_CHARS_VERBOSE"] > values["_MAX_LINE_CHARS_NORMAL"]

    def test_flush_verbose_less_than_normal(self, _src: str) -> None:
        """Verbose mode flushes more frequently (lower threshold)."""
        tree = ast.parse(_src)
        values: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(
                        node.value, ast.Constant
                    ):
                        values[target.id] = node.value.value
        assert values["_FLUSH_CHARS_VERBOSE"] < values["_FLUSH_CHARS_NORMAL"]


# ---------------------------------------------------------------------------
# Ruff config — combine-as-imports enabled
# ---------------------------------------------------------------------------


class TestRuffConfig:
    """Verify the ruff isort configuration enables combined as-imports."""

    def test_combine_as_imports_enabled(self) -> None:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "combine-as-imports = true" in content, (
            "pyproject.toml should have combine-as-imports = true in "
            "[tool.ruff.lint.isort]"
        )
