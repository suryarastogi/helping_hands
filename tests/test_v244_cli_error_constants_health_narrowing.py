"""Tests for v244: CLI error constants and health check exception narrowing.

Covers:
- _MODEL_NOT_FOUND_MARKERS constant value and usage
- _MODEL_NOT_AVAILABLE_MSG constant template
- _CLI_ERROR_EXIT_BACKENDS constant value and usage
- _check_workers_health narrowed to (ConnectionError, OSError, TimeoutError)
- _resolve_worker_capacity narrowed to (ConnectionError, OSError, TimeoutError)
- Source consistency: no bare model-not-found strings in cli/main.py
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.cli.main import (
    _CLI_ERROR_EXIT_BACKENDS,
    _MODEL_NOT_AVAILABLE_MSG,
    _MODEL_NOT_FOUND_MARKERS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _src_root() -> Path:
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands"


def _find_handlers_near_keyword(path: Path, keyword: str) -> list[ast.ExceptHandler]:
    """Return except handlers whose body contains *keyword* as a string."""
    tree = ast.parse(path.read_text(), filename=str(path))
    results: list[ast.ExceptHandler] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Constant)
                and isinstance(child.value, str)
                and keyword in child.value
            ):
                results.append(node)
                break
    return results


def _handler_type_names(handler: ast.ExceptHandler) -> set[str]:
    names: set[str] = set()
    if handler.type is None:
        return names
    if isinstance(handler.type, ast.Name):
        names.add(handler.type.id)
    elif isinstance(handler.type, ast.Tuple):
        for elt in handler.type.elts:
            if isinstance(elt, ast.Name):
                names.add(elt.id)
    return names


# ---------------------------------------------------------------------------
# _MODEL_NOT_FOUND_MARKERS
# ---------------------------------------------------------------------------


class TestModelNotFoundMarkers:
    """Tests for the _MODEL_NOT_FOUND_MARKERS constant."""

    def test_is_tuple(self) -> None:
        assert isinstance(_MODEL_NOT_FOUND_MARKERS, tuple)

    def test_non_empty(self) -> None:
        assert len(_MODEL_NOT_FOUND_MARKERS) > 0

    def test_contains_model_not_found(self) -> None:
        assert "model_not_found" in _MODEL_NOT_FOUND_MARKERS

    def test_contains_does_not_exist(self) -> None:
        assert "does not exist" in _MODEL_NOT_FOUND_MARKERS

    def test_all_entries_are_strings(self) -> None:
        for marker in _MODEL_NOT_FOUND_MARKERS:
            assert isinstance(marker, str)

    def test_all_entries_are_non_empty(self) -> None:
        for marker in _MODEL_NOT_FOUND_MARKERS:
            assert marker.strip()


class TestModelNotFoundMarkersSourceConsistency:
    """Verify cli/main.py uses the constant, not bare strings."""

    def test_no_bare_model_not_found_string(self) -> None:
        from helping_hands.cli import main as cli_main

        src = inspect.getsource(cli_main)
        tree = ast.parse(src)
        # The bare strings should not appear inside function bodies as
        # literal comparisons — only in the constant definition.
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Constant)
                        and child.value == "model_not_found"
                    ):
                        pytest.fail(
                            "cli/main.py function still uses bare 'model_not_found'"
                        )

    def test_no_bare_does_not_exist_string(self) -> None:
        from helping_hands.cli import main as cli_main

        src = inspect.getsource(cli_main)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Constant)
                        and child.value == "does not exist"
                    ):
                        pytest.fail(
                            "cli/main.py function still uses bare 'does not exist'"
                        )


# ---------------------------------------------------------------------------
# _MODEL_NOT_AVAILABLE_MSG
# ---------------------------------------------------------------------------


class TestModelNotAvailableMsg:
    """Tests for the _MODEL_NOT_AVAILABLE_MSG template."""

    def test_is_string(self) -> None:
        assert isinstance(_MODEL_NOT_AVAILABLE_MSG, str)

    def test_contains_placeholder(self) -> None:
        assert "{model" in _MODEL_NOT_AVAILABLE_MSG

    def test_format_works(self) -> None:
        result = _MODEL_NOT_AVAILABLE_MSG.format(model="gpt-99")
        assert "gpt-99" in result

    def test_mentions_model_flag(self) -> None:
        assert "--model" in _MODEL_NOT_AVAILABLE_MSG


# ---------------------------------------------------------------------------
# _CLI_ERROR_EXIT_BACKENDS
# ---------------------------------------------------------------------------


class TestCliErrorExitBackends:
    """Tests for the _CLI_ERROR_EXIT_BACKENDS constant."""

    def test_is_frozenset(self) -> None:
        assert isinstance(_CLI_ERROR_EXIT_BACKENDS, frozenset)

    def test_non_empty(self) -> None:
        assert len(_CLI_ERROR_EXIT_BACKENDS) > 0

    def test_contains_known_cli_backends(self) -> None:
        expected = {
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
        }
        assert expected == _CLI_ERROR_EXIT_BACKENDS

    def test_all_entries_are_strings(self) -> None:
        for name in _CLI_ERROR_EXIT_BACKENDS:
            assert isinstance(name, str)

    def test_all_entries_are_non_empty(self) -> None:
        for name in _CLI_ERROR_EXIT_BACKENDS:
            assert name.strip()


class TestCliErrorExitBackendsSourceConsistency:
    """Verify cli/main.py uses the constant, not an inline set."""

    def test_no_inline_backend_set_in_main_function(self) -> None:
        """The main() function should reference _CLI_ERROR_EXIT_BACKENDS."""
        from helping_hands.cli import main as cli_main

        src = inspect.getsource(cli_main.main)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Set):
                values = {
                    elt.value
                    for elt in node.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                }
                if "codexcli" in values and "claudecodecli" in values:
                    pytest.fail(
                        "main() still uses inline set literal with backend names"
                    )


# ---------------------------------------------------------------------------
# _check_workers_health exception narrowing
# ---------------------------------------------------------------------------


class TestCheckWorkersHealthExceptionNarrowingAST:
    """Verify _check_workers_health handler types via AST (no server import)."""

    def test_handler_types(self) -> None:
        handlers = _find_handlers_near_keyword(
            _src_root() / "server" / "app.py",
            "Workers health check failed",
        )
        assert handlers, "No handler found for _check_workers_health"
        names = _handler_type_names(handlers[0])
        assert "ConnectionError" in names
        assert "OSError" in names
        assert "TimeoutError" in names


class TestResolveWorkerCapacityExceptionNarrowingAST:
    """Verify _resolve_worker_capacity handler types via AST (no server import)."""

    def test_handler_types(self) -> None:
        handlers = _find_handlers_near_keyword(
            _src_root() / "server" / "app.py",
            "Failed to resolve worker capacity",
        )
        assert handlers, "No handler found for _resolve_worker_capacity"
        names = _handler_type_names(handlers[0])
        assert "ConnectionError" in names
        assert "OSError" in names
        assert "TimeoutError" in names


# ---------------------------------------------------------------------------
# Runtime server tests (require fastapi)
# ---------------------------------------------------------------------------

try:
    import fastapi as _fastapi  # noqa: F401

    _has_fastapi = True
except ImportError:
    _has_fastapi = False

_skip_no_fastapi = pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")


@_skip_no_fastapi
class TestCheckWorkersHealthExceptionNarrowingRuntime:
    """Runtime tests for _check_workers_health narrowed exceptions."""

    def test_connection_error_returns_error(self) -> None:
        with patch("helping_hands.server.app.celery_app") as mock_celery:
            mock_celery.control.inspect.side_effect = ConnectionError("refused")
            from helping_hands.server.app import _check_workers_health

            assert _check_workers_health() == "error"

    def test_os_error_returns_error(self) -> None:
        with patch("helping_hands.server.app.celery_app") as mock_celery:
            mock_celery.control.inspect.side_effect = OSError("network")
            from helping_hands.server.app import _check_workers_health

            assert _check_workers_health() == "error"

    def test_timeout_error_returns_error(self) -> None:
        with patch("helping_hands.server.app.celery_app") as mock_celery:
            mock_celery.control.inspect.side_effect = TimeoutError("timed out")
            from helping_hands.server.app import _check_workers_health

            assert _check_workers_health() == "error"


@_skip_no_fastapi
class TestResolveWorkerCapacityExceptionNarrowingRuntime:
    """Runtime tests for _resolve_worker_capacity narrowed exceptions."""

    def test_connection_error_falls_back(self) -> None:
        with patch("helping_hands.server.app.celery_app") as mock_celery:
            mock_celery.control.inspect.side_effect = ConnectionError("refused")
            from helping_hands.server.app import _resolve_worker_capacity

            resp = _resolve_worker_capacity()
            assert resp.source in ("env", "default")

    def test_timeout_error_falls_back(self) -> None:
        with patch("helping_hands.server.app.celery_app") as mock_celery:
            mock_celery.control.inspect.side_effect = TimeoutError("slow")
            from helping_hands.server.app import _resolve_worker_capacity

            resp = _resolve_worker_capacity()
            assert resp.source in ("env", "default")
