"""Tests for scheduled task management."""

from __future__ import annotations

import pytest

pytest.importorskip("celery")

from helping_hands.server.schedules import (
    CRON_PRESETS,
    ScheduledTask,
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
