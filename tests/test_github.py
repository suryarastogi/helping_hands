"""Tests for helping_hands.lib.github."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from helping_hands.lib.github import GitHubClient, PRResult, _run_git

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GITHUB_TOKEN is always set so GitHubClient can be constructed."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_token_for_tests")


@pytest.fixture()
def client() -> GitHubClient:
    with patch("helping_hands.lib.github.Github"):
        return GitHubClient()


# ---------------------------------------------------------------------------
# _run_git helper
# ---------------------------------------------------------------------------


class TestRunGit:
    @patch("helping_hands.lib.github.subprocess.run")
    def test_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"],
            returncode=0,
            stdout="clean\n",
            stderr="",
        )
        result = _run_git(["git", "status"])
        assert result.stdout == "clean\n"
        mock_run.assert_called_once()

    @patch("helping_hands.lib.github.subprocess.run")
    def test_failure_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "fail"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repo",
        )
        with pytest.raises(RuntimeError, match="fatal: not a git repo"):
            _run_git(["git", "fail"])


# ---------------------------------------------------------------------------
# Auth / construction
# ---------------------------------------------------------------------------


class TestGitHubClientAuth:
    def test_raises_without_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with pytest.raises(ValueError, match="No GitHub token provided"):
            GitHubClient()

    def test_uses_env_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_from_env")
        with patch("helping_hands.lib.github.Github"):
            c = GitHubClient()
        assert c.token == "ghp_from_env"

    def test_explicit_token_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_from_env")
        with patch("helping_hands.lib.github.Github"):
            c = GitHubClient(token="ghp_explicit")
        assert c.token == "ghp_explicit"

    def test_gh_token_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "ghp_fallback")
        with patch("helping_hands.lib.github.Github"):
            c = GitHubClient()
        assert c.token == "ghp_fallback"


# ---------------------------------------------------------------------------
# whoami
# ---------------------------------------------------------------------------


class TestWhoami:
    def test_returns_user_info(self, client: GitHubClient) -> None:
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_user.name = "Test User"
        mock_user.html_url = "https://github.com/testuser"
        client._gh.get_user.return_value = mock_user

        info = client.whoami()
        assert info == {
            "login": "testuser",
            "name": "Test User",
            "url": "https://github.com/testuser",
        }


# ---------------------------------------------------------------------------
# clone
# ---------------------------------------------------------------------------


class TestClone:
    @patch("helping_hands.lib.github._run_git")
    def test_clone_default(
        self, mock_git: MagicMock, client: GitHubClient, tmp_path: Path
    ) -> None:
        dest = tmp_path / "repo"
        result = client.clone("owner/repo", dest)
        assert result == dest
        cmd = mock_git.call_args[0][0]
        assert "clone" in cmd
        assert "--depth" in cmd
        assert "1" in cmd
        assert str(dest) in cmd

    @patch("helping_hands.lib.github._run_git")
    def test_clone_with_branch_full_history(
        self, mock_git: MagicMock, client: GitHubClient, tmp_path: Path
    ) -> None:
        dest = tmp_path / "repo"
        client.clone("owner/repo", dest, branch="dev", depth=None)
        cmd = mock_git.call_args[0][0]
        assert "--branch" in cmd
        assert "dev" in cmd
        assert "--depth" not in cmd


# ---------------------------------------------------------------------------
# Branch operations
# ---------------------------------------------------------------------------


class TestBranch:
    @patch("helping_hands.lib.github._run_git")
    def test_create_branch(self, mock_git: MagicMock, tmp_path: Path) -> None:
        GitHubClient.create_branch(tmp_path, "feat/new")
        cmd = mock_git.call_args[0][0]
        assert cmd == ["git", "checkout", "-b", "feat/new"]
        assert mock_git.call_args[1]["cwd"] == tmp_path

    @patch("helping_hands.lib.github._run_git")
    def test_switch_branch(self, mock_git: MagicMock, tmp_path: Path) -> None:
        GitHubClient.switch_branch(tmp_path, "main")
        cmd = mock_git.call_args[0][0]
        assert cmd == ["git", "checkout", "main"]

    @patch("helping_hands.lib.github._run_git")
    def test_current_branch(self, mock_git: MagicMock, tmp_path: Path) -> None:
        mock_git.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="feat/x\n", stderr=""
        )
        branch = GitHubClient.current_branch(tmp_path)
        assert branch == "feat/x"


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------


class TestAddAndCommit:
    @patch("helping_hands.lib.github._run_git")
    def test_add_all_and_commit(self, mock_git: MagicMock, tmp_path: Path) -> None:
        mock_git.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc1234\n", stderr=""
        )
        sha = GitHubClient.add_and_commit(tmp_path, "initial commit")
        assert sha == "abc1234"
        calls = mock_git.call_args_list
        assert calls[0] == call(["git", "add", "."], cwd=tmp_path)
        assert calls[1] == call(["git", "commit", "-m", "initial commit"], cwd=tmp_path)

    @patch("helping_hands.lib.github._run_git")
    def test_add_specific_paths(self, mock_git: MagicMock, tmp_path: Path) -> None:
        mock_git.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="def5678\n", stderr=""
        )
        GitHubClient.add_and_commit(tmp_path, "add files", paths=["a.py", "b.py"])
        add_cmd = mock_git.call_args_list[0][0][0]
        assert add_cmd == ["git", "add", "a.py", "b.py"]


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------


class TestPush:
    @patch("helping_hands.lib.github._run_git")
    def test_push_default(
        self, mock_git: MagicMock, client: GitHubClient, tmp_path: Path
    ) -> None:
        mock_git.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="main\n", stderr=""
        )
        client.push(tmp_path)
        push_call = mock_git.call_args_list[-1]
        cmd = push_call[0][0]
        assert cmd == ["git", "push", "-u", "origin", "main"]

    @patch("helping_hands.lib.github._run_git")
    def test_push_explicit_branch(
        self, mock_git: MagicMock, client: GitHubClient, tmp_path: Path
    ) -> None:
        client.push(tmp_path, branch="feat/x", set_upstream=False)
        cmd = mock_git.call_args[0][0]
        assert cmd == ["git", "push", "origin", "feat/x"]


# ---------------------------------------------------------------------------
# Pull requests
# ---------------------------------------------------------------------------


class TestCreatePR:
    def test_creates_pr(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.number = 42
        mock_pr.html_url = "https://github.com/owner/repo/pull/42"
        mock_pr.title = "Add feature"
        mock_repo.create_pull.return_value = mock_pr
        client._gh.get_repo.return_value = mock_repo

        result = client.create_pr(
            "owner/repo",
            title="Add feature",
            body="Details",
            head="feat/x",
            base="main",
            draft=True,
        )

        assert isinstance(result, PRResult)
        assert result.number == 42
        assert result.url == "https://github.com/owner/repo/pull/42"
        assert result.head == "feat/x"
        assert result.base == "main"
        mock_repo.create_pull.assert_called_once_with(
            title="Add feature",
            body="Details",
            head="feat/x",
            base="main",
            draft=True,
        )


class TestListPRs:
    def test_list_prs(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        pr1 = MagicMock()
        pr1.number, pr1.title, pr1.html_url = 1, "Fix A", "url1"
        pr1.state, pr1.head.ref, pr1.base.ref = "open", "fix/a", "main"
        pr2 = MagicMock()
        pr2.number, pr2.title, pr2.html_url = 2, "Fix B", "url2"
        pr2.state, pr2.head.ref, pr2.base.ref = "open", "fix/b", "main"
        mock_repo.get_pulls.return_value = [pr1, pr2]
        client._gh.get_repo.return_value = mock_repo

        prs = client.list_prs("owner/repo", limit=10)
        assert len(prs) == 2
        assert prs[0]["number"] == 1
        assert prs[1]["title"] == "Fix B"


class TestGetPR:
    def test_get_pr(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        pr = MagicMock()
        pr.number, pr.title, pr.body = 5, "Title", "Body"
        pr.html_url = "url5"
        pr.state, pr.head.ref, pr.base.ref = "open", "feat/y", "main"
        pr.mergeable, pr.merged = True, False
        mock_repo.get_pull.return_value = pr
        client._gh.get_repo.return_value = mock_repo

        result = client.get_pr("owner/repo", 5)
        assert result["number"] == 5
        assert result["mergeable"] is True
        assert result["merged"] is False


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager_calls_close(self, client: GitHubClient) -> None:
        with client as c:
            assert c is client
        client._gh.close.assert_called_once()
