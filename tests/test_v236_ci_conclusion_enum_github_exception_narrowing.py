"""Tests for v236 — CIConclusion enum consistency, GitHub exception narrowing.

Covers:
- ``github.py`` uses ``CIConclusion`` enum members instead of bare strings
- ``base.py`` GitHub-related handlers use ``(GithubException, OSError)``
- ``e2e.py`` GitHub-related handler uses ``(GithubException, OSError)``
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _lib_root() -> Path:
    """Return path to src/helping_hands/lib/."""
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands" / "lib"


def _hand_root() -> Path:
    """Return path to src/helping_hands/lib/hands/v1/hand/."""
    return _lib_root() / "hands" / "v1" / "hand"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# CIConclusion enum consistency in github.py
# ---------------------------------------------------------------------------


class TestCIConclusionEnumUsage:
    """Verify github.py uses CIConclusion enum members, not bare strings."""

    def test_no_bare_success_in_get_check_runs(self) -> None:
        """The get_check_runs method should not compare against bare 'success'."""
        tree = _parse_file(_lib_root() / "github.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_check_runs":
                source = ast.get_source_segment(
                    (_lib_root() / "github.py").read_text(), node
                )
                assert source is not None
                func_tree = ast.parse(source)
                for cmp in ast.walk(func_tree):
                    if isinstance(cmp, ast.Compare):
                        for comparator in cmp.comparators:
                            if (
                                isinstance(comparator, ast.Constant)
                                and comparator.value == "success"
                            ):
                                pytest.fail(
                                    'Bare "success" string found in '
                                    "get_check_runs comparison; use "
                                    "CIConclusion.SUCCESS"
                                )
                break

    def test_no_bare_failure_in_get_check_runs(self) -> None:
        """The get_check_runs method should not compare against bare 'failure'."""
        tree = _parse_file(_lib_root() / "github.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_check_runs":
                source = ast.get_source_segment(
                    (_lib_root() / "github.py").read_text(), node
                )
                assert source is not None
                func_tree = ast.parse(source)
                for cmp in ast.walk(func_tree):
                    if isinstance(cmp, ast.Compare):
                        for comparator in cmp.comparators:
                            if (
                                isinstance(comparator, ast.Constant)
                                and comparator.value == "failure"
                            ):
                                pytest.fail(
                                    'Bare "failure" string found in '
                                    "get_check_runs comparison; use "
                                    "CIConclusion.FAILURE"
                                )
                break

    def test_ci_conclusion_enum_values(self) -> None:
        """CIConclusion enum members compare equal to their string values."""
        from helping_hands.lib.github import CIConclusion

        assert CIConclusion.SUCCESS == "success"
        assert CIConclusion.FAILURE == "failure"
        assert CIConclusion.PENDING == "pending"
        assert CIConclusion.NO_CHECKS == "no_checks"
        assert CIConclusion.MIXED == "mixed"

    def test_uses_enum_attribute_in_comparisons(self) -> None:
        """get_check_runs uses CIConclusion.X attribute access in comparisons."""
        tree = _parse_file(_lib_root() / "github.py")
        found_attr_comparisons = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_check_runs":
                for cmp in ast.walk(node):
                    if isinstance(cmp, ast.Compare):
                        for comparator in cmp.comparators:
                            if isinstance(
                                comparator, ast.Attribute
                            ) and comparator.attr in ("SUCCESS", "FAILURE"):
                                found_attr_comparisons += 1
                break
        assert found_attr_comparisons >= 2, (
            f"Expected >= 2 CIConclusion.X attribute comparisons, "
            f"found {found_attr_comparisons}"
        )


# ---------------------------------------------------------------------------
# GitHub exception narrowing in base.py
# ---------------------------------------------------------------------------


class TestBaseGithubExceptionNarrowing:
    """Verify base.py GitHub handlers use ``_GITHUB_ERRORS`` constant."""

    def test_imports_github_exception(self) -> None:
        """base.py imports GithubException (used in _GITHUB_ERRORS definition)."""
        tree = _parse_file(_hand_root() / "base.py")
        imported = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "github":
                for alias in node.names:
                    if alias.name == "GithubException":
                        imported = True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "github":
                        imported = True
        assert imported, "base.py must import GithubException from github"

    def test_no_bare_exception_for_whoami(self) -> None:
        """whoami() handler should not catch bare Exception."""
        source = (_hand_root() / "base.py").read_text()
        tree = _parse_file(_hand_root() / "base.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and _handler_catches_bare_exception(
                node
            ):
                handler_src = ast.get_source_segment(source, node)
                if handler_src and "whoami" in handler_src:
                    pytest.fail(
                        "whoami() handler catches bare Exception; "
                        "should use _GITHUB_ERRORS"
                    )

    def test_no_bare_exception_for_update_pr_body(self) -> None:
        """update_pr_body() handler should not catch bare Exception."""
        source = (_hand_root() / "base.py").read_text()
        tree = _parse_file(_hand_root() / "base.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and _handler_catches_bare_exception(
                node
            ):
                handler_src = ast.get_source_segment(source, node)
                if handler_src and "update_pr_body" in handler_src:
                    pytest.fail(
                        "update_pr_body() handler catches bare Exception; "
                        "should use _GITHUB_ERRORS"
                    )

    def test_no_bare_exception_for_get_repo(self) -> None:
        """get_repo/default_branch handler should not catch bare Exception."""
        source = (_hand_root() / "base.py").read_text()
        tree = _parse_file(_hand_root() / "base.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and _handler_catches_bare_exception(
                node
            ):
                handler_src = ast.get_source_segment(source, node)
                if handler_src and "default branch" in handler_src:
                    pytest.fail(
                        "get_repo() handler catches bare Exception; "
                        "should use _GITHUB_ERRORS"
                    )

    def test_github_handlers_use_constant(self) -> None:
        """All GitHub-related handlers should reference ``_GITHUB_ERRORS``."""
        source = (_hand_root() / "base.py").read_text()
        assert "except _GITHUB_ERRORS" in source
        # The constant itself contains the right types
        from github import GithubException

        from helping_hands.lib.hands.v1.hand.base import _GITHUB_ERRORS

        assert GithubException in _GITHUB_ERRORS
        assert OSError in _GITHUB_ERRORS


# ---------------------------------------------------------------------------
# GitHub exception narrowing in e2e.py
# ---------------------------------------------------------------------------


class TestE2EGithubExceptionNarrowing:
    """Verify e2e.py GitHub handler uses ``_GITHUB_ERRORS`` constant."""

    def test_imports_github_errors(self) -> None:
        """e2e.py imports _GITHUB_ERRORS from base."""
        source = (_hand_root() / "e2e.py").read_text()
        assert "_GITHUB_ERRORS" in source

    def test_no_bare_exception_for_default_branch(self) -> None:
        """default_branch handler should not catch bare Exception."""
        source = (_hand_root() / "e2e.py").read_text()
        tree = _parse_file(_hand_root() / "e2e.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and _handler_catches_bare_exception(
                node
            ):
                handler_src = ast.get_source_segment(source, node)
                if handler_src and "default branch" in handler_src:
                    pytest.fail(
                        "default_branch handler catches bare Exception; "
                        "should use _GITHUB_ERRORS"
                    )

    def test_handler_uses_github_errors_constant(self) -> None:
        """The default_branch handler references ``_GITHUB_ERRORS``."""
        source = (_hand_root() / "e2e.py").read_text()
        assert "except _GITHUB_ERRORS" in source


# ---------------------------------------------------------------------------
# Runtime smoke tests — GithubException is catchable
# ---------------------------------------------------------------------------


class TestGithubExceptionRuntime:
    """Verify GithubException can be raised and caught properly."""

    def test_github_exception_is_exception(self) -> None:
        from github import GithubException

        assert issubclass(GithubException, Exception)

    def test_github_exception_not_base_exception(self) -> None:
        from github import GithubException

        assert issubclass(GithubException, BaseException)
        assert GithubException is not BaseException

    def test_os_error_catches_connection_error(self) -> None:
        """OSError catches ConnectionError (network failures)."""
        assert issubclass(ConnectionError, OSError)
