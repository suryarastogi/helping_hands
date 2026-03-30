"""Tests for remaining untested server helper functions.

Covers:
- ``_maybe_persist_pr_to_schedule`` in ``celery_app.py``: guards schedule PR
  persistence behind three conditions (schedule_id, no input PR, valid digit string).
- ``_validate_path_param`` in ``app.py``: thin wrapper around
  ``require_non_empty_string`` for URL path parameters.
- ``_is_running_in_docker`` in ``app.py``: container detection via ``/.dockerenv``
  or ``HELPING_HANDS_IN_DOCKER`` env var.

Part of v342 execution plan.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# _maybe_persist_pr_to_schedule (celery_app.py)
# ---------------------------------------------------------------------------

pytest.importorskip("celery")

from helping_hands.server.celery_app import _maybe_persist_pr_to_schedule


class TestMaybePersistPrToSchedule:
    """Tests for _maybe_persist_pr_to_schedule guard conditions."""

    def test_noop_when_no_schedule_id(self) -> None:
        """Skip when build was not triggered from a schedule."""
        # Should not raise or attempt any schedule operations.
        _maybe_persist_pr_to_schedule(None, None, "42")

    def test_noop_when_input_pr_already_set(self) -> None:
        """Skip when the schedule already had a pre-existing PR."""
        _maybe_persist_pr_to_schedule("sched_abc123", 99, "42")

    def test_noop_when_result_pr_empty(self) -> None:
        """Skip when hand produced no PR number."""
        _maybe_persist_pr_to_schedule("sched_abc123", None, "")

    def test_noop_when_result_pr_not_digit(self) -> None:
        """Skip when result_pr_number is not a pure digit string."""
        _maybe_persist_pr_to_schedule("sched_abc123", None, "not-a-number")

    @patch("helping_hands.server.schedules.get_schedule_manager")
    def test_persists_when_all_conditions_met(self, mock_get_mgr) -> None:
        """Calls update_pr_number when schedule_id, no input PR, valid digit."""
        mock_manager = MagicMock()
        mock_get_mgr.return_value = mock_manager

        _maybe_persist_pr_to_schedule("sched_abc123", None, "42")

        mock_get_mgr.assert_called_once()
        mock_manager.update_pr_number.assert_called_once_with("sched_abc123", 42)

    @patch("helping_hands.server.schedules.get_schedule_manager")
    def test_exception_silently_logged(self, mock_get_mgr) -> None:
        """Failures are caught and logged, not raised."""
        mock_get_mgr.side_effect = RuntimeError("redis down")

        # Should not raise.
        _maybe_persist_pr_to_schedule("sched_abc123", None, "42")


# ---------------------------------------------------------------------------
# _validate_path_param (app.py)
# ---------------------------------------------------------------------------

pytest.importorskip("fastapi")

from helping_hands.server.app import (  # noqa: E402
    _is_running_in_docker,
    _validate_path_param,
)


class TestValidatePathParam:
    """Tests for _validate_path_param URL path validation wrapper."""

    def test_returns_stripped_value(self) -> None:
        assert _validate_path_param("  task-123  ", "task_id") == "task-123"

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError):
            _validate_path_param("", "task_id")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError):
            _validate_path_param("   ", "task_id")


# ---------------------------------------------------------------------------
# _is_running_in_docker (app.py)
# ---------------------------------------------------------------------------


class TestIsRunningInDocker:
    """Tests for _is_running_in_docker container detection."""

    def test_true_when_dockerenv_exists(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch("helping_hands.server.app.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            # Need to patch the specific call Path("/.dockerenv").exists()
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance
            assert _is_running_in_docker() is True

    def test_true_when_env_var_set(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "1")
        with patch("helping_hands.server.app.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance
            assert _is_running_in_docker() is True

    def test_false_when_neither(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch("helping_hands.server.app.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance
            assert _is_running_in_docker() is False
