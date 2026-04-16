"""Tests for the watch_issues schedule feature.

Covers:
- ScheduledTask round-trip with watch_labels field
- watch_issues_poll task logic (mock GitHub API)
- watch_issue_complete callback (label swap on success/failure)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery", reason="celery extra not installed")

from helping_hands.server.constants import (
    SCHEDULE_TYPE_WATCH_ISSUES,
    TASK_NAME_WATCH_ISSUE_COMPLETE,
    TASK_NAME_WATCH_ISSUES_POLL,
    WATCH_LABEL_DONE,
    WATCH_LABEL_FAILED,
    WATCH_LABEL_PR,
    WATCH_LABEL_QUEUED,
)
from helping_hands.server.schedules import ScheduledTask

# ---------------------------------------------------------------------------
# ScheduledTask round-trip with watch_labels
# ---------------------------------------------------------------------------


class TestScheduledTaskWatchLabels:
    """Ensure watch_labels survives to_dict/from_dict."""

    def test_watch_labels_default_empty(self) -> None:
        task = ScheduledTask(
            schedule_id="wl1",
            name="Watch",
            cron_expression="*/5 * * * *",
            repo_path="owner/repo",
            prompt="(auto)",
            schedule_type=SCHEDULE_TYPE_WATCH_ISSUES,
        )
        assert task.watch_labels == []

    def test_watch_labels_roundtrip(self) -> None:
        original = ScheduledTask(
            schedule_id="wl2",
            name="Watch Labels",
            cron_expression="0 * * * *",
            repo_path="owner/repo",
            prompt="(auto-generated from issues)",
            schedule_type=SCHEDULE_TYPE_WATCH_ISSUES,
            watch_labels=["bug", "enhancement"],
        )
        data = original.to_dict()
        assert data["watch_labels"] == ["bug", "enhancement"]
        assert data["schedule_type"] == SCHEDULE_TYPE_WATCH_ISSUES

        rebuilt = ScheduledTask.from_dict(data)
        assert rebuilt.watch_labels == ["bug", "enhancement"]
        assert rebuilt.schedule_type == SCHEDULE_TYPE_WATCH_ISSUES

    def test_from_dict_watch_issues_requires_cron(self) -> None:
        with pytest.raises(ValueError, match="cron_expression is required"):
            ScheduledTask.from_dict(
                {
                    "schedule_id": "wl3",
                    "name": "No Cron",
                    "cron_expression": "",
                    "repo_path": "owner/repo",
                    "prompt": "(auto)",
                    "schedule_type": SCHEDULE_TYPE_WATCH_ISSUES,
                }
            )

    def test_from_dict_watch_labels_default(self) -> None:
        task = ScheduledTask.from_dict(
            {
                "schedule_id": "wl4",
                "name": "No Labels",
                "cron_expression": "0 0 * * *",
                "repo_path": "owner/repo",
                "prompt": "(auto)",
                "schedule_type": SCHEDULE_TYPE_WATCH_ISSUES,
            }
        )
        assert task.watch_labels == []


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------


class TestWatchIssuesConstants:
    """Ensure label and task name constants are defined."""

    def test_label_constants(self) -> None:
        assert WATCH_LABEL_QUEUED == "helping-hands:queued"
        assert WATCH_LABEL_DONE == "helping-hands:done"
        assert WATCH_LABEL_FAILED == "helping-hands:failed"
        assert WATCH_LABEL_PR == "helping-hands:watched"

    def test_task_name_constants(self) -> None:
        assert TASK_NAME_WATCH_ISSUES_POLL == "helping_hands.watch_issues_poll"
        assert TASK_NAME_WATCH_ISSUE_COMPLETE == "helping_hands.watch_issue_complete"

    def test_schedule_type_constant(self) -> None:
        assert SCHEDULE_TYPE_WATCH_ISSUES == "watch_issues"


# ---------------------------------------------------------------------------
# watch_issues_poll task logic
# ---------------------------------------------------------------------------


class TestWatchIssuesPoll:
    """Test the poll task with mocked GitHub and Celery."""

    @patch("helping_hands.server.celery_app.build_feature")
    @patch("helping_hands.server.celery_app.watch_issue_complete")
    @patch("helping_hands.lib.github.GitHubClient")
    def test_poll_dispatches_for_new_issues(
        self,
        mock_gh_cls: MagicMock,
        mock_complete_task: MagicMock,
        mock_build: MagicMock,
    ) -> None:
        from helping_hands.server.celery_app import watch_issues_poll

        schedule = ScheduledTask(
            schedule_id="s1",
            name="Watch",
            cron_expression="*/5 * * * *",
            repo_path="owner/repo",
            prompt="(auto)",
            schedule_type=SCHEDULE_TYPE_WATCH_ISSUES,
            github_token="ghp_test",
            enabled=True,
        )

        mock_manager = MagicMock()
        mock_manager.get_schedule.return_value = schedule

        gh_instance = MagicMock()
        mock_gh_cls.return_value = gh_instance
        gh_instance.list_issues_excluding_labels.return_value = [
            {
                "number": 1,
                "title": "Fix bug",
                "body": "There is a bug",
                "url": "https://github.com/owner/repo/issues/1",
                "state": "open",
                "labels": [],
                "user": "testuser",
            },
        ]
        gh_instance.list_prs_with_label.return_value = []

        mock_build.apply_async.return_value = MagicMock(id="task-123")
        mock_complete_task.si.return_value = "callback-sig"

        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            return_value=mock_manager,
        ):
            result = watch_issues_poll("s1")

        assert result["status"] == "polled"
        assert result["issues_dispatched"] == 1
        assert result["dispatched"][0]["issue_number"] == 1

        # Verify queued label was added
        gh_instance.add_issue_labels.assert_called_once_with(
            "owner/repo", 1, labels=[WATCH_LABEL_QUEUED]
        )

        # Verify build was dispatched
        mock_build.apply_async.assert_called_once()
        call_kwargs = mock_build.apply_async.call_args[1]
        assert "Fix GitHub Issue #1" in call_kwargs["kwargs"]["prompt"]

    def test_poll_skips_disabled_schedule(self) -> None:
        from helping_hands.server.celery_app import watch_issues_poll

        schedule = ScheduledTask(
            schedule_id="s2",
            name="Disabled",
            cron_expression="0 0 * * *",
            repo_path="owner/repo",
            prompt="(auto)",
            schedule_type=SCHEDULE_TYPE_WATCH_ISSUES,
            enabled=False,
        )
        mock_manager = MagicMock()
        mock_manager.get_schedule.return_value = schedule

        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            return_value=mock_manager,
        ):
            result = watch_issues_poll("s2")

        assert result["status"] == "skipped"

    def test_poll_missing_schedule(self) -> None:
        from helping_hands.server.celery_app import watch_issues_poll

        mock_manager = MagicMock()
        mock_manager.get_schedule.return_value = None

        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            return_value=mock_manager,
        ):
            result = watch_issues_poll("missing")

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# watch_issue_complete callback
# ---------------------------------------------------------------------------


class TestWatchIssueComplete:
    """Test the completion callback with mocked GitHub."""

    @patch("helping_hands.lib.github.GitHubClient")
    def test_complete_success_labels(self, mock_gh_cls: MagicMock) -> None:
        from helping_hands.server.celery_app import watch_issue_complete

        gh_instance = MagicMock()
        mock_gh_cls.return_value = gh_instance
        gh_instance.list_prs.return_value = [
            {"number": 10, "title": "Fix #5", "url": "..."},
        ]
        gh_instance.get_pr.return_value = {
            "number": 10,
            "title": "Fix #5",
            "body": "Fixes #5",
        }

        result = watch_issue_complete("s1", 5, "owner/repo", "ghp_test", False)

        assert result["status"] == "completed"
        # queued label removed
        gh_instance.remove_issue_label.assert_called_once_with(
            "owner/repo", 5, label=WATCH_LABEL_QUEUED
        )
        # done label added
        gh_instance.add_issue_labels.assert_any_call(
            "owner/repo", 5, labels=[WATCH_LABEL_DONE]
        )
        # PR labeled with watched
        gh_instance.add_issue_labels.assert_any_call(
            "owner/repo", 10, labels=[WATCH_LABEL_PR]
        )

    @patch("helping_hands.lib.github.GitHubClient")
    def test_complete_failure_labels(self, mock_gh_cls: MagicMock) -> None:
        from helping_hands.server.celery_app import watch_issue_complete

        gh_instance = MagicMock()
        mock_gh_cls.return_value = gh_instance

        result = watch_issue_complete("s1", 5, "owner/repo", "ghp_test", True)

        assert result["status"] == "failed"
        gh_instance.remove_issue_label.assert_called_once_with(
            "owner/repo", 5, label=WATCH_LABEL_QUEUED
        )
        gh_instance.add_issue_labels.assert_called_once_with(
            "owner/repo", 5, labels=[WATCH_LABEL_FAILED]
        )
