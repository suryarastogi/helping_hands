"""Unit tests for pure helper functions in server/app.py.

Covers task-extraction helpers, status normalization, source-tag merging,
Flower env config, kwargs parsing, usage-level extraction, and backend
parsing — all pure functions that need no running server or Celery.

Regressions here would silently corrupt the monitor-page task list (wrong
IDs, lost kwargs, mis-sorted statuses) or leak raw Flower payloads into
the frontend.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _extract_nested_str_field,
    _extract_task_id,
    _extract_task_kwargs,
    _extract_task_name,
    _extract_usage_level,
    _flower_api_base_url,
    _flower_timeout_seconds,
    _is_helping_hands_task,
    _is_recently_terminal,
    _merge_source_tags,
    _normalize_task_status,
    _parse_backend,
    _parse_task_kwargs_str,
    _task_state_priority,
    _upsert_current_task,
)

# ---------------------------------------------------------------------------
# _task_state_priority
# ---------------------------------------------------------------------------


class TestTaskStatePriority:
    def test_started_high_priority(self) -> None:
        assert _task_state_priority("STARTED") == 6

    def test_pending_mid_priority(self) -> None:
        assert _task_state_priority("PENDING") == 3

    def test_unknown_returns_zero(self) -> None:
        assert _task_state_priority("UNKNOWN") == 0

    def test_case_insensitive(self) -> None:
        assert _task_state_priority("started") == 6


# ---------------------------------------------------------------------------
# _normalize_task_status
# ---------------------------------------------------------------------------


class TestNormalizeTaskStatus:
    def test_normal_string(self) -> None:
        assert _normalize_task_status("started", default="PENDING") == "STARTED"

    def test_none_uses_default(self) -> None:
        assert _normalize_task_status(None, default="PENDING") == "PENDING"

    def test_empty_string_uses_default(self) -> None:
        assert _normalize_task_status("", default="UNKNOWN") == "UNKNOWN"

    def test_whitespace_only_uses_default(self) -> None:
        assert _normalize_task_status("  ", default="IDLE") == "IDLE"

    def test_strips_whitespace(self) -> None:
        assert _normalize_task_status("  success  ", default="X") == "SUCCESS"

    def test_non_string_coerced(self) -> None:
        assert _normalize_task_status(42, default="DEF") == "42"


# ---------------------------------------------------------------------------
# _extract_nested_str_field
# ---------------------------------------------------------------------------


class TestExtractNestedStrField:
    def test_direct_key(self) -> None:
        assert _extract_nested_str_field({"task_id": "abc"}, ("task_id",)) == "abc"

    def test_priority_order(self) -> None:
        entry = {"uuid": "first", "id": "second"}
        assert _extract_nested_str_field(entry, ("uuid", "id")) == "first"

    def test_skips_non_string(self) -> None:
        entry: dict[str, Any] = {"task_id": 123, "uuid": "fallback"}
        assert _extract_nested_str_field(entry, ("task_id", "uuid")) == "fallback"

    def test_skips_empty_string(self) -> None:
        entry = {"task_id": "  ", "uuid": "real"}
        assert _extract_nested_str_field(entry, ("task_id", "uuid")) == "real"

    def test_recurses_into_request(self) -> None:
        entry: dict[str, Any] = {"request": {"task_id": "nested"}}
        assert _extract_nested_str_field(entry, ("task_id",)) == "nested"

    def test_returns_none_when_not_found(self) -> None:
        assert _extract_nested_str_field({}, ("task_id",)) is None

    def test_non_dict_request_ignored(self) -> None:
        entry: dict[str, Any] = {"request": "not-a-dict"}
        assert _extract_nested_str_field(entry, ("task_id",)) is None

    def test_strips_result(self) -> None:
        assert _extract_nested_str_field({"id": "  abc  "}, ("id",)) == "abc"


# ---------------------------------------------------------------------------
# _extract_task_id / _extract_task_name
# ---------------------------------------------------------------------------


class TestExtractTaskId:
    def test_from_task_id_key(self) -> None:
        assert _extract_task_id({"task_id": "t1"}) == "t1"

    def test_from_uuid_key(self) -> None:
        assert _extract_task_id({"uuid": "u1"}) == "u1"

    def test_from_id_key(self) -> None:
        assert _extract_task_id({"id": "i1"}) == "i1"

    def test_empty_returns_none(self) -> None:
        assert _extract_task_id({}) is None


class TestExtractTaskName:
    def test_from_name_key(self) -> None:
        assert _extract_task_name({"name": "build"}) == "build"

    def test_from_task_key(self) -> None:
        assert _extract_task_name({"task": "build"}) == "build"


# ---------------------------------------------------------------------------
# _extract_task_kwargs
# ---------------------------------------------------------------------------


class TestExtractTaskKwargs:
    def test_dict_kwargs_direct(self) -> None:
        assert _extract_task_kwargs({"kwargs": {"a": 1}}) == {"a": 1}

    def test_string_kwargs_json(self) -> None:
        assert _extract_task_kwargs({"kwargs": '{"b": 2}'}) == {"b": 2}

    def test_request_nested_dict(self) -> None:
        entry: dict[str, Any] = {"request": {"kwargs": {"c": 3}}}
        assert _extract_task_kwargs(entry) == {"c": 3}

    def test_request_nested_string(self) -> None:
        entry: dict[str, Any] = {"request": {"kwargs": '{"d": 4}'}}
        assert _extract_task_kwargs(entry) == {"d": 4}

    def test_empty_when_no_kwargs(self) -> None:
        assert _extract_task_kwargs({}) == {}

    def test_non_dict_non_str_kwargs(self) -> None:
        assert _extract_task_kwargs({"kwargs": 42}) == {}


# ---------------------------------------------------------------------------
# _parse_task_kwargs_str
# ---------------------------------------------------------------------------


class TestParseTaskKwargsStr:
    def test_empty_string(self) -> None:
        assert _parse_task_kwargs_str("") == {}

    def test_valid_json(self) -> None:
        assert _parse_task_kwargs_str('{"x": 1}') == {"x": 1}

    def test_python_literal(self) -> None:
        assert _parse_task_kwargs_str("{'y': 2}") == {"y": 2}

    def test_non_dict_json_returns_empty(self) -> None:
        assert _parse_task_kwargs_str("[1, 2, 3]") == {}

    def test_unparseable_returns_empty(self) -> None:
        assert _parse_task_kwargs_str("not-valid") == {}

    def test_whitespace_only(self) -> None:
        assert _parse_task_kwargs_str("   ") == {}

    def test_oversized_payload_returns_empty(self) -> None:
        huge = '{"k": "' + "x" * 1_100_000 + '"}'
        assert _parse_task_kwargs_str(huge) == {}


# ---------------------------------------------------------------------------
# _is_helping_hands_task
# ---------------------------------------------------------------------------


class TestIsHelpingHandsTask:
    def test_matching_task(self) -> None:
        assert _is_helping_hands_task({"name": "helping_hands.build_feature"}) is True

    def test_non_matching_task(self) -> None:
        assert _is_helping_hands_task({"name": "other.task"}) is False

    def test_no_name_returns_true(self) -> None:
        # When name is unavailable, assume it could be ours
        assert _is_helping_hands_task({}) is True


# ---------------------------------------------------------------------------
# _merge_source_tags
# ---------------------------------------------------------------------------


class TestMergeSourceTags:
    def test_add_to_empty(self) -> None:
        assert _merge_source_tags("", "flower") == "flower"

    def test_add_new_tag(self) -> None:
        result = _merge_source_tags("flower", "inspect")
        assert result == "flower+inspect"

    def test_duplicate_tag(self) -> None:
        result = _merge_source_tags("flower", "flower")
        assert result == "flower"

    def test_sorted_output(self) -> None:
        result = _merge_source_tags("inspect", "celery")
        assert result == "celery+inspect"

    def test_empty_new_tag(self) -> None:
        assert _merge_source_tags("flower", "") == "flower"


# ---------------------------------------------------------------------------
# _upsert_current_task
# ---------------------------------------------------------------------------


class TestUpsertCurrentTask:
    def test_insert_new_task(self) -> None:
        tasks: dict[str, dict[str, Any]] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="claudecodecli",
            repo_path="/repo",
            worker="w1",
            source="flower",
        )
        assert "t1" in tasks
        assert tasks["t1"]["status"] == "STARTED"

    def test_merge_higher_priority_status(self) -> None:
        tasks: dict[str, dict[str, Any]] = {
            "t1": {
                "task_id": "t1",
                "status": "PENDING",
                "backend": None,
                "repo_path": None,
                "worker": None,
                "source": "flower",
            }
        }
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="claudecodecli",
            repo_path="/repo",
            worker="w1",
            source="inspect",
        )
        assert tasks["t1"]["status"] == "STARTED"
        assert tasks["t1"]["backend"] == "claudecodecli"
        assert "flower" in tasks["t1"]["source"]
        assert "inspect" in tasks["t1"]["source"]

    def test_merge_lower_priority_keeps_status(self) -> None:
        tasks: dict[str, dict[str, Any]] = {
            "t1": {
                "task_id": "t1",
                "status": "STARTED",
                "backend": "x",
                "repo_path": "/r",
                "worker": "w",
                "source": "flower",
            }
        }
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="PENDING",
            backend=None,
            repo_path=None,
            worker=None,
            source="",
        )
        assert tasks["t1"]["status"] == "STARTED"


# ---------------------------------------------------------------------------
# _flower_timeout_seconds / _flower_api_base_url
# ---------------------------------------------------------------------------


class TestFlowerTimeoutSeconds:
    def test_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", raising=False)
        assert _flower_timeout_seconds() == 0.75

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "2.5")
        assert _flower_timeout_seconds() == 2.5

    def test_invalid_value_returns_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "abc")
        assert _flower_timeout_seconds() == 0.75

    def test_clamped_to_min(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "0.01")
        assert _flower_timeout_seconds() == 0.1

    def test_clamped_to_max(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "99")
        assert _flower_timeout_seconds() == 10.0


class TestFlowerApiBaseUrl:
    def test_returns_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_FLOWER_API_URL", raising=False)
        assert _flower_api_base_url() is None

    def test_strips_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555/")
        assert _flower_api_base_url() == "http://flower:5555"

    def test_returns_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")
        assert _flower_api_base_url() == "http://flower:5555"


# ---------------------------------------------------------------------------
# _is_recently_terminal
# ---------------------------------------------------------------------------


class TestIsRecentlyTerminal:
    def test_non_terminal_state(self) -> None:
        assert _is_recently_terminal({"succeeded": time.time()}, "STARTED") is False

    def test_success_within_window(self) -> None:
        assert _is_recently_terminal({"succeeded": time.time()}, "SUCCESS") is True

    def test_failure_within_window(self) -> None:
        assert _is_recently_terminal({"failed": time.time()}, "FAILURE") is True

    def test_success_outside_window(self) -> None:
        old_ts = time.time() - 120
        assert _is_recently_terminal({"succeeded": old_ts}, "SUCCESS") is False

    def test_no_timestamp_returns_false(self) -> None:
        assert _is_recently_terminal({}, "SUCCESS") is False

    def test_timestamp_field_fallback(self) -> None:
        assert _is_recently_terminal({"timestamp": time.time()}, "SUCCESS") is True

    def test_non_numeric_timestamp(self) -> None:
        assert _is_recently_terminal({"succeeded": "not-a-number"}, "SUCCESS") is False


# ---------------------------------------------------------------------------
# _extract_usage_level
# ---------------------------------------------------------------------------


class TestExtractUsageLevel:
    def test_valid_usage_level(self) -> None:
        data = {
            "five_hour": {
                "utilization": 45.678,
                "resets_at": "2026-04-04T12:00:00Z",
            }
        }
        level = _extract_usage_level(data, "five_hour", "Session")
        assert level is not None
        assert level.name == "Session"
        assert level.percent_used == 45.7
        assert "Resets" in level.detail

    def test_int_utilization(self) -> None:
        data = {"daily": {"utilization": 50}}
        level = _extract_usage_level(data, "daily", "Daily")
        assert level is not None
        assert level.percent_used == 50

    def test_missing_key_returns_none(self) -> None:
        assert _extract_usage_level({}, "five_hour", "Session") is None

    def test_non_numeric_utilization_returns_none(self) -> None:
        data = {"five_hour": {"utilization": "high"}}
        assert _extract_usage_level(data, "five_hour", "Session") is None

    def test_missing_resets_at(self) -> None:
        data = {"five_hour": {"utilization": 10.0}}
        level = _extract_usage_level(data, "five_hour", "Session")
        assert level is not None
        assert level.detail == ""


# ---------------------------------------------------------------------------
# _parse_backend
# ---------------------------------------------------------------------------


class TestParseBackend:
    def test_valid_backend(self) -> None:
        result = _parse_backend("claudecodecli")
        assert result == "claudecodecli"

    def test_strips_and_lowercases(self) -> None:
        result = _parse_backend("  ClaudeCodeCli  ")
        assert result == "claudecodecli"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            _parse_backend("nonexistent")
