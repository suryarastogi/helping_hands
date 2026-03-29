"""Tests for the FastAPI app used by web UI mode.

Protects the end-to-end HTTP contract of the server: form submission enqueues a
Celery task and returns a 303 redirect to /monitor/<task_id>; the monitor page
auto-refreshes while a task is running and stops once it reaches a terminal state;
worker capacity falls back gracefully from live Celery stats to env-vars to a
default; task-list endpoints merge Flower and Celery sources by UUID; and the
/health family of endpoints correctly surface Redis, DB, and worker status.

If the form-to-Celery handshake regresses, tasks silently disappear with no user
feedback.  If backend validation stops rejecting unknown names, mis-typed backends
are dispatched to Celery and fail at execution time instead of immediately.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.server.app import (
    ClaudeUsageResponse,
    _check_db_health,
    _check_redis_health,
    _check_workers_health,
    app,
)


def _query_from_location(location: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(location).query)


class TestHomeUI:
    def test_form_posts_to_fallback_endpoint(self) -> None:
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert 'form id="run-form" method="post" action="/build/form"' in response.text
        assert "Advanced settings" in response.text
        assert 'id="task_id"' not in response.text

    def test_backend_select_includes_codexcli(self) -> None:
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert '<option value="codexcli" selected>codexcli</option>' in response.text
        assert '<option value="claudecodecli">claudecodecli</option>' in response.text
        assert '<option value="goose">goose</option>' in response.text
        assert '<option value="geminicli">geminicli</option>' in response.text

    def test_home_ui_uses_smoke_test_default_prompt(self) -> None:
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert DEFAULT_SMOKE_TEST_PROMPT in response.text
        assert 'id="enable_execution"' in response.text
        assert 'id="enable_web"' in response.text
        assert 'id="use_native_cli_auth"' in response.text
        assert 'id="skills"' in response.text


class TestBuildForm:
    def test_enqueues_and_redirects_with_task_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-123")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "update readme",
                "backend": "basic-langgraph",
                "model": "gpt-5.2",
                "max_iterations": "4",
                "pr_number": "12",
                "no_pr": "on",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/monitor/task-123"

        assert captured == {
            "repo_path": "suryarastogi/helping_hands",
            "prompt": "update readme",
            "pr_number": 12,
            "backend": "basic-langgraph",
            "model": "gpt-5.2",
            "max_iterations": 4,
            "no_pr": True,
            "enable_execution": False,
            "enable_web": False,
            "use_native_cli_auth": False,
            "fix_ci": False,
            "ci_check_wait_minutes": 3.0,
            "tools": [],
            "skills": [],
            "github_token": None,
            "reference_repos": [],
        }

    def test_enqueues_codexcli_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-codex")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "small codex task",
                "backend": "codexcli",
                "model": "gpt-5.2",
                "max_iterations": "3",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/monitor/task-codex"
        assert captured == {
            "repo_path": "suryarastogi/helping_hands",
            "prompt": "small codex task",
            "pr_number": None,
            "backend": "codexcli",
            "model": "gpt-5.2",
            "max_iterations": 3,
            "no_pr": False,
            "enable_execution": False,
            "enable_web": False,
            "use_native_cli_auth": False,
            "fix_ci": False,
            "ci_check_wait_minutes": 3.0,
            "tools": [],
            "skills": [],
            "github_token": None,
            "reference_repos": [],
        }

    def test_enqueues_claudecodecli_backend(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-claude")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "small claude task",
                "backend": "claudecodecli",
                "model": "anthropic/claude-sonnet-4-5",
                "max_iterations": "3",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/monitor/task-claude"
        assert captured == {
            "repo_path": "suryarastogi/helping_hands",
            "prompt": "small claude task",
            "pr_number": None,
            "backend": "claudecodecli",
            "model": "anthropic/claude-sonnet-4-5",
            "max_iterations": 3,
            "no_pr": False,
            "enable_execution": False,
            "enable_web": False,
            "use_native_cli_auth": False,
            "fix_ci": False,
            "ci_check_wait_minutes": 3.0,
            "tools": [],
            "skills": [],
            "github_token": None,
            "reference_repos": [],
        }

    def test_enqueues_goose_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-goose")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "small goose task",
                "backend": "goose",
                "max_iterations": "3",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/monitor/task-goose"
        assert captured == {
            "repo_path": "suryarastogi/helping_hands",
            "prompt": "small goose task",
            "pr_number": None,
            "backend": "goose",
            "model": None,
            "max_iterations": 3,
            "no_pr": False,
            "enable_execution": False,
            "enable_web": False,
            "use_native_cli_auth": False,
            "fix_ci": False,
            "ci_check_wait_minutes": 3.0,
            "tools": [],
            "skills": [],
            "github_token": None,
            "reference_repos": [],
        }

    def test_enqueues_geminicli_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-gemini")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "small gemini task",
                "backend": "geminicli",
                "model": "gemini-2.0-flash",
                "max_iterations": "3",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/monitor/task-gemini"
        assert captured == {
            "repo_path": "suryarastogi/helping_hands",
            "prompt": "small gemini task",
            "pr_number": None,
            "backend": "geminicli",
            "model": "gemini-2.0-flash",
            "max_iterations": 3,
            "no_pr": False,
            "enable_execution": False,
            "enable_web": False,
            "use_native_cli_auth": False,
            "fix_ci": False,
            "ci_check_wait_minutes": 3.0,
            "tools": [],
            "skills": [],
            "github_token": None,
            "reference_repos": [],
        }

    def test_enqueues_with_tools_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-tools")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "run tools",
                "backend": "basic-langgraph",
                "enable_execution": "on",
                "enable_web": "on",
                "use_native_cli_auth": "on",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/monitor/task-tools"
        assert captured["enable_execution"] is True
        assert captured["enable_web"] is True
        assert captured["use_native_cli_auth"] is True
        assert captured["skills"] == []

    def test_enqueues_with_dynamic_skills(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-skills")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "run with skills",
                "backend": "basic-langgraph",
                "skills": "execution,web",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/monitor/task-skills"
        assert captured["skills"] == ["execution", "web"]

    def test_redirects_with_error_for_invalid_backend(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called = False

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            nonlocal called
            called = True
            return SimpleNamespace(id="task-123")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build/form",
            data={
                "repo_path": "suryarastogi/helping_hands",
                "prompt": "update readme",
                "backend": "bad-backend",
                "max_iterations": "6",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert called is False

        location = response.headers["location"]
        query = _query_from_location(location)
        assert query["backend"] == ["bad-backend"]
        assert "error" in query


class TestMonitorPage:
    def test_monitor_page_auto_refreshes_non_terminal_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "PROGRESS"
        fake_result.ready.return_value = False
        fake_result.info = {"updates": ["step 1", "step 2"]}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/monitor/task-123")

        assert response.status_code == 200
        assert '<meta http-equiv="refresh" content="2">' in response.text
        assert "step 1" in response.text
        assert "PROGRESS" in response.text

    def test_monitor_page_does_not_refresh_terminal_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "SUCCESS"
        fake_result.ready.return_value = True
        fake_result.result = {"updates": ["done"], "message": "ok"}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/monitor/task-123")

        assert response.status_code == 200
        assert '<meta http-equiv="refresh" content="2">' not in response.text
        assert "done" in response.text
        assert "SUCCESS" in response.text


class TestWorkerCapacityEndpoint:
    def test_returns_celery_stats_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = {
            "worker@a": {"pool": {"max-concurrency": 4}},
            "worker@b": {"pool": {"max-concurrency": 4}},
        }
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )

        client = TestClient(app)
        response = client.get("/workers/capacity")

        assert response.status_code == 200
        payload = response.json()
        assert payload["max_workers"] == 8
        assert payload["source"] == "celery"
        assert payload["workers"] == {"worker@a": 4, "worker@b": 4}

    def test_falls_back_to_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = None
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )
        monkeypatch.setenv("HELPING_HANDS_MAX_WORKERS", "12")

        client = TestClient(app)
        response = client.get("/workers/capacity")

        assert response.status_code == 200
        payload = response.json()
        assert payload["max_workers"] == 12
        assert payload["source"] == "env:HELPING_HANDS_MAX_WORKERS"
        assert payload["workers"] == {}

    def test_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = None
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )
        for var in (
            "HELPING_HANDS_MAX_WORKERS",
            "HELPING_HANDS_WORKER_CONCURRENCY",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ):
            monkeypatch.delenv(var, raising=False)

        client = TestClient(app)
        response = client.get("/workers/capacity")

        assert response.status_code == 200
        payload = response.json()
        assert payload["max_workers"] == 8
        assert payload["source"] == "default"
        assert payload["workers"] == {}

    def test_handles_celery_inspect_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def failing_inspect(timeout: float = 1.0) -> None:
            raise ConnectionError("broker unreachable")

        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            failing_inspect,
        )
        for var in (
            "HELPING_HANDS_MAX_WORKERS",
            "HELPING_HANDS_WORKER_CONCURRENCY",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ):
            monkeypatch.delenv(var, raising=False)

        client = TestClient(app)
        response = client.get("/workers/capacity")

        assert response.status_code == 200
        payload = response.json()
        assert payload["max_workers"] == 8
        assert payload["source"] == "default"


class TestCurrentTasksEndpoint:
    def test_returns_flower_tasks_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._fetch_flower_current_tasks",
            lambda: [
                {
                    "task_id": "uuid-flower-1",
                    "status": "STARTED",
                    "backend": "codexcli",
                    "repo_path": "suryarastogi/helping_hands",
                    "worker": "worker@a",
                    "source": "flower",
                }
            ],
        )
        monkeypatch.setattr(
            "helping_hands.server.app._collect_celery_current_tasks",
            lambda: [],
        )

        client = TestClient(app)
        response = client.get("/tasks/current")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source"] == "flower"
        assert payload["tasks"] == [
            {
                "task_id": "uuid-flower-1",
                "status": "STARTED",
                "backend": "codexcli",
                "repo_path": "suryarastogi/helping_hands",
                "worker": "worker@a",
                "source": "flower",
            }
        ]

    def test_falls_back_to_celery_when_flower_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._fetch_flower_current_tasks",
            lambda: [],
        )
        monkeypatch.setattr(
            "helping_hands.server.app._collect_celery_current_tasks",
            lambda: [
                {
                    "task_id": "uuid-celery-1",
                    "status": "RECEIVED",
                    "backend": "geminicli",
                    "repo_path": "owner/repo",
                    "worker": "worker@b",
                    "source": "celery",
                }
            ],
        )

        client = TestClient(app)
        response = client.get("/tasks/current")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source"] == "celery"
        assert payload["tasks"] == [
            {
                "task_id": "uuid-celery-1",
                "status": "RECEIVED",
                "backend": "geminicli",
                "repo_path": "owner/repo",
                "worker": "worker@b",
                "source": "celery",
            }
        ]

    def test_merges_same_uuid_from_flower_and_celery(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._fetch_flower_current_tasks",
            lambda: [
                {
                    "task_id": "uuid-merged-1",
                    "status": "PENDING",
                    "backend": None,
                    "repo_path": None,
                    "worker": None,
                    "source": "flower",
                }
            ],
        )
        monkeypatch.setattr(
            "helping_hands.server.app._collect_celery_current_tasks",
            lambda: [
                {
                    "task_id": "uuid-merged-1",
                    "status": "STARTED",
                    "backend": "codexcli",
                    "repo_path": "owner/repo",
                    "worker": "worker@c",
                    "source": "celery",
                }
            ],
        )

        client = TestClient(app)
        response = client.get("/tasks/current")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source"] == "celery+flower"
        assert payload["tasks"] == [
            {
                "task_id": "uuid-merged-1",
                "status": "STARTED",
                "backend": "codexcli",
                "repo_path": "owner/repo",
                "worker": "worker@c",
                "source": "celery+flower",
            }
        ]


# --- /health endpoint ---


class TestHealthEndpoint:
    """Tests for the basic /health endpoint."""

    def test_returns_ok(self) -> None:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# --- /health/services endpoint ---


class TestHealthServicesEndpoint:
    """Tests for the /health/services endpoint with mocked service checks."""

    def test_all_healthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._check_redis_health", lambda: "ok"
        )
        monkeypatch.setattr("helping_hands.server.app._check_db_health", lambda: "ok")
        monkeypatch.setattr(
            "helping_hands.server.app._check_workers_health", lambda: "ok"
        )

        client = TestClient(app)
        response = client.get("/health/services")

        assert response.status_code == 200
        payload = response.json()
        assert payload == {"redis": "ok", "db": "ok", "workers": "ok"}

    def test_redis_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._check_redis_health", lambda: "error"
        )
        monkeypatch.setattr("helping_hands.server.app._check_db_health", lambda: "ok")
        monkeypatch.setattr(
            "helping_hands.server.app._check_workers_health", lambda: "ok"
        )

        client = TestClient(app)
        response = client.get("/health/services")

        assert response.status_code == 200
        assert response.json()["redis"] == "error"

    def test_db_not_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._check_redis_health", lambda: "ok"
        )
        monkeypatch.setattr("helping_hands.server.app._check_db_health", lambda: "na")
        monkeypatch.setattr(
            "helping_hands.server.app._check_workers_health", lambda: "ok"
        )

        client = TestClient(app)
        response = client.get("/health/services")

        assert response.status_code == 200
        assert response.json()["db"] == "na"

    def test_workers_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._check_redis_health", lambda: "ok"
        )
        monkeypatch.setattr("helping_hands.server.app._check_db_health", lambda: "ok")
        monkeypatch.setattr(
            "helping_hands.server.app._check_workers_health", lambda: "error"
        )

        client = TestClient(app)
        response = client.get("/health/services")

        assert response.status_code == 200
        assert response.json()["workers"] == "error"

    def test_all_services_degraded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._check_redis_health", lambda: "error"
        )
        monkeypatch.setattr(
            "helping_hands.server.app._check_db_health", lambda: "error"
        )
        monkeypatch.setattr(
            "helping_hands.server.app._check_workers_health", lambda: "error"
        )

        client = TestClient(app)
        response = client.get("/health/services")

        assert response.status_code == 200
        payload = response.json()
        assert payload == {"redis": "error", "db": "error", "workers": "error"}


# --- Health check helper functions ---


class TestCheckRedisHealth:
    """Tests for _check_redis_health helper."""

    def test_returns_ok_when_ping_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_redis_cls = MagicMock()
        mock_redis_cls.from_url.return_value.ping.return_value = True
        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis = mock_redis_cls
        monkeypatch.setitem(__import__("sys").modules, "redis", mock_redis_mod)

        assert _check_redis_health() == "ok"

    def test_returns_error_when_ping_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_redis_mod = MagicMock()
        mock_redis_mod.RedisError = type("RedisError", (Exception,), {})
        mock_redis_mod.Redis.from_url.side_effect = mock_redis_mod.RedisError("refused")
        monkeypatch.setitem(__import__("sys").modules, "redis", mock_redis_mod)

        assert _check_redis_health() == "error"

    def test_returns_error_when_import_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        original_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def fail_redis_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "redis":
                raise ImportError("no redis")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fail_redis_import)

        assert _check_redis_health() == "error"


class TestCheckDbHealth:
    """Tests for _check_db_health helper."""

    def test_returns_na_when_no_database_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert _check_db_health() == "na"

    def test_returns_na_when_empty_database_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "  ")
        assert _check_db_health() == "na"

    def test_returns_ok_when_connection_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        mock_psycopg2 = MagicMock()
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        monkeypatch.setitem(__import__("sys").modules, "psycopg2", mock_psycopg2)

        assert _check_db_health() == "ok"
        mock_conn.close.assert_called_once()

    def test_returns_error_when_connection_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        mock_psycopg2 = MagicMock()
        mock_psycopg2.Error = type("Error", (Exception,), {})
        mock_psycopg2.connect.side_effect = mock_psycopg2.Error("connection refused")
        monkeypatch.setitem(__import__("sys").modules, "psycopg2", mock_psycopg2)

        assert _check_db_health() == "error"


class TestCheckWorkersHealth:
    """Tests for _check_workers_health helper."""

    def test_returns_ok_when_workers_respond(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {"worker@1": {"ok": "pong"}}
        mock_control = MagicMock()
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        assert _check_workers_health() == "ok"

    def test_returns_error_when_no_workers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = None
        mock_control = MagicMock()
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        assert _check_workers_health() == "error"

    def test_returns_error_when_empty_ping(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {}
        mock_control = MagicMock()
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        assert _check_workers_health() == "error"

    def test_returns_error_when_inspect_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_control = MagicMock()
        mock_control.inspect.side_effect = ConnectionError("no broker")
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        assert _check_workers_health() == "error"


# --- /health/claude-usage endpoint ---


class TestClaudeUsageEndpoint:
    """Tests for the /health/claude-usage endpoint."""

    def test_returns_error_when_no_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token", lambda: None
        )
        # Reset cache to force fresh fetch
        monkeypatch.setattr("helping_hands.server.app._usage_cache", None)

        client = TestClient(app)
        response = client.get("/health/claude-usage")

        assert response.status_code == 200
        payload = response.json()
        assert payload["error"] is not None
        assert "Keychain" in payload["error"]
        assert payload["fetched_at"] is not None

    def test_returns_cached_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import time

        cached = ClaudeUsageResponse(
            levels=[], error=None, fetched_at="2026-03-10T00:00:00"
        )
        monkeypatch.setattr("helping_hands.server.app._usage_cache", cached)
        monkeypatch.setattr(
            "helping_hands.server.app._usage_cache_ts", time.monotonic()
        )

        client = TestClient(app)
        response = client.get("/health/claude-usage")

        assert response.status_code == 200
        assert response.json()["fetched_at"] == "2026-03-10T00:00:00"

    def test_force_bypasses_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import time

        cached = ClaudeUsageResponse(
            levels=[], error=None, fetched_at="2026-01-01T00:00:00"
        )
        monkeypatch.setattr("helping_hands.server.app._usage_cache", cached)
        monkeypatch.setattr(
            "helping_hands.server.app._usage_cache_ts", time.monotonic()
        )
        # When forced, it re-fetches — mock the token as missing
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token", lambda: None
        )

        client = TestClient(app)
        response = client.get("/health/claude-usage?force=true")

        assert response.status_code == 200
        payload = response.json()
        # Should have re-fetched (error from no credentials, not cached)
        assert payload["error"] is not None
        assert payload["fetched_at"] != "2026-01-01T00:00:00"
