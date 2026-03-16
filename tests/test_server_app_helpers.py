"""Tests for pure helper functions in helping_hands.server.app."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _MAX_TASK_KWARGS_LEN,
    _coerce_optional_str,
    _collect_celery_current_tasks,
    _extract_task_id,
    _extract_task_kwargs,
    _extract_task_name,
    _first_validation_error_msg,
    _flower_api_base_url,
    _flower_timeout_seconds,
    _is_helping_hands_task,
    _merge_source_tags,
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
            "docker-sandbox-claude",
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

    def test_oversized_payload_returns_empty(self) -> None:
        """Payloads exceeding _MAX_TASK_KWARGS_LEN are rejected."""
        oversized = '{"k": "' + "x" * (_MAX_TASK_KWARGS_LEN + 1) + '"}'
        assert _parse_task_kwargs_str(oversized) == {}

    def test_at_limit_payload_is_parsed(self) -> None:
        """Payloads exactly at the limit are accepted."""
        # Build a valid JSON dict that's at the limit
        padding = "a" * (_MAX_TASK_KWARGS_LEN - 12)  # account for {"k":"..."}
        at_limit = '{"k":"' + padding + '"}'
        assert len(at_limit.strip()) <= _MAX_TASK_KWARGS_LEN
        result = _parse_task_kwargs_str(at_limit)
        assert result == {"k": padding}

    def test_max_task_kwargs_len_constant(self) -> None:
        """The constant is a reasonable positive value."""
        assert _MAX_TASK_KWARGS_LEN > 0
        assert _MAX_TASK_KWARGS_LEN == 1_000_000


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


# --- _check_redis_health ---


class TestCheckRedisHealth:
    def test_ok_when_ping_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import types

        from helping_hands.server.app import _check_redis_health

        mock_redis_cls = MagicMock()
        mock_instance = MagicMock()
        mock_redis_cls.from_url.return_value = mock_instance
        mock_instance.ping.return_value = True

        fake_redis = types.ModuleType("redis")
        fake_redis.Redis = mock_redis_cls  # type: ignore[attr-defined]
        fake_redis.RedisError = type("RedisError", (Exception,), {})  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "redis", fake_redis)

        assert _check_redis_health() == "ok"

    def test_error_when_ping_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import types

        from helping_hands.server.app import _check_redis_health

        mock_redis_cls = MagicMock()
        mock_redis_cls.from_url.side_effect = ConnectionError("refused")

        fake_redis = types.ModuleType("redis")
        fake_redis.Redis = mock_redis_cls  # type: ignore[attr-defined]
        fake_redis.RedisError = type("RedisError", (Exception,), {})  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "redis", fake_redis)

        assert _check_redis_health() == "error"


# --- _check_db_health ---


class TestCheckDbHealth:
    def test_na_when_no_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _check_db_health

        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert _check_db_health() == "na"

    def test_na_when_empty_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _check_db_health

        monkeypatch.setenv("DATABASE_URL", "  ")
        assert _check_db_health() == "na"

    def test_ok_when_connect_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _check_db_health

        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

        mock_conn = MagicMock()
        mock_psycopg2 = MagicMock()
        mock_psycopg2.Error = type("Error", (Exception,), {})
        mock_psycopg2.connect.return_value = mock_conn
        monkeypatch.setitem(sys.modules, "psycopg2", mock_psycopg2)

        assert _check_db_health() == "ok"
        mock_conn.close.assert_called_once()

    def test_error_when_connect_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _check_db_health

        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

        fake_pg_error = type("Error", (Exception,), {})
        mock_psycopg2 = MagicMock()
        mock_psycopg2.Error = fake_pg_error
        mock_psycopg2.connect.side_effect = fake_pg_error("connection refused")
        monkeypatch.setitem(sys.modules, "psycopg2", mock_psycopg2)

        assert _check_db_health() == "error"


# --- _check_workers_health ---


class TestCheckWorkersHealth:
    def test_ok_when_ping_returns_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _check_workers_health, celery_app

        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {"worker1": {"ok": "pong"}}
        monkeypatch.setattr(
            celery_app.control, "inspect", lambda timeout=None: mock_inspector
        )

        assert _check_workers_health() == "ok"

    def test_error_when_ping_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server.app import _check_workers_health, celery_app

        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = None
        monkeypatch.setattr(
            celery_app.control, "inspect", lambda timeout=None: mock_inspector
        )

        assert _check_workers_health() == "error"

    def test_error_when_ping_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server.app import _check_workers_health, celery_app

        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {}
        monkeypatch.setattr(
            celery_app.control, "inspect", lambda timeout=None: mock_inspector
        )

        assert _check_workers_health() == "error"

    def test_error_when_inspect_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _check_workers_health, celery_app

        monkeypatch.setattr(
            celery_app.control,
            "inspect",
            MagicMock(side_effect=ConnectionError("no broker")),
        )

        assert _check_workers_health() == "error"


# --- _is_running_in_docker ---


class TestIsRunningInDocker:
    def test_true_when_dockerenv_exists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from helping_hands.server.app import _is_running_in_docker

        dockerenv = tmp_path / ".dockerenv"
        dockerenv.touch()
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        monkeypatch.setattr(
            "helping_hands.server.app.Path",
            lambda p: dockerenv if p == "/.dockerenv" else Path(p),
        )

        assert _is_running_in_docker() is True

    def test_true_when_env_var_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setattr(
            "helping_hands.server.app.Path",
            lambda p: MagicMock(exists=lambda: False),
        )
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "1")

        assert _is_running_in_docker() is True

    def test_true_when_env_var_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setattr(
            "helping_hands.server.app.Path",
            lambda p: MagicMock(exists=lambda: False),
        )
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "true")

        assert _is_running_in_docker() is True

    def test_false_when_neither(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setattr(
            "helping_hands.server.app.Path",
            lambda p: MagicMock(exists=lambda: False),
        )
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)

        assert _is_running_in_docker() is False

    def test_false_when_env_var_no(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setattr(
            "helping_hands.server.app.Path",
            lambda p: MagicMock(exists=lambda: False),
        )
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "no")

        assert _is_running_in_docker() is False


# --- _iter_worker_task_entries ---


class TestIterWorkerTaskEntries:
    def test_flattens_valid_payload(self) -> None:
        from helping_hands.server.app import _iter_worker_task_entries

        payload = {
            "worker1": [{"id": "t1"}, {"id": "t2"}],
            "worker2": [{"id": "t3"}],
        }
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 3
        workers = [w for w, _ in entries]
        assert "worker1" in workers
        assert "worker2" in workers

    def test_returns_empty_for_non_dict(self) -> None:
        from helping_hands.server.app import _iter_worker_task_entries

        assert _iter_worker_task_entries(None) == []
        assert _iter_worker_task_entries([1, 2]) == []
        assert _iter_worker_task_entries("string") == []

    def test_skips_non_list_worker_tasks(self) -> None:
        from helping_hands.server.app import _iter_worker_task_entries

        payload = {"worker1": "not-a-list", "worker2": [{"id": "t1"}]}
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 1

    def test_skips_non_dict_task_entries(self) -> None:
        from helping_hands.server.app import _iter_worker_task_entries

        payload = {"worker1": [{"id": "t1"}, "not-a-dict", 42]}
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 1


# --- _safe_inspect_call ---


class TestSafeInspectCall:
    def test_returns_method_result(self) -> None:
        from helping_hands.server.app import _safe_inspect_call

        inspector = MagicMock()
        inspector.active.return_value = {"w1": []}
        assert _safe_inspect_call(inspector, "active") == {"w1": []}

    def test_returns_none_for_missing_method(self) -> None:
        from helping_hands.server.app import _safe_inspect_call

        class _Bare:
            pass

        assert _safe_inspect_call(_Bare(), "active") is None

    def test_returns_none_on_exception(self) -> None:
        from helping_hands.server.app import _safe_inspect_call

        inspector = MagicMock()
        inspector.active.side_effect = RuntimeError("timeout")
        assert _safe_inspect_call(inspector, "active") is None


# --- BuildRequest max_iterations validation ---


class TestBuildRequestMaxIterations:
    """Validate max_iterations bounds (ge=1, le=100)."""

    def test_default_is_six(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="test")
        assert req.max_iterations == 6

    def test_accepts_one(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="test", max_iterations=1)
        assert req.max_iterations == 1

    def test_accepts_hundred(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="test", max_iterations=100)
        assert req.max_iterations == 100

    def test_rejects_zero(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="max_iterations"):
            BuildRequest(repo_path="/tmp/repo", prompt="test", max_iterations=0)

    def test_rejects_negative(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="max_iterations"):
            BuildRequest(repo_path="/tmp/repo", prompt="test", max_iterations=-5)

    def test_rejects_over_hundred(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="max_iterations"):
            BuildRequest(repo_path="/tmp/repo", prompt="test", max_iterations=101)


# --- _collect_celery_current_tasks ---


class TestCollectCeleryCurrentTasks:
    """Direct tests for the _collect_celery_current_tasks orchestrator."""

    def _make_task_entry(
        self,
        task_id: str = "abc-123",
        name: str = "helping_hands.build_feature",
        state: str | None = None,
        repo_path: str = "/tmp/repo",
        backend: str = "basic-langgraph",
    ) -> dict:
        entry: dict = {
            "id": task_id,
            "name": name,
            "kwargs": f'{{"repo_path": "{repo_path}", "backend": "{backend}"}}',
        }
        if state:
            entry["state"] = state
        return entry

    def test_returns_empty_when_inspector_is_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When celery_app.control.inspect() returns None, returns []."""
        mock_control = MagicMock()
        mock_control.inspect.return_value = None
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app",
            MagicMock(control=mock_control),
        )
        assert _collect_celery_current_tasks() == []

    def test_collects_active_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Active tasks are collected with STARTED status."""
        entry = self._make_task_entry(task_id="task-1")
        inspector = MagicMock()
        inspector.active.return_value = {"worker1": [entry]}
        inspector.reserved.return_value = {}
        inspector.scheduled.return_value = {}
        mock_control = MagicMock()
        mock_control.inspect.return_value = inspector
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app",
            MagicMock(control=mock_control),
        )

        result = _collect_celery_current_tasks()
        assert len(result) == 1
        assert result[0]["task_id"] == "task-1"
        assert result[0]["status"] == "STARTED"

    def test_collects_reserved_task_with_received_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Reserved tasks get RECEIVED as default status."""
        entry = self._make_task_entry(task_id="task-2")
        inspector = MagicMock()
        inspector.active.return_value = {}
        inspector.reserved.return_value = {"worker1": [entry]}
        inspector.scheduled.return_value = {}
        mock_control = MagicMock()
        mock_control.inspect.return_value = inspector
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app",
            MagicMock(control=mock_control),
        )

        result = _collect_celery_current_tasks()
        assert len(result) == 1
        assert result[0]["status"] == "RECEIVED"

    def test_skips_non_helping_hands_tasks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tasks with non-helping_hands names are filtered out."""
        entry = self._make_task_entry(task_id="task-3", name="some.other.task")
        inspector = MagicMock()
        inspector.active.return_value = {"worker1": [entry]}
        inspector.reserved.return_value = {}
        inspector.scheduled.return_value = {}
        mock_control = MagicMock()
        mock_control.inspect.return_value = inspector
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app",
            MagicMock(control=mock_control),
        )

        assert _collect_celery_current_tasks() == []

    def test_skips_entries_without_task_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Entries missing an id field are skipped."""
        entry = {
            "name": "helping_hands.server.celery_app.build_feature",
            "kwargs": "{}",
        }
        inspector = MagicMock()
        inspector.active.return_value = {"worker1": [entry]}
        inspector.reserved.return_value = {}
        inspector.scheduled.return_value = {}
        mock_control = MagicMock()
        mock_control.inspect.return_value = inspector
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app",
            MagicMock(control=mock_control),
        )

        assert _collect_celery_current_tasks() == []

    def test_deduplicates_across_inspect_shapes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same task_id appearing in active and reserved yields one entry."""
        entry = self._make_task_entry(task_id="dup-1")
        inspector = MagicMock()
        inspector.active.return_value = {"worker1": [entry]}
        inspector.reserved.return_value = {"worker1": [entry]}
        inspector.scheduled.return_value = {}
        mock_control = MagicMock()
        mock_control.inspect.return_value = inspector
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app",
            MagicMock(control=mock_control),
        )

        result = _collect_celery_current_tasks()
        assert len(result) == 1
        assert result[0]["task_id"] == "dup-1"

    def test_status_fallback_for_invalid_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When entry has a state not in _CURRENT_TASK_STATES, uses default."""
        entry = self._make_task_entry(task_id="task-4", state="SUCCESS")
        inspector = MagicMock()
        inspector.active.return_value = {"worker1": [entry]}
        inspector.reserved.return_value = {}
        inspector.scheduled.return_value = {}
        mock_control = MagicMock()
        mock_control.inspect.return_value = inspector
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app",
            MagicMock(control=mock_control),
        )

        result = _collect_celery_current_tasks()
        assert len(result) == 1
        # SUCCESS is not in _CURRENT_TASK_STATES, falls back to "STARTED"
        assert result[0]["status"] == "STARTED"


# --- _merge_source_tags ---


class TestMergeSourceTags:
    """Tests for _merge_source_tags()."""

    def test_adds_new_tag_to_empty(self) -> None:
        assert _merge_source_tags("", "flower") == "flower"

    def test_adds_new_tag_to_existing(self) -> None:
        assert _merge_source_tags("flower", "inspect") == "flower+inspect"

    def test_does_not_duplicate_existing_tag(self) -> None:
        assert _merge_source_tags("flower+inspect", "flower") == "flower+inspect"

    def test_sorts_alphabetically(self) -> None:
        assert _merge_source_tags("inspect", "active") == "active+inspect"

    def test_empty_new_tag_returns_existing(self) -> None:
        assert _merge_source_tags("flower", "") == "flower"

    def test_both_empty(self) -> None:
        assert _merge_source_tags("", "") == ""

    def test_three_tags_sorted(self) -> None:
        result = _merge_source_tags("flower+inspect", "active")
        assert result == "active+flower+inspect"

    def test_strips_empty_parts_from_existing(self) -> None:
        assert _merge_source_tags("+flower+", "inspect") == "flower+inspect"


# --- _first_validation_error_msg ---


class TestFirstValidationErrorMsg:
    """Tests for _first_validation_error_msg()."""

    def test_extracts_msg_from_pydantic_error(self) -> None:
        exc = MagicMock()
        exc.errors.return_value = [{"msg": "Value is required", "type": "missing"}]
        assert _first_validation_error_msg(exc) == "Value is required"

    def test_returns_fallback_when_errors_empty(self) -> None:
        exc = MagicMock()
        exc.errors.return_value = []
        assert _first_validation_error_msg(exc) == "Invalid form submission."

    def test_returns_custom_fallback(self) -> None:
        exc = MagicMock()
        exc.errors.return_value = []
        assert _first_validation_error_msg(exc, "Custom error.") == "Custom error."

    def test_returns_fallback_when_first_error_not_dict(self) -> None:
        exc = MagicMock()
        exc.errors.return_value = ["not a dict"]
        assert _first_validation_error_msg(exc) == "Invalid form submission."

    def test_returns_fallback_when_msg_not_string(self) -> None:
        exc = MagicMock()
        exc.errors.return_value = [{"msg": 42, "type": "missing"}]
        assert _first_validation_error_msg(exc) == "Invalid form submission."

    def test_returns_fallback_when_msg_missing(self) -> None:
        exc = MagicMock()
        exc.errors.return_value = [{"type": "missing"}]
        assert _first_validation_error_msg(exc) == "Invalid form submission."

    def test_uses_first_of_multiple_errors(self) -> None:
        exc = MagicMock()
        exc.errors.return_value = [
            {"msg": "First error", "type": "a"},
            {"msg": "Second error", "type": "b"},
        ]
        assert _first_validation_error_msg(exc) == "First error"
