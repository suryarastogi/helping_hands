"""Tests for scheduled task management."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.server.schedules import (
    CRON_PRESETS,
    ScheduledTask,
    generate_schedule_id,
    next_run_time,
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

    def test_from_dict_minimal_defaults(self) -> None:
        """from_dict with only required keys uses correct defaults."""
        data = {
            "schedule_id": "s1",
            "name": "Min",
            "cron_expression": "0 0 * * *",
            "repo_path": "o/r",
            "prompt": "p",
        }
        task = ScheduledTask.from_dict(data)
        assert task.backend == "claudecodecli"
        assert task.model is None
        assert task.max_iterations == 6
        assert task.tools == []
        assert task.skills == []
        assert task.enabled is True

    def test_roundtrip_to_dict_from_dict(self) -> None:
        """to_dict -> from_dict preserves all fields."""
        task = ScheduledTask(
            schedule_id="rt_1",
            name="Roundtrip",
            cron_expression="0 0 * * *",
            repo_path="o/r",
            prompt="p",
            tools=["execution"],
            skills=["review"],
            no_pr=True,
        )
        restored = ScheduledTask.from_dict(task.to_dict())
        assert restored.to_dict() == task.to_dict()

    def test_created_at_auto_generated(self) -> None:
        """created_at is automatically set when empty."""
        task = ScheduledTask(
            schedule_id="ts",
            name="N",
            cron_expression="0 0 * * *",
            repo_path="o/r",
            prompt="p",
        )
        assert task.created_at != ""
        # Should be parseable as ISO datetime
        datetime.fromisoformat(task.created_at)


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


class TestNextRunTime:
    """Tests for next_run_time utility."""

    def test_next_run_from_base(self) -> None:
        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        nxt = next_run_time("0 * * * *", base_time=base)
        assert nxt > base
        assert nxt.minute == 0
        assert nxt.hour == 1

    def test_next_run_defaults_to_now(self) -> None:
        nxt = next_run_time("0 0 * * *")
        assert nxt > datetime.now(UTC)


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
# ScheduleManager tests with mocked Redis and RedBeat
# ---------------------------------------------------------------------------


def _make_task(**overrides: object) -> ScheduledTask:
    """Helper to create a ScheduledTask with defaults."""
    defaults: dict = {
        "schedule_id": "sched_test1234",
        "name": "Test",
        "cron_expression": "0 0 * * *",
        "repo_path": "owner/repo",
        "prompt": "Do work",
    }
    defaults.update(overrides)
    return ScheduledTask(**defaults)


class TestScheduleManager:
    """Tests for ScheduleManager CRUD with mocked backends."""

    @pytest.fixture()
    def mock_redis(self) -> MagicMock:
        """In-memory dict-backed mock Redis."""
        store: dict[str, bytes] = {}
        r = MagicMock()
        r.get = MagicMock(side_effect=lambda k: store.get(k))
        r.set = MagicMock(side_effect=lambda k, v: store.__setitem__(k, v))
        r.delete = MagicMock(side_effect=lambda k: store.pop(k, None))
        r.keys = MagicMock(
            side_effect=lambda pat: [
                k for k in store if k.startswith(pat.replace("*", ""))
            ]
        )
        r._store = store
        return r

    @pytest.fixture()
    def manager(self, mock_redis: MagicMock) -> object:
        """Build a ScheduleManager with mocked Redis and RedBeat."""
        from helping_hands.server.schedules import ScheduleManager

        mock_app = MagicMock()
        mock_app.conf = MagicMock()
        mock_app.conf.get = MagicMock(return_value="redis://localhost:6379/0")
        mock_app.conf.broker_url = "redis://localhost:6379/0"

        with (
            patch(
                "helping_hands.server.schedules._check_redbeat",
                return_value=None,
            ),
            patch.object(
                ScheduleManager,
                "_get_redis_client",
                return_value=mock_redis,
            ),
            patch(
                "helping_hands.server.schedules.RedBeatSchedulerEntry",
            ) as mock_rbe,
        ):
            mock_rbe_instance = MagicMock()
            mock_rbe.return_value = mock_rbe_instance
            mock_rbe.from_key = MagicMock(return_value=mock_rbe_instance)

            mgr = ScheduleManager(mock_app)
            mgr._redbeat_cls = mock_rbe
            yield mgr

    def test_create_and_get(self, manager: object) -> None:
        task = _make_task()
        created = manager.create_schedule(task)
        assert created.schedule_id == "sched_test1234"

        fetched = manager.get_schedule("sched_test1234")
        assert fetched is not None
        assert fetched.name == "Test"

    def test_create_duplicate_raises(self, manager: object) -> None:
        manager.create_schedule(_make_task())
        with pytest.raises(ValueError, match="already exists"):
            manager.create_schedule(_make_task())

    def test_create_generates_id_when_empty(self, manager: object) -> None:
        task = _make_task(schedule_id="")
        created = manager.create_schedule(task)
        assert created.schedule_id.startswith("sched_")
        assert len(created.schedule_id) == 18

    def test_get_nonexistent_returns_none(self, manager: object) -> None:
        assert manager.get_schedule("does_not_exist") is None

    def test_list_schedules_empty(self, manager: object) -> None:
        assert manager.list_schedules() == []

    def test_list_schedules_returns_created(self, manager: object) -> None:
        manager.create_schedule(_make_task(schedule_id="s1", name="First"))
        manager.create_schedule(_make_task(schedule_id="s2", name="Second"))
        tasks = manager.list_schedules()
        assert len(tasks) == 2
        names = {t.name for t in tasks}
        assert names == {"First", "Second"}

    def test_update_schedule(self, manager: object) -> None:
        manager.create_schedule(_make_task())
        updated_task = _make_task(prompt="New prompt")
        result = manager.update_schedule(updated_task)
        assert result.prompt == "New prompt"

        fetched = manager.get_schedule("sched_test1234")
        assert fetched is not None
        assert fetched.prompt == "New prompt"

    def test_update_nonexistent_raises(self, manager: object) -> None:
        with pytest.raises(ValueError, match="not found"):
            manager.update_schedule(_make_task(schedule_id="nope"))

    def test_update_preserves_metadata(self, manager: object) -> None:
        task = _make_task()
        manager.create_schedule(task)
        manager.record_run("sched_test1234", "celery-id-1")

        updated = _make_task(prompt="Changed")
        result = manager.update_schedule(updated)
        assert result.run_count == 1
        assert result.last_run_task_id == "celery-id-1"

    def test_delete_schedule(self, manager: object) -> None:
        manager.create_schedule(_make_task())
        assert manager.delete_schedule("sched_test1234") is True
        assert manager.get_schedule("sched_test1234") is None

    def test_delete_nonexistent_returns_false(self, manager: object) -> None:
        assert manager.delete_schedule("nope") is False

    def test_enable_schedule(self, manager: object) -> None:
        task = _make_task(enabled=False)
        manager.create_schedule(task)
        result = manager.enable_schedule("sched_test1234")
        assert result is not None
        assert result.enabled is True

    def test_enable_nonexistent_returns_none(self, manager: object) -> None:
        assert manager.enable_schedule("nope") is None

    def test_disable_schedule(self, manager: object) -> None:
        manager.create_schedule(_make_task(enabled=True))
        result = manager.disable_schedule("sched_test1234")
        assert result is not None
        assert result.enabled is False

    def test_disable_nonexistent_returns_none(self, manager: object) -> None:
        assert manager.disable_schedule("nope") is None

    def test_record_run(self, manager: object) -> None:
        manager.create_schedule(_make_task())
        manager.record_run("sched_test1234", "task-abc")
        fetched = manager.get_schedule("sched_test1234")
        assert fetched is not None
        assert fetched.run_count == 1
        assert fetched.last_run_task_id == "task-abc"
        assert fetched.last_run_at is not None

    def test_record_run_increments(self, manager: object) -> None:
        manager.create_schedule(_make_task())
        manager.record_run("sched_test1234", "r1")
        manager.record_run("sched_test1234", "r2")
        fetched = manager.get_schedule("sched_test1234")
        assert fetched is not None
        assert fetched.run_count == 2
        assert fetched.last_run_task_id == "r2"

    def test_record_run_nonexistent_is_noop(self, manager: object) -> None:
        manager.record_run("nope", "task-id")  # Should not raise

    def test_trigger_now(self, manager: object) -> None:
        manager.create_schedule(_make_task())
        mock_result = MagicMock()
        mock_result.id = "celery-trigger-1"
        with patch(
            "helping_hands.server.celery_app.build_feature",
            create=True,
        ) as mock_bf:
            mock_bf.delay.return_value = mock_result
            result_id = manager.trigger_now("sched_test1234")
            assert result_id == "celery-trigger-1"

    def test_trigger_now_nonexistent_returns_none(
        self,
        manager: object,
    ) -> None:
        assert manager.trigger_now("nope") is None
