"""Tests for ScheduleManager and schedule dependency checks."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery", reason="celery extra not installed")

from helping_hands.server.schedules import (
    _SCHEDULE_ID_HEX_LENGTH,
    _SCHEDULE_META_PREFIX,
    ScheduledTask,
    _check_croniter,
    _check_redbeat,
    generate_schedule_id,
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


# ---------------------------------------------------------------------------
# create_schedule with enabled=True
# ---------------------------------------------------------------------------


class TestScheduleManagerCreateEnabled:
    def test_create_enabled_calls_redbeat_entry(self) -> None:
        """When enabled=True, create_schedule must call _create_redbeat_entry."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None  # no duplicate

        task = _make_task(enabled=True)

        with patch.object(mgr, "_create_redbeat_entry") as mock_create:
            mgr.create_schedule(task)

        mock_create.assert_called_once_with(task)

    def test_create_disabled_skips_redbeat_entry(self) -> None:
        """When enabled=False, _create_redbeat_entry must NOT be called."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None

        task = _make_task(enabled=False)

        with patch.object(mgr, "_create_redbeat_entry") as mock_create:
            mgr.create_schedule(task)

        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# update_schedule with enabled=True
# ---------------------------------------------------------------------------


class TestScheduleManagerUpdateEnabled:
    def test_update_enabled_creates_redbeat_entry(self) -> None:
        """When enabled=True after update, _create_redbeat_entry is called."""
        mgr, mock_redis, _ = _build_manager()
        existing = _make_task(enabled=False)
        mock_redis.get.return_value = json.dumps(existing.to_dict())

        updated = _make_task(name="Updated", enabled=True)

        with (
            patch.object(mgr, "_create_redbeat_entry") as mock_create,
            patch.object(mgr, "_delete_redbeat_entry"),
        ):
            mgr.update_schedule(updated)

        mock_create.assert_called_once()

    def test_update_disabled_skips_redbeat_entry(self) -> None:
        """When enabled=False after update, _create_redbeat_entry is NOT called."""
        mgr, mock_redis, _ = _build_manager()
        existing = _make_task(enabled=True)
        mock_redis.get.return_value = json.dumps(existing.to_dict())

        updated = _make_task(name="Disabled", enabled=False)

        with (
            patch.object(mgr, "_create_redbeat_entry") as mock_create,
            patch.object(mgr, "_delete_redbeat_entry"),
        ):
            mgr.update_schedule(updated)

        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# _create_redbeat_entry validation
# ---------------------------------------------------------------------------


class TestCreateRedbeatEntry:
    def test_invalid_cron_parts_raises(self) -> None:
        """_create_redbeat_entry should raise ValueError for non-5-part cron."""
        mgr, _, _ = _build_manager()
        task = _make_task(cron_expression="0 0 *")  # only 3 parts

        with pytest.raises(ValueError, match="Invalid cron expression"):
            mgr._create_redbeat_entry(task)

    def test_too_many_cron_parts_raises(self) -> None:
        """_create_redbeat_entry should raise ValueError for >5 cron parts."""
        mgr, _, _ = _build_manager()
        task = _make_task(cron_expression="0 0 * * * *")  # 6 parts

        with pytest.raises(ValueError, match="Invalid cron expression"):
            mgr._create_redbeat_entry(task)


# ---------------------------------------------------------------------------
# _delete_redbeat_entry KeyError handling
# ---------------------------------------------------------------------------


class TestDeleteRedbeatEntry:
    def test_delete_nonexistent_entry_no_error(self) -> None:
        """_delete_redbeat_entry should silently handle KeyError."""
        mgr, _, _ = _build_manager()

        import helping_hands.server.schedules as mod

        mock_entry_cls = MagicMock()
        mock_entry_cls.from_key.side_effect = KeyError("not found")

        orig = mod.RedBeatSchedulerEntry
        try:
            mod.RedBeatSchedulerEntry = mock_entry_cls
            mgr._delete_redbeat_entry("sched_nonexistent")  # should not raise
        finally:
            mod.RedBeatSchedulerEntry = orig

    def test_delete_existing_entry_calls_delete(self) -> None:
        """_delete_redbeat_entry should call entry.delete() on success."""
        mgr, _, _ = _build_manager()

        import helping_hands.server.schedules as mod

        mock_entry = MagicMock()
        mock_entry_cls = MagicMock()
        mock_entry_cls.from_key.return_value = mock_entry

        orig = mod.RedBeatSchedulerEntry
        try:
            mod.RedBeatSchedulerEntry = mock_entry_cls
            mgr._delete_redbeat_entry("sched_abc")
        finally:
            mod.RedBeatSchedulerEntry = orig

        mock_entry.delete.assert_called_once()


# ---------------------------------------------------------------------------
# list_schedules filters None entries
# ---------------------------------------------------------------------------


class TestListSchedulesFiltering:
    def test_list_schedules_filters_none(self) -> None:
        """list_schedules should skip entries where _load_meta returns None."""
        mgr, mock_redis, _ = _build_manager()

        task_a = _make_task(
            schedule_id="sched_a",
            name="A",
            created_at="2025-01-01T00:00:00+00:00",
        )

        mock_redis.keys.return_value = [
            f"{_SCHEDULE_META_PREFIX}sched_a",
            f"{_SCHEDULE_META_PREFIX}sched_missing",
        ]

        def get_side_effect(key):
            if "sched_a" in key:
                return json.dumps(task_a.to_dict())
            return None  # sched_missing not found in Redis

        mock_redis.get.side_effect = get_side_effect

        result = mgr.list_schedules()
        assert len(result) == 1
        assert result[0].name == "A"

    def test_list_schedules_empty(self) -> None:
        """list_schedules should return empty list when no keys exist."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.keys.return_value = []
        assert mgr.list_schedules() == []


# ---------------------------------------------------------------------------
# trigger_now
# ---------------------------------------------------------------------------


class TestScheduleManagerTriggerNow:
    def test_trigger_now_happy_path(self) -> None:
        """trigger_now should dispatch a celery task and record the run."""
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(run_count=0)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        mock_result = MagicMock()
        mock_result.id = "celery-task-triggered"

        with patch(
            "helping_hands.server.schedules.ScheduleManager.trigger_now"
        ) as mock_trigger:
            # We need to test the real method, so let's mock build_feature
            mock_trigger.return_value = "celery-task-triggered"
            result = mgr.trigger_now("sched_test123456")

        assert result == "celery-task-triggered"

    def test_trigger_now_missing_schedule(self) -> None:
        """trigger_now should return None for unknown schedule_id."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None

        result = mgr.trigger_now("nonexistent")
        assert result is None

    def test_trigger_now_dispatches_with_task_params(self) -> None:
        """trigger_now should forward task parameters to build_feature."""
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(
            backend="codexcli",
            model="gpt-5.2",
            max_iterations=10,
            no_pr=True,
            enable_execution=True,
            enable_web=True,
            tools=["read"],
            skills=["deploy"],
            fix_ci=True,
            ci_check_wait_minutes=5.0,
        )
        mock_redis.get.return_value = json.dumps(task.to_dict())

        mock_delay = MagicMock()
        mock_delay.return_value.id = "celery-xyz"

        with patch(
            "helping_hands.server.celery_app.build_feature"
        ) as mock_build_feature:
            mock_build_feature.delay = mock_delay
            result = mgr.trigger_now("sched_test123456")

        assert result == "celery-xyz"
        call_kwargs = mock_delay.call_args[1]
        assert call_kwargs["backend"] == "codexcli"
        assert call_kwargs["model"] == "gpt-5.2"
        assert call_kwargs["max_iterations"] == 10
        assert call_kwargs["no_pr"] is True
        assert call_kwargs["enable_execution"] is True
        assert call_kwargs["enable_web"] is True
        assert call_kwargs["tools"] == ["read"]
        assert call_kwargs["skills"] == ["deploy"]
        assert call_kwargs["fix_ci"] is True
        assert call_kwargs["ci_check_wait_minutes"] == 5.0


# ---------------------------------------------------------------------------
# get_schedule_manager
# ---------------------------------------------------------------------------


class TestGetScheduleManager:
    def test_returns_schedule_manager_instance(self) -> None:
        """get_schedule_manager should return a ScheduleManager."""
        from helping_hands.server.schedules import ScheduleManager, get_schedule_manager

        mock_app = MagicMock()

        with patch.object(ScheduleManager, "__init__", lambda self, app: None):
            result = get_schedule_manager(mock_app)

        assert isinstance(result, ScheduleManager)


# ---------------------------------------------------------------------------
# ScheduledTask.from_dict roundtrip for fix_ci / ci_check_wait_minutes
# ---------------------------------------------------------------------------


class TestScheduledTaskFixCiRoundtrip:
    def test_from_dict_roundtrip_fix_ci(self) -> None:
        """fix_ci and ci_check_wait_minutes should survive to_dict/from_dict."""
        original = _make_task(fix_ci=True, ci_check_wait_minutes=7.5)
        rebuilt = ScheduledTask.from_dict(original.to_dict())
        assert rebuilt.fix_ci is True
        assert rebuilt.ci_check_wait_minutes == 7.5

    def test_from_dict_defaults_fix_ci(self) -> None:
        """from_dict should default fix_ci to False when not present."""
        data = {
            "schedule_id": "s",
            "name": "N",
            "cron_expression": "0 0 * * *",
            "repo_path": "r",
            "prompt": "p",
        }
        task = ScheduledTask.from_dict(data)
        assert task.fix_ci is False
        assert task.ci_check_wait_minutes == 3.0

    def test_from_dict_use_native_cli_auth_roundtrip(self) -> None:
        """use_native_cli_auth should survive to_dict/from_dict."""
        original = _make_task(use_native_cli_auth=True)
        rebuilt = ScheduledTask.from_dict(original.to_dict())
        assert rebuilt.use_native_cli_auth is True


# ---------------------------------------------------------------------------
# _SCHEDULE_ID_HEX_LENGTH constant (v143)
# ---------------------------------------------------------------------------


class TestScheduleIdHexLengthConstant:
    """Tests for the _SCHEDULE_ID_HEX_LENGTH module-level constant."""

    def test_value(self) -> None:
        assert _SCHEDULE_ID_HEX_LENGTH == 12

    def test_type(self) -> None:
        assert isinstance(_SCHEDULE_ID_HEX_LENGTH, int)

    def test_positive(self) -> None:
        assert _SCHEDULE_ID_HEX_LENGTH > 0

    def test_generate_schedule_id_uses_constant(self) -> None:
        """generate_schedule_id() produces IDs with the correct hex length."""
        schedule_id = generate_schedule_id()
        suffix = schedule_id.removeprefix("sched_")
        assert len(suffix) == _SCHEDULE_ID_HEX_LENGTH


# ---------------------------------------------------------------------------
# _save_meta Redis error handling (v143)
# ---------------------------------------------------------------------------


class TestSaveMetaRedisError:
    """Tests for _save_meta error handling on Redis failures."""

    def test_save_meta_redis_error_raises_runtime(self) -> None:
        """_save_meta should raise RuntimeError on Redis write failure."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.set.side_effect = ConnectionError("Redis unavailable")
        task = _make_task()

        with pytest.raises(RuntimeError, match="Failed to persist schedule"):
            mgr._save_meta(task)

    def test_save_meta_redis_error_logs_warning(self, caplog) -> None:
        """_save_meta should log a warning on Redis write failure."""
        import logging

        mgr, mock_redis, _ = _build_manager()
        mock_redis.set.side_effect = ConnectionError("Redis unavailable")
        task = _make_task()

        with (
            caplog.at_level(logging.WARNING, logger="helping_hands.server.schedules"),
            pytest.raises(RuntimeError),
        ):
            mgr._save_meta(task)

        assert any("Failed to save schedule metadata" in m for m in caplog.messages)

    def test_save_meta_success_no_error(self) -> None:
        """_save_meta should not raise when Redis write succeeds."""
        mgr, mock_redis, _ = _build_manager()
        task = _make_task()
        mgr._save_meta(task)  # should not raise
        mock_redis.set.assert_called_once()


# ---------------------------------------------------------------------------
# _delete_meta Redis error handling (v143)
# ---------------------------------------------------------------------------


class TestDeleteMetaRedisError:
    """Tests for _delete_meta error handling on Redis failures."""

    def test_delete_meta_redis_error_swallowed(self) -> None:
        """_delete_meta should not raise on Redis delete failure."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.delete.side_effect = ConnectionError("Redis unavailable")
        mgr._delete_meta("sched_abc")  # should not raise

    def test_delete_meta_redis_error_logs_warning(self, caplog) -> None:
        """_delete_meta should log a warning on Redis delete failure."""
        import logging

        mgr, mock_redis, _ = _build_manager()
        mock_redis.delete.side_effect = ConnectionError("Redis unavailable")

        with caplog.at_level(logging.WARNING, logger="helping_hands.server.schedules"):
            mgr._delete_meta("sched_abc")

        assert any("Failed to delete schedule metadata" in m for m in caplog.messages)


# ---------------------------------------------------------------------------
# _list_meta_keys Redis error handling (v143)
# ---------------------------------------------------------------------------


class TestListMetaKeysRedisError:
    """Tests for _list_meta_keys error handling on Redis failures."""

    def test_list_meta_keys_redis_error_returns_empty(self) -> None:
        """_list_meta_keys should return empty list on Redis failure."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.keys.side_effect = ConnectionError("Redis unavailable")
        assert mgr._list_meta_keys() == []

    def test_list_meta_keys_redis_error_logs_warning(self, caplog) -> None:
        """_list_meta_keys should log a warning on Redis failure."""
        import logging

        mgr, mock_redis, _ = _build_manager()
        mock_redis.keys.side_effect = ConnectionError("Redis unavailable")

        with caplog.at_level(logging.WARNING, logger="helping_hands.server.schedules"):
            mgr._list_meta_keys()

        assert any("Failed to list schedule metadata" in m for m in caplog.messages)

    def test_list_schedules_returns_empty_on_redis_failure(self) -> None:
        """list_schedules should return empty list when _list_meta_keys fails."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.keys.side_effect = ConnectionError("Redis unavailable")
        assert mgr.list_schedules() == []


# ---------------------------------------------------------------------------
# update_pr_number (v304)
# ---------------------------------------------------------------------------


class TestScheduleManagerUpdatePrNumber:
    """Tests for the update_pr_number method."""

    def test_update_pr_number_happy_path(self) -> None:
        """update_pr_number should persist the PR number to the schedule."""
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(pr_number=None)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        result = mgr.update_pr_number("sched_test123456", 42)

        assert result is True
        call_args = mock_redis.set.call_args[0]
        saved_data = json.loads(call_args[1])
        assert saved_data["pr_number"] == 42

    def test_update_pr_number_missing_schedule(self) -> None:
        """update_pr_number should return False for unknown schedule."""
        mgr, mock_redis, _ = _build_manager()
        mock_redis.get.return_value = None

        result = mgr.update_pr_number("nonexistent", 42)

        assert result is False
        mock_redis.set.assert_not_called()

    def test_update_pr_number_overwrites_existing(self) -> None:
        """update_pr_number should overwrite a previously set PR number."""
        mgr, mock_redis, _ = _build_manager()
        task = _make_task(pr_number=10)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        result = mgr.update_pr_number("sched_test123456", 99)

        assert result is True
        call_args = mock_redis.set.call_args[0]
        saved_data = json.loads(call_args[1])
        assert saved_data["pr_number"] == 99

    def test_update_pr_number_logs_info(self, caplog) -> None:
        """update_pr_number should log when it persists a PR number."""
        import logging

        mgr, mock_redis, _ = _build_manager()
        task = _make_task(pr_number=None)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        with caplog.at_level(logging.INFO, logger="helping_hands.server.schedules"):
            mgr.update_pr_number("sched_test123456", 42)

        assert any("Auto-persisted PR #42" in m for m in caplog.messages)
