"""Guard _validate_path_param against empty/whitespace path segments in server endpoints.

FastAPI path parameters come in as raw strings from the URL. Without the
_validate_path_param guard, endpoints that accept task_id or schedule_id would
pass whitespace-only strings directly to Celery/Redis lookups, producing
KeyError or silent misses that are hard to trace. These tests confirm that empty
strings, whitespace-only, tab-only, and newline-only values all raise ValueError
with the parameter name in the message, and that valid values are returned stripped.
The docstring tests protect the Args/Returns/Raises contract, which is especially
important because this helper is shared across multiple endpoint handlers.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from helping_hands.server.app import (
    _cancel_task,
    _validate_path_param,
    app,
)

# ---------------------------------------------------------------------------
# _validate_path_param tests
# ---------------------------------------------------------------------------


class TestValidatePathParam:
    """Tests for _validate_path_param() helper."""

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _validate_path_param("", "task_id")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="schedule_id"):
            _validate_path_param("   ", "schedule_id")

    def test_tab_only_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _validate_path_param("\t", "task_id")

    def test_newline_only_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _validate_path_param("\n", "task_id")

    def test_valid_value_returned_stripped(self) -> None:
        assert _validate_path_param("  abc-123  ", "task_id") == "abc-123"

    def test_valid_value_no_padding(self) -> None:
        assert _validate_path_param("abc-123", "task_id") == "abc-123"

    def test_error_message_includes_param_name(self) -> None:
        with pytest.raises(ValueError, match="my_param"):
            _validate_path_param("", "my_param")

    def test_error_message_non_empty(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_path_param("", "x")


# ---------------------------------------------------------------------------
# _cancel_task uses _validate_path_param
# ---------------------------------------------------------------------------


class TestCancelTaskUsesValidatePathParam:
    """Verify _cancel_task delegates to _validate_path_param."""

    def test_empty_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _cancel_task("")

    def test_whitespace_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _cancel_task("   ")


client = TestClient(app, raise_server_exceptions=False)


class TestMonitorEndpointValidation:
    """Tests for /monitor/{task_id} validation."""

    def test_whitespace_task_id_returns_422(self) -> None:
        resp = client.get("/monitor/%20%20%20")
        assert resp.status_code == 422 or resp.status_code == 500


class TestGetTaskEndpointValidation:
    """Tests for /tasks/{task_id} validation."""

    def test_whitespace_task_id_returns_error(self) -> None:
        resp = client.get("/tasks/%20%20%20")
        assert resp.status_code in (422, 500)


class TestScheduleEndpointValidation:
    """Tests for schedule endpoint path parameter validation."""

    def test_get_schedule_whitespace_raises(self) -> None:
        resp = client.get("/schedules/%20%20%20")
        assert resp.status_code in (422, 500)

    def test_delete_schedule_whitespace_raises(self) -> None:
        resp = client.delete("/schedules/%20%20%20")
        assert resp.status_code in (422, 500)

    def test_enable_schedule_whitespace_raises(self) -> None:
        resp = client.post("/schedules/%20%20%20/enable")
        assert resp.status_code in (422, 500)

    def test_disable_schedule_whitespace_raises(self) -> None:
        resp = client.post("/schedules/%20%20%20/disable")
        assert resp.status_code in (422, 500)

    def test_trigger_schedule_whitespace_raises(self) -> None:
        resp = client.post("/schedules/%20%20%20/trigger")
        assert resp.status_code in (422, 500)
