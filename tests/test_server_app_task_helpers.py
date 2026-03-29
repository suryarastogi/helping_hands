"""Tests for app.py task-listing helper functions.

Covers pure helper functions used by the task current/listing endpoints:
``_extract_nested_str_field``, ``_merge_source_tags``, ``_is_recently_terminal``,
``_iter_worker_task_entries``, ``_safe_inspect_call``, ``_first_validation_error_msg``,
and ``_is_running_in_docker``.

These helpers are the backbone of the /tasks/current pipeline. If
``_extract_nested_str_field`` stops recursing into ``request`` payloads,
Celery inspect data silently drops task IDs.  If ``_merge_source_tags``
produces duplicates, the UI displays misleading source labels.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _extract_nested_str_field,
    _first_validation_error_msg,
    _is_recently_terminal,
    _is_running_in_docker,
    _iter_worker_task_entries,
    _merge_source_tags,
    _safe_inspect_call,
)

# ---------------------------------------------------------------------------
# _extract_nested_str_field
# ---------------------------------------------------------------------------


class TestExtractNestedStrField:
    def test_returns_first_matching_key(self) -> None:
        entry = {"task_id": "abc-123", "uuid": "xyz-456"}
        assert _extract_nested_str_field(entry, ("task_id", "uuid")) == "abc-123"

    def test_skips_non_string_values(self) -> None:
        entry = {"task_id": 42, "uuid": "xyz-456"}
        assert _extract_nested_str_field(entry, ("task_id", "uuid")) == "xyz-456"

    def test_skips_empty_string_values(self) -> None:
        entry = {"task_id": "  ", "uuid": "xyz-456"}
        assert _extract_nested_str_field(entry, ("task_id", "uuid")) == "xyz-456"

    def test_recurses_into_request_dict(self) -> None:
        entry = {"request": {"task_id": "nested-id"}}
        assert _extract_nested_str_field(entry, ("task_id",)) == "nested-id"

    def test_returns_none_when_no_match(self) -> None:
        entry = {"other": "value"}
        assert _extract_nested_str_field(entry, ("task_id", "uuid")) is None

    def test_returns_none_when_request_not_dict(self) -> None:
        entry = {"request": "not-a-dict"}
        assert _extract_nested_str_field(entry, ("task_id",)) is None

    def test_strips_whitespace(self) -> None:
        entry = {"name": "  my-task  "}
        assert _extract_nested_str_field(entry, ("name",)) == "my-task"


# ---------------------------------------------------------------------------
# _merge_source_tags
# ---------------------------------------------------------------------------


class TestMergeSourceTags:
    def test_adds_new_tag(self) -> None:
        assert _merge_source_tags("flower", "celery") == "celery+flower"

    def test_deduplicates_existing_tag(self) -> None:
        assert _merge_source_tags("flower", "flower") == "flower"

    def test_empty_existing(self) -> None:
        assert _merge_source_tags("", "celery") == "celery"

    def test_empty_new_tag_returns_existing(self) -> None:
        assert _merge_source_tags("flower", "") == "flower"

    def test_sorts_alphabetically(self) -> None:
        assert _merge_source_tags("celery+flower", "api") == "api+celery+flower"

    def test_both_empty(self) -> None:
        assert _merge_source_tags("", "") == ""


# ---------------------------------------------------------------------------
# _is_recently_terminal
# ---------------------------------------------------------------------------


class TestIsRecentlyTerminal:
    def test_non_terminal_status_returns_false(self) -> None:
        assert _is_recently_terminal({"succeeded": time.time()}, "STARTED") is False

    def test_success_within_window(self) -> None:
        assert _is_recently_terminal({"succeeded": time.time() - 5}, "SUCCESS") is True

    def test_success_outside_window(self) -> None:
        assert (
            _is_recently_terminal({"succeeded": time.time() - 120}, "SUCCESS") is False
        )

    def test_failure_within_window(self) -> None:
        assert _is_recently_terminal({"failed": time.time() - 5}, "FAILURE") is True

    def test_falls_back_to_timestamp(self) -> None:
        assert _is_recently_terminal({"timestamp": time.time() - 5}, "FAILURE") is True

    def test_no_timestamp_returns_false(self) -> None:
        assert _is_recently_terminal({}, "SUCCESS") is False

    def test_non_numeric_ts_returns_false(self) -> None:
        assert _is_recently_terminal({"succeeded": "not-a-number"}, "SUCCESS") is False

    def test_revoked_uses_timestamp_fallback(self) -> None:
        assert _is_recently_terminal({"timestamp": time.time() - 5}, "REVOKED") is True


# ---------------------------------------------------------------------------
# _iter_worker_task_entries
# ---------------------------------------------------------------------------


class TestIterWorkerTaskEntries:
    def test_flattens_worker_tasks(self) -> None:
        payload = {
            "worker1@host": [{"task_id": "a"}, {"task_id": "b"}],
            "worker2@host": [{"task_id": "c"}],
        }
        result = _iter_worker_task_entries(payload)
        assert len(result) == 3
        assert result[0] == ("worker1@host", {"task_id": "a"})

    def test_non_dict_payload_returns_empty(self) -> None:
        assert _iter_worker_task_entries(None) == []
        assert _iter_worker_task_entries("string") == []

    def test_skips_non_list_worker_tasks(self) -> None:
        payload = {"worker1@host": "not-a-list"}
        assert _iter_worker_task_entries(payload) == []

    def test_skips_non_dict_task_entries(self) -> None:
        payload = {"worker1@host": ["not-a-dict", {"task_id": "a"}]}
        result = _iter_worker_task_entries(payload)
        assert len(result) == 1
        assert result[0][1] == {"task_id": "a"}

    def test_skips_non_string_worker_keys(self) -> None:
        payload = {42: [{"task_id": "a"}]}
        assert _iter_worker_task_entries(payload) == []


# ---------------------------------------------------------------------------
# _safe_inspect_call
# ---------------------------------------------------------------------------


class TestSafeInspectCall:
    def test_returns_method_result(self) -> None:
        inspector = SimpleNamespace(active=lambda: ["task-1"])
        assert _safe_inspect_call(inspector, "active") == ["task-1"]

    def test_returns_none_for_missing_method(self) -> None:
        inspector = SimpleNamespace()
        assert _safe_inspect_call(inspector, "active") is None

    def test_returns_none_for_non_callable(self) -> None:
        inspector = SimpleNamespace(active="not-callable")
        assert _safe_inspect_call(inspector, "active") is None


# ---------------------------------------------------------------------------
# _first_validation_error_msg
# ---------------------------------------------------------------------------


class TestFirstValidationErrorMsg:
    def test_extracts_first_error_msg(self) -> None:
        from pydantic import BaseModel, ValidationError

        class M(BaseModel):
            x: int

        try:
            M(x="not-an-int")  # type: ignore[arg-type]
        except ValidationError as exc:
            msg = _first_validation_error_msg(exc)
            assert isinstance(msg, str)
            assert len(msg) > 0

    def test_returns_fallback_when_no_errors(self) -> None:
        from pydantic import ValidationError

        exc = ValidationError.from_exception_data(
            "test", line_errors=[], input_type="python"
        )
        assert _first_validation_error_msg(exc) == "Invalid form submission."

    def test_custom_fallback(self) -> None:
        from pydantic import ValidationError

        exc = ValidationError.from_exception_data(
            "test", line_errors=[], input_type="python"
        )
        assert _first_validation_error_msg(exc, fallback="Custom.") == "Custom."


# ---------------------------------------------------------------------------
# _is_running_in_docker
# ---------------------------------------------------------------------------


class TestIsRunningInDocker:
    def test_true_when_dockerenv_exists(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch("helping_hands.server.app.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            assert _is_running_in_docker() is True

    def test_true_when_env_var_truthy(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "1")
        with patch("helping_hands.server.app.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            assert _is_running_in_docker() is True

    def test_false_when_neither(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch("helping_hands.server.app.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            assert _is_running_in_docker() is False
