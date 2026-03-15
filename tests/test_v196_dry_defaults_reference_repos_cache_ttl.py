"""Tests for v196 — DRY shared defaults, reference_repos validation, usage cache TTL.

Validates:
- ``server/constants`` new shared default constants (backend, max_iterations,
  ci_check_wait_minutes, max_reference_repos, usage_cache_ttl_s)
- ``server/app`` BuildRequest/ScheduleRequest/ScheduleResponse use shared constants
- ``server/schedules`` ScheduledTask/from_dict use shared constants
- ``server/app`` BuildRequest/ScheduleRequest reference_repos max_length enforcement
- ``server/app`` usage cache TTL uses shared constant
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# server/constants — new shared defaults
# ---------------------------------------------------------------------------


class TestServerDefaultConstants:
    """Verify new shared default constants in server/constants."""

    def test_default_backend_value(self) -> None:
        from helping_hands.server.constants import DEFAULT_BACKEND

        assert DEFAULT_BACKEND == "claudecodecli"

    def test_default_max_iterations_value(self) -> None:
        from helping_hands.server.constants import DEFAULT_MAX_ITERATIONS

        assert DEFAULT_MAX_ITERATIONS == 6

    def test_default_ci_wait_minutes_value(self) -> None:
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES

        assert DEFAULT_CI_WAIT_MINUTES == 3.0

    def test_default_ci_wait_minutes_is_float(self) -> None:
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES

        assert isinstance(DEFAULT_CI_WAIT_MINUTES, float)

    def test_max_reference_repos_value(self) -> None:
        from helping_hands.server.constants import MAX_REFERENCE_REPOS

        assert MAX_REFERENCE_REPOS == 10

    def test_usage_cache_ttl_s_value(self) -> None:
        from helping_hands.server.constants import USAGE_CACHE_TTL_S

        assert USAGE_CACHE_TTL_S == 300

    def test_all_exports_updated(self) -> None:
        from helping_hands.server import constants

        expected = {
            "ANTHROPIC_BETA_HEADER",
            "ANTHROPIC_USAGE_URL",
            "DEFAULT_BACKEND",
            "DEFAULT_CI_WAIT_MINUTES",
            "DEFAULT_MAX_ITERATIONS",
            "JWT_TOKEN_PREFIX",
            "KEYCHAIN_ACCESS_TOKEN_KEY",
            "KEYCHAIN_OAUTH_KEY",
            "KEYCHAIN_SERVICE_NAME",
            "MAX_REFERENCE_REPOS",
            "USAGE_CACHE_TTL_S",
            "USAGE_USER_AGENT",
        }
        assert set(constants.__all__) == expected


# ---------------------------------------------------------------------------
# Consumer identity — app.py uses shared constants
# ---------------------------------------------------------------------------


class TestAppUsesSharedDefaults:
    """Ensure app.py models reference the shared constants, not local copies."""

    def test_build_request_default_backend(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import DEFAULT_BACKEND

        req = BuildRequest(repo_path="/tmp/r", prompt="test")
        assert req.backend == DEFAULT_BACKEND

    def test_build_request_default_max_iterations(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import DEFAULT_MAX_ITERATIONS

        req = BuildRequest(repo_path="/tmp/r", prompt="test")
        assert req.max_iterations == DEFAULT_MAX_ITERATIONS

    def test_build_request_default_ci_wait_minutes(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES

        req = BuildRequest(repo_path="/tmp/r", prompt="test")
        assert req.ci_check_wait_minutes == DEFAULT_CI_WAIT_MINUTES

    def test_schedule_request_default_backend(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import DEFAULT_BACKEND

        req = ScheduleRequest(
            name="t", cron_expression="0 0 * * *", repo_path="/tmp/r", prompt="test"
        )
        assert req.backend == DEFAULT_BACKEND

    def test_schedule_request_default_max_iterations(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import DEFAULT_MAX_ITERATIONS

        req = ScheduleRequest(
            name="t", cron_expression="0 0 * * *", repo_path="/tmp/r", prompt="test"
        )
        assert req.max_iterations == DEFAULT_MAX_ITERATIONS

    def test_schedule_request_default_ci_wait_minutes(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES

        req = ScheduleRequest(
            name="t", cron_expression="0 0 * * *", repo_path="/tmp/r", prompt="test"
        )
        assert req.ci_check_wait_minutes == DEFAULT_CI_WAIT_MINUTES


# ---------------------------------------------------------------------------
# Consumer identity — schedules.py uses shared constants
# ---------------------------------------------------------------------------


class TestSchedulesUsesSharedDefaults:
    """Ensure ScheduledTask references the shared constants."""

    def test_scheduled_task_default_backend(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.constants import DEFAULT_BACKEND
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="sched_abc",
            name="t",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="test",
        )
        assert task.backend == DEFAULT_BACKEND

    def test_scheduled_task_default_max_iterations(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.constants import DEFAULT_MAX_ITERATIONS
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="sched_abc",
            name="t",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="test",
        )
        assert task.max_iterations == DEFAULT_MAX_ITERATIONS

    def test_scheduled_task_default_ci_wait_minutes(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="sched_abc",
            name="t",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="test",
        )
        assert task.ci_check_wait_minutes == DEFAULT_CI_WAIT_MINUTES

    def test_from_dict_default_backend(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.constants import DEFAULT_BACKEND
        from helping_hands.server.schedules import ScheduledTask

        data = {
            "schedule_id": "sched_abc",
            "name": "t",
            "cron_expression": "0 0 * * *",
            "repo_path": "/tmp/r",
            "prompt": "test",
        }
        task = ScheduledTask.from_dict(data)
        assert task.backend == DEFAULT_BACKEND

    def test_from_dict_default_max_iterations(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.constants import DEFAULT_MAX_ITERATIONS
        from helping_hands.server.schedules import ScheduledTask

        data = {
            "schedule_id": "sched_abc",
            "name": "t",
            "cron_expression": "0 0 * * *",
            "repo_path": "/tmp/r",
            "prompt": "test",
        }
        task = ScheduledTask.from_dict(data)
        assert task.max_iterations == DEFAULT_MAX_ITERATIONS

    def test_from_dict_default_ci_wait_minutes(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES
        from helping_hands.server.schedules import ScheduledTask

        data = {
            "schedule_id": "sched_abc",
            "name": "t",
            "cron_expression": "0 0 * * *",
            "repo_path": "/tmp/r",
            "prompt": "test",
        }
        task = ScheduledTask.from_dict(data)
        assert task.ci_check_wait_minutes == DEFAULT_CI_WAIT_MINUTES


# ---------------------------------------------------------------------------
# reference_repos max_length validation
# ---------------------------------------------------------------------------


class TestReferenceReposMaxLength:
    """Validate that reference_repos enforces max_length."""

    def test_build_request_accepts_valid_list(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(
            repo_path="/tmp/r",
            prompt="test",
            reference_repos=["owner/repo1", "owner/repo2"],
        )
        assert len(req.reference_repos) == 2

    def test_build_request_rejects_too_many_repos(self) -> None:
        pytest.importorskip("fastapi")
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_REFERENCE_REPOS

        repos = [f"owner/repo{i}" for i in range(MAX_REFERENCE_REPOS + 1)]
        with pytest.raises(ValidationError, match="reference_repos"):
            BuildRequest(repo_path="/tmp/r", prompt="test", reference_repos=repos)

    def test_build_request_accepts_exactly_max(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_REFERENCE_REPOS

        repos = [f"owner/repo{i}" for i in range(MAX_REFERENCE_REPOS)]
        req = BuildRequest(repo_path="/tmp/r", prompt="test", reference_repos=repos)
        assert len(req.reference_repos) == MAX_REFERENCE_REPOS

    def test_schedule_request_rejects_too_many_repos(self) -> None:
        pytest.importorskip("fastapi")
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_REFERENCE_REPOS

        repos = [f"owner/repo{i}" for i in range(MAX_REFERENCE_REPOS + 1)]
        with pytest.raises(ValidationError, match="reference_repos"):
            ScheduleRequest(
                name="t",
                cron_expression="0 0 * * *",
                repo_path="/tmp/r",
                prompt="test",
                reference_repos=repos,
            )

    def test_schedule_request_accepts_exactly_max(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_REFERENCE_REPOS

        repos = [f"owner/repo{i}" for i in range(MAX_REFERENCE_REPOS)]
        req = ScheduleRequest(
            name="t",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="test",
            reference_repos=repos,
        )
        assert len(req.reference_repos) == MAX_REFERENCE_REPOS


# ---------------------------------------------------------------------------
# Usage cache TTL uses shared constant
# ---------------------------------------------------------------------------


class TestUsageCacheTTL:
    """Validate that usage cache TTL references the shared constant."""

    def test_app_module_has_no_local_ttl(self) -> None:
        """The old _USAGE_CACHE_TTL local constant should no longer exist."""
        pytest.importorskip("fastapi")
        import helping_hands.server.app as app_mod

        assert not hasattr(app_mod, "_USAGE_CACHE_TTL"), (
            "_USAGE_CACHE_TTL should be removed in favor of _USAGE_CACHE_TTL_S"
        )

    def test_shared_constant_is_positive_int(self) -> None:
        from helping_hands.server.constants import USAGE_CACHE_TTL_S

        assert isinstance(USAGE_CACHE_TTL_S, int)
        assert USAGE_CACHE_TTL_S > 0
