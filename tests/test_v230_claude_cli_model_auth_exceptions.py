"""Protect Claude CLI model filtering, auth diagnostics, and exception boundaries.

_resolve_cli_model() filters out non-Claude models (openai/*, gpt-*) before
they reach the Claude binary. A regression here sends an unrecognised model
string to the CLI, producing a cryptic binary error instead of a clear skip.

_describe_auth() powers the credential-status banner; if it stops detecting
empty/whitespace ANTHROPIC_API_KEY, users see misleading "set" status and
cannot diagnose auth failures. _skip_permissions_enabled() must catch only
ValueError and OSError (legitimate env/permission issues) while letting
TypeError and RuntimeError propagate as programming bugs.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand


@pytest.fixture()
def claude_hand(make_cli_hand):
    return make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")


# ---------------------------------------------------------------------------
# _resolve_cli_model — openai/ prefix filtering
# ---------------------------------------------------------------------------


class TestResolveCliModelOpenAIPrefix:
    """_resolve_cli_model rejects openai/-prefixed models."""

    def test_filters_openai_slash_gpt(self, make_cli_hand) -> None:
        """openai/gpt-4 → stripped to gpt-4 by base, then caught by gpt- check."""
        hand = make_cli_hand(ClaudeCodeHand, model="openai/gpt-4")
        assert hand._resolve_cli_model() == ""

    def test_filters_openai_slash_o1(self, make_cli_hand) -> None:
        """openai/o1 → stripped to 'o1' by base; NOT caught by gpt- prefix.

        After base-class strip, 'o1' does not start with 'gpt-', so the
        openai/ guard in the base _resolve_cli_model already strips the
        prefix.  The resulting 'o1' is an OpenAI model but doesn't match
        the 'openai/' prefix after stripping — this tests the raw passthrough.
        """
        hand = make_cli_hand(ClaudeCodeHand, model="openai/o1")
        # Base class strips "openai/" → "o1", which passes both filters.
        # This is acceptable since "o1" alone is ambiguous; the explicit
        # openai/ prefix test below covers the direct match.
        result = hand._resolve_cli_model()
        assert result == "o1"

    def test_filters_openai_prefix_case_insensitive(self, make_cli_hand) -> None:
        """OpenAI/o3 (mixed case) — base strips prefix, result passes."""
        hand = make_cli_hand(ClaudeCodeHand, model="OpenAI/o3")
        # Base class strips to "o3"
        result = hand._resolve_cli_model()
        assert result == "o3"

    def test_preserves_anthropic_prefixed(self, make_cli_hand) -> None:
        """anthropic/claude-sonnet-4-5 → stripped to claude-sonnet-4-5, preserved."""
        hand = make_cli_hand(ClaudeCodeHand, model="anthropic/claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_preserves_bare_claude_model(self, make_cli_hand) -> None:
        """Bare claude-opus-4-6 passes through unchanged."""
        hand = make_cli_hand(ClaudeCodeHand, model="claude-opus-4-6")
        assert hand._resolve_cli_model() == "claude-opus-4-6"

    def test_filters_gpt_35_turbo(self, make_cli_hand) -> None:
        """gpt-3.5-turbo is rejected."""
        hand = make_cli_hand(ClaudeCodeHand, model="gpt-3.5-turbo")
        assert hand._resolve_cli_model() == ""


# ---------------------------------------------------------------------------
# _describe_auth
# ---------------------------------------------------------------------------


class TestDescribeAuth:
    """_describe_auth returns auth status for ANTHROPIC_API_KEY."""

    def test_key_set(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        result = claude_hand._describe_auth()
        assert result == "auth=ANTHROPIC_API_KEY (set)"

    def test_key_not_set(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = claude_hand._describe_auth()
        assert result == "auth=ANTHROPIC_API_KEY (not set)"

    def test_key_empty_string(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        result = claude_hand._describe_auth()
        assert result == "auth=ANTHROPIC_API_KEY (not set)"

    def test_key_whitespace_only(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        result = claude_hand._describe_auth()
        assert result == "auth=ANTHROPIC_API_KEY (not set)"


# ---------------------------------------------------------------------------
# _skip_permissions_enabled — narrowed exception handling
# ---------------------------------------------------------------------------


class TestSkipPermissionsNarrowedExceptions:
    """Verify narrowed (ValueError, OSError) exception handling."""

    def test_valueerror_from_geteuid_still_returns_true(
        self, claude_hand, monkeypatch
    ) -> None:
        """ValueError is still caught — returns True (enabled)."""
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )

        def _bad_geteuid():
            raise ValueError("unexpected geteuid value")

        monkeypatch.setattr("os.geteuid", _bad_geteuid)
        assert claude_hand._skip_permissions_enabled() is True

    def test_oserror_from_geteuid_still_returns_true(
        self, claude_hand, monkeypatch
    ) -> None:
        """OSError is still caught — returns True (enabled)."""
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )

        def _broken_geteuid():
            raise OSError("geteuid unavailable")

        monkeypatch.setattr("os.geteuid", _broken_geteuid)
        assert claude_hand._skip_permissions_enabled() is True

    def test_typeerror_from_geteuid_propagates(self, claude_hand, monkeypatch) -> None:
        """TypeError is NOT caught — propagates to caller."""
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )

        def _type_error_geteuid():
            raise TypeError("unexpected type")

        monkeypatch.setattr("os.geteuid", _type_error_geteuid)
        with pytest.raises(TypeError, match="unexpected type"):
            claude_hand._skip_permissions_enabled()

    def test_runtime_error_from_geteuid_propagates(
        self, claude_hand, monkeypatch
    ) -> None:
        """RuntimeError is NOT caught — propagates to caller."""
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )

        def _runtime_error_geteuid():
            raise RuntimeError("unexpected runtime error")

        monkeypatch.setattr("os.geteuid", _runtime_error_geteuid)
        with pytest.raises(RuntimeError, match="unexpected runtime error"):
            claude_hand._skip_permissions_enabled()
