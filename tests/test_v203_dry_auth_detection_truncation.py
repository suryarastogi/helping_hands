"""Tests for v203: DRY auth failure detection + text truncation helper.

Covers:
- _truncate_with_ellipsis: no-op for short text, truncation + ellipsis for long text,
  boundary cases
- _detect_auth_failure: shared token detection, extra_tokens, non-auth output,
  tail extraction length
- Subclass refactoring: claude/codex/gemini/opencode use _detect_auth_failure
  (no manual tail/lower_tail/any pattern)
- Claude _StreamJsonEmitter uses _truncate_with_ellipsis (no inline slicing)
"""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import (
    _AUTH_ERROR_TOKENS,
    _FAILURE_OUTPUT_TAIL_LENGTH,
    _detect_auth_failure,
    _truncate_with_ellipsis,
)

# ---------------------------------------------------------------------------
# _truncate_with_ellipsis
# ---------------------------------------------------------------------------


class TestTruncateWithEllipsis:
    """Unit tests for the _truncate_with_ellipsis helper."""

    def test_short_text_unchanged(self) -> None:
        assert _truncate_with_ellipsis("hello", 10) == "hello"

    def test_exact_limit_unchanged(self) -> None:
        assert _truncate_with_ellipsis("abcde", 5) == "abcde"

    def test_truncates_long_text(self) -> None:
        result = _truncate_with_ellipsis("abcdefghij", 7)
        assert result == "abcd..."
        assert len(result) == 7

    def test_empty_string(self) -> None:
        assert _truncate_with_ellipsis("", 5) == ""

    def test_limit_equals_four(self) -> None:
        """Limit of 4 means 1 char + '...'."""
        assert _truncate_with_ellipsis("abcdef", 4) == "a..."

    def test_returns_string(self) -> None:
        assert isinstance(_truncate_with_ellipsis("x" * 100, 10), str)

    def test_ellipsis_suffix(self) -> None:
        result = _truncate_with_ellipsis("a" * 50, 20)
        assert result.endswith("...")

    def test_no_ellipsis_when_within_limit(self) -> None:
        result = _truncate_with_ellipsis("short", 100)
        assert "..." not in result


# ---------------------------------------------------------------------------
# _detect_auth_failure
# ---------------------------------------------------------------------------


class TestDetectAuthFailure:
    """Unit tests for the _detect_auth_failure helper."""

    def test_detects_shared_auth_token(self) -> None:
        output = "some output\n401 Unauthorized\nmore stuff"
        is_auth, tail = _detect_auth_failure(output)
        assert is_auth is True
        assert "401 Unauthorized" in tail

    def test_detects_invalid_api_key(self) -> None:
        is_auth, _ = _detect_auth_failure("Error: Invalid API Key provided")
        assert is_auth is True

    def test_no_auth_failure_for_clean_output(self) -> None:
        is_auth, tail = _detect_auth_failure("Build completed successfully.")
        assert is_auth is False
        assert "Build completed successfully." in tail

    def test_extra_tokens_detected(self) -> None:
        output = "missing bearer or basic authentication"
        is_auth, _ = _detect_auth_failure(
            output, extra_tokens=("missing bearer or basic authentication",)
        )
        assert is_auth is True

    def test_extra_tokens_not_in_shared(self) -> None:
        """Extra tokens alone (not in shared set) should not match without passing them."""
        output = "missing bearer or basic authentication"
        is_auth, _ = _detect_auth_failure(output)
        assert is_auth is False

    def test_case_insensitive(self) -> None:
        is_auth, _ = _detect_auth_failure("AUTHENTICATION FAILED here")
        assert is_auth is True

    def test_tail_length_respected(self) -> None:
        """Output longer than _FAILURE_OUTPUT_TAIL_LENGTH is trimmed."""
        prefix = "x" * (_FAILURE_OUTPUT_TAIL_LENGTH + 500)
        output = prefix + "authentication failed"
        is_auth, tail = _detect_auth_failure(output)
        assert is_auth is True
        assert len(tail) <= _FAILURE_OUTPUT_TAIL_LENGTH

    def test_tail_strips_whitespace(self) -> None:
        output = "  \n  some output  \n  "
        _, tail = _detect_auth_failure(output)
        # The tail is extracted from stripped output
        assert tail == "some output"

    def test_returns_tuple(self) -> None:
        result = _detect_auth_failure("hello")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_empty_output(self) -> None:
        is_auth, tail = _detect_auth_failure("")
        assert is_auth is False
        assert tail == ""

    def test_all_shared_tokens_detected(self) -> None:
        """Each shared auth token should be independently detected."""
        for token in _AUTH_ERROR_TOKENS:
            is_auth, _ = _detect_auth_failure(f"prefix {token} suffix")
            assert is_auth is True, f"Failed to detect token: {token!r}"


# ---------------------------------------------------------------------------
# Subclass refactoring: no manual tail/lower_tail pattern
# ---------------------------------------------------------------------------


class TestSubclassesUseDetectAuthFailure:
    """Verify subclasses use _detect_auth_failure instead of inline patterns."""

    @pytest.mark.parametrize(
        "module_path,class_name",
        [
            ("helping_hands.lib.hands.v1.hand.cli.claude", "ClaudeCodeHand"),
            ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand"),
            ("helping_hands.lib.hands.v1.hand.cli.gemini", "GeminiCLIHand"),
            ("helping_hands.lib.hands.v1.hand.cli.opencode", "OpenCodeCLIHand"),
        ],
    )
    def test_no_manual_tail_extraction(self, module_path: str, class_name: str) -> None:
        """Failure message methods should not contain manual tail extraction."""
        mod = __import__(module_path, fromlist=[class_name])
        src = inspect.getsource(mod)
        # Should not have the old 3-line manual pattern
        assert "lower_tail = tail.lower()" not in src

    def test_gemini_imports_detect_auth_failure(self) -> None:
        """Gemini still uses _detect_auth_failure directly."""
        mod = __import__(
            "helping_hands.lib.hands.v1.hand.cli.gemini", fromlist=["GeminiCLIHand"]
        )
        src = inspect.getsource(mod)
        assert "_detect_auth_failure" in src

    @pytest.mark.parametrize(
        "module_path,class_name",
        [
            ("helping_hands.lib.hands.v1.hand.cli.claude", "ClaudeCodeHand"),
            ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand"),
            ("helping_hands.lib.hands.v1.hand.cli.opencode", "OpenCodeCLIHand"),
        ],
    )
    def test_imports_format_cli_failure(
        self, module_path: str, class_name: str
    ) -> None:
        """Since v271, these modules delegate to _format_cli_failure."""
        mod = __import__(module_path, fromlist=[class_name])
        src = inspect.getsource(mod)
        assert "_format_cli_failure" in src

    @pytest.mark.parametrize(
        "module_path,class_name",
        [
            ("helping_hands.lib.hands.v1.hand.cli.claude", "ClaudeCodeHand"),
            ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand"),
            ("helping_hands.lib.hands.v1.hand.cli.gemini", "GeminiCLIHand"),
            ("helping_hands.lib.hands.v1.hand.cli.opencode", "OpenCodeCLIHand"),
        ],
    )
    def test_no_direct_auth_error_tokens_import(
        self, module_path: str, class_name: str
    ) -> None:
        """Subclasses should no longer directly import _AUTH_ERROR_TOKENS."""
        mod = __import__(module_path, fromlist=[class_name])
        src = inspect.getsource(mod)
        assert "_AUTH_ERROR_TOKENS" not in src

    @pytest.mark.parametrize(
        "module_path,class_name",
        [
            ("helping_hands.lib.hands.v1.hand.cli.claude", "ClaudeCodeHand"),
            ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand"),
            ("helping_hands.lib.hands.v1.hand.cli.gemini", "GeminiCLIHand"),
            ("helping_hands.lib.hands.v1.hand.cli.opencode", "OpenCodeCLIHand"),
        ],
    )
    def test_no_failure_output_tail_length_import(
        self, module_path: str, class_name: str
    ) -> None:
        """Subclasses should no longer directly import _FAILURE_OUTPUT_TAIL_LENGTH."""
        mod = __import__(module_path, fromlist=[class_name])
        src = inspect.getsource(mod)
        assert "_FAILURE_OUTPUT_TAIL_LENGTH" not in src


# ---------------------------------------------------------------------------
# Claude _StreamJsonEmitter uses _truncate_with_ellipsis
# ---------------------------------------------------------------------------


class TestClaudeEmitterUsesTruncateHelper:
    """Verify _StreamJsonEmitter uses _truncate_with_ellipsis."""

    def test_no_inline_slicing_pattern(self) -> None:
        """The old `text[:limit - 3] + '...'` pattern should be gone."""
        from helping_hands.lib.hands.v1.hand.cli import claude

        src = inspect.getsource(claude._StreamJsonEmitter)
        assert '- 3] + "..."' not in src

    def test_imports_truncate_helper(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import claude

        src = inspect.getsource(claude)
        assert "_truncate_with_ellipsis" in src

    def test_summarize_tool_bash_truncates(self) -> None:
        """Bash commands exceeding limit are truncated with ellipsis."""
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _COMMAND_PREVIEW_MAX_LENGTH,
            _StreamJsonEmitter,
        )

        long_cmd = "x" * (_COMMAND_PREVIEW_MAX_LENGTH + 50)
        result = _StreamJsonEmitter._summarize_tool("Bash", {"command": long_cmd})
        assert result.startswith("$ ")
        assert result.endswith("...")
        # "$ " prefix (2 chars) + truncated command
        assert len(result) == 2 + _COMMAND_PREVIEW_MAX_LENGTH

    def test_summarize_tool_bash_short_unchanged(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        result = _StreamJsonEmitter._summarize_tool("Bash", {"command": "ls -la"})
        assert result == "$ ls -la"

    def test_summarize_tool_cron_create_truncates(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _COMMAND_PREVIEW_MAX_LENGTH,
            _StreamJsonEmitter,
        )

        long_prompt = "y" * (_COMMAND_PREVIEW_MAX_LENGTH + 50)
        result = _StreamJsonEmitter._summarize_tool(
            "CronCreate", {"prompt": long_prompt}
        )
        assert "..." in result
        assert result.startswith("CronCreate ")


# ---------------------------------------------------------------------------
# __all__ exports
# ---------------------------------------------------------------------------


class TestBaseAllExports:
    """Verify new helpers are in __all__."""

    def test_detect_auth_failure_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import base

        assert "_detect_auth_failure" in base.__all__

    def test_truncate_with_ellipsis_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import base

        assert "_truncate_with_ellipsis" in base.__all__


# ---------------------------------------------------------------------------
# Functional: failure messages still produce correct output
# ---------------------------------------------------------------------------


class TestFailureMessagesFunctional:
    """Ensure failure message methods still produce correct output after refactor."""

    def test_claude_auth_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="Error: 401 Unauthorized"
        )
        assert "authentication failed" in msg.lower()
        assert "ANTHROPIC_API_KEY" in msg

    def test_claude_generic_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="some random error"
        )
        assert "exit=1" in msg
        assert "authentication" not in msg.lower()

    def test_codex_auth_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1,
            output="missing bearer or basic authentication",
        )
        assert "authentication failed" in msg.lower()
        assert "OPENAI_API_KEY" in msg

    def test_codex_generic_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        msg = CodexCLIHand._build_codex_failure_message(return_code=2, output="timeout")
        assert "exit=2" in msg

    def test_gemini_auth_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1, output="gemini_api_key not set"
        )
        assert "authentication failed" in msg.lower()
        assert "GEMINI_API_KEY" in msg

    def test_gemini_generic_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=3, output="network error"
        )
        assert "exit=3" in msg

    def test_opencode_auth_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="authentication failed"
        )
        assert "authentication failed" in msg.lower()

    def test_opencode_generic_failure(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=4, output="crash"
        )
        assert "exit=4" in msg
