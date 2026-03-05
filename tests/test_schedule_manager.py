"""Tests for ScheduleManager and schedule dependency checks."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery", reason="celery extra not installed")

from helping_hands.server.schedules import (
    _SCHEDULE_META_PREFIX,
    ScheduledTask,
    _check_croniter,
    _check_redbeat,
)

# ---------------------------------------------------------------------------
# _check_redbeat / _check_croniter
# ---------------------------------------------------------------------------


class TestCheckRedbeat:
    def test_raises_when_unavailable(self) -> None:
        import helping_hands.server.schedules as mod

        orig = mod._redbeat_available
        try:
            mod._redbeat_available = False
            with pytest.raises(ImportError, match="celery-redbeat is required"):
                _check_redbeat()
        finally:
            mod._redbeat_available = orig

    def test_passes_when_available(self) -> None:
        import helping_hands.server.schedules as mod

        orig = mod._redbeat_available
        try:
            mod._redbeat_available = True
            _check_redbeat()  # should not raise
        finally:
            mod._redbeat_available = orig


class TestCheckCroniter:
    def test_raises_when_unavailable(self) -> None:
        import helping_hands.server.schedules as mod

        orig = mod.croniter
        try:
            mod.croniter = None  # type: ignore[assignment]
            with pytest.raises(ImportError, match="croniter is required"):
                _check_croniter()
        finally:
            mod.croniter = orig

    def test_passes_when_available(self) -> None:
        _check_croniter()  # croniter is installed; should not raise


# ---------------------------------------------------------------------------
# ScheduleManager
# ---------------------------------------------------------------------------


def _make_task(**overrides) -> ScheduledTask:
    """Helper to create a ScheduledTask with sensible defaults."""
    defaults = {
        "schedule_id": "sched_test123456",
        "name": "Test Schedule",
        "cron_expression": "0 0 * * *",
        "repo_path": "owner/repo",
        "prompt": "fix bugs",
    }
    defaults.update(overrides)
    return ScheduledTask(**defaults)


def _build_manager():
    """Build a ScheduleManager with a mocked Celery app and Redis client."""
    from helping_hands.server.schedules import ScheduleManager

    mock_app = MagicMock()
    mock_app.conf.get.return_value = "redis://localhost:6379/0"
    mock_app.conf.broker_url = "redis://localhost:6379/0"

    mock_redis = MagicMock()

    with patch.object(ScheduleManager, "__init__", lambda self, app: None):
        mgr = ScheduleManager(mock_app)

    mgr._app = mock_app
    mgr._redis = mock_redis
    return mgr, mock_redis, mock_app


class TestScheduleManagerMetaKey:
    def test_key_format(self) -> None:
        mgr, _, _ = _build_manager()
        key = mgr._meta_key("sched_abc123")
        assert key == f"{_SCHEDULE_META_PREFIX}sched_abc123"


class TestScheduleManagerCRUD:
    def test_save_and_load_meta(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task()

        mgr._save_meta(task)
        mock_redis.set.assert_called_once()
        key_arg = mock_redis.set.call_args[0][0]
        json_arg = mock_redis.set.call_args[0][1]
        assert "sched_test123456" in key_arg
        data = json.loads(json_arg)
        assert data["name"] == "Test Schedule"

    def test_load_meta_returns_none_when_missing(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None
        result = mgr._load_meta("nonexistent")
        assert result is None

    def test_load_meta_returns_task(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())

        result = mgr._load_meta("sched_test123456")
        assert result is not None
        assert result.name == "Test Schedule"

    def test_delete_meta(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mgr._delete_meta("sched_abc")
        mock_redis.delete.assert_called_once()

    def test_list_meta_keys_decodes_bytes(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.keys.return_value = [
            b"helping_hands:schedule:meta:sched_a",
            b"helping_hands:schedule:meta:sched_b",
        ]
        keys = mgr._list_meta_keys()
        assert len(keys) == 2
        assert all(isinstance(k, str) for k in keys)

    def test_list_meta_keys_handles_strings(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.keys.return_value = [
            "helping_hands:schedule:meta:sched_a",
        ]
        keys = mgr._list_meta_keys()
        assert keys == ["helping_hands:schedule:meta:sched_a"]


class TestScheduleManagerCreateSchedule:
    def test_create_schedule_happy_path(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None  # no duplicate

        task = _make_task(enabled=False)

        with patch.object(mgr, "_create_redbeat_entry"):
            result = mgr.create_schedule(task)

        assert result.schedule_id == "sched_test123456"
        mock_redis.set.assert_called_once()

    def test_create_schedule_duplicate_raises(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        existing = _make_task()
        mock_redis.get.return_value = json.dumps(existing.to_dict())

        with pytest.raises(ValueError, match="already exists"):
            mgr.create_schedule(_make_task())

    def test_create_schedule_generates_id_when_empty(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None

        task = _make_task(schedule_id="", enabled=False)
        with patch.object(mgr, "_create_redbeat_entry"):
            result = mgr.create_schedule(task)

        assert result.schedule_id.startswith("sched_")
        assert len(result.schedule_id) == 18


class TestScheduleManagerGetAndList:
    def test_get_schedule_returns_task(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())

        result = mgr.get_schedule("sched_test123456")
        assert result is not None
        assert result.schedule_id == "sched_test123456"

    def test_get_schedule_returns_none(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None
        assert mgr.get_schedule("nonexistent") is None

    def test_list_schedules_sorted_by_created_at(self) -> None:
        mgr, mock_redis, _ = _build_manager()

        task_old = _make_task(
            schedule_id="sched_old",
            name="Old",
            created_at="2025-01-01T00:00:00+00:00",
        )
        task_new = _make_task(
            schedule_id="sched_new",
            name="New",
            created_at="2025-06-01T00:00:00+00:00",
        )

        mock_redis.keys.return_value = [
            f"{_SCHEDULE_META_PREFIX}sched_old",
            f"{_SCHEDULE_META_PREFIX}sched_new",
        ]

        def get_side_effect(key):
            if "sched_old" in key:
                return json.dumps(task_old.to_dict())
            if "sched_new" in key:
                return json.dumps(task_new.to_dict())
            return None

        mock_redis.get.side_effect = get_side_effect

        result = mgr.list_schedules()
        assert len(result) == 2
        assert result[0].name == "New"  # newest first
        assert result[1].name == "Old"


class TestScheduleManagerUpdate:
    def test_update_preserves_metadata(self) -> None:
        mgr, mock_redis, _ = _build_manager()

        existing = _make_task(
            created_at="2025-01-01T00:00:00+00:00",
            last_run_at="2025-06-01T00:00:00+00:00",
            last_run_task_id="celery-xyz",
            run_count=5,
        )
        mock_redis.get.return_value = json.dumps(existing.to_dict())

        updated = _make_task(name="Updated Name", enabled=False)

        with (
            patch.object(mgr, "_create_redbeat_entry"),
            patch.object(mgr, "_delete_redbeat_entry"),
        ):
            result = mgr.update_schedule(updated)

        assert result.created_at == "2025-01-01T00:00:00+00:00"
        assert result.last_run_at == "2025-06-01T00:00:00+00:00"
        assert result.run_count == 5

    def test_update_not_found_raises(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            mgr.update_schedule(_make_task())


class TestScheduleManagerDelete:
    def test_delete_success(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())

        with patch.object(mgr, "_delete_redbeat_entry"):
            result = mgr.delete_schedule("sched_test123456")

        assert result is True
        mock_redis.delete.assert_called_once()

    def test_delete_not_found(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None
        assert mgr.delete_schedule("nonexistent") is False


class TestScheduleManagerEnableDisable:
    def test_enable_schedule(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(enabled=False)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        with patch.object(mgr, "_create_redbeat_entry"):
            result = mgr.enable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is True

    def test_enable_already_enabled(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(enabled=True)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        with patch.object(mgr, "_create_redbeat_entry") as mock_create:
            result = mgr.enable_schedule("sched_test123456")

        assert result is not None
        mock_create.assert_not_called()

    def test_enable_not_found(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None
        assert mgr.enable_schedule("nonexistent") is None

    def test_disable_schedule(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(enabled=True)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        with patch.object(mgr, "_delete_redbeat_entry"):
            result = mgr.disable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is False

    def test_disable_already_disabled(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(enabled=False)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        with patch.object(mgr, "_delete_redbeat_entry") as mock_delete:
            result = mgr.disable_schedule("sched_test123456")

        assert result is not None
        mock_delete.assert_not_called()

    def test_disable_not_found(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None
        assert mgr.disable_schedule("nonexistent") is None


class TestScheduleManagerRecordRun:
    def test_record_run_updates_metadata(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(run_count=2)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        mgr.record_run("sched_test123456", "celery-task-abc")

        # Check that save was called with updated data
        call_args = mock_redis.set.call_args[0]
        saved_data = json.loads(call_args[1])
        assert saved_data["run_count"] == 3
        assert saved_data["last_run_task_id"] == "celery-task-abc"
        assert saved_data["last_run_at"] is not None

    def test_record_run_missing_schedule(self) -> None:
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None

        mgr.record_run("nonexistent", "celery-task-abc")  # should not raise
        mock_redis.set.assert_not_called()
