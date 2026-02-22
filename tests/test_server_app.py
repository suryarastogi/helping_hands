"""Tests for the FastAPI app used by web UI mode."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from helping_hands.server.app import app


def _query_from_location(location: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(location).query)


class TestHomeUI:
    def test_form_posts_to_fallback_endpoint(self) -> None:
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert 'form id="run-form" method="post" action="/build/form"' in response.text

    def test_backend_select_includes_codexcli(self) -> None:
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert '<option value="codexcli">codexcli</option>' in response.text


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
        }

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
