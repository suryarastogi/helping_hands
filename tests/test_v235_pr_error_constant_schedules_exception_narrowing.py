"""Tests for v235: _META_PR_ERROR constant and schedules.py exception narrowing.

_META_PR_ERROR is the metadata key written when PR creation fails. If base.py
and cli/base.py use different string literals for this key, the server reads
one and the CLI writes the other, so pr_error metadata is silently lost and
error diagnosis becomes impossible.

The "only one bare occurrence" AST test ensures the string literal exists
exactly once — at the constant definition — and is nowhere else duplicated.

schedules.py handlers must be narrowed to OSError (file/network issues during
schedule persistence) to avoid accidentally swallowing logic errors.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _hand_root() -> Path:
    """Return path to src/helping_hands/lib/hands/v1/hand/."""
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "helping_hands"
        / "lib"
        / "hands"
        / "v1"
        / "hand"
    )


def _server_root() -> Path:
    """Return path to src/helping_hands/server/."""
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands" / "server"


# ---------------------------------------------------------------------------
# _META_PR_ERROR constant exists and has correct value
# ---------------------------------------------------------------------------


class TestMetaPrErrorConstant:
    """Verify _META_PR_ERROR is defined in base.py."""

    def test_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _META_PR_ERROR

        assert _META_PR_ERROR == "pr_error"

    def test_is_string(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _META_PR_ERROR

        assert isinstance(_META_PR_ERROR, str)


# ---------------------------------------------------------------------------
# No bare "pr_error" strings in base.py — all should use _META_PR_ERROR
# ---------------------------------------------------------------------------


class TestNoBareprErrorInBase:
    """Verify base.py has no bare 'pr_error' string literals except the constant def."""

    def test_no_bare_pr_error_string(self) -> None:
        source = (_hand_root() / "base.py").read_text()
        tree = ast.parse(source)

        bare_uses: list[int] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "pr_error":
                # Allow the constant definition itself (_META_PR_ERROR = "pr_error")
                bare_uses.append(node.lineno)

        # Exactly one occurrence: the constant definition
        assert len(bare_uses) == 1, (
            f"Expected exactly 1 'pr_error' string (the constant def), "
            f"found {len(bare_uses)} at lines {bare_uses}"
        )


class TestNoBareprErrorInCliBase:
    """Verify cli/base.py has no bare 'pr_error' string literals."""

    def test_no_bare_pr_error_string(self) -> None:
        source = (_hand_root() / "cli" / "base.py").read_text()
        tree = ast.parse(source)

        bare_uses: list[int] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "pr_error":
                bare_uses.append(node.lineno)

        assert len(bare_uses) == 0, (
            f"Expected 0 bare 'pr_error' strings in cli/base.py, "
            f"found {len(bare_uses)} at lines {bare_uses}"
        )


class TestCliBaseImportsMetaPrError:
    """Verify cli/base.py imports _META_PR_ERROR from base."""

    def test_import_present(self) -> None:
        source = (_hand_root() / "cli" / "base.py").read_text()
        tree = ast.parse(source)

        imported_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.append(alias.name)

        assert "_META_PR_ERROR" in imported_names, (
            "_META_PR_ERROR not found in cli/base.py imports"
        )


# ---------------------------------------------------------------------------
# schedules.py — no bare except Exception in _save_meta, _delete_meta, _list_meta_keys
# ---------------------------------------------------------------------------


def _get_except_handler_types(source: str, func_name: str) -> list[list[str]]:
    """Extract exception handler type names from a function's try/except blocks."""
    tree = ast.parse(source)
    results: list[list[str]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name != func_name:
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.ExceptHandler):
                    if child.type is None:
                        results.append(["bare except"])
                    elif isinstance(child.type, ast.Name):
                        results.append([child.type.id])
                    elif isinstance(child.type, ast.Tuple):
                        names = []
                        for elt in child.type.elts:
                            if isinstance(elt, ast.Attribute):
                                names.append(f"{ast.dump(elt)}")
                            elif isinstance(elt, ast.Name):
                                names.append(elt.id)
                        results.append(names)
    return results


class TestSchedulesExceptionNarrowing:
    """Verify schedules.py exception handlers are narrowed."""

    @pytest.fixture()
    def source(self) -> str:
        return (_server_root() / "schedules.py").read_text()

    def test_save_meta_no_bare_exception(self, source: str) -> None:
        handlers = _get_except_handler_types(source, "_save_meta")
        for handler_types in handlers:
            assert "Exception" not in handler_types, (
                f"_save_meta still has bare except Exception: {handler_types}"
            )

    def test_delete_meta_no_bare_exception(self, source: str) -> None:
        handlers = _get_except_handler_types(source, "_delete_meta")
        for handler_types in handlers:
            assert "Exception" not in handler_types, (
                f"_delete_meta still has bare except Exception: {handler_types}"
            )

    def test_list_meta_keys_no_bare_exception(self, source: str) -> None:
        handlers = _get_except_handler_types(source, "_list_meta_keys")
        for handler_types in handlers:
            assert "Exception" not in handler_types, (
                f"_list_meta_keys still has bare except Exception: {handler_types}"
            )

    def test_save_meta_catches_oserror(self, source: str) -> None:
        handlers = _get_except_handler_types(source, "_save_meta")
        all_names = [n for h in handlers for n in h]
        assert "OSError" in all_names, "_save_meta should catch OSError"

    def test_delete_meta_catches_oserror(self, source: str) -> None:
        handlers = _get_except_handler_types(source, "_delete_meta")
        all_names = [n for h in handlers for n in h]
        assert "OSError" in all_names, "_delete_meta should catch OSError"

    def test_list_meta_keys_catches_oserror(self, source: str) -> None:
        handlers = _get_except_handler_types(source, "_list_meta_keys")
        all_names = [n for h in handlers for n in h]
        assert "OSError" in all_names, "_list_meta_keys should catch OSError"

    def test_no_bare_except_exception_anywhere(self, source: str) -> None:
        """Count total bare 'except Exception' handlers in schedules.py."""
        tree = ast.parse(source)
        bare_count = 0
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ExceptHandler)
                and isinstance(node.type, ast.Name)
                and node.type.id == "Exception"
            ):
                bare_count += 1
        assert bare_count == 0, (
            f"schedules.py still has {bare_count} bare 'except Exception' handler(s)"
        )


# ---------------------------------------------------------------------------
# Runtime tests — _META_PR_ERROR used in metadata dict operations
# ---------------------------------------------------------------------------


class TestMetaPrErrorRuntime:
    """Verify _META_PR_ERROR constant works at runtime."""

    def test_constant_matches_expected_key(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _META_PR_ERROR

        metadata: dict[str, str] = {}
        metadata[_META_PR_ERROR] = "test error"
        assert metadata["pr_error"] == "test error"

    def test_get_with_constant(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _META_PR_ERROR

        metadata = {"pr_error": "something went wrong"}
        assert metadata.get(_META_PR_ERROR, "") == "something went wrong"

    def test_cli_base_can_import(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _META_PR_ERROR  # noqa: F401
