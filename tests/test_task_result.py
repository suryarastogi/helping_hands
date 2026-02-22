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
