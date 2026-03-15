"""Tests for _schedule_to_response() server helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import _schedule_to_response


@dataclass
class _FakeScheduledTask:
    """Minimal stand-in for ScheduledTask used in _schedule_to_response."""

    schedule_id: str = "sched-1"
    name: str = "Test Schedule"
    cron_expression: str = "0 * * * *"
    repo_path: str = "/tmp/repo"
    prompt: str = "fix bugs"
    backend: str = "claudecodecli"
    model: str | None = None
    max_iterations: int = 6
    pr_number: int | None = None
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    fix_ci: bool = False
    ci_check_wait_minutes: float = 3.0
    github_token: str | None = None
    reference_repos: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = "2026-03-10T00:00:00"
    last_run_at: str | None = None
    last_run_task_id: str | None = None
    run_count: int = 0


class TestScheduleToResponse:
    """Tests for ScheduledTask -> ScheduleResponse conversion."""

    def test_enabled_task_populates_next_run(self) -> None:
        task = _FakeScheduledTask(enabled=True, cron_expression="0 * * * *")
        fake_next = datetime(2026, 3, 10, 12, 0, 0)

        with patch(
            "helping_hands.server.schedules.next_run_time",
            return_value=fake_next,
        ):
            resp = _schedule_to_response(task)

        assert resp.next_run_at == fake_next.isoformat()
        assert resp.schedule_id == "sched-1"
        assert resp.enabled is True

    def test_disabled_task_has_no_next_run(self) -> None:
        task = _FakeScheduledTask(enabled=False)

        resp = _schedule_to_response(task)

        assert resp.next_run_at is None
        assert resp.enabled is False

    def test_all_fields_forwarded(self) -> None:
        task = _FakeScheduledTask(
            schedule_id="s2",
            name="Full Task",
            cron_expression="*/5 * * * *",
            repo_path="/repo",
            prompt="add feature",
            backend="codexcli",
            model="gpt-5.2",
            max_iterations=10,
            pr_number=42,
            no_pr=True,
            enable_execution=True,
            enable_web=True,
            use_native_cli_auth=True,
            fix_ci=True,
            ci_check_wait_minutes=5.0,
            github_token="ghp_longtoken1234567890abcdef",
            reference_repos=["owner/ref-repo"],
            tools=["bash", "python"],
            skills=["prd"],
            enabled=False,
            created_at="2026-01-01T00:00:00",
            last_run_at="2026-03-09T12:00:00",
            last_run_task_id="task-abc",
            run_count=7,
        )

        resp = _schedule_to_response(task)

        assert resp.schedule_id == "s2"
        assert resp.name == "Full Task"
        assert resp.cron_expression == "*/5 * * * *"
        assert resp.repo_path == "/repo"
        assert resp.prompt == "add feature"
        assert resp.backend == "codexcli"
        assert resp.model == "gpt-5.2"
        assert resp.max_iterations == 10
        assert resp.pr_number == 42
        assert resp.no_pr is True
        assert resp.enable_execution is True
        assert resp.enable_web is True
        assert resp.use_native_cli_auth is True
        assert resp.fix_ci is True
        assert resp.ci_check_wait_minutes == 5.0
        assert resp.github_token is not None
        assert resp.github_token.startswith("ghp_")
        assert resp.github_token.endswith("cdef")
        assert "***" in resp.github_token
        assert resp.reference_repos == ["owner/ref-repo"]
        assert resp.tools == ["bash", "python"]
        assert resp.skills == ["prd"]
        assert resp.enabled is False
        assert resp.created_at == "2026-01-01T00:00:00"
        assert resp.last_run_at == "2026-03-09T12:00:00"
        assert resp.last_run_task_id == "task-abc"
        assert resp.run_count == 7

    def test_next_run_exception_suppressed(self) -> None:
        task = _FakeScheduledTask(enabled=True, cron_expression="bad cron")

        with patch(
            "helping_hands.server.schedules.next_run_time",
            side_effect=ValueError("invalid cron"),
        ):
            resp = _schedule_to_response(task)

        assert resp.next_run_at is None
        assert resp.schedule_id == "sched-1"

    def test_task_missing_optional_attrs_uses_defaults(self) -> None:
        """Tasks without fix_ci/ci_check_wait_minutes/tools/etc use getattr defaults."""
        task = _FakeScheduledTask(enabled=False)
        # Remove optional attrs to simulate older ScheduledTask versions
        delattr(task, "fix_ci")
        delattr(task, "ci_check_wait_minutes")
        delattr(task, "github_token")
        delattr(task, "reference_repos")
        delattr(task, "tools")

        resp = _schedule_to_response(task)

        assert resp.fix_ci is False
        assert resp.ci_check_wait_minutes == 3.0
        assert resp.github_token is None
        assert resp.reference_repos == []
        assert resp.tools == []

    def test_run_count_and_last_run_forwarded(self) -> None:
        task = _FakeScheduledTask(
            run_count=15,
            last_run_at="2026-03-10T08:00:00",
            last_run_task_id="task-xyz",
        )

        with patch(
            "helping_hands.server.schedules.next_run_time",
            return_value=datetime(2026, 3, 10, 9, 0, 0),
        ):
            resp = _schedule_to_response(task)

        assert resp.run_count == 15
        assert resp.last_run_at == "2026-03-10T08:00:00"
        assert resp.last_run_task_id == "task-xyz"
