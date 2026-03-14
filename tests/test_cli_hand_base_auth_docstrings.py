"""Tests for v165: _AUTH_ERROR_TOKENS constant, _is_auth_error() helper, and CLI base docstrings."""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import (
    _AUTH_ERROR_TOKENS,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand
from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand
from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand
from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

# ---------------------------------------------------------------------------
# _AUTH_ERROR_TOKENS constant
# ---------------------------------------------------------------------------


class TestAuthErrorTokensConstant:
    def test_is_tuple(self) -> None:
        assert isinstance(_AUTH_ERROR_TOKENS, tuple)

    def test_not_empty(self) -> None:
        assert len(_AUTH_ERROR_TOKENS) > 0

    def test_all_strings(self) -> None:
        assert all(isinstance(t, str) for t in _AUTH_ERROR_TOKENS)

    def test_all_lowercase(self) -> None:
        for token in _AUTH_ERROR_TOKENS:
            assert token == token.lower(), f"{token!r} is not lowercase"

    def test_contains_common_markers(self) -> None:
        assert "401 unauthorized" in _AUTH_ERROR_TOKENS
        assert "authentication failed" in _AUTH_ERROR_TOKENS
        assert "invalid api key" in _AUTH_ERROR_TOKENS
        assert "unauthorized" in _AUTH_ERROR_TOKENS

    def test_has_docstring(self) -> None:
        # Module-level constant docstrings are not introspectable at runtime,
        # so we check the source code directly.
        source = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.cli.base",
                fromlist=["_AUTH_ERROR_TOKENS"],
            )
        )
        assert '"""' in source[source.index("_AUTH_ERROR_TOKENS") :][:500]


# ---------------------------------------------------------------------------
# _is_auth_error() static method
# ---------------------------------------------------------------------------


class TestIsAuthError:
    def test_detects_401_unauthorized(self) -> None:
        assert _TwoPhaseCLIHand._is_auth_error("Error: 401 Unauthorized")

    def test_detects_authentication_failed(self) -> None:
        assert _TwoPhaseCLIHand._is_auth_error("authentication failed for user")

    def test_detects_invalid_api_key(self) -> None:
        assert _TwoPhaseCLIHand._is_auth_error("Error: invalid api key provided")

    def test_detects_api_key_not_valid(self) -> None:
        assert _TwoPhaseCLIHand._is_auth_error("API key not valid.")

    def test_case_insensitive(self) -> None:
        assert _TwoPhaseCLIHand._is_auth_error("401 UNAUTHORIZED")
        assert _TwoPhaseCLIHand._is_auth_error("AUTHENTICATION FAILED")

    def test_no_match_returns_false(self) -> None:
        assert not _TwoPhaseCLIHand._is_auth_error("some random error output")

    def test_empty_output_returns_false(self) -> None:
        assert not _TwoPhaseCLIHand._is_auth_error("")

    def test_extra_tokens_match(self) -> None:
        assert _TwoPhaseCLIHand._is_auth_error(
            "missing ANTHROPIC_API_KEY",
            extra_tokens=("anthropic_api_key",),
        )

    def test_extra_tokens_no_match(self) -> None:
        assert not _TwoPhaseCLIHand._is_auth_error(
            "some other error",
            extra_tokens=("anthropic_api_key",),
        )

    def test_extra_tokens_empty_tuple(self) -> None:
        # Should still match base tokens
        assert _TwoPhaseCLIHand._is_auth_error("401 unauthorized", extra_tokens=())

    def test_has_docstring(self) -> None:
        assert _TwoPhaseCLIHand._is_auth_error.__doc__
        assert "authentication" in _TwoPhaseCLIHand._is_auth_error.__doc__.lower()


# ---------------------------------------------------------------------------
# CLI hands use _is_auth_error (behavioral regression tests)
# ---------------------------------------------------------------------------


class TestCLIHandsAuthDetection:
    """Verify each CLI hand's failure message still detects auth errors."""

    def test_claude_detects_auth(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg

    def test_claude_detects_anthropic_key(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="missing ANTHROPIC_API_KEY"
        )
        assert "authentication failed" in msg

    def test_claude_generic_failure(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="something else"
        )
        assert "Claude Code CLI failed" in msg

    def test_gemini_detects_auth(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg

    def test_gemini_detects_gemini_key(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="GEMINI_API_KEY is not set"
        )
        assert "authentication failed" in msg

    def test_gemini_generic_failure(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="something else"
        )
        assert "Gemini CLI failed" in msg

    def test_opencode_detects_auth(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg

    def test_opencode_generic_failure(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="something else"
        )
        assert "OpenCode CLI failed" in msg

    def test_codex_detects_auth(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg

    def test_codex_detects_bearer(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="Missing bearer or basic authentication"
        )
        assert "authentication failed" in msg

    def test_codex_generic_failure(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="something else"
        )
        assert "Codex CLI failed" in msg


# ---------------------------------------------------------------------------
# Google-style docstring presence tests
# ---------------------------------------------------------------------------


_DOCUMENTED_METHODS = (
    "_base_command",
    "_resolve_cli_model",
    "_render_command",
    "_build_failure_message",
    "_command_not_found_message",
    "_fallback_command_when_not_found",
    "_retry_command_after_failure",
    "_build_init_prompt",
    "_build_task_prompt",
    "_invoke_backend",
    "run",
    "stream",
)


class TestCLIBaseDocstrings:
    @pytest.mark.parametrize("method_name", _DOCUMENTED_METHODS)
    def test_method_has_docstring(self, method_name: str) -> None:
        method = getattr(_TwoPhaseCLIHand, method_name)
        assert method.__doc__, f"{method_name} should have a docstring"
        assert len(method.__doc__.strip()) > 20, f"{method_name} docstring is too short"

    @pytest.mark.parametrize("method_name", _DOCUMENTED_METHODS)
    def test_docstring_has_section(self, method_name: str) -> None:
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = method.__doc__ or ""
        # Every docstring should have either Args, Returns, Yields, or Raises
        has_section = any(
            section in doc for section in ("Args:", "Returns:", "Yields:", "Raises:")
        )
        assert has_section, (
            f"{method_name} docstring should have Args/Returns/Yields/Raises section"
        )
