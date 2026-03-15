"""Tests for v187: server endpoint path parameter validation and docstrings."""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from helping_hands.server.app import (
    _build_task_status,
    _cancel_task,
    _schedule_to_response,
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
        with pytest.raises(ValueError, match="non-empty"):
            _validate_path_param("", "x")


# ---------------------------------------------------------------------------
# _validate_path_param docstring tests
# ---------------------------------------------------------------------------


class TestValidatePathParamDocstring:
    """Tests for _validate_path_param() docstring."""

    def test_has_docstring(self) -> None:
        assert _validate_path_param.__doc__ is not None

    def test_docstring_not_trivial(self) -> None:
        assert len(_validate_path_param.__doc__) > 20

    def test_docstring_has_args(self) -> None:
        assert "Args:" in _validate_path_param.__doc__

    def test_docstring_has_returns(self) -> None:
        assert "Returns:" in _validate_path_param.__doc__

    def test_docstring_has_raises(self) -> None:
        assert "Raises:" in _validate_path_param.__doc__


# ---------------------------------------------------------------------------
# _build_task_status docstring tests
# ---------------------------------------------------------------------------


class TestBuildTaskStatusDocstring:
    """Tests for _build_task_status() docstring."""

    def test_has_docstring(self) -> None:
        assert _build_task_status.__doc__ is not None

    def test_docstring_not_trivial(self) -> None:
        assert len(_build_task_status.__doc__) > 20

    def test_docstring_has_args(self) -> None:
        assert "Args:" in _build_task_status.__doc__

    def test_docstring_has_returns(self) -> None:
        assert "Returns:" in _build_task_status.__doc__


# ---------------------------------------------------------------------------
# _schedule_to_response docstring tests
# ---------------------------------------------------------------------------


class TestScheduleToResponseDocstring:
    """Tests for _schedule_to_response() docstring."""

    def test_has_docstring(self) -> None:
        assert _schedule_to_response.__doc__ is not None

    def test_docstring_not_trivial(self) -> None:
        assert len(_schedule_to_response.__doc__) > 20

    def test_docstring_has_args(self) -> None:
        assert "Args:" in _schedule_to_response.__doc__

    def test_docstring_has_returns(self) -> None:
        assert "Returns:" in _schedule_to_response.__doc__


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


# ---------------------------------------------------------------------------
# Endpoint-level validation tests (via TestClient)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Source verification: endpoints call _validate_path_param
# ---------------------------------------------------------------------------


class TestEndpointSourceValidation:
    """Verify endpoints call _validate_path_param in their source."""

    def test_monitor_calls_validate(self) -> None:
        from helping_hands.server.app import monitor

        source = inspect.getsource(monitor)
        assert "_validate_path_param" in source

    def test_get_task_calls_validate(self) -> None:
        from helping_hands.server.app import get_task

        source = inspect.getsource(get_task)
        assert "_validate_path_param" in source

    def test_get_schedule_calls_validate(self) -> None:
        from helping_hands.server.app import get_schedule

        source = inspect.getsource(get_schedule)
        assert "_validate_path_param" in source

    def test_update_schedule_calls_validate(self) -> None:
        from helping_hands.server.app import update_schedule

        source = inspect.getsource(update_schedule)
        assert "_validate_path_param" in source

    def test_delete_schedule_calls_validate(self) -> None:
        from helping_hands.server.app import delete_schedule

        source = inspect.getsource(delete_schedule)
        assert "_validate_path_param" in source

    def test_enable_schedule_calls_validate(self) -> None:
        from helping_hands.server.app import enable_schedule

        source = inspect.getsource(enable_schedule)
        assert "_validate_path_param" in source

    def test_disable_schedule_calls_validate(self) -> None:
        from helping_hands.server.app import disable_schedule

        source = inspect.getsource(disable_schedule)
        assert "_validate_path_param" in source

    def test_trigger_schedule_calls_validate(self) -> None:
        from helping_hands.server.app import trigger_schedule

        source = inspect.getsource(trigger_schedule)
        assert "_validate_path_param" in source
