"""Tests for server.task_result.normalize_task_result."""

from __future__ import annotations

import pytest

from helping_hands.server.task_result import normalize_task_result


class TestNormalizeTaskResult:
    """Unit tests for the normalize_task_result helper."""

    def test_none_result_returns_none(self) -> None:
        assert normalize_task_result("SUCCESS", None) is None

    def test_dict_passthrough(self) -> None:
        payload = {"output": "hello", "files_changed": 3}
        result = normalize_task_result("SUCCESS", payload)
        assert result is payload

    def test_empty_dict_passthrough(self) -> None:
        result = normalize_task_result("SUCCESS", {})
        assert result == {}

    def test_base_exception_normalized(self) -> None:
        exc = RuntimeError("something broke")
        result = normalize_task_result("FAILURE", exc)
        assert result == {
            "error": "something broke",
            "error_type": "RuntimeError",
            "status": "FAILURE",
        }

    def test_value_error_normalized(self) -> None:
        exc = ValueError("bad value")
        result = normalize_task_result("FAILURE", exc)
        assert result["error_type"] == "ValueError"
        assert result["error"] == "bad value"

    def test_keyboard_interrupt_normalized(self) -> None:
        exc = KeyboardInterrupt()
        result = normalize_task_result("REVOKED", exc)
        assert result["error_type"] == "KeyboardInterrupt"

    def test_json_serializable_value_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", 42)
        assert result == {"value": 42, "value_type": "int", "status": "SUCCESS"}

    def test_string_value_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", "done")
        assert result == {"value": "done", "value_type": "str", "status": "SUCCESS"}

    def test_list_value_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", [1, 2, 3])
        assert result == {"value": [1, 2, 3], "value_type": "list", "status": "SUCCESS"}

    def test_bool_value_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", True)
        assert result == {"value": True, "value_type": "bool", "status": "SUCCESS"}

    def test_non_serializable_falls_back_to_str(self) -> None:
        obj = object()
        result = normalize_task_result("SUCCESS", obj)
        assert result["value"] == str(obj)
        assert result["value_type"] == "object"
        assert result["status"] == "SUCCESS"

    def test_set_falls_back_to_str(self) -> None:
        result = normalize_task_result("SUCCESS", {1, 2})
        assert result["value_type"] == "set"
        assert isinstance(result["value"], str)

    def test_status_must_be_non_empty_string(self) -> None:
        with pytest.raises(ValueError, match="status must not be empty"):
            normalize_task_result("", 42)

    def test_status_must_be_string(self) -> None:
        with pytest.raises(TypeError, match="status must be a string"):
            normalize_task_result(123, 42)  # type: ignore[arg-type]

    def test_whitespace_only_status_rejected(self) -> None:
        with pytest.raises(ValueError, match="status must not be empty"):
            normalize_task_result("   ", 42)
