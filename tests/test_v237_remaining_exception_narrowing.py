"""Protect exception-handler specificity in PR finalization, CI fix loops, and server helpers.

Bare ``except Exception`` in these paths silently swallows programming errors
(AttributeError, NameError, etc.) that should crash loudly. If specificity
regresses, bugs in PR creation, CI-fix retries, worker-capacity probing, or
schedule next-run calculation become invisible in production logs -- users see
empty results or stale data with no traceback to diagnose.

Design decision: each handler's exception set is chosen to match the failure
modes of the external call it wraps (GitHub API, subprocess, Celery broker,
datetime parsing) and nothing else.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path


def _src_root() -> Path:
    """Return path to src/helping_hands/."""
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands"


def _hand_root() -> Path:
    """Return path to src/helping_hands/lib/hands/v1/hand/."""
    return _src_root() / "lib" / "hands" / "v1" / "hand"


def _server_root() -> Path:
    """Return path to src/helping_hands/server/."""
    return _src_root() / "server"


def _parse_file(path: Path) -> ast.Module:
    """Parse a Python source file into an AST."""
    return ast.parse(path.read_text(), filename=str(path))


def _handler_catches_bare_exception(handler: ast.ExceptHandler) -> bool:
    """Return True if the handler catches bare ``Exception``."""
    if handler.type is None:
        return False
    return isinstance(handler.type, ast.Name) and handler.type.id == "Exception"


def _handler_type_names(handler: ast.ExceptHandler) -> set[str]:
    """Return set of exception type names caught by a handler."""
    names: set[str] = set()
    if handler.type is None:
        return names
    if isinstance(handler.type, ast.Name):
        names.add(handler.type.id)
    elif isinstance(handler.type, ast.Tuple):
        for elt in handler.type.elts:
            if isinstance(elt, ast.Name):
                names.add(elt.id)
            elif isinstance(elt, ast.Attribute):
                names.add(elt.attr)
    elif isinstance(handler.type, ast.Attribute):
        names.add(handler.type.attr)
    return names


def _find_try_handlers_by_keyword(path: Path, keyword: str) -> list[ast.ExceptHandler]:
    """Find ExceptHandler nodes in Try statements whose full source contains *keyword*.

    Searches the entire Try node source (try body + handlers) so keywords
    in the try-body are matched even when not in the except-handler body.
    """
    source = path.read_text()
    tree = _parse_file(path)
    results: list[ast.ExceptHandler] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            try_src = ast.get_source_segment(source, node)
            if try_src and keyword in try_src:
                results.extend(node.handlers)
    return results


def _find_handlers_near_keyword(path: Path, keyword: str) -> list[ast.ExceptHandler]:
    """Find ExceptHandler nodes whose handler body source contains *keyword*."""
    source = path.read_text()
    tree = _parse_file(path)
    results: list[ast.ExceptHandler] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            handler_src = ast.get_source_segment(source, node)
            if handler_src and keyword in handler_src:
                results.append(node)
    return results


# ---------------------------------------------------------------------------
# base.py — update_pr_body handler (line ~936)
# ---------------------------------------------------------------------------


class TestBaseUpdatePrBodyHandler:
    """Verify update_pr_body handler is narrowed."""

    def test_no_bare_exception(self) -> None:
        """Handler should not catch bare Exception."""
        handlers = _find_try_handlers_by_keyword(
            _hand_root() / "base.py", "update_pr_body"
        )
        for handler in handlers:
            assert not _handler_catches_bare_exception(handler), (
                "update_pr_body handler still catches bare Exception"
            )

    def test_catches_github_errors_constant(self) -> None:
        """Handler should reference ``_GITHUB_ERRORS`` constant."""
        handlers = _find_try_handlers_by_keyword(
            _hand_root() / "base.py", "update_pr_body"
        )
        assert handlers, "No handler found for update_pr_body"
        names = _handler_type_names(handlers[0])
        assert "_GITHUB_ERRORS" in names


# ---------------------------------------------------------------------------
# base.py — _finalize_repo_pr catch-all (line ~1232)
# ---------------------------------------------------------------------------


class TestBaseFinalizeReprCatchAll:
    """Verify _finalize_repo_pr catch-all is narrowed."""

    def test_no_bare_exception_in_finalize(self) -> None:
        """The finalize catch-all should not catch bare Exception."""
        handlers = _find_handlers_near_keyword(
            _hand_root() / "base.py", "_finalize_repo_pr unexpected"
        )
        for handler in handlers:
            assert not _handler_catches_bare_exception(handler), (
                "_finalize_repo_pr catch-all still catches bare Exception"
            )

    def test_catches_github_errors_constant(self) -> None:
        """Handler should reference ``_GITHUB_ERRORS`` constant."""
        handlers = _find_handlers_near_keyword(
            _hand_root() / "base.py", "_finalize_repo_pr unexpected"
        )
        assert handlers, "No catch-all handler found for _finalize_repo_pr"
        names = _handler_type_names(handlers[0])
        assert "_GITHUB_ERRORS" in names


# ---------------------------------------------------------------------------
# cli/base.py — _ci_fix_loop handler (line ~1544)
# ---------------------------------------------------------------------------


class TestCLIBaseCiFixLoopHandler:
    """Verify _ci_fix_loop handler is narrowed."""

    def test_imports_github_exception(self) -> None:
        """cli/base.py imports GithubException."""
        tree = _parse_file(_hand_root() / "cli" / "base.py")
        imported = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "github":
                for alias in node.names:
                    if alias.name == "GithubException":
                        imported = True
        assert imported, "cli/base.py must import GithubException from github"

    def test_no_bare_exception(self) -> None:
        """Handler should not catch bare Exception."""
        handlers = _find_handlers_near_keyword(
            _hand_root() / "cli" / "base.py", "_ci_fix_loop unexpected"
        )
        for handler in handlers:
            assert not _handler_catches_bare_exception(handler), (
                "_ci_fix_loop handler still catches bare Exception"
            )

    def test_catches_github_exception(self) -> None:
        handlers = _find_handlers_near_keyword(
            _hand_root() / "cli" / "base.py", "_ci_fix_loop unexpected"
        )
        assert handlers, "No handler found for _ci_fix_loop"
        names = _handler_type_names(handlers[0])
        assert "GithubException" in names

    def test_catches_called_process_error(self) -> None:
        handlers = _find_handlers_near_keyword(
            _hand_root() / "cli" / "base.py", "_ci_fix_loop unexpected"
        )
        assert handlers, "No handler found for _ci_fix_loop"
        names = _handler_type_names(handlers[0])
        assert "CalledProcessError" in names

    def test_catches_timeout_expired(self) -> None:
        handlers = _find_handlers_near_keyword(
            _hand_root() / "cli" / "base.py", "_ci_fix_loop unexpected"
        )
        assert handlers, "No handler found for _ci_fix_loop"
        names = _handler_type_names(handlers[0])
        assert "TimeoutExpired" in names

    def test_catches_os_error(self) -> None:
        handlers = _find_handlers_near_keyword(
            _hand_root() / "cli" / "base.py", "_ci_fix_loop unexpected"
        )
        assert handlers, "No handler found for _ci_fix_loop"
        names = _handler_type_names(handlers[0])
        assert "OSError" in names


# ---------------------------------------------------------------------------
# app.py — _resolve_worker_capacity handler
# ---------------------------------------------------------------------------


class TestAppResolveWorkerCapacityHandler:
    """Verify _resolve_worker_capacity catches specific connection exceptions.

    Narrowed in v244 from broad ``except Exception`` to
    ``(ConnectionError, OSError, TimeoutError)`` — the exception types
    Celery inspector calls can raise for broker/network failures.
    """

    def test_catches_specific_exceptions(self) -> None:
        handlers = _find_handlers_near_keyword(
            _server_root() / "app.py", "Failed to resolve worker capacity"
        )
        assert handlers, "No handler found for _resolve_worker_capacity"
        names = _handler_type_names(handlers[0])
        assert "ConnectionError" in names
        assert "OSError" in names
        assert "TimeoutError" in names


# ---------------------------------------------------------------------------
# app.py — _schedule_to_response next_run handler
# ---------------------------------------------------------------------------


class TestAppScheduleToResponseHandler:
    """Verify _schedule_to_response next_run handler is narrowed."""

    def test_no_bare_exception(self) -> None:
        handlers = _find_handlers_near_keyword(
            _server_root() / "app.py", "Failed to calculate next run"
        )
        for handler in handlers:
            assert not _handler_catches_bare_exception(handler), (
                "_schedule_to_response handler still catches bare Exception"
            )

    def test_catches_value_error(self) -> None:
        handlers = _find_handlers_near_keyword(
            _server_root() / "app.py", "Failed to calculate next run"
        )
        assert handlers, "No handler found for next_run calculation"
        names = _handler_type_names(handlers[0])
        assert "ValueError" in names

    def test_catches_type_error(self) -> None:
        handlers = _find_handlers_near_keyword(
            _server_root() / "app.py", "Failed to calculate next run"
        )
        assert handlers
        names = _handler_type_names(handlers[0])
        assert "TypeError" in names


# ---------------------------------------------------------------------------
# Runtime type hierarchy checks
# ---------------------------------------------------------------------------


# TODO: CLEANUP CANDIDATE — these assert stdlib exception hierarchy facts that
# cannot change without a Python major version bump; they duplicate language
# guarantees and add no regression protection for this codebase.
class TestExceptionHierarchy:
    """Verify that narrowed exception types cover expected scenarios."""

    def test_called_process_error_is_subprocess(self) -> None:
        assert issubclass(subprocess.CalledProcessError, subprocess.SubprocessError)

    def test_timeout_expired_is_subprocess(self) -> None:
        assert issubclass(subprocess.TimeoutExpired, subprocess.SubprocessError)

    def test_connection_error_is_os_error(self) -> None:
        assert issubclass(ConnectionError, OSError)

    def test_github_exception_is_exception(self) -> None:
        from github import GithubException

        assert issubclass(GithubException, Exception)
