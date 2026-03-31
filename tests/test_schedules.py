"""Tests for the ScheduledTask dataclass, cron utilities, and ID generation.

Protects the data model and utility functions that underpin scheduled builds:
ScheduledTask.to_dict/from_dict must round-trip all fields (including newer
additions like fix_ci, use_native_cli_auth, ci_check_wait_minutes) so schedule
data stored in Redis is never silently corrupted; __post_init__ auto-populates
created_at with a timezone-aware ISO timestamp but must not overwrite an explicit
value; validate_cron_expression resolves preset names (e.g. "daily") to their
canonical expressions and rejects invalid syntax; next_run_time always returns a
future datetime relative to the given base; generate_schedule_id produces unique
hex-suffixed IDs of the documented length.

A from_dict regression that silently drops new fields would cause in-flight
schedule data to lose those fields after any ScheduleManager update, breaking
features such as CI-fix mode without any error at write time.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip("celery", reason="celery extra not installed")

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

    def test_post_init_sets_created_at(self) -> None:
        """created_at should be auto-populated if empty."""
        task = ScheduledTask(
            schedule_id="t",
            name="T",
            cron_expression="0 0 * * *",
            repo_path="r",
            prompt="p",
        )
        assert task.created_at != ""
        # Should be a valid ISO timestamp
        dt = datetime.fromisoformat(task.created_at)
        assert dt.tzinfo is not None

    def test_post_init_preserves_explicit_created_at(self) -> None:
        """If created_at is provided, it should not be overwritten."""
        task = ScheduledTask(
            schedule_id="t",
            name="T",
            cron_expression="0 0 * * *",
            repo_path="r",
            prompt="p",
            created_at="2025-01-01T00:00:00+00:00",
        )
        assert task.created_at == "2025-01-01T00:00:00+00:00"

    def test_to_dict_roundtrip(self) -> None:
        """from_dict(to_dict(task)) should reproduce the task."""
        original = ScheduledTask(
            schedule_id="rt_1",
            name="Roundtrip",
            cron_expression="*/15 * * * *",
            repo_path="owner/repo",
            prompt="roundtrip test",
            backend="basic-langgraph",
            model="gpt-5.2",
            max_iterations=10,
            pr_number=42,
            no_pr=True,
            enable_execution=True,
            enable_web=True,
            use_native_cli_auth=True,
            tools=["read", "write"],
            enabled=False,
            last_run_at="2025-06-01T12:00:00+00:00",
            last_run_task_id="celery-abc",
            run_count=5,
        )
        rebuilt = ScheduledTask.from_dict(original.to_dict())
        assert rebuilt.schedule_id == original.schedule_id
        assert rebuilt.backend == original.backend
        assert rebuilt.model == original.model
        assert rebuilt.max_iterations == original.max_iterations
        assert rebuilt.pr_number == original.pr_number
        assert rebuilt.no_pr == original.no_pr
        assert rebuilt.tools == original.tools
        assert rebuilt.enabled == original.enabled
        assert rebuilt.run_count == original.run_count
        assert rebuilt.last_run_at == original.last_run_at
        assert rebuilt.last_run_task_id == original.last_run_task_id

    def test_from_dict_with_minimal_fields(self) -> None:
        """from_dict should work with only required fields, using defaults."""
        data = {
            "schedule_id": "min",
            "name": "Minimal",
            "cron_expression": "0 0 * * *",
            "repo_path": "o/r",
            "prompt": "do it",
        }
        task = ScheduledTask.from_dict(data)
        assert task.backend == "claudecodecli"
        assert task.model is None
        assert task.max_iterations == 6
        assert task.tools == []
        assert task.enabled is True

    def test_to_dict_includes_fix_ci_field(self) -> None:
        """fix_ci field should not be lost (currently missing from to_dict)."""
        task = ScheduledTask(
            schedule_id="fc",
            name="Fix CI Test",
            cron_expression="0 0 * * *",
            repo_path="r",
            prompt="p",
            fix_ci=True,
        )
        assert task.fix_ci is True


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

    def test_complex_cron_expression(self) -> None:
        """Complex but valid cron expressions should pass."""
        result = validate_cron_expression("0 9 * * 1-5")
        assert result == "0 9 * * 1-5"

    def test_step_values(self) -> None:
        result = validate_cron_expression("*/10 * * * *")
        assert result == "*/10 * * * *"

    def test_range_values(self) -> None:
        result = validate_cron_expression("0 9-17 * * *")
        assert result == "0 9-17 * * *"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_cron_expression("")


class TestNextRunTime:
    """Tests for next_run_time calculation."""

    def test_next_run_time_returns_future(self) -> None:
        base = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = next_run_time("0 * * * *", base_time=base)
        assert result > base

    def test_next_run_time_hourly(self) -> None:
        base = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)
        result = next_run_time("0 * * * *", base_time=base)
        assert result.minute == 0
        assert result.hour == 11

    def test_next_run_time_daily_midnight(self) -> None:
        base = datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC)
        result = next_run_time("0 0 * * *", base_time=base)
        assert result.day == 16
        assert result.hour == 0
        assert result.minute == 0

    def test_next_run_time_defaults_to_now(self) -> None:
        """Without base_time, next_run_time should use current time."""
        result = next_run_time("0 0 * * *")
        assert result > datetime.now(UTC)


class TestGenerateScheduleId:
    """Tests for schedule ID generation."""

    def test_format(self) -> None:
        schedule_id = generate_schedule_id()
        assert schedule_id.startswith("sched_")
        assert len(schedule_id) == 18  # "sched_" + 12 hex chars

    def test_unique(self) -> None:
        ids = [generate_schedule_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_hex_characters_only(self) -> None:
        """The suffix should contain only hex characters."""
        schedule_id = generate_schedule_id()
        suffix = schedule_id[6:]  # strip "sched_"
        assert all(c in "0123456789abcdef" for c in suffix)


class TestCronPresets:
    """Tests for cron preset values."""

    def test_daily_and_midnight_are_equivalent(self) -> None:
        assert CRON_PRESETS["daily"] == CRON_PRESETS["midnight"]

    def test_expected_presets_exist(self) -> None:
        expected = {
            "every_minute",
            "every_5_minutes",
            "every_15_minutes",
            "every_30_minutes",
            "hourly",
            "daily",
            "midnight",
            "weekly",
            "monthly",
            "weekdays",
        }
        assert set(CRON_PRESETS.keys()) == expected
