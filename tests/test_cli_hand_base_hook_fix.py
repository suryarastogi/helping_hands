"""Tests for git pre-commit hook fix-and-retry logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.base import Hand
from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Stub classes
# ---------------------------------------------------------------------------


class _BaseStub(Hand):
    """Minimal Hand subclass for testing base class methods."""

    def __init__(self) -> None:
        pass  # bypass real __init__

    def run(self, prompt: str):  # type: ignore[override]
        raise NotImplementedError

    async def stream(self, prompt: str):  # type: ignore[override]
        raise NotImplementedError


class _CLIStub(_TwoPhaseCLIHand):
    """Minimal CLI hand subclass for testing override methods."""

    _CLI_LABEL = "stub"
    _BACKEND_NAME = "stub-backend"

    def __init__(self) -> None:
        self._interrupt_event = MagicMock()
        self._interrupt_event.is_set.return_value = False
        self._active_process = None
        self.repo_index = MagicMock()
        self.repo_index.root.resolve.return_value = Path("/fake/repo")
        self.config = MagicMock()
        self.config.model = "test-model"
        self.config.verbose = False
        self.auto_pr = True


# ===================================================================
# _is_git_hook_failure
# ===================================================================


class TestIsGitHookFailure:
    def test_husky_failure(self) -> None:
        msg = (
            "git failed (git commit -m msg): husky - pre-commit hook exited with code 1"
        )
        assert Hand._is_git_hook_failure(msg) is True

    def test_husky_colon_format(self) -> None:
        msg = "git failed: husky: pre-commit script failed"
        assert Hand._is_git_hook_failure(msg) is True

    def test_lint_staged(self) -> None:
        msg = "git failed: lint-staged found errors"
        assert Hand._is_git_hook_failure(msg) is True

    def test_eslint_found(self) -> None:
        msg = "git failed: ESLint found 5 problems"
        assert Hand._is_git_hook_failure(msg) is True

    def test_eslint_colon(self) -> None:
        msg = "git failed: eslint: some error"
        assert Hand._is_git_hook_failure(msg) is True

    def test_prettier(self) -> None:
        msg = "git failed: prettier --check failed"
        assert Hand._is_git_hook_failure(msg) is True

    def test_pre_commit_hook(self) -> None:
        msg = "git failed: pre-commit hook failed"
        assert Hand._is_git_hook_failure(msg) is True

    def test_hook_failed(self) -> None:
        msg = "git failed: hook failed (code 1)"
        assert Hand._is_git_hook_failure(msg) is True

    def test_case_insensitive(self) -> None:
        msg = "git failed: HUSKY - pre-commit"
        assert Hand._is_git_hook_failure(msg) is True

    def test_non_hook_error_returns_false(self) -> None:
        msg = "git failed (git commit -m msg): nothing to commit"
        assert Hand._is_git_hook_failure(msg) is False

    def test_detached_head_returns_false(self) -> None:
        msg = "git failed: HEAD detached at abc123"
        assert Hand._is_git_hook_failure(msg) is False


# ===================================================================
# _build_hook_fix_prompt
# ===================================================================


class TestBuildHookFixPrompt:
    def test_includes_error_output(self) -> None:
        prompt = _CLIStub._build_hook_fix_prompt("eslint: unused var 'x'")
        assert "eslint: unused var 'x'" in prompt

    def test_truncates_long_output(self) -> None:
        long_output = "x" * 4000
        prompt = _CLIStub._build_hook_fix_prompt(long_output)
        assert "...[truncated]" in prompt
        assert len(prompt) < 4000 + 500  # prompt text + truncated output

    def test_instruction_content(self) -> None:
        prompt = _CLIStub._build_hook_fix_prompt("error")
        assert "Do not run git commit yourself" in prompt
        assert "Do not make unrelated changes" in prompt


# ===================================================================
# _try_fix_git_hook_errors — base class no-op
# ===================================================================


class TestTryFixGitHookErrorsBaseNoop:
    def test_returns_false(self) -> None:
        stub = _BaseStub()
        assert stub._try_fix_git_hook_errors(Path("/repo"), "error") is False


# ===================================================================
# _try_fix_git_hook_errors — CLI override
# ===================================================================


class TestTryFixGitHookErrorsCLI:
    def test_invokes_backend_and_returns_true_on_changes(self) -> None:
        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})
        stub._repo_has_changes = MagicMock(return_value=True)

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "eslint error")

        assert result is True
        stub._render_command.assert_called_once()
        stub._repo_has_changes.assert_called_once()

    def test_returns_false_when_no_changes(self) -> None:
        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})
        stub._repo_has_changes = MagicMock(return_value=False)

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "error")

        assert result is False

    def test_handles_file_not_found_with_fallback(self) -> None:
        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})
        stub._fallback_command_when_not_found = MagicMock(
            return_value=["npx", "claude", "-p", "fix"]
        )
        stub._repo_has_changes = MagicMock(return_value=True)

        with patch(
            "subprocess.run",
            side_effect=[FileNotFoundError, MagicMock(returncode=0)],
        ):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "error")

        assert result is True

    def test_handles_file_not_found_no_fallback(self) -> None:
        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})
        stub._fallback_command_when_not_found = MagicMock(return_value=None)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "error")

        assert result is False

    def test_handles_fallback_also_file_not_found(self) -> None:
        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})
        stub._fallback_command_when_not_found = MagicMock(
            return_value=["npx", "claude", "-p", "fix"]
        )

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "error")

        assert result is False

    def test_handles_fallback_timeout(self) -> None:
        import subprocess

        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})
        stub._fallback_command_when_not_found = MagicMock(
            return_value=["npx", "claude", "-p", "fix"]
        )

        with patch(
            "subprocess.run",
            side_effect=[
                FileNotFoundError,
                subprocess.TimeoutExpired("npx", 300),
            ],
        ):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "error")

        assert result is False

    def test_handles_timeout(self) -> None:
        import subprocess

        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "error")

        assert result is False

    def test_nonzero_exit_still_checks_changes(self) -> None:
        stub = _CLIStub()
        stub._render_command = MagicMock(return_value=["claude", "-p", "fix"])
        stub._build_subprocess_env = MagicMock(return_value={})
        stub._repo_has_changes = MagicMock(return_value=True)

        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = stub._try_fix_git_hook_errors(Path("/repo"), "error")

        assert result is True
        stub._repo_has_changes.assert_called_once()


# ===================================================================
# _add_and_commit_with_hook_retry
# ===================================================================


class TestAddAndCommitWithHookRetry:
    def _make_gh(self, side_effect=None, return_value="abc1234"):
        gh = MagicMock()
        if side_effect:
            gh.add_and_commit.side_effect = side_effect
        else:
            gh.add_and_commit.return_value = return_value
        return gh

    def test_success_on_first_try(self) -> None:
        stub = _BaseStub()
        gh = self._make_gh(return_value="sha123")
        result = stub._add_and_commit_with_hook_retry(gh, Path("/repo"), "msg")
        assert result == "sha123"
        assert gh.add_and_commit.call_count == 1

    def test_non_hook_error_propagates(self) -> None:
        stub = _BaseStub()
        gh = self._make_gh(side_effect=RuntimeError("nothing to commit"))
        with pytest.raises(RuntimeError, match="nothing to commit"):
            stub._add_and_commit_with_hook_retry(gh, Path("/repo"), "msg")

    def test_hook_failure_fixed_and_retry_succeeds(self) -> None:
        stub = _BaseStub()
        stub._try_fix_git_hook_errors = MagicMock(return_value=True)
        gh = self._make_gh(
            side_effect=[
                RuntimeError("git failed: husky - pre-commit hook failed"),
                "sha456",
            ]
        )
        result = stub._add_and_commit_with_hook_retry(gh, Path("/repo"), "msg")
        assert result == "sha456"
        assert gh.add_and_commit.call_count == 2
        stub._try_fix_git_hook_errors.assert_called_once()

    def test_hook_failure_fix_no_changes(self) -> None:
        stub = _BaseStub()
        stub._try_fix_git_hook_errors = MagicMock(return_value=False)
        gh = self._make_gh(side_effect=RuntimeError("git failed: husky - hook failed"))
        with pytest.raises(RuntimeError, match="husky"):
            stub._add_and_commit_with_hook_retry(gh, Path("/repo"), "msg")
        assert gh.add_and_commit.call_count == 1

    def test_hook_failure_fix_but_retry_still_fails(self) -> None:
        stub = _BaseStub()
        stub._try_fix_git_hook_errors = MagicMock(return_value=True)
        gh = self._make_gh(
            side_effect=[
                RuntimeError("git failed: husky - hook failed"),
                RuntimeError("git failed: husky - hook failed again"),
            ]
        )
        with pytest.raises(RuntimeError, match="hook failed again"):
            stub._add_and_commit_with_hook_retry(gh, Path("/repo"), "msg")
        assert gh.add_and_commit.call_count == 2
