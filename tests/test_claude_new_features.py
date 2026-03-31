"""Tests for new Claude Code CLI hand features.

Covers:
- ``--permission-mode`` support as an alternative to ``--dangerously-skip-permissions``
- ``--mcp-config`` support for MCP server configuration
- ``--add-dir`` support for reference repo passthrough
- ``--resume`` support for resuming the most recent session
- ``--no-user-profile`` flag for consistent automation behavior
- Tool summary additions for newer Claude Code tools (ToolSearch, SendMessage, etc.)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from helping_hands.lib.hands.v1.hand.cli.claude import (
    _DEFAULT_PERMISSION_MODE,
    _VALID_PERMISSION_MODES,
    ClaudeCodeHand,
    _StreamJsonEmitter,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hand() -> ClaudeCodeHand:
    """Create a minimal ClaudeCodeHand without full initialisation."""
    hand = ClaudeCodeHand.__new__(ClaudeCodeHand)
    hand._config = type("C", (), {"enable_execution": False, "verbose": False})()
    hand._last_session_id = ""
    hand._next_invoke_continue = False
    hand._cumulative_cost_usd = 0.0
    hand._cumulative_input_tokens = 0
    hand._cumulative_output_tokens = 0
    return hand


# ===========================================================================
# --permission-mode
# ===========================================================================


class TestPermissionModeConstants:
    """Verify permission mode constants are correct."""

    def test_valid_modes_is_frozenset(self) -> None:
        assert isinstance(_VALID_PERMISSION_MODES, frozenset)

    def test_valid_modes_contains_expected(self) -> None:
        assert "default" in _VALID_PERMISSION_MODES
        assert "plan" in _VALID_PERMISSION_MODES
        assert "bypassPermissions" in _VALID_PERMISSION_MODES

    def test_default_mode_is_bypass(self) -> None:
        assert _DEFAULT_PERMISSION_MODE == "bypassPermissions"

    def test_constants_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import claude

        assert "_VALID_PERMISSION_MODES" in claude.__all__
        assert "_DEFAULT_PERMISSION_MODE" in claude.__all__


class TestResolvePermissionMode:
    """Tests for ClaudeCodeHand._resolve_permission_mode."""

    def test_empty_when_not_set(self) -> None:
        hand = _make_hand()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HELPING_HANDS_CLAUDE_PERMISSION_MODE", None)
            assert hand._resolve_permission_mode() == ""

    def test_returns_valid_mode(self) -> None:
        hand = _make_hand()
        for mode in _VALID_PERMISSION_MODES:
            with patch.dict(os.environ, {"HELPING_HANDS_CLAUDE_PERMISSION_MODE": mode}):
                assert hand._resolve_permission_mode() == mode

    def test_ignores_invalid_mode(self) -> None:
        hand = _make_hand()
        with patch.dict(
            os.environ, {"HELPING_HANDS_CLAUDE_PERMISSION_MODE": "invalid"}
        ):
            assert hand._resolve_permission_mode() == ""

    def test_strips_whitespace(self) -> None:
        hand = _make_hand()
        with patch.dict(
            os.environ, {"HELPING_HANDS_CLAUDE_PERMISSION_MODE": "  plan  "}
        ):
            assert hand._resolve_permission_mode() == "plan"


class TestInjectPermissionMode:
    """Tests for ClaudeCodeHand._inject_permission_mode."""

    def test_injects_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_permission_mode(cmd, "plan")
        assert result == ["claude", "--permission-mode", "plan", "-p", "hello"]

    def test_skips_when_already_present(self) -> None:
        cmd = ["claude", "--permission-mode", "default", "-p", "hello"]
        result = ClaudeCodeHand._inject_permission_mode(cmd, "plan")
        assert result == cmd

    def test_skips_when_empty(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_permission_mode(cmd, "")
        assert result == cmd

    def test_appends_when_no_p_flag(self) -> None:
        cmd = ["claude"]
        result = ClaudeCodeHand._inject_permission_mode(cmd, "bypassPermissions")
        assert "--permission-mode" in result
        assert "bypassPermissions" in result


class TestApplyBackendDefaultsPermissionMode:
    """Test that --permission-mode takes precedence over --dangerously-skip-permissions."""

    def test_permission_mode_takes_precedence(self) -> None:
        hand = _make_hand()
        cmd = ["claude", "-p", "hello"]
        with patch.dict(os.environ, {"HELPING_HANDS_CLAUDE_PERMISSION_MODE": "plan"}):
            result = hand._apply_backend_defaults(cmd)
        assert "--permission-mode" in result
        assert "plan" in result
        assert "--dangerously-skip-permissions" not in result

    def test_falls_back_to_skip_permissions(self) -> None:
        hand = _make_hand()
        cmd = ["claude", "-p", "hello"]
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HELPING_HANDS_CLAUDE_PERMISSION_MODE", None)
            result = hand._apply_backend_defaults(cmd)
        assert "--dangerously-skip-permissions" in result


# ===========================================================================
# --mcp-config
# ===========================================================================


class TestResolveMcpConfig:
    """Tests for ClaudeCodeHand._resolve_mcp_config."""

    def test_empty_when_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HELPING_HANDS_CLAUDE_MCP_CONFIG", None)
            assert ClaudeCodeHand._resolve_mcp_config() == ""

    def test_returns_path(self) -> None:
        with patch.dict(
            os.environ, {"HELPING_HANDS_CLAUDE_MCP_CONFIG": "/path/to/mcp.json"}
        ):
            assert ClaudeCodeHand._resolve_mcp_config() == "/path/to/mcp.json"

    def test_strips_whitespace(self) -> None:
        with patch.dict(
            os.environ, {"HELPING_HANDS_CLAUDE_MCP_CONFIG": "  /path/mcp.json  "}
        ):
            assert ClaudeCodeHand._resolve_mcp_config() == "/path/mcp.json"


class TestInjectMcpConfig:
    """Tests for ClaudeCodeHand._inject_mcp_config."""

    def test_injects_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_mcp_config(cmd, "/path/mcp.json")
        assert result == ["claude", "--mcp-config", "/path/mcp.json", "-p", "hello"]

    def test_skips_when_already_present(self) -> None:
        cmd = ["claude", "--mcp-config", "/old.json", "-p", "hello"]
        result = ClaudeCodeHand._inject_mcp_config(cmd, "/new.json")
        assert result == cmd

    def test_skips_when_empty(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_mcp_config(cmd, "")
        assert result == cmd


# ===========================================================================
# --add-dir
# ===========================================================================


class TestResolveAddDirs:
    """Tests for ClaudeCodeHand._resolve_add_dirs."""

    def test_empty_when_no_sources(self) -> None:
        hand = _make_hand()
        hand.repo_index = type("RI", (), {"reference_repos": []})()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HELPING_HANDS_CLAUDE_ADD_DIRS", None)
            assert hand._resolve_add_dirs() == []

    def test_from_env_var(self) -> None:
        hand = _make_hand()
        hand.repo_index = type("RI", (), {"reference_repos": []})()
        with patch.dict(os.environ, {"HELPING_HANDS_CLAUDE_ADD_DIRS": "/a,/b,/c"}):
            assert hand._resolve_add_dirs() == ["/a", "/b", "/c"]

    def test_from_reference_repos(self) -> None:
        hand = _make_hand()
        hand.repo_index = type(
            "RI", (), {"reference_repos": [("repo1", Path("/ref/repo1"))]}
        )()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HELPING_HANDS_CLAUDE_ADD_DIRS", None)
            result = hand._resolve_add_dirs()
        assert "/ref/repo1" in result

    def test_deduplicates(self) -> None:
        hand = _make_hand()
        hand.repo_index = type(
            "RI", (), {"reference_repos": [("repo1", Path("/shared"))]}
        )()
        with patch.dict(os.environ, {"HELPING_HANDS_CLAUDE_ADD_DIRS": "/shared"}):
            result = hand._resolve_add_dirs()
        assert result.count("/shared") == 1


class TestInjectAddDirs:
    """Tests for ClaudeCodeHand._inject_add_dirs."""

    def test_injects_multiple_dirs(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_add_dirs(cmd, ["/a", "/b"])
        assert result == [
            "claude",
            "--add-dir",
            "/a",
            "--add-dir",
            "/b",
            "-p",
            "hello",
        ]

    def test_skips_when_empty(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_add_dirs(cmd, [])
        assert result == cmd


# ===========================================================================
# --no-user-profile
# ===========================================================================


class TestNoUserProfile:
    """Tests for --no-user-profile support."""

    def test_enabled_by_default(self) -> None:
        hand = _make_hand()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HELPING_HANDS_CLAUDE_NO_USER_PROFILE", None)
            assert hand._no_user_profile_enabled() is True

    def test_disabled_when_set_to_zero(self) -> None:
        hand = _make_hand()
        with patch.dict(os.environ, {"HELPING_HANDS_CLAUDE_NO_USER_PROFILE": "0"}):
            assert hand._no_user_profile_enabled() is False

    def test_inject_adds_flag(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_no_user_profile(cmd)
        assert result == ["claude", "--no-user-profile", "-p", "hello"]

    def test_inject_skips_when_present(self) -> None:
        cmd = ["claude", "--no-user-profile", "-p", "hello"]
        result = ClaudeCodeHand._inject_no_user_profile(cmd)
        assert result == cmd


# ===========================================================================
# --resume
# ===========================================================================


class TestSessionResume:
    """Tests for --resume session support."""

    def test_disabled_by_default(self) -> None:
        hand = _make_hand()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HELPING_HANDS_CLAUDE_SESSION_RESUME", None)
            assert hand._session_resume_enabled() is False

    def test_enabled_when_set_to_one(self) -> None:
        hand = _make_hand()
        with patch.dict(os.environ, {"HELPING_HANDS_CLAUDE_SESSION_RESUME": "1"}):
            assert hand._session_resume_enabled() is True

    def test_inject_replaces_p_with_resume(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_resume_session(cmd)
        assert result == ["claude", "--resume", "hello"]

    def test_inject_skips_when_resume_present(self) -> None:
        cmd = ["claude", "--resume", "hello"]
        result = ClaudeCodeHand._inject_resume_session(cmd)
        assert result == cmd

    def test_inject_skips_when_continue_present(self) -> None:
        cmd = ["claude", "--continue", "hello"]
        result = ClaudeCodeHand._inject_resume_session(cmd)
        assert result == cmd

    def test_inject_preserves_other_flags(self) -> None:
        cmd = ["claude", "--verbose", "-p", "hello"]
        result = ClaudeCodeHand._inject_resume_session(cmd)
        assert "--verbose" in result
        assert "--resume" in result
        assert "-p" not in result


# ===========================================================================
# New tool summaries
# ===========================================================================


class TestNewToolSummaries:
    """Tests for tool summaries of newer Claude Code tools."""

    def test_tool_search(self) -> None:
        result = _StreamJsonEmitter._summarize_tool(
            "ToolSearch", {"query": "select:Read"}
        )
        assert result == "ToolSearch 'select:Read'"

    def test_tool_search_empty(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("ToolSearch", {})
        assert result == "ToolSearch"

    def test_send_message(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("SendMessage", {"to": "agent-123"})
        assert result == "SendMessage -> agent-123"

    def test_send_message_empty(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("SendMessage", {})
        assert result == "SendMessage"

    def test_task_output(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("TaskOutput", {"task_id": "abc123"})
        assert result == "TaskOutput abc123"

    def test_task_output_empty(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("TaskOutput", {})
        assert result == "TaskOutput"

    def test_task_stop(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("TaskStop", {"task_id": "def456"})
        assert result == "TaskStop def456"

    def test_task_stop_empty(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("TaskStop", {})
        assert result == "TaskStop"

    def test_ask_user_question(self) -> None:
        result = _StreamJsonEmitter._summarize_tool(
            "AskUserQuestion", {"question": "Should I proceed?"}
        )
        assert result == "AskUser: Should I proceed?"

    def test_ask_user_question_truncates(self) -> None:
        long_q = "x" * 100
        result = _StreamJsonEmitter._summarize_tool(
            "AskUserQuestion", {"question": long_q}
        )
        assert result.startswith("AskUser: ")
        assert result.endswith("...")

    def test_ask_user_question_empty(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("AskUserQuestion", {})
        assert result == "AskUserQuestion"

    def test_enter_plan_mode_static(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("EnterPlanMode", {})
        assert result == "EnterPlanMode"

    def test_exit_plan_mode_static(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("ExitPlanMode", {})
        assert result == "ExitPlanMode"

    def test_exit_worktree_static(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("ExitWorktree", {})
        assert result == "ExitWorktree"
