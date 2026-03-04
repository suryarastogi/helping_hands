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


def test_normalize_task_result_base_exception() -> None:
    result = normalize_task_result("FAILURE", KeyboardInterrupt("stopped"))
    assert result == {
        "error": "stopped",
        "error_type": "KeyboardInterrupt",
        "status": "FAILURE",
    }


def test_normalize_task_result_value_error() -> None:
    result = normalize_task_result("FAILURE", ValueError("bad input"))
    assert result == {
        "error": "bad input",
        "error_type": "ValueError",
        "status": "FAILURE",
    }


def test_normalize_task_result_empty_dict() -> None:
    result = normalize_task_result("SUCCESS", {})
    assert result == {}


def test_normalize_task_result_exception_no_message() -> None:
    result = normalize_task_result("FAILURE", RuntimeError())
    assert result == {
        "error": "",
        "error_type": "RuntimeError",
        "status": "FAILURE",
    }


def test_normalize_task_result_bool_value() -> None:
    result = normalize_task_result("SUCCESS", True)
    assert result == {
        "value": "True",
        "value_type": "bool",
        "status": "SUCCESS",
    }
