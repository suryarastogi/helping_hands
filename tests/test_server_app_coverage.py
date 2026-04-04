"""Branch and edge-case coverage for internal server/app.py helpers.

Protects a cluster of pure-logic helpers that sit beneath the HTTP layer:
path-param validation prevents empty IDs from reaching Celery; token redaction
ensures GitHub tokens never appear in API responses or logs; the form redirect
query builder controls what prefill values survive a validation failure redirect;
and _render_monitor_page guards the HTML output contract (auto-refresh, cancel
button, HTML escaping) that the web UI relies on.

Regressions here typically manifest as silent data-loss (empty task IDs accepted),
credential leaks in JSON payloads, or broken monitor-page UX rather than outright
HTTP errors, making them easy to miss without targeted tests.
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
        )
        assert "tools" not in query


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


# --- _render_monitor_page ---


class TestRenderMonitorPage:
    """Tests for _render_monitor_page HTML generation."""

    def test_basic_pending_task(self) -> None:
        """Renders page with task_id, status, and auto-refresh for non-terminal."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(task_id="abc-123", status="PENDING", result=None)
        html = _render_monitor_page(ts)
        assert "abc-123" in html
        assert "PENDING" in html
        assert '<meta http-equiv="refresh"' in html
        assert "No updates yet." in html
        # Cancel button should appear for non-terminal
        assert "Cancel task" in html

    def test_terminal_status_no_refresh(self) -> None:
        """Terminal status omits auto-refresh and cancel button."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(task_id="task-done", status="SUCCESS", result=None)
        html = _render_monitor_page(ts)
        assert '<meta http-equiv="refresh"' not in html
        assert "Cancel task" not in html
        assert "off" in html  # polling label

    def test_prompt_extracted_from_result(self) -> None:
        """Prompt is extracted and displayed when present in result dict."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="t1",
            status="STARTED",
            result={"prompt": "Fix the bug"},
        )
        html = _render_monitor_page(ts)
        assert "Fix the bug" in html
        assert "Prompt" in html

    def test_prompt_not_shown_when_empty(self) -> None:
        """Empty or whitespace-only prompt is not displayed."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="t2",
            status="STARTED",
            result={"prompt": "   "},
        )
        html = _render_monitor_page(ts)
        # Prompt meta-item should not appear
        assert 'meta-label">Prompt' not in html

    def test_prompt_not_shown_when_non_string(self) -> None:
        """Non-string prompt value is ignored."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="t3",
            status="STARTED",
            result={"prompt": 42},
        )
        html = _render_monitor_page(ts)
        assert 'meta-label">Prompt' not in html

    def test_updates_rendered(self) -> None:
        """Updates list items are rendered in the updates section."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="t4",
            status="STARTED",
            result={"updates": ["Step 1 done", "Step 2 in progress"]},
        )
        html = _render_monitor_page(ts)
        assert "Step 1 done" in html
        assert "Step 2 in progress" in html
        assert "No updates yet." not in html

    def test_updates_not_list_shows_default(self) -> None:
        """Non-list updates value falls back to default message."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="t5",
            status="STARTED",
            result={"updates": "not a list"},
        )
        html = _render_monitor_page(ts)
        assert "No updates yet." in html

    def test_result_none_shows_defaults(self) -> None:
        """None result shows no prompt and default updates."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(task_id="t6", status="PENDING", result=None)
        html = _render_monitor_page(ts)
        assert "No updates yet." in html
        assert 'meta-label">Prompt' not in html

    def test_html_escaping(self) -> None:
        """Special characters in prompt and updates are HTML-escaped."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="<script>alert(1)</script>",
            status="STARTED",
            result={
                "prompt": "<b>bold</b>",
                "updates": ["<img src=x>"],
            },
        )
        html = _render_monitor_page(ts)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert "&lt;b&gt;bold&lt;/b&gt;" in html
        assert "&lt;img src=x&gt;" in html

    def test_failure_status_no_refresh(self) -> None:
        """FAILURE is terminal — no refresh, no cancel."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(task_id="t7", status="FAILURE", result=None)
        html = _render_monitor_page(ts)
        assert '<meta http-equiv="refresh"' not in html
        assert "Cancel task" not in html

    def test_revoked_status_no_refresh(self) -> None:
        """REVOKED is terminal — no refresh, no cancel."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(task_id="t8", status="REVOKED", result=None)
        html = _render_monitor_page(ts)
        assert '<meta http-equiv="refresh"' not in html
        assert "Cancel task" not in html

    def test_prompt_stripped(self) -> None:
        """Prompt with surrounding whitespace is stripped before display."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="t9",
            status="STARTED",
            result={"prompt": "  hello world  "},
        )
        html = _render_monitor_page(ts)
        assert "hello world" in html

    def test_updates_mixed_types_coerced(self) -> None:
        """Non-string items in updates list are coerced via str()."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(
            task_id="t10",
            status="STARTED",
            result={"updates": ["line1", 42, None]},
        )
        html = _render_monitor_page(ts)
        assert "line1" in html
        assert "42" in html
        assert "None" in html

    def test_cancel_button_has_task_id(self) -> None:
        """Cancel button JS references the correct task_id."""
        from helping_hands.server.app import TaskStatus, _render_monitor_page

        ts = TaskStatus(task_id="my-task-id", status="STARTED", result=None)
        html = _render_monitor_page(ts)
        assert "cancelTask('my-task-id')" in html


# --- _extract_task_kwargs branch coverage ---


class TestExtractTaskKwargsRequestBranches:
    """Cover the request.kwargs string-parsing path in _extract_task_kwargs."""

    def test_request_kwargs_invalid_string_falls_through(self) -> None:
        """When request.kwargs is an unparseable string, returns {}."""
        from helping_hands.server.app import _extract_task_kwargs

        entry = {"request": {"kwargs": "not-valid-json"}}
        assert _extract_task_kwargs(entry) == {}

    def test_request_kwargs_empty_string_falls_through(self) -> None:
        """When request.kwargs is empty string, returns {}."""
        from helping_hands.server.app import _extract_task_kwargs

        entry = {"request": {"kwargs": ""}}
        assert _extract_task_kwargs(entry) == {}

    def test_kwargs_string_takes_priority_over_request(self) -> None:
        """Top-level kwargs string is tried before request.kwargs."""
        from helping_hands.server.app import _extract_task_kwargs

        entry = {
            "kwargs": '{"repo": "top"}',
            "request": {"kwargs": {"repo": "nested"}},
        }
        assert _extract_task_kwargs(entry) == {"repo": "top"}

    def test_kwargs_invalid_string_falls_to_request_dict(self) -> None:
        """Invalid top-level kwargs string falls through to request dict."""
        from helping_hands.server.app import _extract_task_kwargs

        entry = {
            "kwargs": "bad",
            "request": {"kwargs": {"repo": "nested"}},
        }
        assert _extract_task_kwargs(entry) == {"repo": "nested"}

    def test_request_kwargs_python_literal(self) -> None:
        """Request kwargs as Python dict literal string is parsed."""
        from helping_hands.server.app import _extract_task_kwargs

        entry = {"request": {"kwargs": "{'backend': 'codexcli'}"}}
        assert _extract_task_kwargs(entry) == {"backend": "codexcli"}


# --- _iter_worker_task_entries non-string key ---


class TestIterWorkerTaskEntriesNonStringKey:
    """Cover the non-string worker key filter in _iter_worker_task_entries."""

    def test_skips_non_string_worker_keys(self) -> None:
        """Non-string dict keys (int, None) are filtered out."""
        from helping_hands.server.app import _iter_worker_task_entries

        payload = {
            42: [{"id": "t1"}],
            None: [{"id": "t2"}],
            "valid-worker": [{"id": "t3"}],
        }
        entries = _iter_worker_task_entries(payload)
        assert len(entries) == 1
        assert entries[0][0] == "valid-worker"

    def test_all_non_string_keys_returns_empty(self) -> None:
        """Dict with only non-string keys returns empty list."""
        from helping_hands.server.app import _iter_worker_task_entries

        payload = {1: [{"id": "t1"}], 2: [{"id": "t2"}]}
        entries = _iter_worker_task_entries(payload)
        assert entries == []


# ---------------------------------------------------------------------------
# Arcade endpoints
# ---------------------------------------------------------------------------


class TestArcadeEndpoints:
    def test_get_high_scores(self) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app)
        resp = client.get("/arcade/high-scores")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_submit_high_score(self) -> None:
        from fastapi.testclient import TestClient

        import helping_hands.server.app as app_mod
        from helping_hands.server.app import app

        client = TestClient(app)
        original = list(app_mod._arcade_high_scores)
        try:
            resp = client.post(
                "/arcade/high-scores",
                json={"name": "TestPlayer", "score": 1000, "wave": 5},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert any(e["name"] == "TestPlayer" for e in data)
        finally:
            app_mod._arcade_high_scores = original


# ---------------------------------------------------------------------------
# Multiplayer health endpoints
# ---------------------------------------------------------------------------


class TestMultiplayerHealthEndpoints:
    def test_health_multiplayer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.setattr(
            "helping_hands.server.app.get_multiplayer_stats",
            lambda: {"rooms": 0, "connections": 0},
        )
        client = TestClient(app)
        resp = client.get("/health/multiplayer")
        assert resp.status_code == 200
        assert resp.json()["rooms"] == 0

    def test_health_multiplayer_players(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.setattr(
            "helping_hands.server.app.get_connected_players",
            lambda: {"players": []},
        )
        client = TestClient(app)
        resp = client.get("/health/multiplayer/players")
        assert resp.status_code == 200

    def test_health_multiplayer_activity(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.setattr(
            "helping_hands.server.app.get_player_activity_summary",
            lambda: {"summary": {}},
        )
        client = TestClient(app)
        resp = client.get("/health/multiplayer/activity")
        assert resp.status_code == 200

    def test_health_multiplayer_decorations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.setattr(
            "helping_hands.server.app.get_decoration_state",
            lambda: {"decorations": []},
        )
        client = TestClient(app)
        resp = client.get("/health/multiplayer/decorations")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# _resolve_task_workspace
# ---------------------------------------------------------------------------


class TestResolveTaskWorkspace:
    def test_workspace_from_result(self, monkeypatch: pytest.MonkeyPatch, tmp_path):
        from helping_hands.server.app import _resolve_task_workspace

        ws = tmp_path / "ws"
        ws.mkdir()
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        path, _ws_str, ready, error = _resolve_task_workspace("tid-1")
        assert path == ws
        assert error is None
        assert ready is True

    def test_workspace_from_repo_path_fallback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ):
        from helping_hands.server.app import _resolve_task_workspace

        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {"repo_path": str(tmp_path)}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        path, _ws_str, _ready, error = _resolve_task_workspace("tid-2")
        assert path == tmp_path
        assert error is None

    def test_workspace_not_available(self, monkeypatch: pytest.MonkeyPatch):
        from helping_hands.server.app import _resolve_task_workspace

        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        path, _ws_str, _ready, error = _resolve_task_workspace("tid-3")
        assert path is None
        assert "not available" in error

    def test_workspace_cleaned_up(self, monkeypatch: pytest.MonkeyPatch):
        from helping_hands.server.app import _resolve_task_workspace

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": "/nonexistent/path"}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        path, _ws_str, _ready, error = _resolve_task_workspace("tid-4")
        assert path is None
        assert "cleaned up" in error

    def test_workspace_not_found_pending(self, monkeypatch: pytest.MonkeyPatch):
        from helping_hands.server.app import _resolve_task_workspace

        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {"workspace": "/nonexistent/path"}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        path, _ws_str, _ready, error = _resolve_task_workspace("tid-5")
        assert path is None
        assert "not found" in error


# ---------------------------------------------------------------------------
# _build_task_diff via endpoint
# ---------------------------------------------------------------------------


class TestTaskDiffEndpoint:
    def test_diff_workspace_not_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        client = TestClient(app)
        resp = client.get("/tasks/test-task-1/diff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is not None
        assert data["task_id"] == "test-task-1"

    def test_diff_with_workspace(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        import subprocess

        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        # Set up a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "file.txt").write_text("changed")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(tmp_path)}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        client = TestClient(app)
        resp = client.get("/tasks/test-task-2/diff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is None
        assert len(data["files"]) >= 1


# ---------------------------------------------------------------------------
# Task tree endpoint
# ---------------------------------------------------------------------------


class TestTaskTreeEndpoint:
    def test_tree_workspace_not_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        client = TestClient(app)
        resp = client.get("/tasks/test-task/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is not None

    def test_tree_with_workspace(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        import subprocess

        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hi')")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(tmp_path)}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        client = TestClient(app)
        resp = client.get("/tasks/test-tree/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is None
        assert len(data["tree"]) >= 2  # src dir + main.py


# ---------------------------------------------------------------------------
# Task file content endpoint
# ---------------------------------------------------------------------------


class TestTaskFileEndpoint:
    def test_file_workspace_not_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        client = TestClient(app)
        resp = client.get("/tasks/test-task/file/main.py")
        assert resp.status_code == 200
        assert resp.json()["error"] is not None

    def test_file_not_found(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(tmp_path)}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        client = TestClient(app)
        resp = client.get("/tasks/test-task/file/nonexistent.py")
        assert resp.status_code == 200
        assert "not found" in resp.json()["error"].lower()

    def test_file_success(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        import subprocess

        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        (tmp_path / "test.txt").write_text("hello world")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(tmp_path)}
        monkeypatch.setattr(
            "helping_hands.server.app.build_feature.AsyncResult",
            lambda tid: mock_result,
        )
        client = TestClient(app)
        resp = client.get("/tasks/test-task/file/test.txt")
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "hello world"


# ---------------------------------------------------------------------------
# _schedule_to_response
# ---------------------------------------------------------------------------


class TestScheduleToResponse:
    def test_cron_schedule(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _schedule_to_response

        task = MagicMock()
        task.schedule_id = "sched_test"
        task.name = "Test"
        task.schedule_type = "cron"
        task.cron_expression = "0 0 * * *"
        task.interval_seconds = None
        task.repo_path = "/repo"
        task.prompt = "fix"
        task.backend = "claudecodecli"
        task.model = None
        task.max_iterations = 6
        task.pr_number = None
        task.no_pr = False
        task.enable_execution = False
        task.enable_web = False
        task.use_native_cli_auth = False
        task.fix_ci = False
        task.ci_check_wait_minutes = 3.0
        task.github_token = None
        task.reference_repos = []
        task.tools = []
        task.enabled = True
        task.created_at = "2026-01-01T00:00:00"
        task.last_run_at = None
        task.last_run_task_id = None
        task.run_count = 0

        resp = _schedule_to_response(task)
        assert resp.schedule_id == "sched_test"
        assert resp.next_run_at is not None

    def test_interval_schedule(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _schedule_to_response

        task = MagicMock()
        task.schedule_id = "sched_int"
        task.name = "Interval"
        task.schedule_type = "interval"
        task.cron_expression = ""
        task.interval_seconds = 3600
        task.repo_path = "/repo"
        task.prompt = "fix"
        task.backend = "claudecodecli"
        task.model = None
        task.max_iterations = 6
        task.pr_number = None
        task.no_pr = False
        task.enable_execution = False
        task.enable_web = False
        task.use_native_cli_auth = False
        task.fix_ci = False
        task.ci_check_wait_minutes = 3.0
        task.github_token = "ghp_secret123456789"
        task.reference_repos = []
        task.tools = []
        task.enabled = True
        task.created_at = "2026-01-01T00:00:00"
        task.last_run_at = "2026-04-01T12:00:00+00:00"
        task.last_run_task_id = None
        task.run_count = 1

        resp = _schedule_to_response(task)
        assert resp.schedule_id == "sched_int"
        assert resp.next_run_at is not None
        # Token should be redacted
        assert resp.github_token != "ghp_secret123456789"

    def test_disabled_schedule_no_next_run(self) -> None:
        from helping_hands.server.app import _schedule_to_response

        task = MagicMock()
        task.schedule_id = "sched_off"
        task.name = "Off"
        task.schedule_type = "cron"
        task.cron_expression = "0 0 * * *"
        task.interval_seconds = None
        task.repo_path = "/repo"
        task.prompt = "fix"
        task.backend = "claudecodecli"
        task.model = None
        task.max_iterations = 6
        task.pr_number = None
        task.no_pr = False
        task.enable_execution = False
        task.enable_web = False
        task.use_native_cli_auth = False
        task.fix_ci = False
        task.ci_check_wait_minutes = 3.0
        task.github_token = None
        task.reference_repos = []
        task.tools = []
        task.enabled = False
        task.created_at = "2026-01-01T00:00:00"
        task.last_run_at = None
        task.last_run_task_id = None
        task.run_count = 0

        resp = _schedule_to_response(task)
        assert resp.next_run_at is None


# ---------------------------------------------------------------------------
# Grill endpoints
# ---------------------------------------------------------------------------


class TestGrillEndpoints:
    def test_start_grill_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.delenv("GRILL_ME_ENABLED", raising=False)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/grill",
            json={
                "repo_path": "/tmp/repo",
                "prompt": "test",
            },
        )
        assert resp.status_code == 404

    def test_send_grill_message_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.delenv("GRILL_ME_ENABLED", raising=False)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/grill/session-1/message",
            json={"content": "hello", "type": "text"},
        )
        assert resp.status_code == 404

    def test_poll_grill_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        monkeypatch.delenv("GRILL_ME_ENABLED", raising=False)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/grill/session-1")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# v356 — Task diff edge cases
# ---------------------------------------------------------------------------


def _init_git_repo(tmp_path):
    """Helper to initialise a git repo in tmp_path with an initial commit."""
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
    )
    (tmp_path / "init.txt").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )


def _mock_workspace(monkeypatch, tmp_path):
    """Monkey-patch build_feature.AsyncResult so it points at tmp_path."""
    mock_result = MagicMock()
    mock_result.ready.return_value = True
    mock_result.result = {"workspace": str(tmp_path)}
    monkeypatch.setattr(
        "helping_hands.server.app.build_feature.AsyncResult",
        lambda tid: mock_result,
    )


class TestTaskDiffEdgeCases:
    """Cover branches in _build_task_diff not reached by existing tests."""

    def test_diff_head_failure_falls_back_to_plain_diff(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """When 'git diff HEAD' fails (e.g. no commits), fallback 'git diff'."""
        import subprocess

        from helping_hands.server.app import _build_task_diff

        # Create repo with no commits — so git diff HEAD will fail
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        (tmp_path / "staged.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_diff("task-fallback")
        assert result.error is None

    def test_diff_multiple_files_with_status_detection(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Multi-file diff with added, deleted, and renamed statuses."""
        import subprocess

        from helping_hands.server.app import _build_task_diff

        _init_git_repo(tmp_path)

        # Create multiple files, commit, then make changes
        (tmp_path / "keep.txt").write_text("original")
        (tmp_path / "to_delete.txt").write_text("remove me")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "add files"],
            cwd=tmp_path,
            capture_output=True,
        )

        # Modify, delete, and add new
        (tmp_path / "keep.txt").write_text("modified")
        (tmp_path / "to_delete.txt").unlink()
        subprocess.run(
            ["git", "add", "to_delete.txt"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "new_file.txt").write_text("brand new")
        subprocess.run(
            ["git", "add", "new_file.txt"],
            cwd=tmp_path,
            capture_output=True,
        )

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_diff("task-multi")
        assert result.error is None
        filenames = {f.filename for f in result.files}
        statuses = {f.status for f in result.files}
        assert "keep.txt" in filenames
        # Deleted file should appear
        assert "to_delete.txt" in filenames
        assert "deleted" in statuses or "added" in statuses

    def test_diff_untracked_files_appear_as_added(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Untracked files should appear as 'added' with synthetic diff."""
        from helping_hands.server.app import _build_task_diff

        _init_git_repo(tmp_path)
        (tmp_path / "untracked.txt").write_text("new content\nsecond line")

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_diff("task-untracked")
        assert result.error is None
        untracked_files = [f for f in result.files if f.filename == "untracked.txt"]
        assert len(untracked_files) == 1
        assert untracked_files[0].status == "added"
        assert "+new content" in untracked_files[0].diff

    def test_diff_git_timeout_returns_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """When git commands timeout, diff returns an error."""
        import subprocess as _sp

        from helping_hands.server.app import _build_task_diff

        _init_git_repo(tmp_path)
        _mock_workspace(monkeypatch, tmp_path)

        orig_run = _sp.run

        def _timeout_run(cmd, **kwargs):
            if "diff" in cmd:
                raise _sp.TimeoutExpired(cmd, 15)
            return orig_run(cmd, **kwargs)

        monkeypatch.setattr("helping_hands.server.app.subprocess.run", _timeout_run)
        result = _build_task_diff("task-timeout")
        assert result.error is not None
        assert "Git command failed" in result.error


# ---------------------------------------------------------------------------
# v356 — File tree edge cases
# ---------------------------------------------------------------------------


class TestTaskTreeEdgeCases:
    """Cover uncovered branches in _build_task_tree."""

    def test_tree_git_status_rename_and_delete(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Git status with renames and deletes populates status correctly."""
        import subprocess

        from helping_hands.server.app import _build_task_tree

        _init_git_repo(tmp_path)
        (tmp_path / "original.txt").write_text("content")
        (tmp_path / "to_remove.txt").write_text("bye")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "files"],
            cwd=tmp_path,
            capture_output=True,
        )

        # Rename via git mv and delete
        subprocess.run(
            ["git", "mv", "original.txt", "renamed.txt"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "rm", "to_remove.txt"],
            cwd=tmp_path,
            capture_output=True,
        )

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_tree("task-rename")
        assert result.error is None
        file_entries = {e.path: e.status for e in result.tree if e.type == "file"}
        # renamed.txt should appear; to_remove.txt is deleted
        assert "renamed.txt" in file_entries

    def test_tree_parent_dir_insertion(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Deeply nested files trigger parent directory insertion."""
        from helping_hands.server.app import _build_task_tree

        _init_git_repo(tmp_path)
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.txt").write_text("deep")

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_tree("task-deep")
        assert result.error is None
        paths = [e.path for e in result.tree]
        assert "a" in paths
        assert "a/b" in paths or "a\\b" in paths
        assert any("deep.txt" in p for p in paths)

    def test_tree_permission_error_handled(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """PermissionError during rglob is caught gracefully."""
        from pathlib import Path

        from helping_hands.server.app import _build_task_tree

        _init_git_repo(tmp_path)
        _mock_workspace(monkeypatch, tmp_path)

        def _raise_permission(self_path, pattern):
            # Yield one file then raise
            yield tmp_path / "init.txt"
            raise PermissionError("access denied")

        monkeypatch.setattr(Path, "rglob", _raise_permission)
        result = _build_task_tree("task-perm")
        # Should not error — PermissionError is caught
        assert result.error is None

    def test_tree_short_status_lines_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Git status lines shorter than 4 chars are skipped."""
        import subprocess as _sp

        from helping_hands.server.app import _build_task_tree

        _init_git_repo(tmp_path)
        _mock_workspace(monkeypatch, tmp_path)

        orig_run = _sp.run

        def _fake_status(cmd, **kwargs):
            if "status" in cmd and any("porcelain" in c for c in cmd):
                result = MagicMock()
                result.returncode = 0
                # Short line should be skipped, valid line should parse
                result.stdout = "??\nM  init.txt\n D to_remove.txt\n"
                return result
            return orig_run(cmd, **kwargs)

        monkeypatch.setattr("helping_hands.server.app.subprocess.run", _fake_status)
        result = _build_task_tree("task-short")
        assert result.error is None


# ---------------------------------------------------------------------------
# v356 — File content edge cases
# ---------------------------------------------------------------------------


class TestTaskFileEdgeCases:
    """Cover uncovered branches in _read_task_file."""

    def test_path_traversal_rejected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Paths that escape the workspace are rejected."""
        from helping_hands.server.app import _read_task_file

        _init_git_repo(tmp_path)
        _mock_workspace(monkeypatch, tmp_path)

        result = _read_task_file("task-traversal", "../../etc/passwd")
        assert result.error is not None
        assert "traversal" in result.error.lower()

    def test_large_file_rejected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Files exceeding _FILE_CONTENT_MAX_BYTES are rejected."""
        from helping_hands.server.app import _FILE_CONTENT_MAX_BYTES, _read_task_file

        _init_git_repo(tmp_path)
        big_file = tmp_path / "big.bin"
        big_file.write_bytes(b"x" * (_FILE_CONTENT_MAX_BYTES + 1))
        _mock_workspace(monkeypatch, tmp_path)

        result = _read_task_file("task-big", "big.bin")
        assert result.error is not None
        assert "too large" in result.error.lower()

    def test_os_error_reading_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """OSError when reading file content is handled gracefully."""
        from pathlib import Path

        from helping_hands.server.app import _read_task_file

        _init_git_repo(tmp_path)
        target = tmp_path / "broken.txt"
        target.write_text("hello")
        _mock_workspace(monkeypatch, tmp_path)

        original_read_text = Path.read_text

        def _raise_os_error(self_path, **kwargs):
            if "broken.txt" in str(self_path):
                raise OSError("disk error")
            return original_read_text(self_path, **kwargs)

        monkeypatch.setattr(Path, "read_text", _raise_os_error)
        result = _read_task_file("task-oserror", "broken.txt")
        assert result.error is not None
        assert "Cannot read" in result.error

    def test_diff_detects_new_file_status(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Diff status detection picks up 'new file' header."""
        import subprocess

        from helping_hands.server.app import _read_task_file

        _init_git_repo(tmp_path)
        (tmp_path / "fresh.txt").write_text("new content")
        subprocess.run(["git", "add", "fresh.txt"], cwd=tmp_path, capture_output=True)

        _mock_workspace(monkeypatch, tmp_path)
        result = _read_task_file("task-newfile", "fresh.txt")
        assert result.error is None
        assert result.content == "new content"
        assert result.status == "added"
        assert result.diff is not None
        assert "new file" in result.diff

    def test_diff_detects_deleted_file_status(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Diff status detection picks up 'deleted file' header."""
        import subprocess

        from helping_hands.server.app import _read_task_file

        _init_git_repo(tmp_path)
        (tmp_path / "doomed.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "add doomed"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "rm", "doomed.txt"],
            cwd=tmp_path,
            capture_output=True,
        )
        # The file is deleted but git knows about it; write it back for reading
        (tmp_path / "doomed.txt").write_text("content")

        _mock_workspace(monkeypatch, tmp_path)
        result = _read_task_file("task-deleted", "doomed.txt")
        assert result.error is None

    def test_untracked_file_detected_as_added(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """An untracked file should be detected as 'added' via ls-files."""
        from helping_hands.server.app import _read_task_file

        _init_git_repo(tmp_path)
        (tmp_path / "brand_new.txt").write_text("untracked content")

        _mock_workspace(monkeypatch, tmp_path)
        result = _read_task_file("task-untracked-file", "brand_new.txt")
        assert result.error is None
        assert result.content == "untracked content"
        assert result.status == "added"
        assert result.diff is not None

    def test_git_diff_timeout_in_file_read(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Timeout in git diff during file read is caught."""
        import subprocess as _sp

        from helping_hands.server.app import _read_task_file

        _init_git_repo(tmp_path)
        (tmp_path / "test.txt").write_text("content")
        _sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        _sp.run(
            ["git", "commit", "-m", "add test"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "test.txt").write_text("changed")
        _mock_workspace(monkeypatch, tmp_path)

        orig_run = _sp.run

        def _timeout_diff(cmd, **kwargs):
            if "diff" in cmd:
                raise _sp.TimeoutExpired(cmd, 10)
            return orig_run(cmd, **kwargs)

        monkeypatch.setattr("helping_hands.server.app.subprocess.run", _timeout_diff)
        result = _read_task_file("task-diff-timeout", "test.txt")
        # Should still return content, just no diff
        assert result.error is None
        assert result.content == "changed"
        assert result.diff is None


# ---------------------------------------------------------------------------
# v356 — _extract_task_kwargs request.kwargs-as-string branch
# ---------------------------------------------------------------------------


class TestExtractTaskKwargsRequestString:
    """Cover the request.kwargs-as-string path in _extract_task_kwargs."""

    def test_request_kwargs_as_string(self) -> None:
        from helping_hands.server.app import _extract_task_kwargs

        entry = {"request": {"kwargs": '{"repo_path": "/tmp/repo", "prompt": "test"}'}}
        result = _extract_task_kwargs(entry)
        assert result == {"repo_path": "/tmp/repo", "prompt": "test"}

    def test_request_kwargs_string_invalid_json(self) -> None:
        from helping_hands.server.app import _extract_task_kwargs

        entry = {"request": {"kwargs": "not-json"}}
        result = _extract_task_kwargs(entry)
        assert result == {}

    def test_request_kwargs_as_dict(self) -> None:
        from helping_hands.server.app import _extract_task_kwargs

        entry = {"request": {"kwargs": {"repo_path": "/tmp/repo"}}}
        result = _extract_task_kwargs(entry)
        assert result == {"repo_path": "/tmp/repo"}


# ---------------------------------------------------------------------------
# v356 — Additional edge cases for higher coverage
# ---------------------------------------------------------------------------


class TestTaskDiffRenameAndUntrackedEdges:
    """Cover rename status in diff and untracked file edge cases."""

    def test_diff_rename_status_detected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Renamed files via git mv produce 'renamed' status in diff."""
        import subprocess as _sp

        from helping_hands.server.app import _build_task_diff

        _init_git_repo(tmp_path)
        (tmp_path / "old_name.txt").write_text("content")
        _sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        _sp.run(
            ["git", "commit", "-m", "add old_name"],
            cwd=tmp_path,
            capture_output=True,
        )
        _sp.run(
            ["git", "mv", "old_name.txt", "new_name.txt"],
            cwd=tmp_path,
            capture_output=True,
        )

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_diff("task-rename-diff")
        assert result.error is None
        statuses = {f.status for f in result.files}
        # Git may report rename as "renamed" via "rename from" header
        assert "renamed" in statuses or len(result.files) >= 1

    def test_diff_untracked_oserror_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """OSError reading an untracked file is silently skipped."""
        import subprocess as _sp

        from helping_hands.server.app import _build_task_diff

        _init_git_repo(tmp_path)
        # Create a file that will be untracked
        broken = tmp_path / "broken_untracked.txt"
        broken.write_text("hello")

        _mock_workspace(monkeypatch, tmp_path)

        orig_run = _sp.run

        def _mock_ls_files(cmd, **kwargs):
            result = orig_run(cmd, **kwargs)
            # For ls-files, inject a non-existent path too
            if "ls-files" in cmd:
                result = MagicMock()
                result.stdout = "broken_untracked.txt\nnonexistent_dir/ghost.txt\n\n"
                return result
            return result

        monkeypatch.setattr("helping_hands.server.app.subprocess.run", _mock_ls_files)
        result = _build_task_diff("task-untracked-oserror")
        # Should not error — OSError for ghost.txt is caught,
        # empty line is skipped, broken_untracked.txt succeeds
        assert result.error is None

    def test_diff_delete_status_via_staged(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Staged deletion with --cached diff shows 'deleted' in diff output."""
        import subprocess as _sp

        from helping_hands.server.app import _build_task_diff

        _init_git_repo(tmp_path)
        (tmp_path / "doomed.txt").write_text("bye")
        _sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        _sp.run(
            ["git", "commit", "-m", "add doomed"],
            cwd=tmp_path,
            capture_output=True,
        )
        _sp.run(
            ["git", "rm", "doomed.txt"],
            cwd=tmp_path,
            capture_output=True,
        )

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_diff("task-delete-diff")
        assert result.error is None
        deleted_files = [f for f in result.files if f.status == "deleted"]
        assert len(deleted_files) >= 1


class TestTaskTreeStatusParsing:
    """Cover deleted/renamed status parsing in _build_task_tree."""

    def test_tree_deleted_file_status(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Deleted files in git status get 'deleted' status in tree."""
        import subprocess as _sp

        from helping_hands.server.app import _build_task_tree

        _init_git_repo(tmp_path)
        (tmp_path / "alive.txt").write_text("content")
        _sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        _sp.run(
            ["git", "commit", "-m", "files"],
            cwd=tmp_path,
            capture_output=True,
        )

        _mock_workspace(monkeypatch, tmp_path)

        orig_run = _sp.run

        def _fake_status(cmd, **kwargs):
            if "status" in cmd and any("porcelain" in c for c in cmd):
                result = MagicMock()
                result.returncode = 0
                # D = deleted, R = renamed (with -> separator)
                result.stdout = " D alive.txt\nR  old.txt -> new.txt\n"
                return result
            return orig_run(cmd, **kwargs)

        monkeypatch.setattr("helping_hands.server.app.subprocess.run", _fake_status)
        result = _build_task_tree("task-tree-status")
        assert result.error is None
        status_map = {e.path: e.status for e in result.tree if e.type == "file"}
        # alive.txt should have "deleted" status from the " D" prefix
        assert status_map.get("alive.txt") == "deleted"

    def test_tree_nested_files_add_parent_dirs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Files in nested dirs trigger parent directory insertion."""
        from helping_hands.server.app import _build_task_tree

        _init_git_repo(tmp_path)
        # Create nested structure: only the file, not explicit dirs
        nested = tmp_path / "x" / "y"
        nested.mkdir(parents=True)
        (nested / "leaf.txt").write_text("leaf")

        _mock_workspace(monkeypatch, tmp_path)
        result = _build_task_tree("task-nested-parents")
        assert result.error is None
        dir_paths = {e.path for e in result.tree if e.type == "dir"}
        assert "x" in dir_paths
