"""Tests for the Codex CLI backend in server/grill.py.

Protects the pure helpers and subprocess wrapper added in PR #185 that enable
the Grill Me interactive planning feature to use the Codex CLI as an
alternative to the Claude Code CLI.  ``_build_codex_full_prompt`` must
correctly embed conversation history into a single prompt string because Codex
has no native session/resume capability.  ``_invoke_codex_turn`` must handle
subprocess lifecycle (success, timeout, not-found, non-zero exit) and sandbox
mode selection (env override vs Docker detection).
"""

from __future__ import annotations

from subprocess import TimeoutExpired
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.server.grill import (
    _CODEX_TURN_TIMEOUT_S,
    _build_codex_full_prompt,
    _invoke_codex_turn,
)

# ---------------------------------------------------------------------------
# _CODEX_TURN_TIMEOUT_S constant
# ---------------------------------------------------------------------------


class TestCodexTurnTimeoutConstant:
    """Guard the timeout constant value and type."""

    def test_value(self) -> None:
        assert _CODEX_TURN_TIMEOUT_S == 300

    def test_type(self) -> None:
        assert isinstance(_CODEX_TURN_TIMEOUT_S, int)

    def test_positive(self) -> None:
        assert _CODEX_TURN_TIMEOUT_S > 0


# ---------------------------------------------------------------------------
# _build_codex_full_prompt
# ---------------------------------------------------------------------------


class TestBuildCodexFullPrompt:
    """Tests for the prompt builder that embeds conversation history."""

    def test_empty_history_produces_begin_interview(self) -> None:
        result = _build_codex_full_prompt("System text", [], "Hello")
        assert "System text" in result
        assert "User: Hello" in result
        assert "Begin the interview" in result
        assert "Conversation so far" not in result

    def test_with_history_produces_conversation_block(self) -> None:
        history = [
            {"role": "assistant", "content": "Welcome!"},
            {"role": "user", "content": "Tell me more"},
        ]
        result = _build_codex_full_prompt("System text", history, "New msg")
        assert "Conversation so far" in result
        assert "AI: Welcome!" in result
        assert "User: Tell me more" in result
        assert "User: New msg" in result
        assert "Respond as the AI interviewer" in result

    def test_no_ai_prefix_instruction(self) -> None:
        """Both paths instruct the model not to prefix with 'AI:'."""
        empty = _build_codex_full_prompt("sys", [], "hi")
        assert "no 'AI:' prefix" in empty.lower() or "no 'AI:' prefix" in empty

        with_hist = _build_codex_full_prompt(
            "sys", [{"role": "assistant", "content": "x"}], "hi"
        )
        assert "no 'AI:' prefix" in with_hist

    def test_system_prompt_appears_first(self) -> None:
        result = _build_codex_full_prompt("SYSTEM_START", [], "msg")
        assert result.startswith("SYSTEM_START")

    def test_single_turn_history(self) -> None:
        history = [{"role": "assistant", "content": "Only one turn"}]
        result = _build_codex_full_prompt("sys", history, "follow-up")
        assert "AI: Only one turn" in result
        assert "User: follow-up" in result


# ---------------------------------------------------------------------------
# _invoke_codex_turn
# ---------------------------------------------------------------------------


class TestInvokeCodexTurnSuccess:
    """Happy-path tests for _invoke_codex_turn."""

    @patch("helping_hands.server.grill.subprocess.run")
    def test_returns_stdout_stripped(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(
            returncode=0, stdout="  response text  \n", stderr=""
        )
        result = _invoke_codex_turn(
            user_message="hi",
            cwd="/repo",
            system_prompt="sys",
            conversation_history=[],
        )
        assert result == "response text"

    @patch("helping_hands.server.grill.subprocess.run")
    def test_passes_model_flag(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        _invoke_codex_turn(
            user_message="hi",
            cwd="/repo",
            system_prompt="sys",
            conversation_history=[],
            model="gpt-5.2",
        )
        cmd = mock_run.call_args[0][0]
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "gpt-5.2"

    @patch("helping_hands.server.grill.subprocess.run")
    def test_no_model_flag_when_none(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        _invoke_codex_turn(
            user_message="hi",
            cwd="/repo",
            system_prompt="sys",
            conversation_history=[],
            model=None,
        )
        cmd = mock_run.call_args[0][0]
        assert "--model" not in cmd

    @patch("helping_hands.server.grill.subprocess.run")
    def test_on_status_called(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        status_cb = MagicMock()
        _invoke_codex_turn(
            user_message="hi",
            cwd="/repo",
            system_prompt="sys",
            conversation_history=[],
            on_status=status_cb,
        )
        status_cb.assert_any_call("Thinking...")
        status_cb.assert_any_call("Turn complete")
        assert status_cb.call_count == 2

    @patch("helping_hands.server.grill.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_default_sandbox_mode_non_docker(
        self,
        mock_exists: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Outside Docker, default sandbox mode is 'workspace-write'."""
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        mock_exists.return_value = False
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("HELPING_HANDS_CODEX_SANDBOX_MODE", None)
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )
        cmd = mock_run.call_args[0][0]
        sandbox_idx = cmd.index("--sandbox")
        assert cmd[sandbox_idx + 1] == "workspace-write"

    @patch("helping_hands.server.grill.subprocess.run")
    def test_sandbox_mode_env_override(self, mock_run: MagicMock) -> None:
        """HELPING_HANDS_CODEX_SANDBOX_MODE env var overrides auto-detection."""
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        with patch.dict(
            "os.environ",
            {"HELPING_HANDS_CODEX_SANDBOX_MODE": "custom-mode"},
        ):
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )
        cmd = mock_run.call_args[0][0]
        sandbox_idx = cmd.index("--sandbox")
        assert cmd[sandbox_idx + 1] == "custom-mode"

    @patch("helping_hands.server.grill.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_docker_detection_uses_full_access(
        self, mock_exists: MagicMock, mock_run: MagicMock
    ) -> None:
        """Inside Docker (/.dockerenv exists), sandbox is 'danger-full-access'."""
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        mock_exists.return_value = True
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("HELPING_HANDS_CODEX_SANDBOX_MODE", None)
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )
        cmd = mock_run.call_args[0][0]
        sandbox_idx = cmd.index("--sandbox")
        assert cmd[sandbox_idx + 1] == "danger-full-access"

    @patch("helping_hands.server.grill.subprocess.run")
    def test_timeout_matches_constant(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        _invoke_codex_turn(
            user_message="hi",
            cwd="/repo",
            system_prompt="sys",
            conversation_history=[],
        )
        assert mock_run.call_args[1]["timeout"] == _CODEX_TURN_TIMEOUT_S

    @patch("helping_hands.server.grill.subprocess.run")
    def test_cwd_passed_to_subprocess(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        _invoke_codex_turn(
            user_message="hi",
            cwd="/my/repo",
            system_prompt="sys",
            conversation_history=[],
        )
        assert mock_run.call_args[1]["cwd"] == "/my/repo"


class TestInvokeCodexTurnErrors:
    """Error-path tests for _invoke_codex_turn."""

    @patch("helping_hands.server.grill.subprocess.run")
    def test_file_not_found_raises_runtime_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("codex not found")
        with pytest.raises(RuntimeError, match="not installed or not on PATH"):
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )

    @patch("helping_hands.server.grill.subprocess.run")
    def test_timeout_raises_runtime_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = TimeoutExpired("codex", _CODEX_TURN_TIMEOUT_S)
        with pytest.raises(RuntimeError, match="timed out"):
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )

    @patch("helping_hands.server.grill.subprocess.run")
    def test_nonzero_exit_raises_with_stderr(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(
            returncode=1, stdout="", stderr="bad model"
        )
        with pytest.raises(RuntimeError, match="bad model"):
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )

    @patch("helping_hands.server.grill.subprocess.run")
    def test_nonzero_exit_fallback_message(self, mock_run: MagicMock) -> None:
        """When stderr is empty, error message includes exit code."""
        mock_run.return_value = SimpleNamespace(returncode=42, stdout="", stderr="")
        with pytest.raises(RuntimeError, match="exit code 42"):
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )

    @patch("helping_hands.server.grill.subprocess.run")
    def test_long_stderr_truncated(self, mock_run: MagicMock) -> None:
        """Error text is truncated to 500 chars."""
        long_stderr = "x" * 1000
        mock_run.return_value = SimpleNamespace(
            returncode=1, stdout="", stderr=long_stderr
        )
        with pytest.raises(RuntimeError) as exc_info:
            _invoke_codex_turn(
                user_message="hi",
                cwd="/repo",
                system_prompt="sys",
                conversation_history=[],
            )
        # The error message contains at most 500 chars of the stderr
        error_msg = str(exc_info.value)
        # "Codex CLI error: " prefix + 500 chars
        assert len(error_msg) <= len("Codex CLI error: ") + 500

    @patch("helping_hands.server.grill.subprocess.run")
    def test_command_includes_skip_git_repo_check(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        _invoke_codex_turn(
            user_message="hi",
            cwd="/repo",
            system_prompt="sys",
            conversation_history=[],
        )
        cmd = mock_run.call_args[0][0]
        assert "--skip-git-repo-check" in cmd

    @patch("helping_hands.server.grill.subprocess.run")
    def test_command_starts_with_codex_exec(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        _invoke_codex_turn(
            user_message="hi",
            cwd="/repo",
            system_prompt="sys",
            conversation_history=[],
        )
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "codex"
        assert cmd[1] == "exec"
