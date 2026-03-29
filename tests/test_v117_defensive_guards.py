"""Tests for v117: defensive guards against edge-case inputs in CLI hand plumbing.

_apply_verbose_flags must not crash or produce garbage output when passed an empty
command list — a regression would cause the verbose-mode subprocess call to fail
silently or raise an IndexError instead of returning early.

The _SUMMARY_CHAR_LIMIT consistency check ensures the truncation constant used in
_build_failure_message is honoured uniformly across CLI hand subclasses; divergence
causes some backends to send unbounded output to the AI model.

LangGraphHand.run() must handle empty or missing message lists from the agent loop
without raising an unhandled exception that aborts the entire task.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# CLI base stub
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _COMMAND_ENV_VAR = "STUB_CMD"
    _DEFAULT_CLI_CMD = "stub-cli"
    _DEFAULT_MODEL = "stub-model-1"
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ("--json",)
    _CONTAINER_ENABLED_ENV_VAR = "STUB_CONTAINER"
    _CONTAINER_IMAGE_ENV_VAR = "STUB_CONTAINER_IMAGE"
    _VERBOSE_CLI_FLAGS = ("--verbose", "--debug")
    _SUMMARY_CHAR_LIMIT = 6000

    def __init__(
        self,
        *,
        model: str = "default",
        verbose: bool = False,
    ) -> None:
        self.config = SimpleNamespace(
            model=model,
            verbose=verbose,
            use_native_cli_auth=False,
        )
        self.auto_pr = True
        self._active_process = None
        self._skill_catalog_dir = None


# ---------------------------------------------------------------------------
# _apply_verbose_flags: empty cmd guard
# ---------------------------------------------------------------------------


class TestApplyVerboseFlagsEmptyCmd:
    """Verify _apply_verbose_flags returns empty list for empty cmd."""

    def test_empty_cmd_returns_empty(self) -> None:
        stub = _Stub(verbose=True)
        result = stub._apply_verbose_flags([])
        assert result == []

    def test_single_element_cmd_inserts_after_binary(self) -> None:
        stub = _Stub(verbose=True)
        result = stub._apply_verbose_flags(["my-cli"])
        assert result[0] == "my-cli"
        assert "--verbose" in result
        assert "--debug" in result

    def test_not_verbose_returns_cmd_unchanged(self) -> None:
        stub = _Stub(verbose=False)
        cmd = ["my-cli", "--arg"]
        result = stub._apply_verbose_flags(cmd)
        assert result == ["my-cli", "--arg"]


# ---------------------------------------------------------------------------
# _build_failure_message: _SUMMARY_CHAR_LIMIT consistency
# ---------------------------------------------------------------------------


class TestBuildFailureMessageLimit:
    """Verify _build_failure_message uses _SUMMARY_CHAR_LIMIT, not hardcoded 2000."""

    def test_uses_summary_char_limit(self) -> None:
        stub = _Stub()
        stub._SUMMARY_CHAR_LIMIT = 50
        long_output = "x" * 200
        msg = stub._build_failure_message(return_code=1, output=long_output)
        # The tail should be limited to _SUMMARY_CHAR_LIMIT (50), not 2000
        assert "x" * 50 in msg
        assert "x" * 200 not in msg

    def test_short_output_unchanged(self) -> None:
        stub = _Stub()
        msg = stub._build_failure_message(return_code=42, output="short error")
        assert "short error" in msg
        assert "exit=42" in msg

    def test_default_limit_is_6000(self) -> None:
        stub = _Stub()
        long_output = "a" * 7000
        msg = stub._build_failure_message(return_code=1, output=long_output)
        # With _SUMMARY_CHAR_LIMIT=6000, the tail is 6000 chars
        output_line = msg.split("\n", 1)[1]
        assert len(output_line) == 6000

    def test_whitespace_stripped_before_truncation(self) -> None:
        stub = _Stub()
        stub._SUMMARY_CHAR_LIMIT = 10
        output = "   hello world   "
        msg = stub._build_failure_message(return_code=1, output=output)
        # "hello world" stripped to 11 chars, tail [-10:] = "ello world"
        assert "ello world" in msg


# ---------------------------------------------------------------------------
# LangGraphHand.run(): empty/missing messages defense
# ---------------------------------------------------------------------------


class TestLangGraphHandRunDefensive:
    """Verify LangGraphHand.run() handles empty/missing messages gracefully."""

    @pytest.fixture()
    def _patch_agent(self):
        with patch(
            "helping_hands.lib.hands.v1.hand.langgraph.LangGraphHand._build_agent"
        ) as mock_build:
            yield mock_build

    @pytest.fixture()
    def _hand(self, _patch_agent):
        from helping_hands.lib.hands.v1.hand.langgraph import LangGraphHand

        config = SimpleNamespace(
            model="test-model",
            verbose=False,
            repo="",
            prompt="",
            max_iterations=1,
            no_pr=True,
            use_native_cli_auth=False,
            ci_check_wait_minutes=0,
            tools=(),
            skills=(),
            enabled_tools=(),
            enabled_skills=(),
            enable_execution=False,
            enable_web=False,
        )
        repo_index = SimpleNamespace(
            root=Path("/tmp/fake-repo"),
            files=[],
            tree_snapshot="",
        )
        hand = LangGraphHand(config, repo_index)
        return hand, _patch_agent

    def test_empty_messages_returns_empty_content(self, _hand) -> None:
        hand, _mock_build = _hand
        hand._agent.invoke.return_value = {"messages": []}
        resp = hand.run("hello")
        assert resp.message == ""

    def test_missing_messages_key_returns_empty_content(self, _hand) -> None:
        hand, _mock_build = _hand
        hand._agent.invoke.return_value = {}
        resp = hand.run("hello")
        assert resp.message == ""

    def test_none_messages_returns_empty_content(self, _hand) -> None:
        hand, _mock_build = _hand
        hand._agent.invoke.return_value = {"messages": None}
        resp = hand.run("hello")
        assert resp.message == ""

    def test_normal_message_still_works(self, _hand) -> None:
        hand, _mock_build = _hand
        fake_msg = MagicMock()
        fake_msg.content = "All done."
        hand._agent.invoke.return_value = {"messages": [fake_msg]}
        resp = hand.run("do something")
        assert resp.message == "All done."

    def test_str_fallback_still_works(self, _hand) -> None:
        hand, _mock_build = _hand
        hand._agent.invoke.return_value = {"messages": ["plain string"]}
        resp = hand.run("hello")
        assert resp.message == "plain string"
