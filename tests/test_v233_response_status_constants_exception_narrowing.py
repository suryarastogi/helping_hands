"""Tests for v233 — Response status constants, exception narrowing in log_claude_usage.

Covers:
- ``server/constants`` new response status constants (OK, ERROR, NA)
- ``celery_app`` uses shared constants for response status values
- ``app`` uses shared constants for health-check status values
- ``log_claude_usage`` catches narrowed exceptions (not bare ``Exception``)
- AST-based source consistency — no bare status string literals remain
"""

from __future__ import annotations

import ast
from pathlib import Path


def _src_root() -> Path:
    """Return the path to src/helping_hands/server/."""
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands" / "server"


def _get_string_literals(source: str) -> list[str]:
    """Extract all string literals from Python source."""
    tree = ast.parse(source)
    literals: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
    return literals


# ---------------------------------------------------------------------------
# server/constants — Response status constant values
# ---------------------------------------------------------------------------


class TestResponseStatusConstants:
    """Verify response status constants in server/constants."""

    def test_response_status_ok_value(self) -> None:
        from helping_hands.server.constants import RESPONSE_STATUS_OK

        assert RESPONSE_STATUS_OK == "ok"

    def test_response_status_error_value(self) -> None:
        from helping_hands.server.constants import RESPONSE_STATUS_ERROR

        assert RESPONSE_STATUS_ERROR == "error"

    def test_response_status_na_value(self) -> None:
        from helping_hands.server.constants import RESPONSE_STATUS_NA

        assert RESPONSE_STATUS_NA == "na"

    def test_response_status_constants_are_strings(self) -> None:
        from helping_hands.server.constants import (
            RESPONSE_STATUS_ERROR,
            RESPONSE_STATUS_NA,
            RESPONSE_STATUS_OK,
        )

        assert isinstance(RESPONSE_STATUS_OK, str)
        assert isinstance(RESPONSE_STATUS_ERROR, str)
        assert isinstance(RESPONSE_STATUS_NA, str)

    def test_response_status_constants_are_distinct(self) -> None:
        from helping_hands.server.constants import (
            RESPONSE_STATUS_ERROR,
            RESPONSE_STATUS_NA,
            RESPONSE_STATUS_OK,
        )

        values = {RESPONSE_STATUS_OK, RESPONSE_STATUS_ERROR, RESPONSE_STATUS_NA}
        assert len(values) == 3, "Response status constants must be distinct"


# ---------------------------------------------------------------------------
# server/constants — __all__ includes new response status constants
# ---------------------------------------------------------------------------


class TestServerConstantsAllUpdated:
    """Verify __all__ includes new response status constants."""

    def test_all_contains_response_status_ok(self) -> None:
        from helping_hands.server import constants

        assert "RESPONSE_STATUS_OK" in constants.__all__

    def test_all_contains_response_status_error(self) -> None:
        from helping_hands.server import constants

        assert "RESPONSE_STATUS_ERROR" in constants.__all__

    def test_all_contains_response_status_na(self) -> None:
        from helping_hands.server import constants

        assert "RESPONSE_STATUS_NA" in constants.__all__

    def test_all_exports_superset(self) -> None:
        """__all__ must include at least the pre-v233 set plus new constants."""
        from helping_hands.server import constants

        new_names = {
            "RESPONSE_STATUS_OK",
            "RESPONSE_STATUS_ERROR",
            "RESPONSE_STATUS_NA",
        }
        assert new_names.issubset(set(constants.__all__))

    def test_all_symbols_importable(self) -> None:
        from helping_hands.server import constants

        for name in constants.__all__:
            assert hasattr(constants, name), (
                f"{name} declared in __all__ but not importable"
            )


# ---------------------------------------------------------------------------
# AST-based source consistency — no bare "ok"/"error" in status dicts
# ---------------------------------------------------------------------------


class TestSourceConsistencyStatusStrings:
    """AST checks that bare status strings are not hardcoded in source."""

    def _status_dict_literals(self, source: str) -> list[str]:
        """Find bare string values assigned to 'status' keys in dict literals."""
        tree = ast.parse(source)
        bare: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=True):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "status"
                        and isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                    ):
                        bare.append(value.value)
        return bare

    def test_celery_app_no_bare_status_ok(self) -> None:
        """celery_app.py should not contain bare 'status': 'ok' dict literals."""
        source = (_src_root() / "celery_app.py").read_text()
        bare = self._status_dict_literals(source)
        assert "ok" not in bare, (
            "celery_app.py still contains bare 'status': 'ok' literal"
        )

    def test_celery_app_no_bare_status_error(self) -> None:
        """celery_app.py should not contain bare 'status': 'error' dict literals."""
        source = (_src_root() / "celery_app.py").read_text()
        bare = self._status_dict_literals(source)
        assert "error" not in bare, (
            "celery_app.py still contains bare 'status': 'error' literal"
        )

    def test_app_no_bare_status_ok(self) -> None:
        """app.py should not contain bare 'status': 'ok' dict literals."""
        source = (_src_root() / "app.py").read_text()
        bare = self._status_dict_literals(source)
        assert "ok" not in bare, "app.py still contains bare 'status': 'ok' literal"

    def test_app_no_bare_status_error(self) -> None:
        """app.py should not contain bare 'status': 'error' dict literals."""
        source = (_src_root() / "app.py").read_text()
        bare = self._status_dict_literals(source)
        assert "error" not in bare, (
            "app.py still contains bare 'status': 'error' literal"
        )


# ---------------------------------------------------------------------------
# celery_app — exception narrowing in log_claude_usage
# ---------------------------------------------------------------------------


class TestLogClaudeUsageExceptionNarrowing:
    """Verify log_claude_usage catches specific exceptions, not bare Exception."""

    def _get_except_handler_types(self, source: str, func_name: str) -> list[list[str]]:
        """Return exception type names for each handler in a function."""
        tree = ast.parse(source)
        handlers: list[list[str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                for child in ast.walk(node):
                    if isinstance(child, ast.ExceptHandler) and child.type:
                        if isinstance(child.type, ast.Tuple):
                            names = []
                            for elt in child.type.elts:
                                if isinstance(elt, ast.Name):
                                    names.append(elt.id)
                                elif isinstance(elt, ast.Attribute):
                                    names.append(elt.attr)
                            handlers.append(names)
                        elif isinstance(child.type, ast.Name):
                            handlers.append([child.type.id])
                        elif isinstance(child.type, ast.Attribute):
                            handlers.append([child.type.attr])
        return handlers

    def test_keychain_handler_not_bare_exception(self) -> None:
        """The Keychain subprocess handler should not be bare Exception."""
        source = (_src_root() / "celery_app.py").read_text()
        handlers = self._get_except_handler_types(source, "log_claude_usage")
        # First try block (keychain) has inner JSONDecodeError+AttributeError
        # then outer CalledProcessError+OSError+TimeoutExpired
        flat = [name for group in handlers for name in group]
        assert "CalledProcessError" in flat, (
            "Keychain handler should catch CalledProcessError"
        )
        assert "OSError" in flat, "Keychain handler should catch OSError"
        assert "TimeoutExpired" in flat, "Keychain handler should catch TimeoutExpired"

    def test_urllib_handler_not_bare_exception(self) -> None:
        """The Usage API urllib handler should not be bare Exception."""
        source = (_src_root() / "celery_app.py").read_text()
        handlers = self._get_except_handler_types(source, "log_claude_usage")
        flat = [name for group in handlers for name in group]
        assert "URLError" in flat, "Usage API handler should catch URLError"

    def test_no_bare_exception_in_keychain_or_urllib(self) -> None:
        """log_claude_usage should not have bare 'except Exception' for
        keychain or urllib blocks (DB handler is acceptable)."""
        source = (_src_root() / "celery_app.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "log_claude_usage":
                # Count bare Exception handlers
                bare_exception_count = 0
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.ExceptHandler)
                        and isinstance(child.type, ast.Name)
                        and child.type.id == "Exception"
                    ):
                        bare_exception_count += 1
                # At most 1 bare Exception (the DB write handler)
                assert bare_exception_count <= 1, (
                    f"Expected at most 1 bare 'except Exception' (DB write), "
                    f"found {bare_exception_count}"
                )


# ---------------------------------------------------------------------------
# celery_app — imports response status constants
# ---------------------------------------------------------------------------


class TestCeleryAppImportsResponseConstants:
    """Verify celery_app.py imports and uses response status constants."""

    def test_celery_app_imports_response_status_ok(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        assert "_RESPONSE_STATUS_OK" in source

    def test_celery_app_imports_response_status_error(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        assert "_RESPONSE_STATUS_ERROR" in source


# ---------------------------------------------------------------------------
# app — imports response status constants
# ---------------------------------------------------------------------------


class TestAppImportsResponseConstants:
    """Verify app.py imports and uses response status constants."""

    def test_app_imports_response_status_ok(self) -> None:
        source = (_src_root() / "app.py").read_text()
        assert "_RESPONSE_STATUS_OK" in source

    def test_app_imports_response_status_error(self) -> None:
        source = (_src_root() / "app.py").read_text()
        assert "_RESPONSE_STATUS_ERROR" in source

    def test_app_imports_response_status_na(self) -> None:
        source = (_src_root() / "app.py").read_text()
        assert "_RESPONSE_STATUS_NA" in source
