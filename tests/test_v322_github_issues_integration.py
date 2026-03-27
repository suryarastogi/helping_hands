"""Tests for v322 GitHub Issues integration (project_management flag).

Tests cover:
- GitHubClient.create_issue and get_issue methods
- IssueResult dataclass
- Hand.issue_number attribute and Closes #N in PR body
- BuildRequest project_management field
- ScheduledTask project_management field round-trip
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestIssueResultDataclass:
    """IssueResult has number, url, title fields."""

    def test_create(self) -> None:
        from helping_hands.lib.github import IssueResult

        result = IssueResult(
            number=7, url="https://github.com/o/r/issues/7", title="Fix bug"
        )
        assert result.number == 7
        assert result.url == "https://github.com/o/r/issues/7"
        assert result.title == "Fix bug"

    def test_exported_in_all(self) -> None:
        from helping_hands.lib import github

        assert "IssueResult" in github.__all__


class TestGitHubClientCreateIssue:
    """GitHubClient.create_issue creates an issue via PyGithub."""

    def _make_client(self) -> MagicMock:
        """Build a patched GitHubClient with mock PyGithub."""
        with (
            patch(
                "helping_hands.lib.github._resolve_github_token",
                return_value="ghp_test",
            ),
            patch("helping_hands.lib.github.Github"),
        ):
            from helping_hands.lib.github import GitHubClient

            client = GitHubClient(token="ghp_test")
        return client

    def test_create_issue_basic(self) -> None:
        client = self._make_client()
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_issue.number = 5
        mock_issue.html_url = "https://github.com/owner/repo/issues/5"
        mock_issue.title = "Add feature"
        mock_repo.create_issue.return_value = mock_issue
        client.get_repo = MagicMock(return_value=mock_repo)

        result = client.create_issue("owner/repo", title="Add feature", body="details")
        assert result.number == 5
        assert result.url == "https://github.com/owner/repo/issues/5"
        assert result.title == "Add feature"
        mock_repo.create_issue.assert_called_once_with(
            title="Add feature", body="details"
        )

    def test_create_issue_with_labels(self) -> None:
        client = self._make_client()
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_issue.number = 10
        mock_issue.html_url = "https://github.com/o/r/issues/10"
        mock_issue.title = "Bug"
        mock_repo.create_issue.return_value = mock_issue
        client.get_repo = MagicMock(return_value=mock_repo)

        result = client.create_issue(
            "o/r", title="Bug", body="desc", labels=["bug", "urgent"]
        )
        assert result.number == 10
        mock_repo.create_issue.assert_called_once_with(
            title="Bug", body="desc", labels=["bug", "urgent"]
        )

    def test_create_issue_empty_title_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="title"):
            client.create_issue("owner/repo", title="")

    def test_create_issue_whitespace_title_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="title"):
            client.create_issue("owner/repo", title="   ")


class TestGitHubClientGetIssue:
    """GitHubClient.get_issue retrieves issue details."""

    def _make_client(self) -> MagicMock:
        with (
            patch(
                "helping_hands.lib.github._resolve_github_token",
                return_value="ghp_test",
            ),
            patch("helping_hands.lib.github.Github"),
        ):
            from helping_hands.lib.github import GitHubClient

            client = GitHubClient(token="ghp_test")
        return client

    def test_get_issue_returns_dict(self) -> None:
        client = self._make_client()
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_issue.number = 3
        mock_issue.title = "Fix tests"
        mock_issue.body = "Some body"
        mock_issue.html_url = "https://github.com/o/r/issues/3"
        mock_issue.state = "open"
        label1 = MagicMock()
        label1.name = "bug"
        mock_issue.labels = [label1]
        mock_issue.user.login = "alice"
        mock_repo.get_issue.return_value = mock_issue
        client.get_repo = MagicMock(return_value=mock_repo)

        result = client.get_issue("o/r", 3)
        assert result["number"] == 3
        assert result["title"] == "Fix tests"
        assert result["state"] == "open"
        assert result["labels"] == ["bug"]
        assert result["user"] == "alice"

    def test_get_issue_zero_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="issue number"):
            client.get_issue("o/r", 0)

    def test_get_issue_negative_raises(self) -> None:
        client = self._make_client()
        with pytest.raises(ValueError, match="issue number"):
            client.get_issue("o/r", -1)


class TestHandIssueNumber:
    """Hand.issue_number defaults to None and can be set."""

    def test_issue_number_defaults_to_none(self, fake_config, repo_index) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

        hand = GooseCLIHand(config=fake_config, repo_index=repo_index)
        assert hand.issue_number is None

    def test_issue_number_settable(self, fake_config, repo_index) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

        hand = GooseCLIHand(config=fake_config, repo_index=repo_index)
        hand.issue_number = 42
        assert hand.issue_number == 42


class TestHandPRBodyIssueLink:
    """When issue_number is set, _create_new_pr prepends Closes #N."""

    def test_pr_body_includes_closes_reference(
        self, fake_config, repo_index, mock_github_client
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

        hand = GooseCLIHand(config=fake_config, repo_index=repo_index)
        hand.issue_number = 15

        # Mock the helper methods that _create_new_pr calls
        hand._working_tree_is_clean = MagicMock(return_value=True)
        hand._run_git_read = MagicMock(return_value="abc1234")
        hand._push_noninteractive = MagicMock()
        hand._default_base_branch = MagicMock(return_value="main")
        hand._generate_pr_title_and_body = MagicMock(
            return_value=("Title", "Original body")
        )

        metadata: dict[str, str] = {}
        hand._create_new_pr(
            gh=mock_github_client,
            repo="owner/repo",
            repo_dir=Path(fake_config.repo),
            backend="goose",
            prompt="test prompt",
            summary="test summary",
            metadata=metadata,
        )

        # Verify create_pr was called with body starting with Closes #15
        call_kwargs = mock_github_client.create_pr.call_args
        body = call_kwargs.kwargs.get("body") or call_kwargs[1].get("body", "")
        assert body.startswith("Closes #15\n\n")
        assert "Original body" in body

    def test_pr_body_no_closes_when_no_issue(
        self, fake_config, repo_index, mock_github_client
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

        hand = GooseCLIHand(config=fake_config, repo_index=repo_index)
        # issue_number is None by default

        hand._working_tree_is_clean = MagicMock(return_value=True)
        hand._run_git_read = MagicMock(return_value="abc1234")
        hand._push_noninteractive = MagicMock()
        hand._default_base_branch = MagicMock(return_value="main")
        hand._generate_pr_title_and_body = MagicMock(
            return_value=("Title", "Original body")
        )

        metadata: dict[str, str] = {}
        hand._create_new_pr(
            gh=mock_github_client,
            repo="owner/repo",
            repo_dir=Path(fake_config.repo),
            backend="goose",
            prompt="test prompt",
            summary="test summary",
            metadata=metadata,
        )

        call_kwargs = mock_github_client.create_pr.call_args
        body = call_kwargs.kwargs.get("body") or call_kwargs[1].get("body", "")
        assert not body.startswith("Closes #")
        assert body == "Original body"


class TestBuildRequestProjectManagement:
    """BuildRequest has project_management bool field defaulting to False."""

    def test_default_false(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="owner/repo", prompt="do stuff")
        assert req.project_management is False

    def test_set_true(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(
            repo_path="owner/repo", prompt="do stuff", project_management=True
        )
        assert req.project_management is True


class TestScheduledTaskProjectManagement:
    """ScheduledTask includes project_management in to_dict/from_dict."""

    def test_default_false(self) -> None:
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="s1",
            name="test",
            cron_expression="0 * * * *",
            repo_path="owner/repo",
            prompt="do stuff",
        )
        assert task.project_management is False

    def test_to_dict_includes_field(self) -> None:
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="s1",
            name="test",
            cron_expression="0 * * * *",
            repo_path="owner/repo",
            prompt="do stuff",
            project_management=True,
        )
        d = task.to_dict()
        assert d["project_management"] is True

    def test_from_dict_round_trip(self) -> None:
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="s1",
            name="test",
            cron_expression="0 * * * *",
            repo_path="owner/repo",
            prompt="do stuff",
            project_management=True,
        )
        d = task.to_dict()
        restored = ScheduledTask.from_dict(d)
        assert restored.project_management is True

    def test_from_dict_defaults_false_when_absent(self) -> None:
        from helping_hands.server.schedules import ScheduledTask

        data = {
            "schedule_id": "s1",
            "name": "test",
            "cron_expression": "0 * * * *",
            "repo_path": "owner/repo",
            "prompt": "do stuff",
        }
        task = ScheduledTask.from_dict(data)
        assert task.project_management is False
