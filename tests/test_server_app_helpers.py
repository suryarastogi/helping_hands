"""Tests for pure helper functions in helping_hands.server.app."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _coerce_optional_str,
    _extract_task_id,
    _extract_task_kwargs,
    _extract_task_name,
    _flower_api_base_url,
    _flower_timeout_seconds,
    _is_helping_hands_task,
    _normalize_task_status,
    _parse_backend,
    _parse_task_kwargs_str,
    _task_state_priority,
    _upsert_current_task,
)

# --- _parse_backend ---


class TestParseBackend:
    def test_valid_backend(self) -> None:
        assert _parse_backend("codexcli") == "codexcli"

    def test_valid_backend_whitespace(self) -> None:
        assert _parse_backend("  claudecodecli  ") == "claudecodecli"

    def test_valid_backend_uppercase(self) -> None:
        assert _parse_backend("GOOSE") == "goose"

    def test_all_known_backends(self) -> None:
        for name in (
            "e2e",
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "goose",
            "geminicli",
            "opencodecli",
        ):
            assert _parse_backend(name) == name

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            _parse_backend("nonexistent")


# --- _task_state_priority ---


class TestTaskStatePriority:
    def test_started_has_highest_priority(self) -> None:
        assert _task_state_priority("STARTED") == 6

    def test_pending_priority(self) -> None:
        assert _task_state_priority("PENDING") == 3

    def test_unknown_state_returns_zero(self) -> None:
        assert _task_state_priority("UNKNOWN") == 0

    def test_case_insensitive(self) -> None:
        assert _task_state_priority("started") == 6


# --- _normalize_task_status ---


class TestNormalizeTaskStatus:
    def test_uppercases_value(self) -> None:
        assert _normalize_task_status("pending", default="X") == "PENDING"

    def test_strips_whitespace(self) -> None:
        assert _normalize_task_status("  started  ", default="X") == "STARTED"

    def test_none_uses_default(self) -> None:
        assert _normalize_task_status(None, default="UNKNOWN") == "UNKNOWN"

    def test_empty_string_uses_default(self) -> None:
        assert _normalize_task_status("", default="FALLBACK") == "FALLBACK"

    def test_whitespace_only_uses_default(self) -> None:
        assert _normalize_task_status("   ", default="DEFAULT") == "DEFAULT"


# --- _extract_task_id ---


class TestExtractTaskId:
    def test_from_task_id_key(self) -> None:
        assert _extract_task_id({"task_id": "abc-123"}) == "abc-123"

    def test_from_uuid_key(self) -> None:
        assert _extract_task_id({"uuid": "def-456"}) == "def-456"

    def test_from_id_key(self) -> None:
        assert _extract_task_id({"id": "ghi-789"}) == "ghi-789"

    def test_prefers_task_id_over_uuid(self) -> None:
        assert _extract_task_id({"task_id": "first", "uuid": "second"}) == "first"

    def test_from_nested_request(self) -> None:
        entry = {"request": {"task_id": "nested-id"}}
        assert _extract_task_id(entry) == "nested-id"

    def test_returns_none_when_missing(self) -> None:
        assert _extract_task_id({}) is None

    def test_ignores_empty_string(self) -> None:
        assert _extract_task_id({"task_id": "  "}) is None

    def test_strips_whitespace(self) -> None:
        assert _extract_task_id({"task_id": "  abc  "}) == "abc"


# --- _extract_task_name ---


class TestExtractTaskName:
    def test_from_name_key(self) -> None:
        assert _extract_task_name({"name": "my.task"}) == "my.task"

    def test_from_task_key(self) -> None:
        assert _extract_task_name({"task": "other.task"}) == "other.task"

    def test_prefers_name_over_task(self) -> None:
        assert _extract_task_name({"name": "first", "task": "second"}) == "first"

    def test_from_nested_request(self) -> None:
        entry = {"request": {"name": "nested.task"}}
        assert _extract_task_name(entry) == "nested.task"

    def test_returns_none_when_missing(self) -> None:
        assert _extract_task_name({}) is None

    def test_ignores_empty_string(self) -> None:
        assert _extract_task_name({"name": "  "}) is None


# --- _extract_task_kwargs ---


class TestExtractTaskKwargs:
    def test_dict_passthrough(self) -> None:
        assert _extract_task_kwargs({"kwargs": {"repo": "a/b"}}) == {"repo": "a/b"}

    def test_json_string(self) -> None:
        result = _extract_task_kwargs({"kwargs": '{"repo": "a/b"}'})
        assert result == {"repo": "a/b"}

    def test_python_literal_string(self) -> None:
        result = _extract_task_kwargs({"kwargs": "{'repo': 'a/b'}"})
        assert result == {"repo": "a/b"}

    def test_nested_request_dict(self) -> None:
        entry = {"request": {"kwargs": {"backend": "codexcli"}}}
        assert _extract_task_kwargs(entry) == {"backend": "codexcli"}

    def test_nested_request_string(self) -> None:
        entry = {"request": {"kwargs": '{"backend": "codexcli"}'}}
        assert _extract_task_kwargs(entry) == {"backend": "codexcli"}

    def test_returns_empty_when_missing(self) -> None:
        assert _extract_task_kwargs({}) == {}

    def test_invalid_string_returns_empty(self) -> None:
        assert _extract_task_kwargs({"kwargs": "not-valid"}) == {}


# --- _coerce_optional_str ---


class TestCoerceOptionalStr:
    def test_valid_string(self) -> None:
        assert _coerce_optional_str("hello") == "hello"

    def test_strips_whitespace(self) -> None:
        assert _coerce_optional_str("  hello  ") == "hello"

    def test_empty_string_returns_none(self) -> None:
        assert _coerce_optional_str("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert _coerce_optional_str("   ") is None

    def test_non_string_returns_none(self) -> None:
        assert _coerce_optional_str(123) is None
        assert _coerce_optional_str(None) is None
        assert _coerce_optional_str([]) is None


# --- _parse_task_kwargs_str ---


class TestParseTaskKwargsStr:
    def test_valid_json(self) -> None:
        assert _parse_task_kwargs_str('{"a": 1}') == {"a": 1}

    def test_valid_python_literal(self) -> None:
        assert _parse_task_kwargs_str("{'a': 1}") == {"a": 1}

    def test_empty_string(self) -> None:
        assert _parse_task_kwargs_str("") == {}

    def test_whitespace_only(self) -> None:
        assert _parse_task_kwargs_str("   ") == {}

    def test_invalid_string(self) -> None:
        assert _parse_task_kwargs_str("not-a-dict") == {}

    def test_json_list_ignored(self) -> None:
        assert _parse_task_kwargs_str("[1, 2, 3]") == {}


# --- _is_helping_hands_task ---


class TestIsHelpingHandsTask:
    def test_matching_task_name(self) -> None:
        assert _is_helping_hands_task({"name": "helping_hands.build_feature"}) is True

    def test_non_matching_task_name(self) -> None:
        assert _is_helping_hands_task({"name": "other.task"}) is False

    def test_missing_name_returns_true(self) -> None:
        assert _is_helping_hands_task({}) is True


# --- _upsert_current_task ---


class TestUpsertCurrentTask:
    def test_insert_new_task(self) -> None:
        tasks: dict[str, dict] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="PENDING",
            backend="codexcli",
            repo_path="a/b",
            worker="w1",
            source="celery",
        )
        assert tasks["t1"]["status"] == "PENDING"
        assert tasks["t1"]["backend"] == "codexcli"

    def test_merge_higher_priority_status(self) -> None:
        tasks: dict[str, dict] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="PENDING",
            backend=None,
            repo_path=None,
            worker=None,
            source="flower",
        )
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="codexcli",
            repo_path="a/b",
            worker="w1",
            source="celery",
        )
        assert tasks["t1"]["status"] == "STARTED"
        assert tasks["t1"]["backend"] == "codexcli"
        assert tasks["t1"]["repo_path"] == "a/b"
        assert tasks["t1"]["worker"] == "w1"

    def test_does_not_downgrade_status(self) -> None:
        tasks: dict[str, dict] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="codexcli",
            repo_path="a/b",
            worker="w1",
            source="celery",
        )
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="PENDING",
            backend=None,
            repo_path=None,
            worker=None,
            source="flower",
        )
        assert tasks["t1"]["status"] == "STARTED"

    def test_merges_sources(self) -> None:
        tasks: dict[str, dict] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="PENDING",
            backend=None,
            repo_path=None,
            worker=None,
            source="flower",
        )
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="codexcli",
            repo_path="a/b",
            worker="w1",
            source="celery",
        )
        assert tasks["t1"]["source"] == "celery+flower"


# --- _flower_timeout_seconds ---


class TestFlowerTimeoutSeconds:
    def test_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", raising=False)
        assert _flower_timeout_seconds() == 0.75

    def test_reads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "2.5")
        assert _flower_timeout_seconds() == 2.5

    def test_invalid_env_returns_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "not-a-number")
        assert _flower_timeout_seconds() == 0.75

    def test_clamps_to_max(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "999")
        assert _flower_timeout_seconds() == 10.0

    def test_clamps_to_min(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "0.01")
        assert _flower_timeout_seconds() == 0.1


# --- _flower_api_base_url ---


class TestFlowerApiBaseUrl:
    def test_returns_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_FLOWER_API_URL", raising=False)
        assert _flower_api_base_url() is None

    def test_strips_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555/")
        assert _flower_api_base_url() == "http://flower:5555"

    def test_returns_clean_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")
        assert _flower_api_base_url() == "http://flower:5555"

    def test_empty_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "  ")
        assert _flower_api_base_url() is None
