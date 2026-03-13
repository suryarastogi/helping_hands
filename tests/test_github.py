"""Tests for helping_hands.lib.github."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from helping_hands.lib.github import (
    _VALID_PR_STATES,
    GitHubClient,
    PRResult,
    _run_git,
    _validate_branch_name,
)

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

    def test_clone_rejects_zero_depth(
        self, client: GitHubClient, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="depth must be positive"):
            client.clone("owner/repo", tmp_path / "repo", depth=0)

    def test_clone_rejects_negative_depth(
        self, client: GitHubClient, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="depth must be positive"):
            client.clone("owner/repo", tmp_path / "repo", depth=-5)

    def test_clone_rejects_empty_full_name(
        self, client: GitHubClient, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="full_name must not be empty"):
            client.clone("", tmp_path / "repo")

    def test_clone_rejects_whitespace_full_name(
        self, client: GitHubClient, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="full_name must not be empty"):
            client.clone("   ", tmp_path / "repo")

    def test_clone_rejects_no_slash_full_name(
        self, client: GitHubClient, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            client.clone("justrepo", tmp_path / "repo")


# ---------------------------------------------------------------------------
# Branch operations
# ---------------------------------------------------------------------------


class TestFetchBranch:
    @patch("helping_hands.lib.github._run_git")
    def test_fetch_branch_default_remote(
        self, mock_git: MagicMock, tmp_path: Path
    ) -> None:
        GitHubClient.fetch_branch(tmp_path, "feat/new")
        cmd = mock_git.call_args[0][0]
        assert cmd == [
            "git",
            "fetch",
            "origin",
            "refs/heads/feat/new:refs/heads/feat/new",
        ]
        assert mock_git.call_args[1]["cwd"] == tmp_path

    @patch("helping_hands.lib.github._run_git")
    def test_fetch_branch_custom_remote(
        self, mock_git: MagicMock, tmp_path: Path
    ) -> None:
        GitHubClient.fetch_branch(tmp_path, "main", remote="upstream")
        cmd = mock_git.call_args[0][0]
        assert cmd == [
            "git",
            "fetch",
            "upstream",
            "refs/heads/main:refs/heads/main",
        ]


class TestPull:
    @patch("helping_hands.lib.github._run_git")
    def test_pull_default(self, mock_git: MagicMock, tmp_path: Path) -> None:
        GitHubClient.pull(tmp_path)
        cmd = mock_git.call_args[0][0]
        assert cmd == ["git", "pull", "origin"]

    @patch("helping_hands.lib.github._run_git")
    def test_pull_with_branch(self, mock_git: MagicMock, tmp_path: Path) -> None:
        GitHubClient.pull(tmp_path, branch="main")
        cmd = mock_git.call_args[0][0]
        assert cmd == ["git", "pull", "origin", "main"]

    @patch("helping_hands.lib.github._run_git")
    def test_pull_custom_remote(self, mock_git: MagicMock, tmp_path: Path) -> None:
        GitHubClient.pull(tmp_path, remote="upstream", branch="dev")
        cmd = mock_git.call_args[0][0]
        assert cmd == ["git", "pull", "upstream", "dev"]


class TestSetLocalIdentity:
    @patch("helping_hands.lib.github._run_git")
    def test_sets_name_and_email(self, mock_git: MagicMock, tmp_path: Path) -> None:
        GitHubClient.set_local_identity(tmp_path, name="Bot", email="bot@example.com")
        calls = mock_git.call_args_list
        assert len(calls) == 2
        assert calls[0] == call(["git", "config", "user.name", "Bot"], cwd=tmp_path)
        assert calls[1] == call(
            ["git", "config", "user.email", "bot@example.com"], cwd=tmp_path
        )


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


class TestDefaultBranch:
    def test_default_branch(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_repo.default_branch = "master"
        client._gh.get_repo.return_value = mock_repo

        branch = client.default_branch("owner/repo")
        assert branch == "master"


class TestUpsertPRComment:
    def test_creates_comment_when_marker_missing(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        mock_issue.get_comments.return_value = []
        created = MagicMock()
        created.id = 123
        mock_issue.create_comment.return_value = created
        client._gh.get_repo.return_value = mock_repo

        comment_id = client.upsert_pr_comment(
            "owner/repo",
            9,
            body="Status update",
            marker="<!-- helping_hands:e2e-status -->",
        )

        assert comment_id == 123
        mock_issue.create_comment.assert_called_once_with(
            "Status update\n\n<!-- helping_hands:e2e-status -->"
        )

    def test_updates_existing_comment_when_marker_found(
        self, client: GitHubClient
    ) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        existing = MagicMock()
        existing.id = 77
        existing.body = "old\n\n<!-- helping_hands:e2e-status -->"
        mock_issue.get_comments.return_value = [existing]
        client._gh.get_repo.return_value = mock_repo

        comment_id = client.upsert_pr_comment(
            "owner/repo",
            9,
            body="new status",
            marker="<!-- helping_hands:e2e-status -->",
        )

        assert comment_id == 77
        existing.edit.assert_called_once_with(
            "new status\n\n<!-- helping_hands:e2e-status -->"
        )
        mock_issue.create_comment.assert_not_called()


class TestGetCheckRuns:
    def test_all_passing(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        run1 = MagicMock()
        run1.name = "build"
        run1.status = "completed"
        run1.conclusion = "success"
        run1.html_url = "https://github.com/owner/repo/actions/runs/1"
        run1.started_at = None
        run1.completed_at = None
        mock_commit.get_check_runs.return_value = [run1]
        mock_repo.get_commit.return_value = mock_commit
        client._gh.get_repo.return_value = mock_repo

        result = client.get_check_runs("owner/repo", "abc123")

        assert result["ref"] == "abc123"
        assert result["total_count"] == 1
        assert result["conclusion"] == "success"
        assert result["check_runs"][0]["name"] == "build"

    def test_failure(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        run1 = MagicMock()
        run1.name = "build"
        run1.status = "completed"
        run1.conclusion = "success"
        run1.html_url = "url1"
        run1.started_at = None
        run1.completed_at = None
        run2 = MagicMock()
        run2.name = "test"
        run2.status = "completed"
        run2.conclusion = "failure"
        run2.html_url = "url2"
        run2.started_at = None
        run2.completed_at = None
        mock_commit.get_check_runs.return_value = [run1, run2]
        mock_repo.get_commit.return_value = mock_commit
        client._gh.get_repo.return_value = mock_repo

        result = client.get_check_runs("owner/repo", "abc123")

        assert result["conclusion"] == "failure"
        assert result["total_count"] == 2

    def test_no_checks(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = []
        mock_repo.get_commit.return_value = mock_commit
        client._gh.get_repo.return_value = mock_repo

        result = client.get_check_runs("owner/repo", "abc123")

        assert result["conclusion"] == "no_checks"
        assert result["total_count"] == 0

    def test_pending(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        run = MagicMock()
        run.name = "build"
        run.status = "in_progress"
        run.conclusion = None
        run.html_url = "url"
        run.started_at = None
        run.completed_at = None
        mock_commit.get_check_runs.return_value = [run]
        mock_repo.get_commit.return_value = mock_commit
        client._gh.get_repo.return_value = mock_repo

        result = client.get_check_runs("owner/repo", "abc123")

        assert result["conclusion"] == "pending"


class TestGetCheckRunsMixed:
    def test_mixed_conclusion(self, client: GitHubClient) -> None:
        """All completed, no failure, but not all success => 'mixed'."""
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        run1 = MagicMock()
        run1.name = "build"
        run1.status = "completed"
        run1.conclusion = "success"
        run1.html_url = "url1"
        run1.started_at = None
        run1.completed_at = None
        run2 = MagicMock()
        run2.name = "optional"
        run2.status = "completed"
        run2.conclusion = "neutral"
        run2.html_url = "url2"
        run2.started_at = None
        run2.completed_at = None
        mock_commit.get_check_runs.return_value = [run1, run2]
        mock_repo.get_commit.return_value = mock_commit
        client._gh.get_repo.return_value = mock_repo

        result = client.get_check_runs("owner/repo", "abc123")

        assert result["conclusion"] == "mixed"
        assert result["total_count"] == 2


class TestUpsertPRCommentBodyAlreadyHasMarker:
    def test_body_already_contains_marker_no_duplicate(
        self, client: GitHubClient
    ) -> None:
        """When body already contains the marker, don't append it again."""
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        mock_issue.get_comments.return_value = []
        created = MagicMock()
        created.id = 456
        mock_issue.create_comment.return_value = created
        client._gh.get_repo.return_value = mock_repo

        marker = "<!-- helping_hands:status -->"
        body_with_marker = f"Status update\n\n{marker}"

        comment_id = client.upsert_pr_comment(
            "owner/repo",
            5,
            body=body_with_marker,
            marker=marker,
        )

        assert comment_id == 456
        actual_body = mock_issue.create_comment.call_args[0][0]
        # Marker should appear exactly once
        assert actual_body.count(marker) == 1

    def test_existing_comment_with_none_body(self, client: GitHubClient) -> None:
        """When existing comment has body=None, it should not match."""
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        existing = MagicMock()
        existing.id = 88
        existing.body = None
        mock_issue.get_comments.return_value = [existing]
        created = MagicMock()
        created.id = 789
        mock_issue.create_comment.return_value = created
        client._gh.get_repo.return_value = mock_repo

        comment_id = client.upsert_pr_comment(
            "owner/repo", 7, body="New comment", marker="<!-- test -->"
        )

        assert comment_id == 789
        existing.edit.assert_not_called()
        mock_issue.create_comment.assert_called_once()


class TestUpdatePRBody:
    def test_updates_existing_pr_body(self, client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client._gh.get_repo.return_value = mock_repo

        client.update_pr_body("owner/repo", 12, body="updated body")

        mock_repo.get_pull.assert_called_once_with(12)
        mock_pr.edit.assert_called_once_with(body="updated body")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager_calls_close(self, client: GitHubClient) -> None:
        with client as c:
            assert c is client
        client._gh.close.assert_called_once()


# ---------------------------------------------------------------------------
# _validate_branch_name
# ---------------------------------------------------------------------------


class TestValidateBranchName:
    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            _validate_branch_name("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            _validate_branch_name("   ")

    def test_tab_only_raises(self) -> None:
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            _validate_branch_name("\t")

    def test_valid_branch_name_passes(self) -> None:
        _validate_branch_name("feat/new-feature")  # should not raise

    def test_valid_simple_name_passes(self) -> None:
        _validate_branch_name("main")  # should not raise


# ---------------------------------------------------------------------------
# Branch method input validation
# ---------------------------------------------------------------------------


class TestBranchInputValidation:
    def test_create_branch_rejects_empty(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="branch_name"):
            GitHubClient.create_branch(tmp_path, "")

    def test_create_branch_rejects_whitespace(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="branch_name"):
            GitHubClient.create_branch(tmp_path, "   ")

    def test_switch_branch_rejects_empty(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="branch_name"):
            GitHubClient.switch_branch(tmp_path, "")

    def test_switch_branch_rejects_whitespace(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="branch_name"):
            GitHubClient.switch_branch(tmp_path, "  ")

    def test_fetch_branch_rejects_empty(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="branch_name"):
            GitHubClient.fetch_branch(tmp_path, "")

    def test_fetch_branch_rejects_whitespace(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="branch_name"):
            GitHubClient.fetch_branch(tmp_path, "\t")


# ---------------------------------------------------------------------------
# Commit/identity input validation
# ---------------------------------------------------------------------------


class TestCommitInputValidation:
    def test_add_and_commit_rejects_empty_message(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="commit message must not be empty"):
            GitHubClient.add_and_commit(tmp_path, "")

    def test_add_and_commit_rejects_whitespace_message(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="commit message must not be empty"):
            GitHubClient.add_and_commit(tmp_path, "   ")


class TestIdentityInputValidation:
    def test_set_local_identity_rejects_empty_name(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="name must not be empty"):
            GitHubClient.set_local_identity(tmp_path, name="", email="a@b.com")

    def test_set_local_identity_rejects_whitespace_name(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="name must not be empty"):
            GitHubClient.set_local_identity(tmp_path, name="  ", email="a@b.com")

    def test_set_local_identity_rejects_empty_email(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="email must not be empty"):
            GitHubClient.set_local_identity(tmp_path, name="Bot", email="")

    def test_set_local_identity_rejects_whitespace_email(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="email must not be empty"):
            GitHubClient.set_local_identity(tmp_path, name="Bot", email="  ")


# ---------------------------------------------------------------------------
# create_pr input validation (v150)
# ---------------------------------------------------------------------------


class TestCreatePrInputValidation:
    def test_rejects_empty_title(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="title must not be empty"):
            client.create_pr("owner/repo", title="", head="feat", base="main")

    def test_rejects_whitespace_title(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="title must not be empty"):
            client.create_pr("owner/repo", title="   ", head="feat", base="main")

    def test_rejects_empty_head(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            client.create_pr("owner/repo", title="Add feature", head="", base="main")

    def test_rejects_whitespace_head(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            client.create_pr("owner/repo", title="Add feature", head="  ", base="main")

    def test_rejects_empty_base(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            client.create_pr("owner/repo", title="Add feature", head="feat", base="")

    def test_rejects_whitespace_base(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            client.create_pr("owner/repo", title="Add feature", head="feat", base="  ")


# ---------------------------------------------------------------------------
# list_prs state validation (v150)
# ---------------------------------------------------------------------------


class TestListPrsStateValidation:
    def test_accepts_open(self, client: GitHubClient) -> None:
        """Valid state 'open' should not raise."""
        repo_mock = MagicMock()
        repo_mock.get_pulls.return_value = []
        client._gh.get_repo.return_value = repo_mock
        result = client.list_prs("owner/repo", state="open")
        assert result == []

    def test_accepts_closed(self, client: GitHubClient) -> None:
        repo_mock = MagicMock()
        repo_mock.get_pulls.return_value = []
        client._gh.get_repo.return_value = repo_mock
        result = client.list_prs("owner/repo", state="closed")
        assert result == []

    def test_accepts_all(self, client: GitHubClient) -> None:
        repo_mock = MagicMock()
        repo_mock.get_pulls.return_value = []
        client._gh.get_repo.return_value = repo_mock
        result = client.list_prs("owner/repo", state="all")
        assert result == []

    def test_rejects_invalid_state(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="state must be one of"):
            client.list_prs("owner/repo", state="merged")

    def test_rejects_empty_state(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="state must be one of"):
            client.list_prs("owner/repo", state="")

    def test_valid_pr_states_constant(self) -> None:
        assert {"open", "closed", "all"} == _VALID_PR_STATES

    def test_valid_pr_states_is_frozenset(self) -> None:
        assert isinstance(_VALID_PR_STATES, frozenset)


# ---------------------------------------------------------------------------
# get_check_runs ref validation (v150)
# ---------------------------------------------------------------------------


class TestGetCheckRunsRefValidation:
    def test_rejects_empty_ref(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="ref must not be empty"):
            client.get_check_runs("owner/repo", "")

    def test_rejects_whitespace_ref(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="ref must not be empty"):
            client.get_check_runs("owner/repo", "   ")

    def test_rejects_tab_ref(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="ref must not be empty"):
            client.get_check_runs("owner/repo", "\t")


# ---------------------------------------------------------------------------
# upsert_pr_comment input validation (v150)
# ---------------------------------------------------------------------------


class TestUpsertPrCommentInputValidation:
    def test_rejects_zero_number(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="PR number must be positive"):
            client.upsert_pr_comment("owner/repo", 0, body="hello")

    def test_rejects_negative_number(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="PR number must be positive"):
            client.upsert_pr_comment("owner/repo", -1, body="hello")

    def test_rejects_empty_body(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="comment body must not be empty"):
            client.upsert_pr_comment("owner/repo", 1, body="")

    def test_rejects_whitespace_body(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="comment body must not be empty"):
            client.upsert_pr_comment("owner/repo", 1, body="   ")
