"""Tests for CodexCLIHand static/pure helper methods."""

from __future__ import annotations

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_codex_hand(tmp_path, model="gpt-5.2"):
    (tmp_path / "main.py").write_text("")
    config = Config(repo=str(tmp_path), model=model)
    repo_index = RepoIndex.from_path(tmp_path)
    return CodexCLIHand(config=config, repo_index=repo_index)


@pytest.fixture()
def codex_hand(tmp_path):
    return _make_codex_hand(tmp_path)


# ---------------------------------------------------------------------------
# _build_codex_failure_message
# ---------------------------------------------------------------------------


class TestBuildCodexFailureMessage:
    def test_generic_failure(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="something broke"
        )
        assert "Codex CLI failed (exit=1)" in msg
        assert "something broke" in msg

    def test_auth_failure_401(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg
        assert "OPENAI_API_KEY" in msg

    def test_auth_failure_missing_bearer(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1, output="Missing bearer or basic authentication"
        )
        assert "authentication failed" in msg

    def test_output_truncated_to_2000(self) -> None:
        long_output = "y" * 5000
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1, output=long_output
        )
        assert len(msg) < 5000


# ---------------------------------------------------------------------------
# _normalize_base_command
# ---------------------------------------------------------------------------


class TestNormalizeBaseCommand:
    def test_bare_codex_becomes_codex_exec(self, codex_hand) -> None:
        result = codex_hand._normalize_base_command(["codex"])
        assert result == ["codex", "exec"]

    def test_codex_exec_unchanged(self, codex_hand) -> None:
        result = codex_hand._normalize_base_command(["codex", "exec"])
        assert result == ["codex", "exec"]

    def test_other_command_passthrough(self, codex_hand) -> None:
        result = codex_hand._normalize_base_command(["other-tool"])
        # Should call super() which just returns as-is
        assert "other-tool" in result


# ---------------------------------------------------------------------------
# _apply_codex_exec_sandbox_defaults
# ---------------------------------------------------------------------------


class TestApplyCodexExecSandboxDefaults:
    def test_adds_default_sandbox_mode(self, codex_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CODEX_SANDBOX_MODE", raising=False)
        cmd = ["codex", "exec", "-p", "fix bug"]
        result = codex_hand._apply_codex_exec_sandbox_defaults(cmd)
        assert "--sandbox" in result
        assert "workspace-write" in result

    def test_no_inject_when_sandbox_present(self, codex_hand) -> None:
        cmd = ["codex", "exec", "--sandbox", "full-access", "-p", "fix"]
        result = codex_hand._apply_codex_exec_sandbox_defaults(cmd)
        assert result.count("--sandbox") == 1

    def test_no_inject_with_equals_syntax(self, codex_hand) -> None:
        cmd = ["codex", "exec", "--sandbox=full-access", "-p", "fix"]
        result = codex_hand._apply_codex_exec_sandbox_defaults(cmd)
        assert result == cmd

    def test_env_override(self, codex_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_SANDBOX_MODE", "danger-full-access")
        cmd = ["codex", "exec", "-p", "fix"]
        result = codex_hand._apply_codex_exec_sandbox_defaults(cmd)
        assert "--sandbox" in result
        assert "danger-full-access" in result

    def test_non_codex_exec_passthrough(self, codex_hand) -> None:
        cmd = ["other", "stuff"]
        result = codex_hand._apply_codex_exec_sandbox_defaults(cmd)
        assert result == cmd

    def test_codex_without_exec_passthrough(self, codex_hand) -> None:
        cmd = ["codex"]
        result = codex_hand._apply_codex_exec_sandbox_defaults(cmd)
        assert result == cmd


# ---------------------------------------------------------------------------
# _auto_sandbox_mode
# ---------------------------------------------------------------------------


class TestAutoSandboxMode:
    def test_non_docker_returns_workspace_write(self, codex_hand) -> None:
        # Not running in Docker
        assert codex_hand._auto_sandbox_mode() == "workspace-write"


# ---------------------------------------------------------------------------
# _skip_git_repo_check_enabled
# ---------------------------------------------------------------------------


class TestSkipGitRepoCheckEnabled:
    def test_defaults_to_true(self, codex_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", raising=False)
        assert codex_hand._skip_git_repo_check_enabled() is True

    def test_disabled_when_0(self, codex_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", "0")
        assert codex_hand._skip_git_repo_check_enabled() is False

    def test_enabled_when_1(self, codex_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", "1")
        assert codex_hand._skip_git_repo_check_enabled() is True


# ---------------------------------------------------------------------------
# _apply_codex_exec_git_repo_check_defaults
# ---------------------------------------------------------------------------


class TestApplyCodexExecGitRepoCheckDefaults:
    def test_adds_skip_flag_by_default(self, codex_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", raising=False)
        cmd = ["codex", "exec", "-p", "fix"]
        result = codex_hand._apply_codex_exec_git_repo_check_defaults(cmd)
        assert "--skip-git-repo-check" in result

    def test_no_inject_when_already_present(self, codex_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", raising=False)
        cmd = ["codex", "exec", "--skip-git-repo-check", "-p", "fix"]
        result = codex_hand._apply_codex_exec_git_repo_check_defaults(cmd)
        assert result.count("--skip-git-repo-check") == 1

    def test_no_inject_when_disabled(self, codex_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", "0")
        cmd = ["codex", "exec", "-p", "fix"]
        result = codex_hand._apply_codex_exec_git_repo_check_defaults(cmd)
        assert "--skip-git-repo-check" not in result

    def test_non_codex_exec_passthrough(self, codex_hand) -> None:
        cmd = ["other", "tool"]
        result = codex_hand._apply_codex_exec_git_repo_check_defaults(cmd)
        assert result == cmd


# ---------------------------------------------------------------------------
# _apply_backend_defaults (combines sandbox + git repo check)
# ---------------------------------------------------------------------------


class TestApplyBackendDefaults:
    def test_applies_both_defaults(self, codex_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CODEX_SANDBOX_MODE", raising=False)
        monkeypatch.delenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", raising=False)
        cmd = ["codex", "exec", "-p", "fix"]
        result = codex_hand._apply_backend_defaults(cmd)
        assert "--sandbox" in result
        assert "--skip-git-repo-check" in result
