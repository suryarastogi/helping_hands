"""Tests for v184: PR metadata and CI fix status constants.

Verifies that:
- PR metadata key constants have correct string values
- PR status constants have correct string values
- CI fix metadata key constants have correct string values
- CI fix status constants have correct string values
- __all__ exports include all new constants
- Source code uses constants instead of raw strings
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# PR metadata key constants — values
# ---------------------------------------------------------------------------


class TestPRMetaKeyConstants:
    """Verify PR metadata key name constants have correct values."""

    def test_pr_meta_status_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_META_STATUS

        assert _PR_META_STATUS == "pr_status"

    def test_pr_meta_url_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_META_URL

        assert _PR_META_URL == "pr_url"

    def test_pr_meta_number_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_META_NUMBER

        assert _PR_META_NUMBER == "pr_number"

    def test_pr_meta_branch_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_META_BRANCH

        assert _PR_META_BRANCH == "pr_branch"

    def test_pr_meta_commit_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_META_COMMIT

        assert _PR_META_COMMIT == "pr_commit"

    def test_pr_meta_error_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_META_ERROR

        assert _PR_META_ERROR == "pr_error"


# ---------------------------------------------------------------------------
# PR status constants — values
# ---------------------------------------------------------------------------


class TestPRStatusConstants:
    """Verify PR status constants have correct string values."""

    def test_not_attempted(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NOT_ATTEMPTED

        assert _PR_STATUS_NOT_ATTEMPTED == "not_attempted"

    def test_disabled(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_DISABLED

        assert _PR_STATUS_DISABLED == "disabled"

    def test_no_repo(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NO_REPO

        assert _PR_STATUS_NO_REPO == "no_repo"

    def test_not_git_repo(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NOT_GIT_REPO

        assert _PR_STATUS_NOT_GIT_REPO == "not_git_repo"

    def test_no_changes(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NO_CHANGES

        assert _PR_STATUS_NO_CHANGES == "no_changes"

    def test_no_github_origin(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NO_GITHUB_ORIGIN

        assert _PR_STATUS_NO_GITHUB_ORIGIN == "no_github_origin"

    def test_precommit_failed(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_PRECOMMIT_FAILED

        assert _PR_STATUS_PRECOMMIT_FAILED == "precommit_failed"

    def test_created(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_CREATED

        assert _PR_STATUS_CREATED == "created"

    def test_updated(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_UPDATED

        assert _PR_STATUS_UPDATED == "updated"

    def test_missing_token(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_MISSING_TOKEN

        assert _PR_STATUS_MISSING_TOKEN == "missing_token"

    def test_git_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_GIT_ERROR

        assert _PR_STATUS_GIT_ERROR == "git_error"

    def test_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_ERROR

        assert _PR_STATUS_ERROR == "error"

    def test_interrupted(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_INTERRUPTED

        assert _PR_STATUS_INTERRUPTED == "interrupted"


# ---------------------------------------------------------------------------
# CI fix metadata key constants — values
# ---------------------------------------------------------------------------


class TestCIFixMetaKeyConstants:
    """Verify CI fix metadata key name constants have correct values."""

    def test_ci_fix_meta_status_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_META_STATUS

        assert _CI_FIX_META_STATUS == "ci_fix_status"

    def test_ci_fix_meta_error_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_META_ERROR

        assert _CI_FIX_META_ERROR == "ci_fix_error"

    def test_ci_fix_meta_attempts_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_META_ATTEMPTS

        assert _CI_FIX_META_ATTEMPTS == "ci_fix_attempts"


# ---------------------------------------------------------------------------
# CI fix status constants — values
# ---------------------------------------------------------------------------


class TestCIFixStatusConstants:
    """Verify CI fix status constants have correct string values."""

    def test_checking(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_STATUS_CHECKING

        assert _CI_FIX_STATUS_CHECKING == "checking"

    def test_success(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_STATUS_SUCCESS

        assert _CI_FIX_STATUS_SUCCESS == "success"

    def test_no_checks(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_STATUS_NO_CHECKS

        assert _CI_FIX_STATUS_NO_CHECKS == "no_checks"

    def test_pending_timeout(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _CI_FIX_STATUS_PENDING_TIMEOUT,
        )

        assert _CI_FIX_STATUS_PENDING_TIMEOUT == "pending_timeout"

    def test_interrupted(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _CI_FIX_STATUS_INTERRUPTED,
        )

        assert _CI_FIX_STATUS_INTERRUPTED == "interrupted"

    def test_exhausted(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_STATUS_EXHAUSTED

        assert _CI_FIX_STATUS_EXHAUSTED == "exhausted"

    def test_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_FIX_STATUS_ERROR

        assert _CI_FIX_STATUS_ERROR == "error"


# ---------------------------------------------------------------------------
# __all__ exports — base.py
# ---------------------------------------------------------------------------


class TestBaseAllExports:
    """Verify base.py __all__ includes all new PR constants."""

    def test_all_includes_pr_meta_constants(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import __all__

        expected = [
            "_PR_META_BRANCH",
            "_PR_META_COMMIT",
            "_PR_META_ERROR",
            "_PR_META_NUMBER",
            "_PR_META_STATUS",
            "_PR_META_URL",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from base.py __all__"

    def test_all_includes_pr_status_constants(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import __all__

        expected = [
            "_PR_STATUS_CREATED",
            "_PR_STATUS_DISABLED",
            "_PR_STATUS_ERROR",
            "_PR_STATUS_GIT_ERROR",
            "_PR_STATUS_INTERRUPTED",
            "_PR_STATUS_MISSING_TOKEN",
            "_PR_STATUS_NO_CHANGES",
            "_PR_STATUS_NO_GITHUB_ORIGIN",
            "_PR_STATUS_NO_REPO",
            "_PR_STATUS_NOT_ATTEMPTED",
            "_PR_STATUS_NOT_GIT_REPO",
            "_PR_STATUS_PRECOMMIT_FAILED",
            "_PR_STATUS_UPDATED",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from base.py __all__"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.base as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} in __all__ but not importable"


# ---------------------------------------------------------------------------
# __all__ exports — cli/base.py
# ---------------------------------------------------------------------------


class TestCLIBaseAllExports:
    """Verify cli/base.py __all__ includes all new CI fix constants."""

    def test_all_includes_ci_fix_meta_constants(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import __all__

        expected = [
            "_CI_FIX_META_ATTEMPTS",
            "_CI_FIX_META_ERROR",
            "_CI_FIX_META_STATUS",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from cli/base.py __all__"

    def test_all_includes_ci_fix_status_constants(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import __all__

        expected = [
            "_CI_FIX_STATUS_CHECKING",
            "_CI_FIX_STATUS_ERROR",
            "_CI_FIX_STATUS_EXHAUSTED",
            "_CI_FIX_STATUS_INTERRUPTED",
            "_CI_FIX_STATUS_NO_CHECKS",
            "_CI_FIX_STATUS_PENDING_TIMEOUT",
            "_CI_FIX_STATUS_SUCCESS",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from cli/base.py __all__"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.base as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} in __all__ but not importable"


# ---------------------------------------------------------------------------
# Source usage — no raw PR status strings in source
# ---------------------------------------------------------------------------


def _collect_string_literals(filepath: Path) -> set[str]:
    """Parse a Python file and return all string literal values."""
    source = filepath.read_text()
    tree = ast.parse(source)
    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add(node.value)
    return literals


_PR_STATUS_STRINGS = frozenset(
    {
        "not_attempted",
        "disabled",
        "no_repo",
        "not_git_repo",
        "no_changes",
        "no_github_origin",
        "precommit_failed",
        "created",
        "updated",
        "missing_token",
        "git_error",
    }
)

_CI_FIX_STATUS_STRINGS = frozenset(
    {
        "checking",
        "interrupted",
        "exhausted",
        "pending_timeout",
    }
)


class TestNoRawPRStatusStringsInBase:
    """Verify base.py no longer uses raw PR status string literals."""

    def test_no_raw_pr_status_in_finalize_repo_pr(self) -> None:
        """The _finalize_repo_pr method should use constants, not raw strings."""
        import helping_hands.lib.hands.v1.hand.base as mod

        source = Path(mod.__file__).read_text()  # type: ignore[arg-type]
        tree = ast.parse(source)

        # Find the _finalize_repo_pr method
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_finalize_repo_pr":
                method_source = ast.get_source_segment(source, node) or ""
                method_tree = ast.parse(method_source)
                literals = set()
                for child in ast.walk(method_tree):
                    if isinstance(child, ast.Constant) and isinstance(child.value, str):
                        literals.add(child.value)
                raw_statuses = literals & _PR_STATUS_STRINGS
                assert raw_statuses == set(), (
                    f"Raw PR status strings found in _finalize_repo_pr: {raw_statuses}"
                )
                return
        pytest.fail("_finalize_repo_pr method not found in base.py")


class TestNoRawCIFixStringsInCLIBase:
    """Verify cli/base.py no longer uses raw CI fix status string literals."""

    def test_no_raw_ci_fix_status_in_ci_fix_loop(self) -> None:
        """The _ci_fix_loop method should use constants, not raw strings."""
        import helping_hands.lib.hands.v1.hand.cli.base as mod

        source = Path(mod.__file__).read_text()  # type: ignore[arg-type]
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_ci_fix_loop"
            ):
                method_source = ast.get_source_segment(source, node) or ""
                method_tree = ast.parse(textwrap.dedent(method_source))
                literals = set()
                for child in ast.walk(method_tree):
                    if isinstance(child, ast.Constant) and isinstance(child.value, str):
                        literals.add(child.value)
                raw_statuses = literals & _CI_FIX_STATUS_STRINGS
                assert raw_statuses == set(), (
                    f"Raw CI fix status strings in _ci_fix_loop: {raw_statuses}"
                )
                return
        pytest.fail("_ci_fix_loop method not found in cli/base.py")


class TestNoRawPRMetaKeysInIterative:
    """Verify iterative.py uses imported constants for PR metadata keys."""

    def test_imports_pr_meta_constants(self) -> None:
        """iterative.py should import _PR_META_STATUS and _PR_META_URL."""
        import helping_hands.lib.hands.v1.hand.iterative as mod

        assert hasattr(mod, "_PR_META_STATUS")
        assert hasattr(mod, "_PR_META_URL")
        assert hasattr(mod, "_PR_STATUS_NO_CHANGES")
        assert hasattr(mod, "_PR_STATUS_DISABLED")


# ---------------------------------------------------------------------------
# Constant uniqueness — no duplicate values
# ---------------------------------------------------------------------------


class TestPRStatusUniqueness:
    """Verify all PR status constant values are unique."""

    def test_all_pr_status_values_unique(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUS_CREATED,
            _PR_STATUS_DISABLED,
            _PR_STATUS_ERROR,
            _PR_STATUS_GIT_ERROR,
            _PR_STATUS_INTERRUPTED,
            _PR_STATUS_MISSING_TOKEN,
            _PR_STATUS_NO_CHANGES,
            _PR_STATUS_NO_GITHUB_ORIGIN,
            _PR_STATUS_NO_REPO,
            _PR_STATUS_NOT_ATTEMPTED,
            _PR_STATUS_NOT_GIT_REPO,
            _PR_STATUS_PRECOMMIT_FAILED,
            _PR_STATUS_UPDATED,
        )

        values = [
            _PR_STATUS_CREATED,
            _PR_STATUS_DISABLED,
            _PR_STATUS_ERROR,
            _PR_STATUS_GIT_ERROR,
            _PR_STATUS_INTERRUPTED,
            _PR_STATUS_MISSING_TOKEN,
            _PR_STATUS_NO_CHANGES,
            _PR_STATUS_NO_GITHUB_ORIGIN,
            _PR_STATUS_NO_REPO,
            _PR_STATUS_NOT_ATTEMPTED,
            _PR_STATUS_NOT_GIT_REPO,
            _PR_STATUS_PRECOMMIT_FAILED,
            _PR_STATUS_UPDATED,
        ]
        assert len(values) == len(set(values)), "Duplicate PR status values found"

    def test_all_ci_fix_status_values_unique(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _CI_FIX_STATUS_CHECKING,
            _CI_FIX_STATUS_ERROR,
            _CI_FIX_STATUS_EXHAUSTED,
            _CI_FIX_STATUS_INTERRUPTED,
            _CI_FIX_STATUS_NO_CHECKS,
            _CI_FIX_STATUS_PENDING_TIMEOUT,
            _CI_FIX_STATUS_SUCCESS,
        )

        values = [
            _CI_FIX_STATUS_CHECKING,
            _CI_FIX_STATUS_ERROR,
            _CI_FIX_STATUS_EXHAUSTED,
            _CI_FIX_STATUS_INTERRUPTED,
            _CI_FIX_STATUS_NO_CHECKS,
            _CI_FIX_STATUS_PENDING_TIMEOUT,
            _CI_FIX_STATUS_SUCCESS,
        ]
        assert len(values) == len(set(values)), "Duplicate CI fix status values found"
