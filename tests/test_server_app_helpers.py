"""Unit tests for app.py internal helper functions.

These tests exercise the private helpers directly, complementing the
integration-style endpoint tests in test_server_app.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _coerce_optional_str,
    _extract_task_id,
    _extract_task_kwargs,
    _extract_task_name,
    _flower_timeout_seconds,
    _is_helping_hands_task,
    _is_running_in_docker,
    _iter_worker_task_entries,
    _normalize_task_status,
    _parse_backend,
    _parse_task_kwargs_str,
    _task_state_priority,
    _upsert_current_task,
)

# ---------------------------------------------------------------------------
# _parse_backend
# ---------------------------------------------------------------------------


class TestParseBackend:
    def test_valid_backends(self) -> None:
        assert _parse_backend("codexcli") == "codexcli"
        assert _parse_backend("basic-langgraph") == "basic-langgraph"
        assert _parse_backend("e2e") == "e2e"
        assert _parse_backend("claudecodecli") == "claudecodecli"
        assert _parse_backend("goose") == "goose"
        assert _parse_backend("geminicli") == "geminicli"

    def test_normalizes_whitespace_and_case(self) -> None:
        assert _parse_backend("  CodExCli  ") == "codexcli"
        assert _parse_backend("BASIC-LANGGRAPH") == "basic-langgraph"

    def test_raises_on_invalid_backend(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            _parse_backend("nonexistent")

    def test_raises_on_empty_string(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            _parse_backend("")


# ---------------------------------------------------------------------------
# _normalize_task_status
# ---------------------------------------------------------------------------


class TestNormalizeTaskStatus:
    def test_normal_status(self) -> None:
        assert _normalize_task_status("started", default="PENDING") == "STARTED"

    def test_none_falls_back_to_default(self) -> None:
        assert _normalize_task_status(None, default="PENDING") == "PENDING"

    def test_empty_string_falls_back_to_default(self) -> None:
        assert _normalize_task_status("", default="UNKNOWN") == "UNKNOWN"

    def test_whitespace_only_falls_back_to_default(self) -> None:
        assert _normalize_task_status("   ", default="QUEUED") == "QUEUED"

    def test_mixed_case_uppercased(self) -> None:
        assert _normalize_task_status("Progress", default="X") == "PROGRESS"


# ---------------------------------------------------------------------------
# _extract_task_id
# ---------------------------------------------------------------------------


class TestExtractTaskId:
    def test_from_task_id_key(self) -> None:
        assert _extract_task_id({"task_id": "abc-123"}) == "abc-123"

    def test_from_uuid_key(self) -> None:
        assert _extract_task_id({"uuid": "def-456"}) == "def-456"

    def test_from_id_key(self) -> None:
        assert _extract_task_id({"id": "ghi-789"}) == "ghi-789"

    def test_from_nested_request(self) -> None:
        entry = {"request": {"id": "nested-id"}}
        assert _extract_task_id(entry) == "nested-id"

    def test_returns_none_for_empty(self) -> None:
        assert _extract_task_id({}) is None

    def test_skips_empty_string_values(self) -> None:
        assert _extract_task_id({"task_id": "  ", "uuid": "real-id"}) == "real-id"

    def test_prefers_task_id_over_uuid(self) -> None:
        assert _extract_task_id({"task_id": "a", "uuid": "b"}) == "a"


# ---------------------------------------------------------------------------
# _extract_task_name
# ---------------------------------------------------------------------------


class TestExtractTaskName:
    def test_from_name_key(self) -> None:
        assert _extract_task_name({"name": "helping_hands.build_feature"}) == (
            "helping_hands.build_feature"
        )

    def test_from_task_key(self) -> None:
        assert _extract_task_name({"task": "my_task"}) == "my_task"

    def test_from_nested_request(self) -> None:
        entry = {"request": {"name": "nested_name"}}
        assert _extract_task_name(entry) == "nested_name"

    def test_returns_none_for_empty(self) -> None:
        assert _extract_task_name({}) is None

    def test_skips_whitespace_values(self) -> None:
        assert _extract_task_name({"name": "  ", "task": "fallback"}) == "fallback"


# ---------------------------------------------------------------------------
# _extract_task_kwargs
# ---------------------------------------------------------------------------


class TestExtractTaskKwargs:
    def test_from_dict_kwargs(self) -> None:
        entry = {"kwargs": {"repo_path": "owner/repo", "backend": "codexcli"}}
        assert _extract_task_kwargs(entry) == {
            "repo_path": "owner/repo",
            "backend": "codexcli",
        }

    def test_from_json_string_kwargs(self) -> None:
        entry = {"kwargs": '{"repo_path": "owner/repo"}'}
        assert _extract_task_kwargs(entry) == {"repo_path": "owner/repo"}

    def test_from_literal_string_kwargs(self) -> None:
        entry = {"kwargs": "{'repo_path': 'owner/repo'}"}
        assert _extract_task_kwargs(entry) == {"repo_path": "owner/repo"}

    def test_from_nested_request_kwargs(self) -> None:
        entry = {"request": {"kwargs": {"backend": "goose"}}}
        assert _extract_task_kwargs(entry) == {"backend": "goose"}

    def test_from_nested_request_string_kwargs(self) -> None:
        entry = {"request": {"kwargs": '{"backend": "goose"}'}}
        assert _extract_task_kwargs(entry) == {"backend": "goose"}

    def test_returns_empty_for_missing_kwargs(self) -> None:
        assert _extract_task_kwargs({}) == {}

    def test_returns_empty_for_unparseable_string(self) -> None:
        assert _extract_task_kwargs({"kwargs": "not-json-or-literal"}) == {}


# ---------------------------------------------------------------------------
# _coerce_optional_str
# ---------------------------------------------------------------------------


class TestCoerceOptionalStr:
    def test_normal_string(self) -> None:
        assert _coerce_optional_str("hello") == "hello"

    def test_strips_whitespace(self) -> None:
        assert _coerce_optional_str("  trimmed  ") == "trimmed"

    def test_empty_string_returns_none(self) -> None:
        assert _coerce_optional_str("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert _coerce_optional_str("   ") is None

    def test_non_string_returns_none(self) -> None:
        assert _coerce_optional_str(42) is None
        assert _coerce_optional_str(None) is None
        assert _coerce_optional_str(["list"]) is None


# ---------------------------------------------------------------------------
# _parse_task_kwargs_str
# ---------------------------------------------------------------------------


class TestParseTaskKwargsStr:
    def test_valid_json(self) -> None:
        assert _parse_task_kwargs_str('{"a": 1}') == {"a": 1}

    def test_valid_python_literal(self) -> None:
        assert _parse_task_kwargs_str("{'b': 2}") == {"b": 2}

    def test_empty_string(self) -> None:
        assert _parse_task_kwargs_str("") == {}

    def test_whitespace_only(self) -> None:
        assert _parse_task_kwargs_str("   ") == {}

    def test_invalid_string(self) -> None:
        assert _parse_task_kwargs_str("not-parseable") == {}

    def test_json_array_not_dict(self) -> None:
        assert _parse_task_kwargs_str("[1, 2, 3]") == {}


# ---------------------------------------------------------------------------
# _is_helping_hands_task
# ---------------------------------------------------------------------------


class TestIsHelpingHandsTask:
    def test_matching_task_name(self) -> None:
        assert _is_helping_hands_task({"name": "helping_hands.build_feature"}) is True

    def test_non_matching_task_name(self) -> None:
        assert _is_helping_hands_task({"name": "other.task"}) is False

    def test_missing_task_name_defaults_true(self) -> None:
        assert _is_helping_hands_task({}) is True


# ---------------------------------------------------------------------------
# _upsert_current_task
# ---------------------------------------------------------------------------


class TestUpsertCurrentTask:
    def test_inserts_new_task(self) -> None:
        tasks: dict[str, dict[str, Any]] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="codexcli",
            repo_path="owner/repo",
            worker="w@a",
            source="flower",
        )
        assert "t1" in tasks
        assert tasks["t1"]["status"] == "STARTED"
        assert tasks["t1"]["backend"] == "codexcli"

    def test_merges_higher_priority_status(self) -> None:
        tasks: dict[str, dict[str, Any]] = {}
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
            repo_path="owner/repo",
            worker="w@a",
            source="celery",
        )
        assert tasks["t1"]["status"] == "STARTED"
        assert tasks["t1"]["backend"] == "codexcli"
        assert tasks["t1"]["repo_path"] == "owner/repo"
        assert tasks["t1"]["worker"] == "w@a"
        assert "celery" in tasks["t1"]["source"]
        assert "flower" in tasks["t1"]["source"]

    def test_keeps_higher_priority_existing_status(self) -> None:
        tasks: dict[str, dict[str, Any]] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="codexcli",
            repo_path=None,
            worker=None,
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

    def test_fills_missing_fields_from_later_upsert(self) -> None:
        tasks: dict[str, dict[str, Any]] = {}
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend=None,
            repo_path=None,
            worker=None,
            source="flower",
        )
        _upsert_current_task(
            tasks,
            task_id="t1",
            status="STARTED",
            backend="goose",
            repo_path="o/r",
            worker="w@b",
            source="celery",
        )
        assert tasks["t1"]["backend"] == "goose"
        assert tasks["t1"]["repo_path"] == "o/r"
        assert tasks["t1"]["worker"] == "w@b"


# ---------------------------------------------------------------------------
# _flower_timeout_seconds
# ---------------------------------------------------------------------------


class TestFlowerTimeoutSeconds:
    def test_default_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", raising=False)
        assert _flower_timeout_seconds() == 0.75

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "3.5")
        assert _flower_timeout_seconds() == 3.5

    def test_clamped_to_minimum(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "0.001")
        assert _flower_timeout_seconds() == 0.1

    def test_clamped_to_maximum(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "999")
        assert _flower_timeout_seconds() == 10.0

    def test_invalid_value_returns_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS", "not-a-number")
        assert _flower_timeout_seconds() == 0.75


# ---------------------------------------------------------------------------
# _task_state_priority
# ---------------------------------------------------------------------------


class TestTaskStatePriority:
    def test_known_states(self) -> None:
        assert _task_state_priority("STARTED") == 6
        assert _task_state_priority("PENDING") == 1

    def test_unknown_state_returns_zero(self) -> None:
        assert _task_state_priority("CUSTOM_STATE") == 0

    def test_case_sensitive(self) -> None:
        assert _task_state_priority("started") == 0


# ---------------------------------------------------------------------------
# _iter_worker_task_entries
# ---------------------------------------------------------------------------


class TestIterWorkerTaskEntries:
    def test_valid_payload(self) -> None:
        payload = {
            "worker@a": [{"id": "t1"}, {"id": "t2"}],
            "worker@b": [{"id": "t3"}],
        }
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 3
        assert entries[0] == ("worker@a", {"id": "t1"})

    def test_non_dict_payload_returns_empty(self) -> None:
        assert _iter_worker_task_entries(None) == []
        assert _iter_worker_task_entries("string") == []
        assert _iter_worker_task_entries([1, 2]) == []

    def test_skips_non_list_worker_tasks(self) -> None:
        payload = {"worker@a": "not-a-list", "worker@b": [{"id": "t1"}]}
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 1
        assert entries[0] == ("worker@b", {"id": "t1"})

    def test_skips_non_dict_task_entries(self) -> None:
        payload = {"worker@a": [{"id": "t1"}, "not-a-dict", 42]}
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 1

    def test_skips_non_string_worker_keys(self) -> None:
        payload = {42: [{"id": "t1"}], "worker@a": [{"id": "t2"}]}
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 1
        assert entries[0][0] == "worker@a"


# ---------------------------------------------------------------------------
# _is_running_in_docker
# ---------------------------------------------------------------------------


class TestIsRunningInDocker:
    def test_dockerenv_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch.object(Path, "exists", return_value=True):
            assert _is_running_in_docker() is True

    def test_env_var_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "1")
        with patch.object(Path, "exists", return_value=False):
            assert _is_running_in_docker() is True

    def test_env_var_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "yes")
        with patch.object(Path, "exists", return_value=False):
            assert _is_running_in_docker() is True

    def test_not_in_docker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        with patch.object(Path, "exists", return_value=False):
            assert _is_running_in_docker() is False


# ---------------------------------------------------------------------------
# Health check endpoints
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestHealthServicesEndpoint:
    def test_health_services_returns_all_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.setattr(
            "helping_hands.server.app._check_redis_health", lambda: "ok"
        )
        monkeypatch.setattr("helping_hands.server.app._check_db_health", lambda: "na")
        monkeypatch.setattr(
            "helping_hands.server.app._check_workers_health", lambda: "error"
        )

        client = TestClient(app)
        response = client.get("/health/services")
        assert response.status_code == 200
        body = response.json()
        assert body["redis"] == "ok"
        assert body["db"] == "na"
        assert body["workers"] == "error"


# ---------------------------------------------------------------------------
# JSON /build endpoint
# ---------------------------------------------------------------------------


class TestBuildJsonEndpoint:
    def test_json_build_enqueues_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from types import SimpleNamespace

        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-json-1")

        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.delay",
            fake_delay,
        )

        client = TestClient(app)
        response = client.post(
            "/build",
            json={
                "repo_path": "owner/repo",
                "prompt": "add feature",
                "backend": "geminicli",
                "model": "gemini-2.0-flash",
                "max_iterations": 8,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["task_id"] == "task-json-1"
        assert body["backend"] == "geminicli"
        assert captured["model"] == "gemini-2.0-flash"
        assert captured["max_iterations"] == 8

    def test_json_build_validates_empty_repo(self) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app)
        response = client.post(
            "/build",
            json={"repo_path": "", "prompt": "fix bug"},
        )
        assert response.status_code == 422

    def test_json_build_validates_empty_prompt(self) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app)
        response = client.post(
            "/build",
            json={"repo_path": "owner/repo", "prompt": ""},
        )
        assert response.status_code == 422

    def test_json_build_validates_max_iterations_bounds(self) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app)
        response = client.post(
            "/build",
            json={
                "repo_path": "owner/repo",
                "prompt": "fix bug",
                "max_iterations": 0,
            },
        )
        assert response.status_code == 422

        response = client.post(
            "/build",
            json={
                "repo_path": "owner/repo",
                "prompt": "fix bug",
                "max_iterations": 101,
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Task status endpoint
# ---------------------------------------------------------------------------


class TestTaskStatusEndpoint:
    def test_task_status_pending(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        fake_result = MagicMock()
        fake_result.status = "PENDING"
        fake_result.ready.return_value = False
        fake_result.info = None
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda _task_id: fake_result,
        )

        client = TestClient(app)
        response = client.get("/tasks/task-xyz")
        assert response.status_code == 200
        body = response.json()
        assert body["task_id"] == "task-xyz"
        assert body["status"] == "PENDING"


# ---------------------------------------------------------------------------
# Config endpoint
# ---------------------------------------------------------------------------


class TestConfigEndpoint:
    def test_config_not_in_docker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.setattr(
            "helping_hands.server.app._is_running_in_docker", lambda: False
        )

        client = TestClient(app)
        response = client.get("/config")
        assert response.status_code == 200
        body = response.json()
        assert body["in_docker"] is False
        assert body["native_auth_default"] is True

    def test_config_in_docker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.setattr(
            "helping_hands.server.app._is_running_in_docker", lambda: True
        )

        client = TestClient(app)
        response = client.get("/config")
        assert response.status_code == 200
        body = response.json()
        assert body["in_docker"] is True
        assert body["native_auth_default"] is False
