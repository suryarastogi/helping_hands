"""Tests for GitHubClient.list_issues, list_issues_excluding_labels, list_prs_with_label.

Covers previously untested methods:
- github.py:667-684 — list_issues (issue→dict mapping, PR filtering, user=None)
- github.py:801-842 — list_issues_excluding_labels (filter_labels dedup, exclude, no-filter)
- github.py:865-892 — list_prs_with_label (label-not-found, PR mapping, limit)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from helping_hands.lib.github import GitHubClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_issue(
    number: int,
    title: str = "Issue",
    body: str | None = "desc",
    state: str = "open",
    labels: list[str] | None = None,
    user_login: str | None = "alice",
    is_pr: bool = False,
) -> MagicMock:
    """Build a mock issue/PR matching PyGithub's interface."""
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.body = body
    issue.html_url = f"https://github.com/o/r/issues/{number}"
    issue.state = state
    issue.pull_request = MagicMock() if is_pr else None

    label_mocks = []
    for name in labels or []:
        lbl = MagicMock()
        lbl.name = name
        label_mocks.append(lbl)
    issue.labels = label_mocks

    if user_login is not None:
        issue.user = MagicMock()
        issue.user.login = user_login
    else:
        issue.user = None
    return issue


def _make_pr(
    number: int,
    title: str = "PR",
    state: str = "open",
    head: str = "feat",
    base: str = "main",
    mergeable: bool = True,
) -> MagicMock:
    """Build a mock PullRequest matching PyGithub's interface."""
    pr = MagicMock()
    pr.number = number
    pr.title = title
    pr.html_url = f"https://github.com/o/r/pull/{number}"
    pr.state = state
    pr.head.ref = head
    pr.base.ref = base
    pr.mergeable = mergeable
    return pr


def _client() -> GitHubClient:
    """Return a GitHubClient with a fake token (no real API calls)."""
    with patch("helping_hands.lib.github.Github"):
        return GitHubClient(token="ghp_fake123")


# ---------------------------------------------------------------------------
# list_issues
# ---------------------------------------------------------------------------


class TestListIssues:
    """Cover github.py:667-684 — list_issues mapping."""

    def test_maps_issue_fields(self) -> None:
        client = _client()
        issue = _make_issue(1, title="Bug", body="details", labels=["bug"])
        repo = MagicMock()
        repo.get_issues.return_value = [issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues("o/r")
        assert len(result) == 1
        assert result[0]["number"] == 1
        assert result[0]["title"] == "Bug"
        assert result[0]["body"] == "details"
        assert result[0]["labels"] == ["bug"]
        assert result[0]["user"] == "alice"

    def test_filters_out_pull_requests(self) -> None:
        client = _client()
        issue = _make_issue(1)
        pr_issue = _make_issue(2, is_pr=True)
        repo = MagicMock()
        repo.get_issues.return_value = [issue, pr_issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues("o/r")
        assert len(result) == 1
        assert result[0]["number"] == 1

    def test_user_none_returns_empty_string(self) -> None:
        client = _client()
        issue = _make_issue(3, user_login=None)
        repo = MagicMock()
        repo.get_issues.return_value = [issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues("o/r")
        assert result[0]["user"] == ""

    def test_body_none_returns_empty_string(self) -> None:
        client = _client()
        issue = _make_issue(4, body=None)
        repo = MagicMock()
        repo.get_issues.return_value = [issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues("o/r")
        assert result[0]["body"] == ""


# ---------------------------------------------------------------------------
# list_issues_excluding_labels
# ---------------------------------------------------------------------------


class TestListIssuesExcludingLabels:
    """Cover github.py:801-842 — label filtering, dedup, exclusion."""

    def test_no_filter_labels_fetches_all(self) -> None:
        client = _client()
        issue = _make_issue(10, labels=["feat"])
        repo = MagicMock()
        repo.get_issues.return_value = [issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues_excluding_labels("o/r", exclude_labels=["wontfix"])
        assert len(result) == 1
        assert result[0]["number"] == 10

    def test_exclude_labels_filters_out(self) -> None:
        client = _client()
        issue_keep = _make_issue(11, labels=["feat"])
        issue_drop = _make_issue(12, labels=["wontfix"])
        repo = MagicMock()
        repo.get_issues.return_value = [issue_keep, issue_drop]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues_excluding_labels("o/r", exclude_labels=["wontfix"])
        assert len(result) == 1
        assert result[0]["number"] == 11

    def test_filter_labels_deduplicates(self) -> None:
        client = _client()
        issue = _make_issue(20, labels=["bug", "urgent"])
        repo = MagicMock()
        # Same issue returned for both label queries.
        repo.get_issues.return_value = [issue]
        repo.get_label.return_value = MagicMock()
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues_excluding_labels(
            "o/r",
            exclude_labels=[],
            filter_labels=["bug", "urgent"],
        )
        # Should appear only once despite matching both labels.
        assert len(result) == 1
        assert result[0]["number"] == 20

    def test_pr_issues_excluded(self) -> None:
        client = _client()
        issue = _make_issue(30, is_pr=True)
        repo = MagicMock()
        repo.get_issues.return_value = [issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues_excluding_labels("o/r", exclude_labels=[])
        assert result == []

    def test_user_none_returns_empty_string(self) -> None:
        client = _client()
        issue = _make_issue(31, user_login=None)
        repo = MagicMock()
        repo.get_issues.return_value = [issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_issues_excluding_labels("o/r", exclude_labels=[])
        assert result[0]["user"] == ""


# ---------------------------------------------------------------------------
# list_prs_with_label
# ---------------------------------------------------------------------------


class TestListPrsWithLabel:
    """Cover github.py:865-892 — PR label listing."""

    def test_label_not_found_returns_empty(self) -> None:
        client = _client()
        repo = MagicMock()
        repo.get_label.side_effect = GithubException(404, {}, {})
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_prs_with_label("o/r", label="missing")
        assert result == []

    def test_maps_pr_fields(self) -> None:
        client = _client()
        pr_issue = _make_issue(5, is_pr=True)
        pr_obj = _make_pr(5, title="Fix", head="fix-it", base="main")
        repo = MagicMock()
        repo.get_label.return_value = MagicMock()
        repo.get_issues.return_value = [pr_issue]
        repo.get_pull.return_value = pr_obj
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_prs_with_label("o/r", label="ready")
        assert len(result) == 1
        assert result[0]["number"] == 5
        assert result[0]["head"] == "fix-it"
        assert result[0]["base"] == "main"
        assert result[0]["mergeable"] is True

    def test_skips_non_pr_issues(self) -> None:
        client = _client()
        plain_issue = _make_issue(6, is_pr=False)
        repo = MagicMock()
        repo.get_label.return_value = MagicMock()
        repo.get_issues.return_value = [plain_issue]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_prs_with_label("o/r", label="ready")
        assert result == []

    def test_respects_limit(self) -> None:
        client = _client()
        pr1 = _make_issue(7, is_pr=True)
        pr2 = _make_issue(8, is_pr=True)
        repo = MagicMock()
        repo.get_label.return_value = MagicMock()
        repo.get_issues.return_value = [pr1, pr2]
        repo.get_pull.side_effect = [
            _make_pr(7),
            _make_pr(8),
        ]
        client.get_repo = MagicMock(return_value=repo)

        result = client.list_prs_with_label("o/r", label="ready", limit=1)
        assert len(result) == 1
        assert result[0]["number"] == 7

    def test_empty_label_raises(self) -> None:
        client = _client()
        with pytest.raises(ValueError):
            client.list_prs_with_label("o/r", label="")
