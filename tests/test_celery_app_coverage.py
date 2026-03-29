"""Tests for celery_app.py coverage gaps: ProgressEmitter, issue lifecycle, PR persist.

Covers the untested pure helper functions in celery_app.py that handle
GitHub issue lifecycle sync, schedule PR persistence, project board
integration, DB URL resolution, and the ProgressEmitter class.

If ``_maybe_persist_pr_to_schedule`` breaks, scheduled builds silently
lose track of created PRs.  If ``_try_create_issue`` fails to set
``hand.issue_number``, PR finalization cannot include "Closes #N".
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery")

from helping_hands.server import celery_app as mod

# ---------------------------------------------------------------------------
# _ProgressEmitter
# ---------------------------------------------------------------------------


def _make_emitter(**overrides):
    """Create a _ProgressEmitter with sensible defaults."""
    task = MagicMock()
    defaults = dict(
        task_id="task-123",
        updates=[],
        prompt="test prompt",
        pr_number=None,
        backend="codexcli",
        runtime_backend="codexcli",
        repo_path="/tmp/repo",
        model="gpt-5.2",
        max_iterations=6,
        no_pr=False,
        enable_execution=False,
        enable_web=False,
        use_native_cli_auth=False,
        tools=(),
        skills=(),
    )
    defaults.update(overrides)
    return mod._ProgressEmitter(task, **defaults)


class TestProgressEmitter:
    def test_emit_calls_update_progress(self) -> None:
        emitter = _make_emitter()
        with patch.object(mod, "_update_progress") as mock_update:
            emitter.emit("starting")
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args
            assert call_kwargs.kwargs["stage"] == "starting"
            assert call_kwargs.kwargs["backend"] == "codexcli"

    def test_emit_sticky_workspace(self) -> None:
        emitter = _make_emitter()
        with patch.object(mod, "_update_progress"):
            emitter.emit("running", workspace="/ws/1")
            assert emitter._workspace == "/ws/1"
            emitter.emit("running")
            # workspace should persist
            assert emitter._workspace == "/ws/1"

    def test_emit_sticky_model(self) -> None:
        emitter = _make_emitter(model=None)
        with patch.object(mod, "_update_progress"):
            emitter.emit("running", model="claude-sonnet-4-5")
            assert emitter._model == "claude-sonnet-4-5"

    def test_emit_with_overrides(self) -> None:
        emitter = _make_emitter()
        with patch.object(mod, "_update_progress") as mock_update:
            emitter.emit("done", pr_number=42, no_pr=True)
            kw = mock_update.call_args.kwargs
            assert kw["pr_number"] == 42
            assert kw["no_pr"] is True

    def test_init_stores_all_fields(self) -> None:
        emitter = _make_emitter(
            fix_ci=True,
            ci_check_wait_minutes=5.0,
            reference_repos=["org/ref"],
            issue_number=99,
        )
        assert emitter._fix_ci is True
        assert emitter._ci_check_wait_minutes == 5.0
        assert emitter._reference_repos == ["org/ref"]
        assert emitter._issue_number == 99


# ---------------------------------------------------------------------------
# _maybe_persist_pr_to_schedule
# ---------------------------------------------------------------------------


class TestMaybePersistPrToSchedule:
    def test_noop_when_no_schedule_id(self) -> None:
        # Should not raise or call anything
        mod._maybe_persist_pr_to_schedule(None, None, "123")

    def test_noop_when_input_pr_exists(self) -> None:
        mod._maybe_persist_pr_to_schedule("sched-1", 42, "123")

    def test_noop_when_result_not_digit(self) -> None:
        mod._maybe_persist_pr_to_schedule("sched-1", None, "")
        mod._maybe_persist_pr_to_schedule("sched-1", None, "not-a-number")

    def test_persists_valid_pr(self) -> None:
        mock_manager = MagicMock()
        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            return_value=mock_manager,
        ):
            mod._maybe_persist_pr_to_schedule("sched-1", None, "99")
            mock_manager.update_pr_number.assert_called_once_with("sched-1", 99)

    def test_logs_warning_on_exception(self) -> None:
        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            side_effect=RuntimeError("Redis down"),
        ):
            # Should not raise
            mod._maybe_persist_pr_to_schedule("sched-1", None, "99")


# ---------------------------------------------------------------------------
# _try_create_issue
# ---------------------------------------------------------------------------


class TestTryCreateIssue:
    def test_creates_issue_and_sets_hand_number(self) -> None:
        hand = SimpleNamespace(issue_number=None)
        updates: list[str] = []

        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        mock_gh.create_issue.return_value = {
            "number": 7,
            "url": "https://github.com/org/repo/issues/7",
        }

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._try_create_issue("org/repo", "Fix the bug", hand, updates, "token")

        assert hand.issue_number == 7
        assert any("#7" in u for u in updates)

    def test_logs_on_failure(self) -> None:
        hand = SimpleNamespace(issue_number=None)
        updates: list[str] = []

        with patch(
            "helping_hands.lib.github.GitHubClient",
            side_effect=RuntimeError("API down"),
        ):
            mod._try_create_issue("org/repo", "Fix it", hand, updates, "token")

        assert hand.issue_number is None
        assert any("Failed" in u for u in updates)


# ---------------------------------------------------------------------------
# _sync_issue_started
# ---------------------------------------------------------------------------


class TestSyncIssueStarted:
    def test_adds_label_on_success(self) -> None:
        updates: list[str] = []
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._sync_issue_started("org/repo", 5, updates, "token")

        mock_gh.add_issue_labels.assert_called_once()
        assert any("in-progress" in u for u in updates)

    def test_logs_on_failure(self) -> None:
        updates: list[str] = []
        with patch(
            "helping_hands.lib.github.GitHubClient",
            side_effect=RuntimeError("fail"),
        ):
            mod._sync_issue_started("org/repo", 5, updates, "token")
        # Should not raise


# ---------------------------------------------------------------------------
# _sync_issue_status
# ---------------------------------------------------------------------------


class TestSyncIssueStatus:
    def test_noop_when_issue_number_none(self) -> None:
        mod._sync_issue_status("org/repo", None, "running", "token")

    def test_posts_running_comment(self) -> None:
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._sync_issue_status("org/repo", 5, "running", "token")

        mock_gh.upsert_pr_comment.assert_called_once()
        body = mock_gh.upsert_pr_comment.call_args.kwargs["body"]
        assert "running" in body

    def test_completed_includes_pr_url(self) -> None:
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._sync_issue_status(
                "org/repo",
                5,
                "completed",
                "token",
                pr_url="https://github.com/org/repo/pull/10",
            )

        body = mock_gh.upsert_pr_comment.call_args.kwargs["body"]
        assert "pull/10" in body

    def test_failed_includes_error(self) -> None:
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._sync_issue_status("org/repo", 5, "failed", "token", error="Timed out")

        body = mock_gh.upsert_pr_comment.call_args.kwargs["body"]
        assert "Timed out" in body

    def test_logs_on_exception(self) -> None:
        with patch(
            "helping_hands.lib.github.GitHubClient",
            side_effect=RuntimeError("API down"),
        ):
            mod._sync_issue_status("org/repo", 5, "running", "token")


# ---------------------------------------------------------------------------
# _sync_issue_completed / _sync_issue_failed
# ---------------------------------------------------------------------------


class TestSyncIssueCompleted:
    def test_swaps_labels_and_posts_comment(self) -> None:
        updates: list[str] = []
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._sync_issue_completed(
                "org/repo", 5, updates, "token", pr_url="https://pr", runtime="1m 30s"
            )

        assert mock_gh.add_issue_labels.called
        assert mock_gh.remove_issue_label.called

    def test_logs_on_failure(self) -> None:
        updates: list[str] = []
        with patch(
            "helping_hands.lib.github.GitHubClient",
            side_effect=RuntimeError("fail"),
        ):
            mod._sync_issue_completed("org/repo", 5, updates, "token")


class TestSyncIssueFailed:
    def test_swaps_labels_and_posts_failure(self) -> None:
        updates: list[str] = []
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._sync_issue_failed(
                "org/repo", 5, updates, "token", error_message="Boom"
            )

        assert mock_gh.add_issue_labels.called

    def test_logs_on_failure(self) -> None:
        updates: list[str] = []
        with patch(
            "helping_hands.lib.github.GitHubClient",
            side_effect=RuntimeError("fail"),
        ):
            mod._sync_issue_failed("org/repo", 5, updates, "token", error_message="X")


# ---------------------------------------------------------------------------
# _try_add_to_project
# ---------------------------------------------------------------------------


class TestTryAddToProject:
    def test_noop_when_no_project_url(self) -> None:
        mod._try_add_to_project("org/repo", 5, None, "token", [])

    def test_noop_when_no_issue_number(self) -> None:
        mod._try_add_to_project("org/repo", None, "https://project", "token", [])

    def test_adds_to_project(self) -> None:
        updates: list[str] = []
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        mock_gh.add_to_project_v2.return_value = "item-abc"

        with patch("helping_hands.lib.github.GitHubClient", return_value=mock_gh):
            mod._try_add_to_project("org/repo", 5, "https://project", "token", updates)

        mock_gh.add_to_project_v2.assert_called_once()
        assert any("item=item-abc" in u for u in updates)

    def test_logs_on_failure(self) -> None:
        updates: list[str] = []
        with patch(
            "helping_hands.lib.github.GitHubClient",
            side_effect=RuntimeError("fail"),
        ):
            mod._try_add_to_project("org/repo", 5, "https://project", "token", updates)
        assert any("Failed" in u for u in updates)


# ---------------------------------------------------------------------------
# _get_db_url_writer
# ---------------------------------------------------------------------------


class TestGetDbUrlWriter:
    def test_returns_url_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/mydb")
        assert mod._get_db_url_writer() == "postgresql://localhost/mydb"

    def test_strips_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "  postgresql://localhost/mydb  ")
        assert mod._get_db_url_writer() == "postgresql://localhost/mydb"

    def test_raises_when_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            mod._get_db_url_writer()

    def test_raises_when_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "  ")
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            mod._get_db_url_writer()
