"""Tests for v193: DRY _AUTH_ERROR_TOKENS, iterative docstrings, cross-module sync.

Covers:
- _AUTH_ERROR_TOKENS shared constant in cli/base.py (value, type, contents)
- Cross-module import consistency (claude, codex, gemini, opencode all use base)
- Iterative docstrings (BasicLangGraphHand.run/stream, BasicAtomicHand.run/stream)
- ClaudeCodeHand._EXTRA_AUTH_TOKENS backend-specific constant
"""

from __future__ import annotations

import inspect

from helping_hands.lib.hands.v1.hand.cli.base import _AUTH_ERROR_TOKENS

# ---------------------------------------------------------------------------
# _AUTH_ERROR_TOKENS shared constant
# ---------------------------------------------------------------------------


class TestAuthErrorTokensSharedConstant:
    """Verify _AUTH_ERROR_TOKENS in cli/base.py is the canonical source."""

    def test_is_tuple(self) -> None:
        assert isinstance(_AUTH_ERROR_TOKENS, tuple)

    def test_has_five_tokens(self) -> None:
        assert len(_AUTH_ERROR_TOKENS) == 5

    def test_all_lowercase_strings(self) -> None:
        for token in _AUTH_ERROR_TOKENS:
            assert isinstance(token, str)
            assert token == token.lower(), f"{token!r} is not lowercase"

    def test_contains_401_unauthorized(self) -> None:
        assert "401 unauthorized" in _AUTH_ERROR_TOKENS

    def test_contains_authentication_failed(self) -> None:
        assert "authentication failed" in _AUTH_ERROR_TOKENS

    def test_contains_invalid_api_key(self) -> None:
        assert "invalid api key" in _AUTH_ERROR_TOKENS

    def test_contains_api_key_not_valid(self) -> None:
        assert "api key not valid" in _AUTH_ERROR_TOKENS

    def test_contains_unauthorized(self) -> None:
        assert "unauthorized" in _AUTH_ERROR_TOKENS


# ---------------------------------------------------------------------------
# Cross-module import consistency
# ---------------------------------------------------------------------------


class TestAuthErrorTokensCrossModuleSync:
    """All CLI hands import _AUTH_ERROR_TOKENS from the same base module."""

    def test_opencode_uses_same_object(self) -> None:
        """OpenCode imports _AUTH_ERROR_TOKENS from base (same object identity)."""
        import helping_hands.lib.hands.v1.hand.cli.opencode as mod

        assert mod._AUTH_ERROR_TOKENS is _AUTH_ERROR_TOKENS

    def test_claude_uses_same_object(self) -> None:
        """Claude imports _AUTH_ERROR_TOKENS from base (same object identity)."""
        import helping_hands.lib.hands.v1.hand.cli.claude as mod

        assert mod._AUTH_ERROR_TOKENS is _AUTH_ERROR_TOKENS

    def test_codex_uses_same_object(self) -> None:
        """Codex imports _AUTH_ERROR_TOKENS from base (same object identity)."""
        import helping_hands.lib.hands.v1.hand.cli.codex as mod

        assert mod._AUTH_ERROR_TOKENS is _AUTH_ERROR_TOKENS

    def test_gemini_uses_same_object(self) -> None:
        """Gemini imports _AUTH_ERROR_TOKENS from base (same object identity)."""
        import helping_hands.lib.hands.v1.hand.cli.gemini as mod

        assert mod._AUTH_ERROR_TOKENS is _AUTH_ERROR_TOKENS


# ---------------------------------------------------------------------------
# ClaudeCodeHand._EXTRA_AUTH_TOKENS
# ---------------------------------------------------------------------------


class TestClaudeExtraAuthTokens:
    """Verify ClaudeCodeHand has backend-specific auth tokens."""

    def test_extra_auth_tokens_is_tuple(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        assert isinstance(ClaudeCodeHand._EXTRA_AUTH_TOKENS, tuple)

    def test_extra_auth_tokens_contains_anthropic_api_key(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        assert "anthropic_api_key" in ClaudeCodeHand._EXTRA_AUTH_TOKENS

    def test_claude_auth_detection_uses_shared_tokens(self) -> None:
        """Shared tokens should trigger Claude auth failure message."""
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        for token in _AUTH_ERROR_TOKENS:
            result = ClaudeCodeHand._build_claude_failure_message(
                return_code=1, output=f"Error: {token}"
            )
            assert "authentication failed" in result.lower(), (
                f"Shared token {token!r} did not trigger auth message"
            )

    def test_claude_extra_token_triggers_auth_message(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        result = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="Missing ANTHROPIC_API_KEY"
        )
        assert "authentication failed" in result.lower()


# ---------------------------------------------------------------------------
# Codex auth detection uses shared tokens
# ---------------------------------------------------------------------------


class TestCodexAuthDetection:
    """Verify Codex uses shared _AUTH_ERROR_TOKENS for auth detection."""

    def test_shared_token_triggers_auth_message(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        result = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="Error: 401 Unauthorized"
        )
        assert "authentication failed" in result.lower()

    def test_codex_specific_token_triggers_auth_message(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        result = CodexCLIHand._build_codex_failure_message(
            return_code=1,
            output="Missing Bearer or Basic Authentication",
        )
        assert "authentication failed" in result.lower()

    def test_generic_error_uses_fallback_message(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        result = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="Some other error"
        )
        assert "Codex CLI failed" in result


# ---------------------------------------------------------------------------
# Gemini auth detection uses shared tokens
# ---------------------------------------------------------------------------


class TestGeminiAuthDetection:
    """Verify Gemini uses shared _AUTH_ERROR_TOKENS for auth detection."""

    def test_shared_token_triggers_auth_message(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        result = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="Error: invalid api key"
        )
        assert "authentication failed" in result.lower()

    def test_gemini_specific_token_triggers_auth_message(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        result = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="Missing GEMINI_API_KEY"
        )
        assert "authentication failed" in result.lower()


# ---------------------------------------------------------------------------
# BasicLangGraphHand docstrings
# ---------------------------------------------------------------------------


class TestLangGraphHandDocstrings:
    """Verify BasicLangGraphHand.run and .stream have Google-style docstrings."""

    def test_run_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        doc = inspect.getdoc(BasicLangGraphHand.run)
        assert doc, "BasicLangGraphHand.run() is missing a docstring"

    def test_run_docstring_has_args(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        doc = inspect.getdoc(BasicLangGraphHand.run)
        assert "Args:" in doc

    def test_run_docstring_has_returns(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        doc = inspect.getdoc(BasicLangGraphHand.run)
        assert "Returns:" in doc

    def test_run_docstring_mentions_handresponse(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        doc = inspect.getdoc(BasicLangGraphHand.run)
        assert "HandResponse" in doc

    def test_stream_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        doc = inspect.getdoc(BasicLangGraphHand.stream)
        assert doc, "BasicLangGraphHand.stream() is missing a docstring"

    def test_stream_docstring_has_args(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        doc = inspect.getdoc(BasicLangGraphHand.stream)
        assert "Args:" in doc

    def test_stream_docstring_has_yields(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        doc = inspect.getdoc(BasicLangGraphHand.stream)
        assert "Yields:" in doc


# ---------------------------------------------------------------------------
# BasicAtomicHand docstrings
# ---------------------------------------------------------------------------


class TestAtomicHandDocstrings:
    """Verify BasicAtomicHand.run and .stream have Google-style docstrings."""

    def test_run_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.run)
        assert doc, "BasicAtomicHand.run() is missing a docstring"

    def test_run_docstring_has_args(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.run)
        assert "Args:" in doc

    def test_run_docstring_has_returns(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.run)
        assert "Returns:" in doc

    def test_run_docstring_mentions_handresponse(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.run)
        assert "HandResponse" in doc

    def test_stream_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.stream)
        assert doc, "BasicAtomicHand.stream() is missing a docstring"

    def test_stream_docstring_has_args(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.stream)
        assert "Args:" in doc

    def test_stream_docstring_has_yields(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.stream)
        assert "Yields:" in doc

    def test_stream_docstring_mentions_assertionerror(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        doc = inspect.getdoc(BasicAtomicHand.stream)
        assert "AssertionError" in doc
