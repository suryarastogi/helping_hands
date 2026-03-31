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
