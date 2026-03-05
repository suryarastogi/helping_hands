"""Tests for helping_hands.server.task_result."""

from helping_hands.server.task_result import normalize_task_result


def test_normalize_task_result_none() -> None:
    assert normalize_task_result("PENDING", None) is None


def test_normalize_task_result_dict_passthrough() -> None:
    payload = {"ok": True}
    assert normalize_task_result("SUCCESS", payload) == payload


def test_normalize_task_result_exception() -> None:
    result = normalize_task_result("FAILURE", RuntimeError("boom"))
    assert result == {
        "error": "boom",
        "error_type": "RuntimeError",
        "status": "FAILURE",
    }


def test_normalize_task_result_other_value() -> None:
    result = normalize_task_result("SUCCESS", 123)
    assert result == {
        "value": "123",
        "value_type": "int",
        "status": "SUCCESS",
    }


def test_normalize_task_result_string_value() -> None:
    result = normalize_task_result("SUCCESS", "hello")
    assert result == {
        "value": "hello",
        "value_type": "str",
        "status": "SUCCESS",
    }


def test_normalize_task_result_list_value() -> None:
    result = normalize_task_result("SUCCESS", [1, 2, 3])
    assert result == {
        "value": "[1, 2, 3]",
        "value_type": "list",
        "status": "SUCCESS",
    }


def test_normalize_task_result_empty_dict() -> None:
    """An empty dict should still be passed through."""
    result = normalize_task_result("SUCCESS", {})
    assert result == {}


def test_normalize_task_result_nested_dict() -> None:
    payload = {"data": {"items": [1, 2]}, "meta": {"page": 1}}
    result = normalize_task_result("SUCCESS", payload)
    assert result == payload


def test_normalize_task_result_value_error() -> None:
    result = normalize_task_result("FAILURE", ValueError("bad input"))
    assert result == {
        "error": "bad input",
        "error_type": "ValueError",
        "status": "FAILURE",
    }


def test_normalize_task_result_custom_exception() -> None:
    class MyError(Exception):
        pass

    result = normalize_task_result("FAILURE", MyError("custom"))
    assert result == {
        "error": "custom",
        "error_type": "MyError",
        "status": "FAILURE",
    }


def test_normalize_task_result_bool_value() -> None:
    result = normalize_task_result("SUCCESS", True)
    assert result == {
        "value": "True",
        "value_type": "bool",
        "status": "SUCCESS",
    }


def test_normalize_task_result_preserves_status_string() -> None:
    """The status parameter should be passed through as-is."""
    result = normalize_task_result("CUSTOM_STATUS", 42)
    assert result is not None
    assert result["status"] == "CUSTOM_STATUS"


def test_normalize_task_result_exception_empty_message() -> None:
    result = normalize_task_result("FAILURE", RuntimeError())
    assert result is not None
    assert result["error"] == ""
    assert result["error_type"] == "RuntimeError"
