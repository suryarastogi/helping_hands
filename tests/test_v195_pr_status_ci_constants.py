"""Tests for v195: PR status constants, CI conclusion constants, model sentinels.

Validates that all extracted constants in base.py and cli/base.py have correct
values, types, and are used consistently across modules.
"""

from __future__ import annotations

import inspect
import re

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
from helping_hands.lib.hands.v1.hand.cli.base import (
    _CI_CONCLUSION_NO_CHECKS,
    _CI_CONCLUSION_PENDING,
    _CI_CONCLUSION_SUCCESS,
    _CI_POLL_MAX_MULTIPLIER,
    _MODEL_SENTINEL_VALUES,
    _TwoPhaseCLIHand,
)

# ---------------------------------------------------------------------------
# PR status constants — values
# ---------------------------------------------------------------------------


class TestPRStatusConstantValues:
    """Verify each _PR_STATUS_* constant has the expected string value."""

    def test_created(self) -> None:
        assert _PR_STATUS_CREATED == "created"

    def test_updated(self) -> None:
        assert _PR_STATUS_UPDATED == "updated"

    def test_disabled(self) -> None:
        assert _PR_STATUS_DISABLED == "disabled"

    def test_no_changes(self) -> None:
        assert _PR_STATUS_NO_CHANGES == "no_changes"

    def test_interrupted(self) -> None:
        assert _PR_STATUS_INTERRUPTED == "interrupted"

    def test_not_attempted(self) -> None:
        assert _PR_STATUS_NOT_ATTEMPTED == "not_attempted"

    def test_no_repo(self) -> None:
        assert _PR_STATUS_NO_REPO == "no_repo"

    def test_not_git_repo(self) -> None:
        assert _PR_STATUS_NOT_GIT_REPO == "not_git_repo"

    def test_no_github_origin(self) -> None:
        assert _PR_STATUS_NO_GITHUB_ORIGIN == "no_github_origin"

    def test_precommit_failed(self) -> None:
        assert _PR_STATUS_PRECOMMIT_FAILED == "precommit_failed"

    def test_missing_token(self) -> None:
        assert _PR_STATUS_MISSING_TOKEN == "missing_token"

    def test_git_error(self) -> None:
        assert _PR_STATUS_GIT_ERROR == "git_error"

    def test_error(self) -> None:
        assert _PR_STATUS_ERROR == "error"


# ---------------------------------------------------------------------------
# PR status constants — types and uniqueness
# ---------------------------------------------------------------------------


class TestPRStatusConstantTypes:
    """Verify PR status constants are strings and unique."""

    _ALL_PR_STATUSES = (
        _PR_STATUS_CREATED,
        _PR_STATUS_UPDATED,
        _PR_STATUS_DISABLED,
        _PR_STATUS_NO_CHANGES,
        _PR_STATUS_INTERRUPTED,
        _PR_STATUS_NOT_ATTEMPTED,
        _PR_STATUS_NO_REPO,
        _PR_STATUS_NOT_GIT_REPO,
        _PR_STATUS_NO_GITHUB_ORIGIN,
        _PR_STATUS_PRECOMMIT_FAILED,
        _PR_STATUS_MISSING_TOKEN,
        _PR_STATUS_GIT_ERROR,
        _PR_STATUS_ERROR,
    )

    def test_all_are_strings(self) -> None:
        for status in self._ALL_PR_STATUSES:
            assert isinstance(status, str), f"{status!r} is not a string"

    def test_all_non_empty(self) -> None:
        for status in self._ALL_PR_STATUSES:
            assert status.strip(), "Empty PR status found"

    def test_all_unique(self) -> None:
        assert len(set(self._ALL_PR_STATUSES)) == len(self._ALL_PR_STATUSES)

    def test_all_snake_case(self) -> None:
        for status in self._ALL_PR_STATUSES:
            assert re.fullmatch(r"[a-z][a-z_]*", status), (
                f"{status!r} is not snake_case"
            )


# ---------------------------------------------------------------------------
# PR status constants — no bare strings remain in base.py
# ---------------------------------------------------------------------------


class TestPRStatusNoBareStringsInBase:
    """Verify base.py _finalize_repo_pr uses constants, not bare strings."""

    def test_no_bare_pr_status_strings_in_finalize(self) -> None:
        from helping_hands.lib.hands.v1.hand import base as base_mod

        source = inspect.getsource(base_mod)
        # Find all "pr_status" assignments — they should use _PR_STATUS_*
        matches = re.findall(r'"pr_status":\s*"([^"]+)"', source)
        assert matches == [], f"Bare pr_status strings found in base.py: {matches}"


# ---------------------------------------------------------------------------
# CI conclusion constants
# ---------------------------------------------------------------------------


class TestCIConclusionConstants:
    """Verify CI conclusion constant values and types."""

    def test_success_value(self) -> None:
        assert _CI_CONCLUSION_SUCCESS == "success"

    def test_pending_value(self) -> None:
        assert _CI_CONCLUSION_PENDING == "pending"

    def test_no_checks_value(self) -> None:
        assert _CI_CONCLUSION_NO_CHECKS == "no_checks"

    def test_all_are_strings(self) -> None:
        for val in (
            _CI_CONCLUSION_SUCCESS,
            _CI_CONCLUSION_PENDING,
            _CI_CONCLUSION_NO_CHECKS,
        ):
            assert isinstance(val, str)

    def test_all_unique(self) -> None:
        vals = {
            _CI_CONCLUSION_SUCCESS,
            _CI_CONCLUSION_PENDING,
            _CI_CONCLUSION_NO_CHECKS,
        }
        assert len(vals) == 3


# ---------------------------------------------------------------------------
# CI poll multiplier
# ---------------------------------------------------------------------------


class TestCIPollMaxMultiplier:
    """Verify the CI poll max multiplier constant."""

    def test_value(self) -> None:
        assert _CI_POLL_MAX_MULTIPLIER == 2

    def test_is_int(self) -> None:
        assert isinstance(_CI_POLL_MAX_MULTIPLIER, int)

    def test_positive(self) -> None:
        assert _CI_POLL_MAX_MULTIPLIER > 0

    def test_used_in_ci_fix_loop(self) -> None:
        source = inspect.getsource(_TwoPhaseCLIHand._ci_fix_loop)
        assert "_CI_POLL_MAX_MULTIPLIER" in source


# ---------------------------------------------------------------------------
# Model sentinel values
# ---------------------------------------------------------------------------


class TestModelSentinelValues:
    """Verify _MODEL_SENTINEL_VALUES frozenset."""

    def test_is_frozenset(self) -> None:
        assert isinstance(_MODEL_SENTINEL_VALUES, frozenset)

    def test_contains_default(self) -> None:
        assert "default" in _MODEL_SENTINEL_VALUES

    def test_contains_none_string(self) -> None:
        assert "None" in _MODEL_SENTINEL_VALUES

    def test_exactly_two_members(self) -> None:
        assert len(_MODEL_SENTINEL_VALUES) == 2

    def test_used_in_cli_base_resolve(self) -> None:
        source = inspect.getsource(_TwoPhaseCLIHand._resolve_cli_model)
        assert "_MODEL_SENTINEL_VALUES" in source

    def test_used_in_opencode_resolve(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        source = inspect.getsource(OpenCodeCLIHand._resolve_cli_model)
        assert "_MODEL_SENTINEL_VALUES" in source


# ---------------------------------------------------------------------------
# Cross-module consistency: cli/base.py uses base.py PR status constants
# ---------------------------------------------------------------------------


class TestCrossModuleConsistency:
    """Verify cli/base.py imports and uses PR status constants from base.py."""

    def test_format_pr_status_uses_constants(self) -> None:
        source = inspect.getsource(_TwoPhaseCLIHand._format_pr_status_message)
        assert "_PR_STATUS_CREATED" in source
        assert "_PR_STATUS_UPDATED" in source
        assert "_PR_STATUS_DISABLED" in source
        assert "_PR_STATUS_NO_CHANGES" in source
        assert "_PR_STATUS_INTERRUPTED" in source

    def test_ci_fix_loop_uses_pr_status_constants(self) -> None:
        source = inspect.getsource(_TwoPhaseCLIHand._ci_fix_loop)
        assert "_PR_STATUS_CREATED" in source
        assert "_PR_STATUS_UPDATED" in source

    def test_ci_fix_loop_uses_conclusion_constants(self) -> None:
        source = inspect.getsource(_TwoPhaseCLIHand._ci_fix_loop)
        assert "_CI_CONCLUSION_SUCCESS" in source
        assert "_CI_CONCLUSION_PENDING" in source
        assert "_CI_CONCLUSION_NO_CHECKS" in source

    def test_no_bare_pr_status_in_cli_base_format(self) -> None:
        source = inspect.getsource(_TwoPhaseCLIHand._format_pr_status_message)
        bare = re.findall(r'status\s*==\s*"([^"]+)"', source)
        assert bare == [], (
            f"Bare pr_status comparisons in _format_pr_status_message: {bare}"
        )

    def test_no_bare_conclusion_in_ci_fix_loop(self) -> None:
        source = inspect.getsource(_TwoPhaseCLIHand._ci_fix_loop)
        bare = re.findall(r'conclusion\s*==\s*"([^"]+)"', source)
        assert bare == [], f"Bare conclusion comparisons in _ci_fix_loop: {bare}"


# ---------------------------------------------------------------------------
# Iterative.py uses PR status constants from base.py
# ---------------------------------------------------------------------------


class TestIterativeUsesConstants:
    """Verify iterative.py imports and uses PR status constants."""

    def test_langgraph_stream_uses_constants(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        source = inspect.getsource(BasicLangGraphHand.stream)
        assert "_PR_STATUS_NO_CHANGES" in source
        assert "_PR_STATUS_DISABLED" in source

    def test_no_bare_status_in_iterative_module(self) -> None:
        from helping_hands.lib.hands.v1.hand import iterative as mod

        source = inspect.getsource(mod)
        # Should not find {"no_changes", "disabled"} as bare strings in set literals
        bare = re.findall(r'\{"no_changes"', source)
        assert bare == [], "Bare 'no_changes' set literal found in iterative.py"


# ---------------------------------------------------------------------------
# __all__ exports include new constants
# ---------------------------------------------------------------------------


class TestAllExports:
    """Verify __all__ includes new constants."""

    def test_cli_base_exports_ci_constants(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import base as cli_base

        assert "_CI_CONCLUSION_SUCCESS" in cli_base.__all__
        assert "_CI_CONCLUSION_PENDING" in cli_base.__all__
        assert "_CI_CONCLUSION_NO_CHECKS" in cli_base.__all__
        assert "_CI_POLL_MAX_MULTIPLIER" in cli_base.__all__
        assert "_MODEL_SENTINEL_VALUES" in cli_base.__all__

    def test_cli_base_all_sorted(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import base as cli_base

        assert cli_base.__all__ == sorted(cli_base.__all__)
