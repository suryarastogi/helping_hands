"""Protect canonical _GITHUB_ERRORS tuple usage across hand implementations and Celery inspect exception specificity.

_GITHUB_ERRORS centralizes the except-tuple for all GitHub API calls. If
base.py or e2e.py construct the tuple inline, adding a new exception type
(e.g. RateLimitExceededException) requires edits in multiple files and a
missed site lets that error propagate uncaught, crashing the PR flow.

The "exactly 4 uses" count in base.py guards against handlers that silently
revert to a bare tuple. Celery inspect helpers must catch only broker/network
errors so Celery API changes crash loudly instead of reporting wrong capacity.
"""

from __future__ import annotations

import ast
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


# ---------------------------------------------------------------------------
# _GITHUB_ERRORS constant
# ---------------------------------------------------------------------------


class TestGithubErrorsConstant:
    """Verify ``_GITHUB_ERRORS`` is defined and contains expected exception types."""

    def test_constant_exists(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        assert isinstance(_GITHUB_ERRORS, tuple)

    def test_contains_github_exception(self) -> None:
        from github import GithubException

        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        assert GithubException in _GITHUB_ERRORS

    def test_contains_os_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        assert OSError in _GITHUB_ERRORS

    def test_exactly_two_types(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        assert len(_GITHUB_ERRORS) == 2

    # TODO: CLEANUP CANDIDATE — asserts that exception types are exception
    # subclasses, which is a tautology if the content tests above pass.
    def test_all_are_exception_subclasses(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        for exc_type in _GITHUB_ERRORS:
            assert issubclass(exc_type, BaseException)


# ---------------------------------------------------------------------------
# base.py — uses _GITHUB_ERRORS in except handlers (no bare tuple)
# ---------------------------------------------------------------------------


class TestBasePyUsesGithubErrors:
    """Verify that ``base.py`` references ``_GITHUB_ERRORS`` in except handlers."""

    def test_no_bare_github_exception_oserror_in_except(self) -> None:
        """No except handler should contain ``(GithubException, OSError)`` as a
        literal tuple — they should all reference ``_GITHUB_ERRORS``."""
        source = (_hand_root() / "base.py").read_text()
        assert "except (GithubException, OSError)" not in source

    def test_uses_github_errors_in_except(self) -> None:
        """At least one except handler references ``_GITHUB_ERRORS``."""
        source = (_hand_root() / "base.py").read_text()
        assert "except _GITHUB_ERRORS" in source

    def test_four_except_github_errors(self) -> None:
        """Exactly 4 except handlers reference ``_GITHUB_ERRORS``."""
        source = (_hand_root() / "base.py").read_text()
        count = source.count("except _GITHUB_ERRORS")
        assert count == 4, f"expected 4, got {count}"


# ---------------------------------------------------------------------------
# e2e.py — imports and uses _GITHUB_ERRORS
# ---------------------------------------------------------------------------


class TestE2ePyUsesGithubErrors:
    """Verify that ``e2e.py`` imports and uses ``_GITHUB_ERRORS``."""

    def test_imports_github_errors(self) -> None:
        source = (_hand_root() / "e2e.py").read_text()
        assert "_GITHUB_ERRORS" in source

    def test_no_direct_github_exception_import(self) -> None:
        """``e2e.py`` should not import ``GithubException`` from ``github``."""
        tree = _parse_file(_hand_root() / "e2e.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "github":
                names = [alias.name for alias in node.names]
                assert "GithubException" not in names, (
                    "e2e.py should not import GithubException directly"
                )

    def test_uses_github_errors_in_except(self) -> None:
        source = (_hand_root() / "e2e.py").read_text()
        assert "except _GITHUB_ERRORS" in source

    def test_no_bare_tuple_in_except(self) -> None:
        source = (_hand_root() / "e2e.py").read_text()
        assert "(GithubException, OSError)" not in source


# ---------------------------------------------------------------------------
# app.py — Celery inspect exception narrowing
# ---------------------------------------------------------------------------


def _except_handler_types(handler: ast.ExceptHandler) -> list[str]:
    """Return the exception type names from an except handler."""
    if handler.type is None:
        return ["bare"]
    if isinstance(handler.type, ast.Name):
        return [handler.type.id]
    if isinstance(handler.type, ast.Tuple):
        return [
            elt.id if isinstance(elt, ast.Name) else ast.dump(elt)
            for elt in handler.type.elts
        ]
    return [ast.dump(handler.type)]


def _find_function_handlers(
    tree: ast.Module, func_name: str
) -> list[ast.ExceptHandler]:
    """Return all except handlers inside the given function."""
    handlers: list[ast.ExceptHandler] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == func_name
        ):
            for child in ast.walk(node):
                if isinstance(child, ast.ExceptHandler):
                    handlers.append(child)
    return handlers


_CELERY_INSPECT_EXCEPTIONS = {
    "AttributeError",
    "ConnectionError",
    "OSError",
    "RuntimeError",
    "TimeoutError",
}


class TestAppCeleryInspectNarrowing:
    """Verify Celery inspect helpers no longer catch bare ``Exception``."""

    def test_safe_inspect_call_no_bare_exception(self) -> None:
        tree = _parse_file(_server_root() / "app.py")
        handlers = _find_function_handlers(tree, "_safe_inspect_call")
        assert handlers, "no except handlers found in _safe_inspect_call"
        for handler in handlers:
            types = _except_handler_types(handler)
            assert "Exception" not in types, (
                f"_safe_inspect_call still catches bare Exception: {types}"
            )

    def test_safe_inspect_call_catches_expected(self) -> None:
        tree = _parse_file(_server_root() / "app.py")
        handlers = _find_function_handlers(tree, "_safe_inspect_call")
        for handler in handlers:
            types = set(_except_handler_types(handler))
            assert types == _CELERY_INSPECT_EXCEPTIONS, (
                f"expected {_CELERY_INSPECT_EXCEPTIONS}, got {types}"
            )

    def test_collect_celery_current_tasks_no_bare_exception(self) -> None:
        tree = _parse_file(_server_root() / "app.py")
        handlers = _find_function_handlers(tree, "_collect_celery_current_tasks")
        assert handlers, "no except handlers found in _collect_celery_current_tasks"
        for handler in handlers:
            types = _except_handler_types(handler)
            assert "Exception" not in types, (
                f"_collect_celery_current_tasks still catches bare Exception: {types}"
            )

    def test_collect_celery_current_tasks_catches_expected(self) -> None:
        tree = _parse_file(_server_root() / "app.py")
        handlers = _find_function_handlers(tree, "_collect_celery_current_tasks")
        for handler in handlers:
            types = set(_except_handler_types(handler))
            assert types == _CELERY_INSPECT_EXCEPTIONS, (
                f"expected {_CELERY_INSPECT_EXCEPTIONS}, got {types}"
            )


# ---------------------------------------------------------------------------
# Integration: _GITHUB_ERRORS catches real exceptions
# ---------------------------------------------------------------------------


class TestGithubErrorsCatchesBehavior:
    """Functional test that ``_GITHUB_ERRORS`` actually catches expected errors."""

    def test_catches_os_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        caught = False
        try:
            raise OSError("network failure")
        except _GITHUB_ERRORS:
            caught = True
        assert caught

    def test_catches_github_exception(self) -> None:
        from github import GithubException

        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        caught = False
        try:
            raise GithubException(404, "not found", None)
        except _GITHUB_ERRORS:
            caught = True
        assert caught

    def test_does_not_catch_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        with __import__("pytest").raises(ValueError, match="wrong"):
            try:
                raise ValueError("wrong")
            except _GITHUB_ERRORS:
                pass
