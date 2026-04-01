"""Protect the task cancellation contract between the UI and the Celery backend.

When a user clicks "Cancel" in the web UI, the server must distinguish active
tasks (revoke + SIGTERM, return cancelled=True) from terminal tasks (no-op,
return cancelled=False). A regression here causes the UI to show a success
banner for already-finished tasks or silently fail to kill running workers.

Empty/whitespace task IDs must fail fast with ValueError; forwarding a blank
ID to Celery silently "revokes" nothing and returns a misleading 200 OK.
The inline HTML monitor must render the cancel button only while a task is
active -- showing it for terminal tasks invites a confusing double-cancel.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from helping_hands.server.app import (
    _TERMINAL_TASK_STATES,
    TaskCancelResponse,
    _cancel_task,
    app,
)

# --- Response model tests ---


# TODO: CLEANUP CANDIDATE — tests below only assert Pydantic field assignment;
# Pydantic's own validation already guarantees field presence and types.
class TestTaskCancelResponseModel:
    """Tests for TaskCancelResponse Pydantic model."""

    def test_fields_present(self) -> None:
        resp = TaskCancelResponse(
            task_id="abc-123", cancelled=True, detail="Task revoked (was STARTED)"
        )
        assert resp.task_id == "abc-123"
        assert resp.cancelled is True
        assert resp.detail == "Task revoked (was STARTED)"

    def test_not_cancelled_response(self) -> None:
        resp = TaskCancelResponse(
            task_id="abc-123",
            cancelled=False,
            detail="Task already in terminal state: SUCCESS",
        )
        assert resp.cancelled is False


# --- _cancel_task helper tests ---


class TestCancelTaskHelper:
    """Tests for _cancel_task() logic."""

    def test_empty_task_id_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _cancel_task("")

    def test_whitespace_task_id_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _cancel_task("   ")

    @pytest.mark.parametrize("terminal_state", sorted(_TERMINAL_TASK_STATES))
    def test_already_terminal_returns_not_cancelled(
        self, monkeypatch: pytest.MonkeyPatch, terminal_state: str
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = terminal_state
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        resp = _cancel_task("task-xyz")

        assert resp.cancelled is False
        assert terminal_state in resp.detail

    def test_running_task_revoked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "STARTED"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        revoke_calls: list[dict] = []

        def fake_revoke(task_id, terminate=False, signal=None):
            revoke_calls.append(
                {"task_id": task_id, "terminate": terminate, "signal": signal}
            )

        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.revoke", fake_revoke
        )

        resp = _cancel_task("task-abc")

        assert resp.cancelled is True
        assert resp.task_id == "task-abc"
        assert "STARTED" in resp.detail
        assert len(revoke_calls) == 1
        assert revoke_calls[0]["task_id"] == "task-abc"
        assert revoke_calls[0]["terminate"] is True
        assert revoke_calls[0]["signal"] == "SIGTERM"

    def test_pending_task_revoked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "PENDING"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.revoke",
            lambda *_a, **_kw: None,
        )

        resp = _cancel_task("task-pending")

        assert resp.cancelled is True
        assert "PENDING" in resp.detail

    def test_strips_task_id_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "STARTED"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.revoke",
            lambda *_a, **_kw: None,
        )

        resp = _cancel_task("  task-padded  ")

        assert resp.task_id == "task-padded"


# --- HTTP endpoint tests ---


class TestCancelTaskEndpoint:
    """Tests for POST /tasks/{task_id}/cancel endpoint."""

    def test_cancel_running_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "STARTED"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.revoke",
            lambda *_a, **_kw: None,
        )

        client = TestClient(app)
        response = client.post("/tasks/task-123/cancel")

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == "task-123"
        assert payload["cancelled"] is True

    def test_cancel_terminal_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_result = MagicMock()
        fake_result.status = "SUCCESS"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.post("/tasks/task-done/cancel")

        assert response.status_code == 200
        payload = response.json()
        assert payload["cancelled"] is False
        assert "SUCCESS" in payload["detail"]


# --- Inline HTML monitor cancel button tests ---


class TestMonitorCancelButton:
    """Tests for cancel button rendering in inline HTML monitor."""

    def test_cancel_button_shown_for_running_task(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "PROGRESS"
        fake_result.ready.return_value = False
        fake_result.info = {"updates": []}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/monitor/task-running")

        assert response.status_code == 200
        assert "Cancel task" in response.text
        assert "cancelTask" in response.text

    def test_cancel_button_hidden_for_terminal_task(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "SUCCESS"
        fake_result.ready.return_value = True
        fake_result.result = {"updates": ["done"]}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/monitor/task-done")

        assert response.status_code == 200
        assert "Cancel task" not in response.text

    def test_cancel_button_hidden_for_revoked_task(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "REVOKED"
        fake_result.ready.return_value = True
        fake_result.result = None
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/monitor/task-revoked")

        assert response.status_code == 200
        assert "Cancel task" not in response.text
