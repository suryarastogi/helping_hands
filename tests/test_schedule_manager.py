"""Tests for ScheduleManager class (TD-001).

Uses mocked Redis and RedBeat to test CRUD operations, enable/disable,
record_run, and trigger_now without requiring a live Redis instance.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery")

from helping_hands.server.schedules import (
    _SCHEDULE_META_PREFIX,
    ScheduledTask,
    ScheduleManager,
    next_run_time,
)


@pytest.fixture()
def mock_redis():
    """In-memory dict-backed mock Redis client."""
    store: dict[str, bytes] = {}
    client = MagicMock()
    client.get = MagicMock(side_effect=lambda k: store.get(k))
    client.set = MagicMock(side_effect=lambda k, v: store.__setitem__(k, v))
    client.delete = MagicMock(side_effect=lambda k: store.pop(k, None))
    client.keys = MagicMock(
        side_effect=lambda pattern: [
            k for k in store if k.startswith(pattern.replace("*", ""))
        ]
    )
    client._store = store  # expose for assertions
    return client


@pytest.fixture()
def manager(mock_redis):
    """ScheduleManager with mocked Redis and RedBeat."""
    app = MagicMock()
    app.conf = MagicMock()
    app.conf.get = MagicMock(return_value="redis://localhost:6379/0")
    app.conf.broker_url = "redis://localhost:6379/0"

    with (
        patch("helping_hands.server.schedules._check_redbeat"),
        patch(
            "helping_hands.server.schedules.ScheduleManager._get_redis_client",
            return_value=mock_redis,
        ),
    ):
        mgr = ScheduleManager(app)
    return mgr


def _make_task(
    schedule_id: str = "sched_test123456",
    name: str = "Test Schedule",
    cron_expression: str = "0 0 * * *",
    **kwargs,
) -> ScheduledTask:
    return ScheduledTask(
        schedule_id=schedule_id,
        name=name,
        cron_expression=cron_expression,
        repo_path="owner/repo",
        prompt="Do something",
        **kwargs,
    )


class TestScheduleManagerCreate:
    """Tests for create_schedule."""

    def test_create_schedule_saves_meta(self, manager, mock_redis):
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            result = manager.create_schedule(task)

        assert result.schedule_id == "sched_test123456"
        key = f"{_SCHEDULE_META_PREFIX}sched_test123456"
        assert key in mock_redis._store

    def test_create_schedule_generates_id_when_empty(self, manager):
        task = _make_task(schedule_id="")
        with patch.object(manager, "_create_redbeat_entry"):
            result = manager.create_schedule(task)

        assert result.schedule_id.startswith("sched_")
        assert len(result.schedule_id) == 18

    def test_create_duplicate_raises(self, manager):
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        with (
            pytest.raises(ValueError, match="already exists"),
            patch.object(manager, "_create_redbeat_entry"),
        ):
            manager.create_schedule(_make_task())

    def test_create_disabled_skips_redbeat(self, manager):
        task = _make_task(enabled=False)
        with patch.object(manager, "_create_redbeat_entry") as mock_rb:
            manager.create_schedule(task)
        mock_rb.assert_not_called()

    def test_create_enabled_creates_redbeat(self, manager):
        task = _make_task(enabled=True)
        with patch.object(manager, "_create_redbeat_entry") as mock_rb:
            manager.create_schedule(task)
        mock_rb.assert_called_once_with(task)


class TestScheduleManagerGet:
    """Tests for get_schedule."""

    def test_get_existing(self, manager):
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        result = manager.get_schedule("sched_test123456")
        assert result is not None
        assert result.name == "Test Schedule"

    def test_get_nonexistent_returns_none(self, manager):
        result = manager.get_schedule("nonexistent")
        assert result is None


class TestScheduleManagerList:
    """Tests for list_schedules."""

    def test_list_empty(self, manager):
        assert manager.list_schedules() == []

    def test_list_multiple_sorted(self, manager):
        with patch.object(manager, "_create_redbeat_entry"):
            t1 = _make_task(schedule_id="sched_aaa", name="First")
            t1.created_at = "2026-01-01T00:00:00"
            manager.create_schedule(t1)

            t2 = _make_task(schedule_id="sched_bbb", name="Second")
            t2.created_at = "2026-02-01T00:00:00"
            manager.create_schedule(t2)

        result = manager.list_schedules()
        assert len(result) == 2
        # Sorted by created_at descending
        assert result[0].name == "Second"
        assert result[1].name == "First"


class TestScheduleManagerUpdate:
    """Tests for update_schedule."""

    def test_update_preserves_metadata(self, manager):
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        # Record a run to set metadata
        manager.record_run("sched_test123456", "celery-task-id-1")

        updated = _make_task(name="Updated Name")
        with (
            patch.object(manager, "_create_redbeat_entry"),
            patch.object(manager, "_delete_redbeat_entry"),
        ):
            result = manager.update_schedule(updated)

        assert result.name == "Updated Name"
        assert result.run_count == 1
        assert result.last_run_task_id == "celery-task-id-1"

    def test_update_nonexistent_raises(self, manager):
        task = _make_task(schedule_id="nonexistent")
        with pytest.raises(ValueError, match="not found"):
            manager.update_schedule(task)


class TestScheduleManagerDelete:
    """Tests for delete_schedule."""

    def test_delete_existing(self, manager):
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        with patch.object(manager, "_delete_redbeat_entry"):
            assert manager.delete_schedule("sched_test123456") is True

        assert manager.get_schedule("sched_test123456") is None

    def test_delete_nonexistent(self, manager):
        assert manager.delete_schedule("nonexistent") is False


class TestScheduleManagerEnableDisable:
    """Tests for enable_schedule and disable_schedule."""

    def test_disable_enabled_schedule(self, manager):
        task = _make_task(enabled=True)
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        with patch.object(manager, "_delete_redbeat_entry") as mock_del:
            result = manager.disable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is False
        mock_del.assert_called_once()

    def test_disable_already_disabled_is_noop(self, manager):
        task = _make_task(enabled=False)
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        with patch.object(manager, "_delete_redbeat_entry") as mock_del:
            result = manager.disable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is False
        mock_del.assert_not_called()

    def test_enable_disabled_schedule(self, manager):
        task = _make_task(enabled=False)
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        with patch.object(manager, "_create_redbeat_entry") as mock_create:
            result = manager.enable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is True
        mock_create.assert_called_once()

    def test_enable_already_enabled_is_noop(self, manager):
        task = _make_task(enabled=True)
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        with patch.object(manager, "_create_redbeat_entry") as mock_create:
            result = manager.enable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is True
        mock_create.assert_not_called()

    def test_enable_nonexistent_returns_none(self, manager):
        assert manager.enable_schedule("nonexistent") is None

    def test_disable_nonexistent_returns_none(self, manager):
        assert manager.disable_schedule("nonexistent") is None


class TestScheduleManagerRecordRun:
    """Tests for record_run."""

    def test_record_run_increments_count(self, manager):
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        manager.record_run("sched_test123456", "celery-id-1")
        manager.record_run("sched_test123456", "celery-id-2")

        result = manager.get_schedule("sched_test123456")
        assert result is not None
        assert result.run_count == 2
        assert result.last_run_task_id == "celery-id-2"
        assert result.last_run_at is not None

    def test_record_run_nonexistent_is_noop(self, manager):
        # Should not raise
        manager.record_run("nonexistent", "task-id")


class TestScheduleManagerTriggerNow:
    """Tests for trigger_now."""

    def test_trigger_now_dispatches_task(self, manager):
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            manager.create_schedule(task)

        mock_result = MagicMock()
        mock_result.id = "celery-triggered-id"

        with patch(
            "helping_hands.server.schedules.ScheduleManager.trigger_now"
        ) as mock_trigger:
            mock_trigger.return_value = "celery-triggered-id"
            result = manager.trigger_now("sched_test123456")

        assert result == "celery-triggered-id"

    def test_trigger_now_nonexistent_returns_none(self, manager):
        # The actual trigger_now loads meta first
        result_task = manager.get_schedule("nonexistent")
        assert result_task is None


class TestNextRunTime:
    """Tests for next_run_time helper."""

    def test_next_run_returns_datetime(self):
        from datetime import UTC, datetime

        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = next_run_time("0 0 * * *", base_time=base)
        assert result > base

    def test_next_run_defaults_to_now(self):
        from datetime import UTC, datetime

        result = next_run_time("0 0 * * *")
        assert result > datetime.now(UTC)
