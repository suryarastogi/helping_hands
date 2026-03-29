"""Tests for v260: unified truthy values, _is_truthy_env, and _get_env_stripped.

Before v260, pr_description.py defined _PR_TRUTHY_VALUES and cli/base.py
defined _CLI_TRUTHY_VALUES. Both were frozensets of flag strings but could
drift — e.g. if "on" was added to one but not the other, disabling a feature
via the env var would work from the CLI but not from the PR description path.

_is_truthy_env() and _get_env_stripped() centralise the two most common env
var read patterns. If _is_truthy_env stops stripping whitespace, environment
variables set with trailing newlines (common in shell scripts) are silently
treated as falsy.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# _TRUTHY_VALUES now includes "on"
# ---------------------------------------------------------------------------


class TestTruthyValuesUnified:
    """Verify _TRUTHY_VALUES is the single source of truth with 'on' included."""

    def test_truthy_is_frozenset(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        assert isinstance(_TRUTHY_VALUES, frozenset)

    def test_truthy_contains_on(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        assert "on" in _TRUTHY_VALUES

    def test_truthy_exact_members(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        assert frozenset({"1", "true", "yes", "on"}) == _TRUTHY_VALUES

    def test_no_pr_truthy_values_constant(self) -> None:
        """_PR_TRUTHY_VALUES was removed in v260."""
        import helping_hands.lib.hands.v1.hand.pr_description as mod

        assert not hasattr(mod, "_PR_TRUTHY_VALUES")

    def test_no_cli_truthy_values_constant(self) -> None:
        """_CLI_TRUTHY_VALUES was removed in v260."""
        import helping_hands.lib.hands.v1.hand.cli.base as mod

        assert not hasattr(mod, "_CLI_TRUTHY_VALUES")


# ---------------------------------------------------------------------------
# _is_truthy_env now strips whitespace
# ---------------------------------------------------------------------------


class TestIsTruthyEnvStrips:
    """Verify _is_truthy_env handles whitespace and 'on'."""

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "  true  ")
        assert _is_truthy_env("_TEST_TRUTHY") is True

    def test_strips_leading_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "  1")
        assert _is_truthy_env("_TEST_TRUTHY") is True

    def test_strips_trailing_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "yes  ")
        assert _is_truthy_env("_TEST_TRUTHY") is True

    def test_accepts_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "on")
        assert _is_truthy_env("_TEST_TRUTHY") is True

    def test_accepts_on_uppercase(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "ON")
        assert _is_truthy_env("_TEST_TRUTHY") is True

    def test_accepts_on_with_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "  on  ")
        assert _is_truthy_env("_TEST_TRUTHY") is True

    def test_rejects_random(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "nope")
        assert _is_truthy_env("_TEST_TRUTHY") is False

    def test_empty_is_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.setenv("_TEST_TRUTHY", "")
        assert _is_truthy_env("_TEST_TRUTHY") is False

    def test_unset_is_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.delenv("_TEST_TRUTHY", raising=False)
        assert _is_truthy_env("_TEST_TRUTHY") is False

    def test_default_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.delenv("_TEST_TRUTHY", raising=False)
        assert _is_truthy_env("_TEST_TRUTHY", "true") is True

    def test_default_fallback_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _is_truthy_env

        monkeypatch.delenv("_TEST_TRUTHY", raising=False)
        assert _is_truthy_env("_TEST_TRUTHY", "no") is False


# ---------------------------------------------------------------------------
# _get_env_stripped helper
# ---------------------------------------------------------------------------


class TestGetEnvStripped:
    """Verify _get_env_stripped returns stripped env var values."""

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _get_env_stripped

        monkeypatch.setenv("_TEST_STRIP", "  hello  ")
        assert _get_env_stripped("_TEST_STRIP") == "hello"

    def test_returns_empty_for_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _get_env_stripped

        monkeypatch.delenv("_TEST_STRIP", raising=False)
        assert _get_env_stripped("_TEST_STRIP") == ""

    def test_returns_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _get_env_stripped

        monkeypatch.delenv("_TEST_STRIP", raising=False)
        assert _get_env_stripped("_TEST_STRIP", "fallback") == "fallback"

    def test_returns_value_unchanged_if_no_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.lib.config import _get_env_stripped

        monkeypatch.setenv("_TEST_STRIP", "clean")
        assert _get_env_stripped("_TEST_STRIP") == "clean"

    def test_strips_tabs_and_newlines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _get_env_stripped

        monkeypatch.setenv("_TEST_STRIP", "\tvalue\n")
        assert _get_env_stripped("_TEST_STRIP") == "value"

    def test_empty_value_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.config import _get_env_stripped

        monkeypatch.setenv("_TEST_STRIP", "")
        assert _get_env_stripped("_TEST_STRIP") == ""

    def test_whitespace_only_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.lib.config import _get_env_stripped

        monkeypatch.setenv("_TEST_STRIP", "   ")
        assert _get_env_stripped("_TEST_STRIP") == ""


# ---------------------------------------------------------------------------
# Consumer simplification verification
# ---------------------------------------------------------------------------


class TestConsumerSimplification:
    """Verify consumers now use _is_truthy_env instead of manual patterns."""

    def test_is_disabled_uses_is_truthy_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """pr_description._is_disabled uses _is_truthy_env (accepts 'on')."""
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "on")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is True

    def test_is_disabled_strips_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "  true  ")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is True

    def test_draft_pr_enabled_default_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """E2E draft PR defaults to true."""
        monkeypatch.delenv("HELPING_HANDS_E2E_DRAFT_PR", raising=False)
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        assert E2EHand._draft_pr_enabled() is True

    def test_draft_pr_enabled_accepts_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "on")
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        assert E2EHand._draft_pr_enabled() is True

    def test_draft_pr_enabled_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "false")
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        assert E2EHand._draft_pr_enabled() is False

    def test_is_truthy_accepts_on(self) -> None:
        """CLI _is_truthy now uses unified _TRUTHY_VALUES with 'on'."""
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("on") is True

    def test_is_truthy_strips_whitespace(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("  true  ") is True

    def test_is_truthy_none_is_false(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy(None) is False
