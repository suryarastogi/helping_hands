"""Guard FastAPI schedule endpoints and the _get_schedule_manager singleton pattern.

These tests verify the full REST surface for recurring schedules (list, create,
get, update, delete, enable, disable, trigger) using a mocked ScheduleManager so
no live Redis or Celery is needed. Key invariants protected: (1) _get_schedule_manager
returns the cached singleton rather than constructing a new manager on every request,
which would lose in-memory state; (2) the trigger endpoint enqueues a Celery task
rather than running synchronously; (3) the enqueue_build_form ValidationError path
redirects with an error query param rather than returning a 422 JSON response, which
is required for the HTML form workflow. Regressions here would silently break the
schedule UI without any Python-level exception being raised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from starlette.testclient import TestClient

from helping_hands.server.app import (
    _get_schedule_manager,
    _is_running_in_docker,
    app,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _FakeScheduledTask:
    """Stand-in for ScheduledTask returned by ScheduleManager."""

    schedule_id: str = "sched-abc123"
    name: str = "Nightly build"
    schedule_type: str = "cron"
    cron_expression: str = "0 0 * * *"
    interval_seconds: int | None = None
    repo_path: str = "/tmp/repo"
    prompt: str = "fix all bugs"
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
    enabled: bool = True
    created_at: str = "2026-03-15T00:00:00"
    last_run_at: str | None = None
    last_run_task_id: str | None = None
    run_count: int = 0


@pytest.fixture()
def _mock_schedule_manager(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Inject a mock ScheduleManager into the app singleton."""
    manager = MagicMock()
    monkeypatch.setattr("helping_hands.server.app._schedule_manager", manager)
    return manager


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# _get_schedule_manager
# ---------------------------------------------------------------------------


class TestGetScheduleManager:
    def test_returns_cached_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sentinel = MagicMock()
        monkeypatch.setattr("helping_hands.server.app._schedule_manager", sentinel)
        result = _get_schedule_manager()
        assert result is sentinel

    def test_creates_manager_on_first_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("helping_hands.server.app._schedule_manager", None)
        fake_manager = MagicMock()
        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            return_value=fake_manager,
        ):
            result = _get_schedule_manager()
        assert result is fake_manager
        # Reset global to not pollute other tests
        monkeypatch.setattr("helping_hands.server.app._schedule_manager", None)

    def test_import_error_raises_http_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("helping_hands.server.app._schedule_manager", None)
        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            side_effect=ImportError("no redbeat"),
        ):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                _get_schedule_manager()
            assert exc_info.value.status_code == 503
        monkeypatch.setattr("helping_hands.server.app._schedule_manager", None)


# ---------------------------------------------------------------------------
# /schedules/presets
# ---------------------------------------------------------------------------


class TestGetCronPresets:
    def test_returns_presets(self, client: TestClient) -> None:
        resp = client.get("/schedules/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "presets" in data
        assert isinstance(data["presets"], dict)
        assert "hourly" in data["presets"]


# ---------------------------------------------------------------------------
# /schedules (list)
# ---------------------------------------------------------------------------


class TestListSchedules:
    def test_returns_empty_list(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.list_schedules.return_value = []
        resp = client.get("/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert data["schedules"] == []
        assert data["total"] == 0

    def test_returns_populated_list(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        task = _FakeScheduledTask()
        _mock_schedule_manager.list_schedules.return_value = [task]
        with patch(
            "helping_hands.server.schedules.next_run_time",
        ) as mock_next:
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.get("/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["schedules"][0]["schedule_id"] == "sched-abc123"


# ---------------------------------------------------------------------------
# /schedules (create)
# ---------------------------------------------------------------------------


class TestCreateSchedule:
    def test_create_success(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        created_task = _FakeScheduledTask(schedule_id="sched-new")
        _mock_schedule_manager.create_schedule.return_value = created_task
        with (
            patch(
                "helping_hands.server.schedules.generate_schedule_id",
                return_value="sched-new",
            ),
            patch(
                "helping_hands.server.schedules.next_run_time",
            ) as mock_next,
        ):
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.post(
                "/schedules",
                json={
                    "name": "Test",
                    "cron_expression": "0 * * * *",
                    "repo_path": "/tmp/repo",
                    "prompt": "test",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["schedule_id"] == "sched-new"

    def test_create_value_error_returns_400(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.create_schedule.side_effect = ValueError("bad cron")
        with patch(
            "helping_hands.server.schedules.generate_schedule_id",
            return_value="sched-err",
        ):
            resp = client.post(
                "/schedules",
                json={
                    "name": "Test",
                    "cron_expression": "bad",
                    "repo_path": "/tmp/repo",
                    "prompt": "test",
                },
            )
        assert resp.status_code == 400
        assert "bad cron" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /schedules/{schedule_id} (get)
# ---------------------------------------------------------------------------


class TestGetSchedule:
    def test_found(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        task = _FakeScheduledTask()
        _mock_schedule_manager.get_schedule.return_value = task
        with patch("helping_hands.server.schedules.next_run_time") as mock_next:
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.get("/schedules/sched-abc123")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Nightly build"

    def test_not_found(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.get_schedule.return_value = None
        resp = client.get("/schedules/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /schedules/{schedule_id} (update)
# ---------------------------------------------------------------------------


class TestUpdateSchedule:
    def test_update_success(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        updated = _FakeScheduledTask(name="Updated")
        _mock_schedule_manager.update_schedule.return_value = updated
        with patch("helping_hands.server.schedules.next_run_time") as mock_next:
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.put(
                "/schedules/sched-abc123",
                json={
                    "name": "Updated",
                    "cron_expression": "0 * * * *",
                    "repo_path": "/tmp/repo",
                    "prompt": "test",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_not_found(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.update_schedule.side_effect = ValueError("not found")
        resp = client.put(
            "/schedules/sched-missing",
            json={
                "name": "Test",
                "cron_expression": "0 * * * *",
                "repo_path": "/tmp/repo",
                "prompt": "test",
            },
        )
        assert resp.status_code == 404

    def test_update_redacted_token_preserves_existing(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        existing = _FakeScheduledTask(github_token="ghp_real_secret_token_123")
        _mock_schedule_manager.get_schedule.return_value = existing
        updated = _FakeScheduledTask(github_token="ghp_real_secret_token_123")
        _mock_schedule_manager.update_schedule.return_value = updated

        with patch("helping_hands.server.schedules.next_run_time") as mock_next:
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.put(
                "/schedules/sched-abc123",
                json={
                    "name": "Test",
                    "cron_expression": "0 * * * *",
                    "repo_path": "/tmp/repo",
                    "prompt": "test",
                    "github_token": "ghp_***_123",
                },
            )
        assert resp.status_code == 200
        # Verify the manager was called — the redacted token should have been
        # replaced with the existing token
        call_args = _mock_schedule_manager.update_schedule.call_args
        task_arg = call_args[0][0]
        assert task_arg.github_token == "ghp_real_secret_token_123"

    def test_update_redacted_token_no_existing(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.get_schedule.return_value = None
        updated = _FakeScheduledTask(github_token=None)
        _mock_schedule_manager.update_schedule.return_value = updated

        with patch("helping_hands.server.schedules.next_run_time") as mock_next:
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.put(
                "/schedules/sched-abc123",
                json={
                    "name": "Test",
                    "cron_expression": "0 * * * *",
                    "repo_path": "/tmp/repo",
                    "prompt": "test",
                    "github_token": "ghp_***_123",
                },
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /schedules/{schedule_id} (delete)
# ---------------------------------------------------------------------------


class TestDeleteSchedule:
    def test_delete_success(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.delete_schedule.return_value = True
        resp = client.delete("/schedules/sched-abc123")
        assert resp.status_code == 204

    def test_delete_not_found(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.delete_schedule.return_value = False
        resp = client.delete("/schedules/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /schedules/{schedule_id}/enable and /disable
# ---------------------------------------------------------------------------


class TestEnableDisableSchedule:
    def test_enable_success(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        task = _FakeScheduledTask(enabled=True)
        _mock_schedule_manager.enable_schedule.return_value = task
        with patch("helping_hands.server.schedules.next_run_time") as mock_next:
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.post("/schedules/sched-abc123/enable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_enable_not_found(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.enable_schedule.return_value = None
        resp = client.post("/schedules/nonexistent/enable")
        assert resp.status_code == 404

    def test_disable_success(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        task = _FakeScheduledTask(enabled=False)
        _mock_schedule_manager.disable_schedule.return_value = task
        with patch("helping_hands.server.schedules.next_run_time") as mock_next:
            from datetime import datetime

            mock_next.return_value = datetime(2026, 3, 16, 0, 0, 0)
            resp = client.post("/schedules/sched-abc123/disable")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_disable_not_found(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.disable_schedule.return_value = None
        resp = client.post("/schedules/nonexistent/disable")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /schedules/{schedule_id}/trigger
# ---------------------------------------------------------------------------


class TestTriggerSchedule:
    def test_trigger_success(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.trigger_now.return_value = "task-id-123"
        resp = client.post("/schedules/sched-abc123/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-id-123"
        assert data["schedule_id"] == "sched-abc123"

    def test_trigger_not_found(
        self,
        client: TestClient,
        _mock_schedule_manager: MagicMock,
    ) -> None:
        _mock_schedule_manager.trigger_now.return_value = None
        resp = client.post("/schedules/nonexistent/trigger")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /notif-sw.js
# ---------------------------------------------------------------------------


class TestNotifServiceWorker:
    def test_returns_js(self, client: TestClient) -> None:
        resp = client.get("/notif-sw.js")
        assert resp.status_code == 200
        assert "application/javascript" in resp.headers["content-type"]
        assert "self.addEventListener" in resp.text


# ---------------------------------------------------------------------------
# /config
# ---------------------------------------------------------------------------


class TestServerConfig:
    def test_not_in_docker(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._is_running_in_docker", lambda: False
        )
        resp = client.get("/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["in_docker"] is False
        assert data["native_auth_default"] is True

    def test_in_docker(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._is_running_in_docker", lambda: True
        )
        resp = client.get("/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["in_docker"] is True
        assert data["native_auth_default"] is False


# ---------------------------------------------------------------------------
# /build (JSON endpoint)
# ---------------------------------------------------------------------------


class TestEnqueueBuild:
    def test_enqueue_success(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_task = MagicMock()
        mock_task.id = "task-xyz"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature",
            MagicMock(delay=MagicMock(return_value=mock_task)),
        )
        resp = client.post(
            "/build",
            json={
                "repo_path": "/tmp/repo",
                "prompt": "add feature",
                "backend": "claudecodecli",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-xyz"
        assert data["status"] == "queued"


# ---------------------------------------------------------------------------
# /build/form — ValidationError redirect path
# ---------------------------------------------------------------------------


class TestEnqueueBuildFormValidationError:
    def test_validation_error_redirects(self, client: TestClient) -> None:
        # Submit form with max_iterations=0 to trigger Pydantic ValidationError
        resp = client.post(
            "/build/form",
            data={
                "repo_path": "/tmp/repo",
                "prompt": "test",
                "backend": "claudecodecli",
                "max_iterations": "0",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        location = resp.headers["location"]
        assert location.startswith("/?")
        assert "error" in location

    def test_validation_error_preserves_form_fields(self, client: TestClient) -> None:
        resp = client.post(
            "/build/form",
            data={
                "repo_path": "/tmp/repo",
                "prompt": "test prompt",
                "backend": "claudecodecli",
                "max_iterations": "0",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        location = resp.headers["location"]
        assert "repo_path" in location
        assert "prompt" in location

    def test_form_success_redirects_to_monitor(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_task = MagicMock()
        mock_task.id = "task-form-123"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature",
            MagicMock(delay=MagicMock(return_value=mock_task)),
        )
        resp = client.post(
            "/build/form",
            data={
                "repo_path": "/tmp/repo",
                "prompt": "fix bugs",
                "backend": "claudecodecli",
                "max_iterations": "6",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        location = resp.headers["location"]
        assert "/monitor/task-form-123" in location

    def test_form_with_optional_flags(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test form submission with fix_ci, pr_number, valid tools."""
        mock_task = MagicMock()
        mock_task.id = "task-opts"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature",
            MagicMock(delay=MagicMock(return_value=mock_task)),
        )
        resp = client.post(
            "/build/form",
            data={
                "repo_path": "/tmp/repo",
                "prompt": "fix",
                "backend": "claudecodecli",
                "max_iterations": "3",
                "fix_ci": "true",
                "pr_number": "42",
                "tools": "execution,web",
                "enable_execution": "true",
                "enable_web": "true",
                "use_native_cli_auth": "true",
                "no_pr": "true",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        location = resp.headers["location"]
        assert "/monitor/task-opts" in location


# ---------------------------------------------------------------------------
# _is_running_in_docker
# ---------------------------------------------------------------------------


class TestIsRunningInDocker:
    def test_not_in_docker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch("pathlib.Path.exists", return_value=False):
            assert _is_running_in_docker() is False

    def test_dockerenv_file_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch("pathlib.Path.exists", return_value=True):
            assert _is_running_in_docker() is True

    def test_env_var_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "1")
        with patch("pathlib.Path.exists", return_value=False):
            assert _is_running_in_docker() is True

    def test_env_var_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "no")
        with patch("pathlib.Path.exists", return_value=False):
            assert _is_running_in_docker() is False
