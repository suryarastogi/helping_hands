"""Tests for _TwoPhaseCLIHand static utility methods."""

from __future__ import annotations

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand
from helping_hands.lib.repo import RepoIndex


class TestIsTruthy:
    def test_true_values(self) -> None:
        for val in ("1", "true", "yes", "on"):
            assert _TwoPhaseCLIHand._is_truthy(val) is True

    def test_case_insensitive(self) -> None:
        assert _TwoPhaseCLIHand._is_truthy("TRUE") is True
        assert _TwoPhaseCLIHand._is_truthy("Yes") is True
        assert _TwoPhaseCLIHand._is_truthy("ON") is True

    def test_false_values(self) -> None:
        for val in ("0", "false", "no", "off", ""):
            assert _TwoPhaseCLIHand._is_truthy(val) is False

    def test_none_returns_false(self) -> None:
        assert _TwoPhaseCLIHand._is_truthy(None) is False

    def test_whitespace_stripped(self) -> None:
        assert _TwoPhaseCLIHand._is_truthy("  true  ") is True
        assert _TwoPhaseCLIHand._is_truthy("  ") is False


class TestTruncateSummary:
    def test_under_limit_unchanged(self) -> None:
        assert _TwoPhaseCLIHand._truncate_summary("short", limit=100) == "short"

    def test_over_limit_truncates(self) -> None:
        text = "a" * 200
        result = _TwoPhaseCLIHand._truncate_summary(text, limit=50)
        assert result.startswith("a" * 50)
        assert result.endswith("...[truncated]")

    def test_strips_whitespace(self) -> None:
        assert _TwoPhaseCLIHand._truncate_summary("  hello  ", limit=100) == "hello"

    def test_exact_limit_unchanged(self) -> None:
        text = "x" * 50
        assert _TwoPhaseCLIHand._truncate_summary(text, limit=50) == text


class TestLooksLikeEditRequest:
    def test_detects_action_verbs(self) -> None:
        for verb in ("update", "fix", "add", "create", "implement", "refactor"):
            assert _TwoPhaseCLIHand._looks_like_edit_request(f"Please {verb} the code")

    def test_case_insensitive(self) -> None:
        assert _TwoPhaseCLIHand._looks_like_edit_request("UPDATE the config")
        assert _TwoPhaseCLIHand._looks_like_edit_request("Fix the bug")

    def test_rejects_neutral_prompts(self) -> None:
        assert not _TwoPhaseCLIHand._looks_like_edit_request("explain this code")
        assert not _TwoPhaseCLIHand._looks_like_edit_request("how does it work?")


class TestFloatEnv:
    def test_returns_default_when_not_set(self) -> None:
        assert _TwoPhaseCLIHand._float_env("__NOT_SET_TEST_VAR__", default=5.0) == 5.0

    def test_parses_valid_float(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_FLOAT__", "3.5")
        assert _TwoPhaseCLIHand._float_env("__TEST_FLOAT__", default=1.0) == 3.5

    def test_returns_default_for_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_FLOAT__", "abc")
        assert _TwoPhaseCLIHand._float_env("__TEST_FLOAT__", default=2.0) == 2.0

    def test_returns_default_for_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("__TEST_FLOAT__", "0")
        assert _TwoPhaseCLIHand._float_env("__TEST_FLOAT__", default=9.0) == 9.0

    def test_returns_default_for_negative(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("__TEST_FLOAT__", "-1.5")
        assert _TwoPhaseCLIHand._float_env("__TEST_FLOAT__", default=7.0) == 7.0


# ---------------------------------------------------------------------------
# _base_command shlex.split error wrapping
# ---------------------------------------------------------------------------


def _make_cli_stub(monkeypatch, env_value):
    """Create a minimal _TwoPhaseCLIHand stub with STUB_CMD env var."""
    monkeypatch.setenv("STUB_CMD", env_value)
    cls = type(
        "_Stub",
        (_TwoPhaseCLIHand,),
        {
            "_COMMAND_ENV_VAR": "STUB_CMD",
            "_DEFAULT_CLI_CMD": "stub-cli",
            "_DEFAULT_MODEL": "test-model",
            "_DEFAULT_APPEND_ARGS": (),
            "_PROMPT_PLACEHOLDER": "{prompt}",
            "_REPO_ROOT_PLACEHOLDER": "{repo}",
            "_VERBOSE_FLAGS": (),
            "run": lambda self, **kw: None,
            "stream": lambda self, **kw: None,
            "_pr_description_cmd": lambda self: None,
        },
    )
    return cls(
        config=Config(repo="/tmp/test", model="test"),
        repo_index=RepoIndex(root=None),
    )


class TestBaseCommandShlexError:
    """Verify shlex.split ValueError is wrapped with context."""

    def test_unclosed_quote_gives_clear_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub = _make_cli_stub(monkeypatch, "my-cli --flag 'unclosed")
        with pytest.raises(RuntimeError, match="invalid shell expression"):
            stub._base_command()

    def test_shlex_error_does_not_include_raw_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """v149: raw env var value is redacted from error message."""
        raw_value = 'my-cli "unclosed-with-secret-token'
        stub = _make_cli_stub(monkeypatch, raw_value)
        with pytest.raises(RuntimeError, match="invalid shell expression") as exc_info:
            stub._base_command()
        # The raw value should NOT appear in the error message
        assert raw_value not in str(exc_info.value)

    def test_valid_command_still_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        stub = _make_cli_stub(monkeypatch, "my-cli --flag value")
        result = stub._base_command()
        assert result == ["my-cli", "--flag", "value"]
