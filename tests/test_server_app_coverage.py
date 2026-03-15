"""Tests for previously uncovered server/app.py functions.

Covers: _validate_path_param, _redact_token, _build_form_redirect_query,
_build_task_status, _cancel_task, _enqueue_build_task,
_fetch_flower_current_tasks, _resolve_worker_capacity.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    BuildRequest,
    BuildResponse,
    WorkerCapacityResponse,
    _build_form_redirect_query,
    _build_task_status,
    _cancel_task,
    _enqueue_build_task,
    _fetch_flower_current_tasks,
    _redact_token,
    _resolve_worker_capacity,
    _validate_path_param,
)

# ---------------------------------------------------------------------------
# _validate_path_param
# ---------------------------------------------------------------------------


class TestValidatePathParam:
    def test_valid_value_stripped(self) -> None:
        assert _validate_path_param("  task-123  ", "task_id") == "task-123"

    def test_valid_value_passthrough(self) -> None:
        assert _validate_path_param("abc", "task_id") == "abc"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _validate_path_param("", "task_id")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="schedule_id"):
            _validate_path_param("   ", "schedule_id")

    def test_error_includes_param_name(self) -> None:
        with pytest.raises(ValueError, match="my_param"):
            _validate_path_param("", "my_param")


# ---------------------------------------------------------------------------
# _redact_token
# ---------------------------------------------------------------------------


class TestRedactToken:
    def test_none_returns_none(self) -> None:
        assert _redact_token(None) is None

    def test_empty_returns_none(self) -> None:
        assert _redact_token("") is None

    def test_short_token_fully_redacted(self) -> None:
        assert _redact_token("abc123") == "***"

    def test_exactly_12_chars_fully_redacted(self) -> None:
        assert _redact_token("123456789012") == "***"

    def test_long_token_partial_redact(self) -> None:
        result = _redact_token("ghp_abcdef123456789xyz")
        assert result.startswith("ghp_")
        assert result.endswith("9xyz")
        assert "***" in result

    def test_13_char_token_shows_ends(self) -> None:
        result = _redact_token("1234567890abc")
        assert result == "1234***0abc"


# ---------------------------------------------------------------------------
# _build_form_redirect_query
# ---------------------------------------------------------------------------


class TestBuildFormRedirectQuery:
    def test_minimal_args(self) -> None:
        query = _build_form_redirect_query(
            repo_path="/tmp/repo",
            prompt="fix bugs",
            backend="codexcli",
            max_iterations=6,
            error="something broke",
        )
        assert query["repo_path"] == "/tmp/repo"
        assert query["prompt"] == "fix bugs"
        assert query["backend"] == "codexcli"
        assert query["max_iterations"] == "6"
        assert query["error"] == "something broke"
        assert "model" not in query
        assert "no_pr" not in query
        assert "pr_number" not in query

    def test_all_optional_flags(self) -> None:
        query = _build_form_redirect_query(
            repo_path="/repo",
            prompt="p",
            backend="b",
            max_iterations=3,
            error="e",
            model="gpt-5.2",
            no_pr=True,
            enable_execution=True,
            enable_web=True,
            use_native_cli_auth=True,
            fix_ci=True,
            ci_check_wait_minutes=5.0,
            pr_number=42,
            tools="bash,python",
            skills="deploy",
        )
        assert query["model"] == "gpt-5.2"
        assert query["no_pr"] == "1"
        assert query["enable_execution"] == "1"
        assert query["enable_web"] == "1"
        assert query["use_native_cli_auth"] == "1"
        assert query["fix_ci"] == "1"
        assert query["ci_check_wait_minutes"] == "5.0"
        assert query["pr_number"] == "42"
        assert query["tools"] == "bash,python"
        assert query["skills"] == "deploy"

    def test_default_ci_wait_not_included(self) -> None:
        query = _build_form_redirect_query(
            repo_path="/repo",
            prompt="p",
            backend="b",
            max_iterations=6,
            error="e",
            ci_check_wait_minutes=3.0,
        )
        assert "ci_check_wait_minutes" not in query

    def test_false_booleans_not_included(self) -> None:
        query = _build_form_redirect_query(
            repo_path="/repo",
            prompt="p",
            backend="b",
            max_iterations=6,
            error="e",
            no_pr=False,
            enable_execution=False,
            enable_web=False,
        )
        assert "no_pr" not in query
        assert "enable_execution" not in query
        assert "enable_web" not in query

    def test_whitespace_only_tools_not_included(self) -> None:
        query = _build_form_redirect_query(
            repo_path="/repo",
            prompt="p",
            backend="b",
            max_iterations=6,
            error="e",
            tools="   ",
            skills="   ",
        )
        assert "tools" not in query
        assert "skills" not in query


# ---------------------------------------------------------------------------
# _build_task_status
# ---------------------------------------------------------------------------


class TestBuildTaskStatus:
    def test_ready_task_uses_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.status = "SUCCESS"
        mock_result.result = {"message": "PR created", "updates": ["done"]}
        mock_result.info = {"should": "not be used"}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )

        status = _build_task_status("task-abc")
        assert status.task_id == "task-abc"
        assert status.status == "SUCCESS"
        assert status.result is not None
        assert status.result["message"] == "PR created"

    def test_pending_task_uses_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.status = "PROGRESS"
        mock_result.info = {"stage": "running", "updates": ["step 1"]}
        mock_result.result = {"should": "not be used"}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )

        status = _build_task_status("task-xyz")
        assert status.task_id == "task-xyz"
        assert status.status == "PROGRESS"

    def test_pending_unknown_returns_none_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.status = "PENDING"
        mock_result.info = None
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )

        status = _build_task_status("unknown-task")
        assert status.task_id == "unknown-task"
        assert status.status == "PENDING"


# ---------------------------------------------------------------------------
# _cancel_task
# ---------------------------------------------------------------------------


class TestCancelTask:
    def test_cancel_running_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_result = MagicMock()
        mock_result.status = "STARTED"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        mock_revoke = MagicMock()
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.revoke", mock_revoke
        )

        resp = _cancel_task("task-run")
        assert resp.task_id == "task-run"
        assert resp.cancelled is True
        assert "STARTED" in resp.detail
        mock_revoke.assert_called_once_with(
            "task-run", terminate=True, signal="SIGTERM"
        )

    def test_cancel_terminal_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )

        resp = _cancel_task("task-done")
        assert resp.task_id == "task-done"
        assert resp.cancelled is False
        assert "terminal" in resp.detail.lower()

    def test_cancel_terminal_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_result = MagicMock()
        mock_result.status = "FAILURE"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )

        resp = _cancel_task("task-fail")
        assert resp.cancelled is False

    def test_cancel_terminal_revoked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_result = MagicMock()
        mock_result.status = "REVOKED"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )

        resp = _cancel_task("task-rev")
        assert resp.cancelled is False

    def test_cancel_pending_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        mock_revoke = MagicMock()
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.revoke", mock_revoke
        )

        resp = _cancel_task("task-pend")
        assert resp.cancelled is True
        mock_revoke.assert_called_once()

    def test_cancel_empty_task_id_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _cancel_task("")

    def test_cancel_whitespace_task_id_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            _cancel_task("   ")


# ---------------------------------------------------------------------------
# _enqueue_build_task
# ---------------------------------------------------------------------------


class TestEnqueueBuildTask:
    def test_enqueues_and_returns_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="celery-task-42")

        monkeypatch.setattr("helping_hands.server.app.build_feature.delay", fake_delay)

        req = BuildRequest(
            repo_path="/tmp/repo",
            prompt="fix bug",
            backend="claudecodecli",
            model="gpt-5.2",
            max_iterations=3,
        )
        resp = _enqueue_build_task(req)

        assert isinstance(resp, BuildResponse)
        assert resp.task_id == "celery-task-42"
        assert resp.status == "queued"
        assert resp.backend == "claudecodecli"
        assert captured["repo_path"] == "/tmp/repo"
        assert captured["prompt"] == "fix bug"
        assert captured["model"] == "gpt-5.2"
        assert captured["max_iterations"] == 3

    def test_enqueue_forwards_all_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_delay(**kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(id="task-full")

        monkeypatch.setattr("helping_hands.server.app.build_feature.delay", fake_delay)

        req = BuildRequest(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            no_pr=True,
            enable_execution=True,
            enable_web=True,
            use_native_cli_auth=True,
            fix_ci=True,
            ci_check_wait_minutes=5.0,
            pr_number=99,
        )
        _enqueue_build_task(req)

        assert captured["no_pr"] is True
        assert captured["enable_execution"] is True
        assert captured["enable_web"] is True
        assert captured["use_native_cli_auth"] is True
        assert captured["fix_ci"] is True
        assert captured["ci_check_wait_minutes"] == 5.0
        assert captured["pr_number"] == 99


# ---------------------------------------------------------------------------
# _fetch_flower_current_tasks
# ---------------------------------------------------------------------------


class TestFetchFlowerCurrentTasks:
    def test_returns_empty_when_no_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_FLOWER_API_URL", raising=False)
        assert _fetch_flower_current_tasks() == []

    def test_returns_empty_on_http_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")

        def _raise(*a, **kw):
            raise ConnectionError("refused")

        monkeypatch.setattr("helping_hands.server.app.urllib_request.urlopen", _raise)

        assert _fetch_flower_current_tasks() == []

    def test_returns_empty_on_non_dict_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([1, 2, 3]).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        assert _fetch_flower_current_tasks() == []

    def test_extracts_active_tasks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")

        payload = {
            "uuid-1": {
                "name": "helping_hands.build_feature",
                "state": "STARTED",
                "kwargs": '{"repo_path": "/repo", "backend": "codexcli"}',
                "worker": "worker@a",
            },
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        result = _fetch_flower_current_tasks()
        assert len(result) == 1
        assert result[0]["task_id"] == "uuid-1"
        assert result[0]["status"] == "STARTED"
        assert result[0]["backend"] == "codexcli"
        assert result[0]["repo_path"] == "/repo"
        assert result[0]["source"] == "flower"

    def test_filters_terminal_states(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")

        payload = {
            "uuid-done": {
                "name": "helping_hands.build_feature",
                "state": "SUCCESS",
                "kwargs": "{}",
            },
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        assert _fetch_flower_current_tasks() == []

    def test_filters_non_helping_hands_tasks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")

        payload = {
            "uuid-other": {
                "name": "other.task",
                "state": "STARTED",
                "kwargs": "{}",
            },
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        assert _fetch_flower_current_tasks() == []

    def test_skips_non_dict_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_FLOWER_API_URL", "http://flower:5555")

        payload = {
            "uuid-valid": {
                "name": "helping_hands.build_feature",
                "state": "STARTED",
                "kwargs": "{}",
            },
            "uuid-bad": "not a dict",
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        result = _fetch_flower_current_tasks()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _resolve_worker_capacity
# ---------------------------------------------------------------------------


class TestResolveWorkerCapacity:
    def test_returns_celery_stats(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = {
            "worker@a": {"pool": {"max-concurrency": 4}},
            "worker@b": {"pool": {"max-concurrency": 2}},
        }
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )

        resp = _resolve_worker_capacity()
        assert isinstance(resp, WorkerCapacityResponse)
        assert resp.max_workers == 6
        assert resp.source == "celery"
        assert resp.workers == {"worker@a": 4, "worker@b": 2}

    def test_falls_back_to_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = None
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )
        # Clear all env vars except the one we want
        for var in (
            "HELPING_HANDS_MAX_WORKERS",
            "HELPING_HANDS_WORKER_CONCURRENCY",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_WORKER_CONCURRENCY", "16")

        resp = _resolve_worker_capacity()
        assert resp.max_workers == 16
        assert resp.source == "env:HELPING_HANDS_WORKER_CONCURRENCY"

    def test_falls_back_to_celery_concurrency_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = None
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )
        for var in (
            "HELPING_HANDS_MAX_WORKERS",
            "HELPING_HANDS_WORKER_CONCURRENCY",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("CELERY_WORKER_CONCURRENCY", "4")

        resp = _resolve_worker_capacity()
        assert resp.max_workers == 4
        assert resp.source == "env:CELERY_WORKER_CONCURRENCY"

    def test_celery_stats_empty_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = {}
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )
        for var in (
            "HELPING_HANDS_MAX_WORKERS",
            "HELPING_HANDS_WORKER_CONCURRENCY",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ):
            monkeypatch.delenv(var, raising=False)

        resp = _resolve_worker_capacity()
        assert resp.source == "default"
        assert resp.max_workers == 8

    def test_celery_inspect_exception_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def failing_inspect(timeout: float = 1.0) -> None:
            raise ConnectionError("broker unreachable")

        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            failing_inspect,
        )
        for var in (
            "HELPING_HANDS_MAX_WORKERS",
            "HELPING_HANDS_WORKER_CONCURRENCY",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ):
            monkeypatch.delenv(var, raising=False)

        resp = _resolve_worker_capacity()
        assert resp.max_workers == 8
        assert resp.source == "default"

    def test_worker_missing_pool_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Workers without pool info should not cause errors."""
        fake_inspector = MagicMock()
        fake_inspector.stats.return_value = {
            "worker@a": {},  # no pool key
        }
        monkeypatch.setattr(
            "helping_hands.server.app.celery_app.control.inspect",
            lambda timeout=1.0: fake_inspector,
        )
        for var in (
            "HELPING_HANDS_MAX_WORKERS",
            "HELPING_HANDS_WORKER_CONCURRENCY",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ):
            monkeypatch.delenv(var, raising=False)

        # Should not raise; falls back gracefully
        resp = _resolve_worker_capacity()
        assert isinstance(resp, WorkerCapacityResponse)
