"""Tests for untested FastAPI route handlers in helping_hands.server.app.

Covers the JSON ``POST /build`` API endpoint (the primary programmatic interface),
``GET /tasks/{task_id}`` status lookup, ``GET /config`` runtime configuration,
``GET /notif-sw.js`` service worker delivery, ``POST /tasks/{task_id}/cancel``
task cancellation, and the ``GET /health/multiplayer`` endpoint family.

These routes are exercised via ``fastapi.testclient.TestClient`` with mocked
Celery and multiplayer backends.  A regression in the JSON build endpoint would
silently break the React frontend and all API integrations; a regression in
``/config`` would cause the frontend to use wrong defaults.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from helping_hands.server.app import app

# ---------------------------------------------------------------------------
# POST /build  (JSON API)
# ---------------------------------------------------------------------------


class TestBuildJsonEndpoint:
    """Test the JSON POST /build endpoint used by the React frontend."""

    def test_enqueues_and_returns_task_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-json-1")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build",
            json={
                "repo_path": "owner/repo",
                "prompt": "add tests",
                "backend": "basic-langgraph",
                "model": "gpt-5.2",
                "max_iterations": 4,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == "task-json-1"
        assert payload["status"] == "queued"
        assert payload["backend"] == "basic-langgraph"
        assert captured["repo_path"] == "owner/repo"
        assert captured["prompt"] == "add tests"
        assert captured["model"] == "gpt-5.2"
        assert captured["max_iterations"] == 4

    def test_uses_default_backend_when_omitted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_delay(**kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(id="task-default")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build",
            json={"repo_path": "owner/repo", "prompt": "hello"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == "task-default"
        # backend should be the configured default
        assert payload["backend"] is not None

    def test_rejects_empty_repo_path(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/build",
            json={"repo_path": "", "prompt": "fix bug"},
        )

        assert response.status_code == 422

    def test_rejects_empty_prompt(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/build",
            json={"repo_path": "owner/repo", "prompt": ""},
        )

        assert response.status_code == 422

    def test_rejects_invalid_backend(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/build",
            json={
                "repo_path": "owner/repo",
                "prompt": "fix",
                "backend": "nonexistent-backend",
            },
        )

        assert response.status_code == 422

    def test_passes_optional_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-opts")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build",
            json={
                "repo_path": "owner/repo",
                "prompt": "do stuff",
                "backend": "codexcli",
                "no_pr": True,
                "enable_execution": True,
                "enable_web": True,
                "fix_ci": True,
                "pr_number": 42,
                "issue_number": 99,
                "create_issue": True,
                "project_url": "https://github.com/orgs/x/projects/1",
                "ci_check_wait_minutes": 5.0,
            },
        )

        assert response.status_code == 200
        assert captured["no_pr"] is True
        assert captured["enable_execution"] is True
        assert captured["enable_web"] is True
        assert captured["fix_ci"] is True
        assert captured["pr_number"] == 42
        assert captured["issue_number"] == 99
        assert captured["create_issue"] is True
        assert captured["project_url"] == "https://github.com/orgs/x/projects/1"
        assert captured["ci_check_wait_minutes"] == 5.0

    def test_rejects_max_iterations_too_high(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/build",
            json={
                "repo_path": "owner/repo",
                "prompt": "fix",
                "max_iterations": 999999,
            },
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}
# ---------------------------------------------------------------------------


class TestGetTaskEndpoint:
    """Test the GET /tasks/{task_id} task status endpoint."""

    def test_returns_pending_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "PENDING"
        fake_result.ready.return_value = False
        fake_result.info = None
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/tasks/task-pending-1")

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == "task-pending-1"
        assert payload["status"] == "PENDING"

    def test_returns_completed_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "SUCCESS"
        fake_result.ready.return_value = True
        fake_result.result = {"message": "done", "updates": ["finished"]}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/tasks/task-done-1")

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == "task-done-1"
        assert payload["status"] == "SUCCESS"
        assert payload["result"] is not None

    def test_returns_failed_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "FAILURE"
        fake_result.ready.return_value = True
        fake_result.result = RuntimeError("oops")
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/tasks/task-fail-1")

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == "task-fail-1"
        assert payload["status"] == "FAILURE"


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/cancel
# ---------------------------------------------------------------------------


class TestCancelTaskEndpoint:
    """Test the POST /tasks/{task_id}/cancel endpoint."""

    def test_cancels_running_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "STARTED"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )
        revoked: list[str] = []
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.revoke",
            lambda tid, **kw: revoked.append(tid),
        )

        client = TestClient(app)
        response = client.post("/tasks/cancel-me/cancel")

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == "cancel-me"
        assert payload["cancelled"] is True
        assert "revoked" in payload["detail"].lower()
        assert revoked == ["cancel-me"]

    def test_refuses_to_cancel_terminal_task(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "SUCCESS"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.post("/tasks/done-task/cancel")

        assert response.status_code == 200
        payload = response.json()
        assert payload["cancelled"] is False
        assert "terminal" in payload["detail"].lower()


# ---------------------------------------------------------------------------
# GET /config
# ---------------------------------------------------------------------------


class TestConfigEndpoint:
    """Test the GET /config runtime configuration endpoint."""

    def test_returns_config_not_in_docker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._is_running_in_docker",
            lambda: False,
        )
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.factory.get_enabled_backends",
            lambda: ["codexcli", "basic-langgraph"],
        )

        client = TestClient(app)
        response = client.get("/config")

        assert response.status_code == 200
        payload = response.json()
        assert payload["in_docker"] is False
        assert payload["native_auth_default"] is True  # not in docker → True
        assert payload["has_github_token"] is True
        assert "codexcli" in payload["enabled_backends"]

    def test_returns_config_in_docker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._is_running_in_docker",
            lambda: True,
        )
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.factory.get_enabled_backends",
            lambda: ["codexcli"],
        )

        client = TestClient(app)
        response = client.get("/config")

        assert response.status_code == 200
        payload = response.json()
        assert payload["in_docker"] is True
        assert payload["native_auth_default"] is False  # in docker → False
        assert payload["has_github_token"] is False

    def test_returns_claude_native_auth_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app._is_running_in_docker",
            lambda: False,
        )
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH", "1")
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.factory.get_enabled_backends",
            lambda: [],
        )

        client = TestClient(app)
        response = client.get("/config")

        assert response.status_code == 200
        assert response.json()["claude_native_cli_auth"] is True


# ---------------------------------------------------------------------------
# GET /notif-sw.js
# ---------------------------------------------------------------------------


class TestNotifServiceWorker:
    """Test the GET /notif-sw.js service worker endpoint."""

    def test_returns_javascript(self) -> None:
        client = TestClient(app)
        response = client.get("/notif-sw.js")

        assert response.status_code == 200
        assert "application/javascript" in response.headers["content-type"]
        assert "addEventListener" in response.text


# ---------------------------------------------------------------------------
# GET /health/multiplayer*
# ---------------------------------------------------------------------------


class TestMultiplayerHealthEndpoints:
    """Test the four /health/multiplayer endpoints."""

    def test_multiplayer_stats(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app.get_multiplayer_stats",
            lambda: {"rooms": 0, "connections": 0},
        )

        client = TestClient(app)
        response = client.get("/health/multiplayer")

        assert response.status_code == 200
        payload = response.json()
        assert "rooms" in payload or "connections" in payload

    def test_multiplayer_players(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app.get_connected_players",
            lambda: {"players": []},
        )

        client = TestClient(app)
        response = client.get("/health/multiplayer/players")

        assert response.status_code == 200
        assert "players" in response.json()

    def test_multiplayer_activity(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app.get_player_activity_summary",
            lambda: {"summary": [], "total": 0},
        )

        client = TestClient(app)
        response = client.get("/health/multiplayer/activity")

        assert response.status_code == 200

    def test_multiplayer_decorations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.app.get_decoration_state",
            lambda: {"decorations": {}},
        )

        client = TestClient(app)
        response = client.get("/health/multiplayer/decorations")

        assert response.status_code == 200
