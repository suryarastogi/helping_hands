"""Tests for v239: DRY helpers for feedback, transcripts, GitHub repo, and PR comments.

_collect_tool_feedback() joins multiple tool output lines into the context
fed back to the AI on the next iteration; if the join separator changes, the
model sees garbled multi-tool feedback and produces worse edits.

_append_iteration_transcript() builds the running history shown in PR comments;
regressions here cause the PR to display an incomplete or misordered transcript.

_github_repo_from_origin() parses the remote URL to a PyGitHub Repo object;
if it stops handling SSH and HTTPS URL variants correctly, CI checks and PR
comment upserts silently fail for repos cloned via SSH.

upsert_pr_comment() must create a new comment on first call and update the
existing one on subsequent calls; regression to "always create" spams PRs with
duplicate status comments.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.github import CIConclusion, GitHubClient
from helping_hands.lib.hands.v1.hand.base import Hand

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_token_for_tests")


@pytest.fixture()
def github_client() -> GitHubClient:
    with patch("helping_hands.lib.github.Github"):
        return GitHubClient()


# ---------------------------------------------------------------------------
# _collect_tool_feedback (DRY helper on _BasicIterativeHand)
# ---------------------------------------------------------------------------


class TestCollectToolFeedback:
    """Verify that _collect_tool_feedback delegates to read + tool execution."""

    def _make_hand(self) -> MagicMock:
        """Create a hand-like mock with _collect_tool_feedback bound."""
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        hand = MagicMock(spec=_BasicIterativeHand)
        hand._execute_read_requests = MagicMock(return_value="")
        hand._execute_tool_requests = MagicMock(return_value="")
        hand._collect_tool_feedback = (
            _BasicIterativeHand._collect_tool_feedback.__get__(hand)
        )
        return hand

    def test_empty_when_no_feedback(self) -> None:
        hand = self._make_hand()
        result = hand._collect_tool_feedback("content")
        assert result == ""

    def test_read_feedback_only(self) -> None:
        hand = self._make_hand()
        hand._execute_read_requests.return_value = "read result"
        result = hand._collect_tool_feedback("content")
        assert result == "read result"

    def test_tool_feedback_only(self) -> None:
        hand = self._make_hand()
        hand._execute_tool_requests.return_value = "tool result"
        result = hand._collect_tool_feedback("content")
        assert result == "tool result"

    def test_both_feedbacks_joined(self) -> None:
        hand = self._make_hand()
        hand._execute_read_requests.return_value = "read result"
        hand._execute_tool_requests.return_value = "tool result"
        result = hand._collect_tool_feedback("content")
        assert result == "read result\n\ntool result"

    def test_strips_whitespace(self) -> None:
        hand = self._make_hand()
        hand._execute_read_requests.return_value = "  read  "
        hand._execute_tool_requests.return_value = ""
        result = hand._collect_tool_feedback("content")
        assert result == "read"

    def test_delegates_content_arg(self) -> None:
        hand = self._make_hand()
        hand._collect_tool_feedback("my content")
        hand._execute_read_requests.assert_called_once_with("my content")
        hand._execute_tool_requests.assert_called_once_with("my content")


# ---------------------------------------------------------------------------
# _append_iteration_transcript (DRY helper on _BasicIterativeHand)
# ---------------------------------------------------------------------------


class TestAppendIterationTranscript:
    """Verify that _append_iteration_transcript builds correct transcript."""

    def _append(
        self,
        iteration: int = 1,
        content: str = "response",
        changed: list[str] | None = None,
        feedback: str = "",
    ) -> list[str]:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        transcripts: list[str] = []
        _BasicIterativeHand._append_iteration_transcript(
            transcripts,
            iteration,
            content,
            changed or [],
            feedback,
        )
        return transcripts

    def test_basic_transcript(self) -> None:
        result = self._append(iteration=1, content="hello")
        assert result == ["[iteration 1]\nhello"]

    def test_with_changed_files(self) -> None:
        result = self._append(changed=["a.py", "b.py"])
        assert "[files updated] a.py, b.py" in result

    def test_with_feedback(self) -> None:
        result = self._append(feedback="tool output")
        assert "[tool results]\ntool output" in result

    def test_all_fields(self) -> None:
        result = self._append(
            iteration=3,
            content="AI response",
            changed=["main.py"],
            feedback="read output",
        )
        assert len(result) == 3
        assert result[0] == "[iteration 3]\nAI response"
        assert result[1] == "[files updated] main.py"
        assert result[2] == "[tool results]\nread output"

    def test_empty_changed_not_appended(self) -> None:
        result = self._append(changed=[])
        assert len(result) == 1

    def test_empty_feedback_not_appended(self) -> None:
        result = self._append(feedback="")
        assert len(result) == 1

    def test_appends_to_existing(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        transcripts = ["existing"]
        _BasicIterativeHand._append_iteration_transcript(
            transcripts,
            2,
            "content",
            [],
            "",
        )
        assert len(transcripts) == 2
        assert transcripts[0] == "existing"


# ---------------------------------------------------------------------------
# _github_repo_from_origin
# ---------------------------------------------------------------------------


class TestGithubRepoFromOrigin:
    """Test Hand._github_repo_from_origin with various URL formats."""

    @patch.object(Hand, "_run_git_read")
    def test_https_url(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "https://github.com/owner/repo.git"
        assert Hand._github_repo_from_origin(Path("/fake")) == "owner/repo"

    @patch.object(Hand, "_run_git_read")
    def test_https_url_no_git_suffix(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "https://github.com/owner/repo"
        assert Hand._github_repo_from_origin(Path("/fake")) == "owner/repo"

    @patch.object(Hand, "_run_git_read")
    def test_ssh_url(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "ssh://git@github.com/owner/repo.git"
        assert Hand._github_repo_from_origin(Path("/fake")) == "owner/repo"

    @patch.object(Hand, "_run_git_read")
    def test_scp_style_url(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "git@github.com:owner/repo.git"
        assert Hand._github_repo_from_origin(Path("/fake")) == "owner/repo"

    @patch.object(Hand, "_run_git_read")
    def test_scp_style_no_git_suffix(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "git@github.com:owner/repo"
        assert Hand._github_repo_from_origin(Path("/fake")) == "owner/repo"

    @patch.object(Hand, "_run_git_read")
    def test_non_github_url(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "https://gitlab.com/owner/repo.git"
        assert Hand._github_repo_from_origin(Path("/fake")) == ""

    @patch.object(Hand, "_run_git_read")
    def test_empty_remote(self, mock_git: MagicMock) -> None:
        mock_git.return_value = ""
        assert Hand._github_repo_from_origin(Path("/fake")) == ""

    @patch.object(Hand, "_run_git_read")
    def test_malformed_url(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "not-a-url"
        assert Hand._github_repo_from_origin(Path("/fake")) == ""

    @patch.object(Hand, "_run_git_read")
    def test_github_with_deep_path(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "https://github.com/owner/repo/extra/path"
        # Should not match — repo pattern requires exactly owner/repo
        assert Hand._github_repo_from_origin(Path("/fake")) == ""

    @patch.object(Hand, "_run_git_read")
    def test_http_scheme(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "http://github.com/owner/repo.git"
        assert Hand._github_repo_from_origin(Path("/fake")) == "owner/repo"

    @patch.object(Hand, "_run_git_read")
    def test_scp_non_github(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "git@gitlab.com:owner/repo.git"
        assert Hand._github_repo_from_origin(Path("/fake")) == ""

    @patch.object(Hand, "_run_git_read")
    def test_calls_remote_get_url(self, mock_git: MagicMock) -> None:
        mock_git.return_value = ""
        Hand._github_repo_from_origin(Path("/myrepo"))
        mock_git.assert_called_once_with(
            Path("/myrepo"),
            "remote",
            "get-url",
            "origin",
        )


# ---------------------------------------------------------------------------
# get_check_runs
# ---------------------------------------------------------------------------


def _make_check_run(
    name: str = "ci",
    status: str = "completed",
    conclusion: str = "success",
) -> MagicMock:
    run = MagicMock()
    run.name = name
    run.status = status
    run.conclusion = conclusion
    run.html_url = f"https://github.com/runs/{name}"
    run.started_at = datetime(2026, 3, 16, tzinfo=UTC)
    run.completed_at = datetime(2026, 3, 16, 0, 5, tzinfo=UTC)
    return run


class TestGetCheckRuns:
    """Test GitHubClient.get_check_runs with all conclusion paths."""

    def test_no_checks(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = []
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "abc123")
        assert result["conclusion"] == CIConclusion.NO_CHECKS
        assert result["total_count"] == 0

    def test_all_success(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = [
            _make_check_run("lint", conclusion="success"),
            _make_check_run("test", conclusion="success"),
        ]
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "abc123")
        assert result["conclusion"] == CIConclusion.SUCCESS
        assert result["total_count"] == 2

    def test_pending(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = [
            _make_check_run("lint", status="in_progress", conclusion=None),
            _make_check_run("test", conclusion="success"),
        ]
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "abc123")
        assert result["conclusion"] == CIConclusion.PENDING

    def test_failure(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = [
            _make_check_run("lint", conclusion="success"),
            _make_check_run("test", conclusion="failure"),
        ]
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "abc123")
        assert result["conclusion"] == CIConclusion.FAILURE

    def test_mixed(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = [
            _make_check_run("lint", conclusion="success"),
            _make_check_run("test", conclusion="skipped"),
        ]
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "abc123")
        assert result["conclusion"] == CIConclusion.MIXED

    def test_ref_in_result(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = []
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "sha123")
        assert result["ref"] == "sha123"

    def test_check_run_details(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        run = _make_check_run("lint", conclusion="success")
        mock_commit.get_check_runs.return_value = [run]
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "abc123")
        checks = result["check_runs"]
        assert len(checks) == 1
        assert checks[0]["name"] == "lint"
        assert checks[0]["status"] == "completed"
        assert checks[0]["conclusion"] == "success"

    def test_empty_ref_rejected(self, github_client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="ref must not be empty"):
            github_client.get_check_runs("owner/repo", "")

    def test_started_at_none(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        run = _make_check_run("ci")
        run.started_at = None
        run.completed_at = None
        mock_commit.get_check_runs.return_value = [run]
        mock_repo.get_commit.return_value = mock_commit
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.get_check_runs("owner/repo", "abc")
        assert result["check_runs"][0]["started_at"] is None
        assert result["check_runs"][0]["completed_at"] is None


# ---------------------------------------------------------------------------
# upsert_pr_comment (behavior, not just validation)
# ---------------------------------------------------------------------------


class TestUpsertPrCommentBehavior:
    """Test actual create/update behavior of upsert_pr_comment."""

    def test_creates_new_comment(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_issue.get_comments.return_value = []
        mock_created = MagicMock()
        mock_created.id = 42
        mock_issue.create_comment.return_value = mock_created
        mock_repo.get_issue.return_value = mock_issue
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.upsert_pr_comment(
            "owner/repo",
            1,
            body="Hello world",
        )
        assert result == 42
        mock_issue.create_comment.assert_called_once()
        body_arg = mock_issue.create_comment.call_args[0][0]
        assert "Hello world" in body_arg
        assert "<!-- helping_hands:status -->" in body_arg

    def test_updates_existing_comment(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        existing = MagicMock()
        existing.body = "old text\n\n<!-- helping_hands:status -->"
        existing.id = 99
        mock_issue.get_comments.return_value = [existing]
        mock_repo.get_issue.return_value = mock_issue
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.upsert_pr_comment(
            "owner/repo",
            1,
            body="New text",
        )
        assert result == 99
        existing.edit.assert_called_once()
        mock_issue.create_comment.assert_not_called()

    def test_custom_marker(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_issue.get_comments.return_value = []
        mock_created = MagicMock()
        mock_created.id = 10
        mock_issue.create_comment.return_value = mock_created
        mock_repo.get_issue.return_value = mock_issue
        github_client.get_repo = MagicMock(return_value=mock_repo)

        github_client.upsert_pr_comment(
            "owner/repo",
            1,
            body="Hi",
            marker="<!-- custom -->",
        )
        body_arg = mock_issue.create_comment.call_args[0][0]
        assert "<!-- custom -->" in body_arg

    def test_marker_already_in_body(self, github_client: GitHubClient) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_issue.get_comments.return_value = []
        mock_created = MagicMock()
        mock_created.id = 5
        mock_issue.create_comment.return_value = mock_created
        mock_repo.get_issue.return_value = mock_issue
        github_client.get_repo = MagicMock(return_value=mock_repo)

        body_with_marker = "Hello\n\n<!-- helping_hands:status -->"
        github_client.upsert_pr_comment(
            "owner/repo",
            1,
            body=body_with_marker,
        )
        body_arg = mock_issue.create_comment.call_args[0][0]
        # Marker should appear exactly once (not duplicated)
        assert body_arg.count("<!-- helping_hands:status -->") == 1

    def test_skips_non_matching_comments(
        self,
        github_client: GitHubClient,
    ) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        other_comment = MagicMock()
        other_comment.body = "unrelated comment"
        mock_issue.get_comments.return_value = [other_comment]
        mock_created = MagicMock()
        mock_created.id = 7
        mock_issue.create_comment.return_value = mock_created
        mock_repo.get_issue.return_value = mock_issue
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.upsert_pr_comment(
            "owner/repo",
            1,
            body="New",
        )
        assert result == 7
        other_comment.edit.assert_not_called()

    def test_none_body_comment_skipped(
        self,
        github_client: GitHubClient,
    ) -> None:
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        none_comment = MagicMock()
        none_comment.body = None
        mock_issue.get_comments.return_value = [none_comment]
        mock_created = MagicMock()
        mock_created.id = 8
        mock_issue.create_comment.return_value = mock_created
        mock_repo.get_issue.return_value = mock_issue
        github_client.get_repo = MagicMock(return_value=mock_repo)

        result = github_client.upsert_pr_comment(
            "owner/repo",
            1,
            body="text",
        )
        assert result == 8
        none_comment.edit.assert_not_called()


# ---------------------------------------------------------------------------
# _collect_tool_feedback docstring presence
# ---------------------------------------------------------------------------


class TestDryHelperDocstrings:
    def test_collect_tool_feedback_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        doc = _BasicIterativeHand._collect_tool_feedback.__doc__
        assert doc is not None
        assert "Args:" in doc
        assert "Returns:" in doc

    def test_append_iteration_transcript_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        doc = _BasicIterativeHand._append_iteration_transcript.__doc__
        assert doc is not None
        assert "Args:" in doc
