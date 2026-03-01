"""Tests for scheduled task management."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery")

from helping_hands.server.schedules import (
    _SCHEDULE_META_PREFIX,
    CRON_PRESETS,
    ScheduledTask,
    ScheduleManager,
    generate_schedule_id,
    validate_cron_expression,
)


class TestScheduledTask:
    """Tests for ScheduledTask dataclass."""

    def test_create_with_defaults(self) -> None:
        task = ScheduledTask(
            schedule_id="test_123",
            name="Test Schedule",
            cron_expression="0 0 * * *",
            repo_path="owner/repo",
            prompt="Update docs",
        )
        assert task.schedule_id == "test_123"
        assert task.name == "Test Schedule"
        assert task.cron_expression == "0 0 * * *"
        assert task.repo_path == "owner/repo"
        assert task.prompt == "Update docs"
        assert task.backend == "claudecodecli"
        assert task.model is None
        assert task.max_iterations == 6
        assert task.no_pr is False
        assert task.enabled is True
        assert task.run_count == 0

    def test_to_dict(self) -> None:
        task = ScheduledTask(
            schedule_id="test_123",
            name="Test",
            cron_expression="0 * * * *",
            repo_path="owner/repo",
            prompt="Test prompt",
        )
        data = task.to_dict()
        assert data["schedule_id"] == "test_123"
        assert data["name"] == "Test"
        assert data["cron_expression"] == "0 * * * *"
        assert "created_at" in data

    def test_from_dict(self) -> None:
        data = {
            "schedule_id": "test_456",
            "name": "From Dict",
            "cron_expression": "*/5 * * * *",
            "repo_path": "foo/bar",
            "prompt": "Do something",
            "backend": "codexcli",
            "model": "gpt-5.2",
            "enabled": False,
            "run_count": 10,
        }
        task = ScheduledTask.from_dict(data)
        assert task.schedule_id == "test_456"
        assert task.name == "From Dict"
        assert task.backend == "codexcli"
        assert task.model == "gpt-5.2"
        assert task.enabled is False
        assert task.run_count == 10


class TestCronValidation:
    """Tests for cron expression validation."""

    def test_valid_expression(self) -> None:
        result = validate_cron_expression("0 0 * * *")
        assert result == "0 0 * * *"

    def test_preset_name(self) -> None:
        result = validate_cron_expression("daily")
        assert result == "0 0 * * *"

    def test_invalid_expression_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cron expression"):
            validate_cron_expression("not a cron")

    def test_all_presets_valid(self) -> None:
        for name, expr in CRON_PRESETS.items():
            result = validate_cron_expression(name)
            assert result == expr


class TestGenerateScheduleId:
    """Tests for schedule ID generation."""

    def test_format(self) -> None:
        schedule_id = generate_schedule_id()
        assert schedule_id.startswith("sched_")
        assert len(schedule_id) == 18  # "sched_" + 12 hex chars

    def test_unique(self) -> None:
        ids = [generate_schedule_id() for _ in range(100)]
        assert len(set(ids)) == 100


# ---------------------------------------------------------------------------
# ScheduleManager unit tests (mocked Redis / RedBeat)
# ---------------------------------------------------------------------------


def _make_task(**overrides: object) -> ScheduledTask:
    """Create a ScheduledTask with sensible defaults for testing."""
    defaults = {
        "schedule_id": "sched_test123456",
        "name": "Unit Test Schedule",
        "cron_expression": "0 0 * * *",
        "repo_path": "owner/repo",
        "prompt": "Run tests",
    }
    defaults.update(overrides)
    return ScheduledTask(**defaults)


@pytest.fixture
def mock_redis() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_celery_app(mock_redis: MagicMock) -> MagicMock:
    app = MagicMock()
    app.conf.get.return_value = "redis://localhost:6379/0"
    app.conf.broker_url = "redis://localhost:6379/0"
    return app


@pytest.fixture
def manager(mock_celery_app: MagicMock, mock_redis: MagicMock) -> ScheduleManager:
    """Create a ScheduleManager with mocked Redis and RedBeat."""
    with patch.object(ScheduleManager, "_get_redis_client", return_value=mock_redis):
        mgr = ScheduleManager(mock_celery_app)
    return mgr


class TestScheduleManagerCreate:
    """Tests for ScheduleManager.create_schedule()."""

    def test_create_schedule_happy_path(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None  # no existing schedule
        task = _make_task()
        with patch.object(manager, "_create_redbeat_entry"):
            result = manager.create_schedule(task)

        assert result.schedule_id == "sched_test123456"
        mock_redis.set.assert_called_once()
        key, value = mock_redis.set.call_args.args
        assert key == f"{_SCHEDULE_META_PREFIX}sched_test123456"
        stored = json.loads(value)
        assert stored["name"] == "Unit Test Schedule"

    def test_create_schedule_rejects_duplicate(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        existing = _make_task()
        mock_redis.get.return_value = json.dumps(existing.to_dict())
        with pytest.raises(ValueError, match="already exists"):
            manager.create_schedule(_make_task())

    def test_create_schedule_generates_id_when_empty(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        task = _make_task(schedule_id="")
        with patch.object(manager, "_create_redbeat_entry"):
            result = manager.create_schedule(task)

        assert result.schedule_id.startswith("sched_")
        assert len(result.schedule_id) == 18

    def test_create_disabled_schedule_skips_redbeat(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        task = _make_task(enabled=False)
        with patch.object(manager, "_create_redbeat_entry") as mock_rb:
            manager.create_schedule(task)

        mock_rb.assert_not_called()
        mock_redis.set.assert_called_once()


class TestScheduleManagerGet:
    """Tests for ScheduleManager.get_schedule()."""

    def test_get_existing_schedule(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())

        result = manager.get_schedule("sched_test123456")

        assert result is not None
        assert result.schedule_id == "sched_test123456"
        assert result.name == "Unit Test Schedule"

    def test_get_missing_schedule_returns_none(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.get_schedule("nonexistent") is None


class TestScheduleManagerList:
    """Tests for ScheduleManager.list_schedules()."""

    def test_list_empty(self, manager: ScheduleManager, mock_redis: MagicMock) -> None:
        mock_redis.keys.return_value = []
        assert manager.list_schedules() == []

    def test_list_multiple_sorted_by_created_at(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task1 = _make_task(
            schedule_id="sched_aaa", name="First", created_at="2026-01-01T00:00:00"
        )
        task2 = _make_task(
            schedule_id="sched_bbb", name="Second", created_at="2026-02-01T00:00:00"
        )
        mock_redis.keys.return_value = [
            f"{_SCHEDULE_META_PREFIX}sched_aaa".encode(),
            f"{_SCHEDULE_META_PREFIX}sched_bbb".encode(),
        ]

        def get_side_effect(key: str) -> str | None:
            if "sched_aaa" in key:
                return json.dumps(task1.to_dict())
            if "sched_bbb" in key:
                return json.dumps(task2.to_dict())
            return None

        mock_redis.get.side_effect = get_side_effect

        result = manager.list_schedules()
        assert len(result) == 2
        assert result[0].name == "Second"  # reverse chronological
        assert result[1].name == "First"


class TestScheduleManagerUpdate:
    """Tests for ScheduleManager.update_schedule()."""

    def test_update_happy_path_preserves_metadata(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        existing = _make_task(
            created_at="2026-01-01T00:00:00",
            last_run_at="2026-02-15T12:00:00",
            last_run_task_id="celery-task-42",
            run_count=7,
        )
        mock_redis.get.return_value = json.dumps(existing.to_dict())

        updated = _make_task(name="Updated Name", prompt="New prompt")
        with (
            patch.object(manager, "_delete_redbeat_entry"),
            patch.object(manager, "_create_redbeat_entry"),
        ):
            result = manager.update_schedule(updated)

        assert result.name == "Updated Name"
        assert result.prompt == "New prompt"
        assert result.created_at == "2026-01-01T00:00:00"
        assert result.last_run_at == "2026-02-15T12:00:00"
        assert result.last_run_task_id == "celery-task-42"
        assert result.run_count == 7

    def test_update_missing_schedule_raises(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            manager.update_schedule(_make_task(schedule_id="nonexistent"))


class TestScheduleManagerDelete:
    """Tests for ScheduleManager.delete_schedule()."""

    def test_delete_existing(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_delete_redbeat_entry"):
            assert manager.delete_schedule("sched_test123456") is True
        mock_redis.delete.assert_called_once()

    def test_delete_missing_returns_false(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.delete_schedule("nonexistent") is False


class TestScheduleManagerEnableDisable:
    """Tests for enable_schedule() / disable_schedule()."""

    def test_enable_disabled_schedule(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=False)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_create_redbeat_entry") as mock_rb:
            result = manager.enable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is True
        mock_rb.assert_called_once()
        mock_redis.set.assert_called_once()

    def test_enable_already_enabled_is_noop(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=True)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_create_redbeat_entry") as mock_rb:
            result = manager.enable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is True
        mock_rb.assert_not_called()

    def test_enable_missing_returns_none(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.enable_schedule("nonexistent") is None

    def test_disable_enabled_schedule(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=True)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_delete_redbeat_entry") as mock_rb:
            result = manager.disable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is False
        mock_rb.assert_called_once()
        mock_redis.set.assert_called_once()

    def test_disable_already_disabled_is_noop(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(enabled=False)
        mock_redis.get.return_value = json.dumps(task.to_dict())
        with patch.object(manager, "_delete_redbeat_entry") as mock_rb:
            result = manager.disable_schedule("sched_test123456")

        assert result is not None
        assert result.enabled is False
        mock_rb.assert_not_called()

    def test_disable_missing_returns_none(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.disable_schedule("nonexistent") is None


class TestScheduleManagerRecordRun:
    """Tests for ScheduleManager.record_run()."""

    def test_record_run_updates_metadata(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task(run_count=3)
        mock_redis.get.return_value = json.dumps(task.to_dict())

        manager.record_run("sched_test123456", "celery-task-99")

        mock_redis.set.assert_called_once()
        stored = json.loads(mock_redis.set.call_args.args[1])
        assert stored["run_count"] == 4
        assert stored["last_run_task_id"] == "celery-task-99"
        assert stored["last_run_at"] is not None

    def test_record_run_missing_schedule_is_noop(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        manager.record_run("nonexistent", "task-id")
        mock_redis.set.assert_not_called()


class TestScheduleManagerTriggerNow:
    """Tests for ScheduleManager.trigger_now()."""

    def test_trigger_now_dispatches_and_records(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        task = _make_task()
        mock_redis.get.return_value = json.dumps(task.to_dict())

        mock_result = MagicMock()
        mock_result.id = "triggered-task-id"
        with patch("helping_hands.server.celery_app.build_feature") as mock_bf:
            mock_bf.delay.return_value = mock_result
            result = manager.trigger_now("sched_test123456")

        assert result == "triggered-task-id"
        mock_bf.delay.assert_called_once_with(
            repo_path="owner/repo",
            prompt="Run tests",
            backend="claudecodecli",
            model=None,
            max_iterations=6,
            no_pr=False,
            enable_execution=False,
            enable_web=False,
            use_native_cli_auth=False,
            skills=[],
        )

    def test_trigger_now_missing_returns_none(
        self, manager: ScheduleManager, mock_redis: MagicMock
    ) -> None:
        mock_redis.get.return_value = None
        assert manager.trigger_now("nonexistent") is None
