"""Tests for the FastAPI app used by web UI mode."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.server.app import app


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
            "tools": [],
            "skills": [],
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
            "tools": [],
            "skills": [],
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
            "tools": [],
            "skills": [],
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
            "tools": [],
            "skills": [],
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
            "tools": [],
            "skills": [],
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
