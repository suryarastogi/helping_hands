"""Tests for ScheduleManager CRUD operations in server/schedules.py.

All Redis and RedBeat interactions are mocked so no live services are required.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery", reason="celery extra not installed")

from helping_hands.server.schedules import (
    _SCHEDULE_META_PREFIX,
    ScheduledTask,
    ScheduleManager,
    _check_croniter,
    _check_redbeat,
    get_schedule_manager,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_task(**overrides: object) -> ScheduledTask:
    """Create a ScheduledTask with sensible defaults."""
    defaults: dict = {
        "schedule_id": "sched_abc123def456",
        "name": "Test Schedule",
        "cron_expression": "0 0 * * *",
        "repo_path": "owner/repo",
        "prompt": "Update docs",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(overrides)
    return ScheduledTask(**defaults)


@pytest.fixture()
def mock_redis() -> MagicMock:
    """A mock Redis client."""
    return MagicMock()


@pytest.fixture()
def mock_celery(mock_redis: MagicMock) -> MagicMock:
    """A mock Celery app whose conf exposes a broker_url."""
    app = MagicMock()
    app.conf.get.return_value = "redis://localhost:6379/0"
    app.conf.broker_url = "redis://localhost:6379/0"
    return app


@pytest.fixture()
def manager(mock_celery: MagicMock, mock_redis: MagicMock) -> ScheduleManager:
    """A ScheduleManager wired to mock Redis (bypassing real connections)."""
    with (
        patch("helping_hands.server.schedules._redbeat_available", True),
        patch.object(ScheduleManager, "_get_redis_client", return_value=mock_redis),
    ):
        mgr = ScheduleManager(mock_celery)
    return mgr


# ---------------------------------------------------------------------------
# _check_redbeat / _check_croniter guards
# ---------------------------------------------------------------------------


class TestDependencyGuards:
    """Tests for optional dependency import guards."""

    def test_check_redbeat_raises_when_unavailable(self) -> None:
        with (
            patch("helping_hands.server.schedules._redbeat_available", False),
            pytest.raises(ImportError, match="celery-redbeat"),
        ):
            _check_redbeat()

    def test_check_redbeat_passes_when_available(self) -> None:
        with patch("helping_hands.server.schedules._redbeat_available", True):
            _check_redbeat()  # should not raise

    def test_check_croniter_raises_when_unavailable(self) -> None:
        with (
            patch("helping_hands.server.schedules.croniter", None),
            pytest.raises(ImportError, match="croniter"),
        ):
            _check_croniter()

    def test_check_croniter_passes_when_available(self) -> None:
        _check_croniter()  # should not raise (croniter is installed)


# ---------------------------------------------------------------------------
# ScheduleManager.__init__
# ---------------------------------------------------------------------------


class TestScheduleManagerInit:
    """Tests for ScheduleManager initialization."""

    def test_init_stores_celery_app(
        self, manager: ScheduleManager, mock_celery: MagicMock
    ) -> None:
        assert manager._app is mock_celery

    def test_init_raises_when_redbeat_unavailable(self, mock_celery: MagicMock) -> None:
        with (
            patch("helping_hands.server.schedules._redbeat_available", False),
            pytest.raises(ImportError, match="celery-redbeat"),
        ):
            ScheduleManager(mock_celery)


# ---------------------------------------------------------------------------
# _meta_key
# ---------------------------------------------------------------------------


class TestMetaKey:
    """Tests for Redis key generation."""

    def test_meta_key_format(self, manager: ScheduleManager) -> None:
        key = manager._meta_key("sched_123")
        assert key == f"{_SCHEDULE_META_PREFIX}sched_123"

    def test_meta_key_empty_id(self, manager: ScheduleManager) -> None:
        key = manager._meta_key("")
        assert key == _SCHEDULE_META_PREFIX


# ---------------------------------------------------------------------------
# _save_meta / _load_meta / _delete_meta / _list_meta_keys
# ---------------------------------------------------------------------------


class TestMetaPersistence:
    """Tests for Redis metadata CRUD helpers."""

    def test_save_meta_writes_json(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        manager._save_meta(task)
        mock_redis.set.assert_called_once()
        key, value = mock_redis.set.call_args[0]
        assert key == manager._meta_key(task.schedule_id)
        assert json.loads(value)["name"] == "Test Schedule"

    def test_save_meta_raises_on_redis_error(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.set.side_effect = ConnectionError("redis down")
        with pytest.raises(RuntimeError, match="Failed to persist schedule"):
            manager._save_meta(_make_task())

    def test_load_meta_returns_task(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())
        loaded = manager._load_meta(task.schedule_id)
        assert loaded is not None
        assert loaded.schedule_id == task.schedule_id
        assert loaded.name == task.name

    def test_load_meta_returns_none_when_missing(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager._load_meta("nonexistent") is None

    def test_load_meta_returns_none_on_corrupt_json(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = "not valid json{{"
        assert manager._load_meta("bad") is None

    def test_load_meta_returns_none_on_missing_fields(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = json.dumps({"name": "incomplete"})
        assert manager._load_meta("incomplete") is None

    def test_delete_meta_calls_redis_delete(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        manager._delete_meta("sched_xyz")
        mock_redis.delete.assert_called_once_with(manager._meta_key("sched_xyz"))

    def test_delete_meta_logs_warning_on_error(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.delete.side_effect = ConnectionError("redis down")
        # Should not raise
        manager._delete_meta("sched_xyz")

    def test_list_meta_keys_returns_decoded_keys(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.keys.return_value = [
            b"helping_hands:schedule:meta:sched_aaa",
            b"helping_hands:schedule:meta:sched_bbb",
        ]
        keys = manager._list_meta_keys()
        assert len(keys) == 2
        assert all(isinstance(k, str) for k in keys)

    def test_list_meta_keys_handles_string_keys(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.keys.return_value = [
            "helping_hands:schedule:meta:sched_aaa",
        ]
        keys = manager._list_meta_keys()
        assert keys == ["helping_hands:schedule:meta:sched_aaa"]

    def test_list_meta_keys_returns_empty_on_error(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.keys.side_effect = ConnectionError("redis down")
        assert manager._list_meta_keys() == []


# ---------------------------------------------------------------------------
# create_schedule
# ---------------------------------------------------------------------------


class TestCreateSchedule:
    """Tests for ScheduleManager.create_schedule()."""

    def test_create_schedule_saves_and_returns(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None  # no duplicate
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            result = manager.create_schedule(task)
        assert result.schedule_id == task.schedule_id
        mock_redis.set.assert_called_once()

    def test_create_schedule_generates_id_when_empty(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        task = _make_task(schedule_id="")
        with patch.object(manager, "_create_redbeat_entry"):
            result = manager.create_schedule(task)
        assert result.schedule_id.startswith("sched_")
        assert len(result.schedule_id) == 18

    def test_create_schedule_raises_on_duplicate(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        existing = _make_task()
        mock_redis.get.return_value = json.dumps(existing.to_dict())
        with pytest.raises(ValueError, match="already exists"):
            manager.create_schedule(_make_task())

    def test_create_schedule_skips_redbeat_when_disabled(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        task = _make_task(enabled=False)
        with patch.object(manager, "_create_redbeat_entry") as mock_rb:
            manager.create_schedule(task)
        mock_rb.assert_not_called()

    def test_create_schedule_creates_redbeat_when_enabled(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        task = _make_task(enabled=True)
        with patch.object(manager, "_create_redbeat_entry") as mock_rb:
            manager.create_schedule(task)
        mock_rb.assert_called_once_with(task)


# ---------------------------------------------------------------------------
# _create_redbeat_entry / _delete_redbeat_entry
# ---------------------------------------------------------------------------


class TestRedBeatEntries:
    """Tests for RedBeat entry creation and deletion."""

    def test_create_redbeat_entry_calls_save(self, manager: ScheduleManager) -> None:
        task = _make_task(cron_expression="0 9 * * 1-5")
        with patch(
            "helping_hands.server.schedules.RedBeatSchedulerEntry"
        ) as mock_entry_cls:
            mock_entry = MagicMock()
            mock_entry_cls.return_value = mock_entry
            manager._create_redbeat_entry(task)
        mock_entry.save.assert_called_once()

    def test_create_redbeat_entry_rejects_bad_cron(
        self, manager: ScheduleManager
    ) -> None:
        task = _make_task(cron_expression="bad")
        with pytest.raises(ValueError, match="Invalid cron expression"):
            manager._create_redbeat_entry(task)

    def test_delete_redbeat_entry_calls_delete(self, manager: ScheduleManager) -> None:
        with patch(
            "helping_hands.server.schedules.RedBeatSchedulerEntry"
        ) as mock_entry_cls:
            mock_entry = MagicMock()
            mock_entry_cls.from_key.return_value = mock_entry
            manager._delete_redbeat_entry("sched_abc")
        mock_entry.delete.assert_called_once()

    def test_delete_redbeat_entry_handles_missing(
        self, manager: ScheduleManager
    ) -> None:
        with patch(
            "helping_hands.server.schedules.RedBeatSchedulerEntry"
        ) as mock_entry_cls:
            mock_entry_cls.from_key.side_effect = KeyError("not found")
            manager._delete_redbeat_entry("sched_missing")
        # Should not raise


# ---------------------------------------------------------------------------
# get_schedule
# ---------------------------------------------------------------------------


class TestGetSchedule:
    """Tests for ScheduleManager.get_schedule()."""

    def test_get_existing_schedule(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())
        result = manager.get_schedule(task.schedule_id)
        assert result is not None
        assert result.schedule_id == task.schedule_id

    def test_get_missing_schedule(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.get_schedule("nonexistent") is None


# ---------------------------------------------------------------------------
# list_schedules
# ---------------------------------------------------------------------------


class TestListSchedules:
    """Tests for ScheduleManager.list_schedules()."""

    def test_list_returns_sorted_by_created_at_desc(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task_a = _make_task(
            schedule_id="sched_aaa",
            name="A",
            created_at="2026-01-01T00:00:00+00:00",
        )
        task_b = _make_task(
            schedule_id="sched_bbb",
            name="B",
            created_at="2026-02-01T00:00:00+00:00",
        )
        mock_redis.keys.return_value = [
            f"{_SCHEDULE_META_PREFIX}sched_aaa".encode(),
            f"{_SCHEDULE_META_PREFIX}sched_bbb".encode(),
        ]

        def fake_get(key: str) -> str | None:
            if "sched_aaa" in key:
                return json.dumps(task_a.to_dict())
            if "sched_bbb" in key:
                return json.dumps(task_b.to_dict())
            return None

        mock_redis.get.side_effect = fake_get
        results = manager.list_schedules()
        assert len(results) == 2
        assert results[0].name == "B"  # newer first
        assert results[1].name == "A"

    def test_list_skips_corrupt_entries(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.keys.return_value = [
            f"{_SCHEDULE_META_PREFIX}sched_ok".encode(),
            f"{_SCHEDULE_META_PREFIX}sched_bad".encode(),
        ]

        def fake_get(key: str) -> str | None:
            if "sched_ok" in key:
                return json.dumps(_make_task(schedule_id="sched_ok").to_dict())
            if "sched_bad" in key:
                return "corrupt{json"
            return None

        mock_redis.get.side_effect = fake_get
        results = manager.list_schedules()
        assert len(results) == 1
        assert results[0].schedule_id == "sched_ok"

    def test_list_returns_empty_on_no_schedules(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.keys.return_value = []
        assert manager.list_schedules() == []


# ---------------------------------------------------------------------------
# update_schedule
# ---------------------------------------------------------------------------


class TestUpdateSchedule:
    """Tests for ScheduleManager.update_schedule()."""

    def test_update_preserves_metadata(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        existing = _make_task(
            last_run_at="2026-03-01T00:00:00+00:00",
            last_run_task_id="celery-task-99",
            run_count=5,
        )
        mock_redis.get.return_value = json.dumps(existing.to_dict())

        updated = _make_task(name="Updated Name", prompt="new prompt")
        with (
            patch.object(manager, "_create_redbeat_entry"),
            patch.object(manager, "_delete_redbeat_entry"),
        ):
            result = manager.update_schedule(updated)

        assert result.name == "Updated Name"
        assert result.last_run_at == "2026-03-01T00:00:00+00:00"
        assert result.last_run_task_id == "celery-task-99"
        assert result.run_count == 5

    def test_update_raises_when_not_found(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            manager.update_schedule(_make_task())

    def test_update_recreates_redbeat_when_enabled(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        existing = _make_task()
        mock_redis.get.return_value = json.dumps(existing.to_dict())
        with (
            patch.object(manager, "_create_redbeat_entry") as mock_create,
            patch.object(manager, "_delete_redbeat_entry") as mock_del,
        ):
            manager.update_schedule(_make_task(enabled=True))
        mock_del.assert_called_once()
        mock_create.assert_called_once()

    def test_update_skips_redbeat_when_disabled(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        existing = _make_task()
        mock_redis.get.return_value = json.dumps(existing.to_dict())
        with (
            patch.object(manager, "_create_redbeat_entry") as mock_create,
            patch.object(manager, "_delete_redbeat_entry") as mock_del,
        ):
            manager.update_schedule(_make_task(enabled=False))
        mock_del.assert_called_once()
        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# delete_schedule
# ---------------------------------------------------------------------------


class TestDeleteSchedule:
    """Tests for ScheduleManager.delete_schedule()."""

    def test_delete_existing_returns_true(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_delete_redbeat_entry"):
            result = manager.delete_schedule(task.schedule_id)
        assert result is True
        mock_redis.delete.assert_called_once()

    def test_delete_missing_returns_false(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        result = manager.delete_schedule("nonexistent")
        assert result is False


# ---------------------------------------------------------------------------
# enable_schedule / disable_schedule
# ---------------------------------------------------------------------------


class TestEnableDisableSchedule:
    """Tests for ScheduleManager.enable_schedule/disable_schedule."""

    def test_enable_creates_redbeat_entry(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=False)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_create_redbeat_entry") as mock_create:
            result = manager.enable_schedule(task.schedule_id)
        assert result is not None
        assert result.enabled is True
        mock_create.assert_called_once()

    def test_enable_noop_when_already_enabled(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=True)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_create_redbeat_entry") as mock_create:
            result = manager.enable_schedule(task.schedule_id)
        assert result is not None
        mock_create.assert_not_called()

    def test_enable_returns_none_when_missing(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.enable_schedule("nonexistent") is None

    def test_disable_deletes_redbeat_entry(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=True)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_delete_redbeat_entry") as mock_del:
            result = manager.disable_schedule(task.schedule_id)
        assert result is not None
        assert result.enabled is False
        mock_del.assert_called_once()

    def test_disable_noop_when_already_disabled(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=False)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_delete_redbeat_entry") as mock_del:
            result = manager.disable_schedule(task.schedule_id)
        assert result is not None
        mock_del.assert_not_called()

    def test_disable_returns_none_when_missing(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.disable_schedule("nonexistent") is None


# ---------------------------------------------------------------------------
# record_run
# ---------------------------------------------------------------------------


class TestRecordRun:
    """Tests for ScheduleManager.record_run()."""

    def test_record_run_updates_metadata(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(run_count=3)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        manager.record_run(task.schedule_id, "celery-task-42")
        # Should have saved updated metadata
        assert mock_redis.set.call_count == 1
        saved = json.loads(mock_redis.set.call_args[0][1])
        assert saved["run_count"] == 4
        assert saved["last_run_task_id"] == "celery-task-42"
        assert saved["last_run_at"] is not None

    def test_record_run_noop_when_missing(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        manager.record_run("nonexistent", "task-id")
        mock_redis.set.assert_not_called()


# ---------------------------------------------------------------------------
# trigger_now
# ---------------------------------------------------------------------------


class TestTriggerNow:
    """Tests for ScheduleManager.trigger_now()."""

    def test_trigger_now_dispatches_task(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())
        mock_result = MagicMock()
        mock_result.id = "celery-dispatched-123"

        mock_build = MagicMock()
        mock_build.delay.return_value = mock_result
        with patch.dict(
            "sys.modules",
            {"helping_hands.server.celery_app": MagicMock(build_feature=mock_build)},
        ):
            result = manager.trigger_now(task.schedule_id)

        assert result == "celery-dispatched-123"
        mock_build.delay.assert_called_once()
        kwargs = mock_build.delay.call_args[1]
        assert kwargs["repo_path"] == task.repo_path
        assert kwargs["prompt"] == task.prompt

    def test_trigger_now_returns_none_when_missing(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.trigger_now("nonexistent") is None


# ---------------------------------------------------------------------------
# get_schedule_manager factory
# ---------------------------------------------------------------------------


class TestGetScheduleManager:
    """Tests for the get_schedule_manager factory function."""

    def test_returns_manager_instance(self, mock_celery: MagicMock) -> None:
        with (
            patch("helping_hands.server.schedules._redbeat_available", True),
            patch.object(
                ScheduleManager,
                "_get_redis_client",
                return_value=MagicMock(),
            ),
        ):
            mgr = get_schedule_manager(mock_celery)
        assert isinstance(mgr, ScheduleManager)
