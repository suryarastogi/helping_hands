"""Tests for v166: _FAILURE_OUTPUT_TAIL_LENGTH consolidation and "on" added to truthy set.

Before v166, codex.py, claude.py, gemini.py, and opencode.py each defined their own
tail-length constant.  If one subclass's constant drifted, auth-failure detection
would scan different amounts of subprocess output per backend, causing inconsistent
"wrong credentials" detection.  The consolidation into base.py's single constant
means all four backends share the same scan window.

Adding "on" to _TRUTHY_VALUES matches common shell/ansible conventions where
FEATURE=on means enabled; without it, environment variables set to "on" would be
silently treated as false, disabling features for users following those conventions.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. _FAILURE_OUTPUT_TAIL_LENGTH consolidation
# ---------------------------------------------------------------------------


class TestFailureOutputTailConsolidation:
    """Verify _FAILURE_OUTPUT_TAIL_LENGTH is exported from cli/base.py and
    re-exported identically by all 4 CLI hand subclass modules."""

    def test_base_defines_constant(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FAILURE_OUTPUT_TAIL_LENGTH,
        )

        assert _FAILURE_OUTPUT_TAIL_LENGTH == 2000

    def test_base_constant_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FAILURE_OUTPUT_TAIL_LENGTH,
        )

        assert _FAILURE_OUTPUT_TAIL_LENGTH > 0

    def test_subclasses_use_auth_detection(self) -> None:
        """Since v271, codex/claude/opencode delegate to _format_cli_failure
        (which internally calls _detect_auth_failure).  Gemini still calls
        _detect_auth_failure directly due to its model-not-found branch."""
        import inspect

        from helping_hands.lib.hands.v1.hand.cli import claude, codex, gemini, opencode

        # Gemini still uses _detect_auth_failure directly
        assert "_detect_auth_failure" in inspect.getsource(gemini)

        # Others delegate via _format_cli_failure
        for mod in (claude, codex, opencode):
            src = inspect.getsource(mod)
            assert "_format_cli_failure" in src, (
                f"{mod.__name__} should use _format_cli_failure"
            )

    def test_constant_in_base_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import __all__

        assert "_FAILURE_OUTPUT_TAIL_LENGTH" in __all__


# ---------------------------------------------------------------------------
# 2. _CLI_TRUTHY_VALUES harmonization
# ---------------------------------------------------------------------------


class TestCLITruthyValues:
    """Verify _TRUTHY_VALUES includes 'on' and _is_truthy uses it."""

    def test_truthy_is_frozenset(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        assert isinstance(_TRUTHY_VALUES, frozenset)

    def test_truthy_contains_on(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        assert "on" in _TRUTHY_VALUES

    def test_truthy_expected_members(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        assert frozenset({"1", "true", "yes", "on"}) == _TRUTHY_VALUES

    def test_is_truthy_uses_truthy_values(self) -> None:
        """_is_truthy should accept 'on' (via _TRUTHY_VALUES)."""
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("on") is True

    def test_is_truthy_accepts_standard_truthy(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("1") is True
        assert _TwoPhaseCLIHand._is_truthy("true") is True
        assert _TwoPhaseCLIHand._is_truthy("yes") is True

    def test_is_truthy_rejects_falsy(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy("0") is False
        assert _TwoPhaseCLIHand._is_truthy("false") is False
        assert _TwoPhaseCLIHand._is_truthy("no") is False
        assert _TwoPhaseCLIHand._is_truthy("") is False

    def test_is_truthy_none_returns_false(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand._is_truthy(None) is False
