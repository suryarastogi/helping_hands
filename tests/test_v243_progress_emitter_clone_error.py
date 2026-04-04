"""Tests for v243: _ProgressEmitter DRY refactor and DEFAULT_CLONE_ERROR_MSG.

_ProgressEmitter.emit() is the single update path for Celery task progress;
if it stops delegating to _update_progress correctly, partial progress updates
get dropped and the UI shows stale or missing status information.

The sticky-vs-non-sticky field distinction is important: sticky fields (like
the error message) must survive subsequent emit() calls while non-sticky fields
(like the current step) may be overridden. Reversing this logic would cause
error messages to be overwritten mid-run.

DEFAULT_CLONE_ERROR_MSG is the fallback shown when git clone exits non-zero
with no stderr. If it drifts between the server and the celery_app modules,
users see different error text depending on which code path ran.
"""

from __future__ import annotations

import ast
import inspect
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.github_url import (
    DEFAULT_CLONE_ERROR_MSG,
    __all__ as github_url_all,
)


class TestDefaultCloneErrorMsg:
    """Tests for the DEFAULT_CLONE_ERROR_MSG constant."""

    def test_value(self) -> None:
        assert DEFAULT_CLONE_ERROR_MSG == "unknown git clone error"

    def test_is_string(self) -> None:
        assert isinstance(DEFAULT_CLONE_ERROR_MSG, str)

    def test_non_empty(self) -> None:
        assert DEFAULT_CLONE_ERROR_MSG.strip()

    def test_in_all(self) -> None:
        assert "DEFAULT_CLONE_ERROR_MSG" in github_url_all


class TestCloneErrorMsgUsedInCli:
    """Verify cli/main.py uses the constant instead of a bare string."""

    def test_cli_main_uses_constant(self) -> None:
        from helping_hands.cli import main as cli_main

        src = inspect.getsource(cli_main)
        tree = ast.parse(src)
        # Should not contain the bare string "unknown git clone error"
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and node.value == "unknown git clone error"
            ):
                pytest.fail(
                    "cli/main.py still contains bare 'unknown git clone error' string"
                )


class TestCloneErrorMsgUsedInCelery:
    """Verify celery_app.py uses the constant instead of bare strings."""

    def test_celery_app_uses_constant(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server import celery_app

        src = inspect.getsource(celery_app)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in (
                "unknown git clone error",
                "unknown error",
            ):
                pytest.fail(f"celery_app.py still contains bare {node.value!r} string")


# ---------------------------------------------------------------------------
# _ProgressEmitter
# ---------------------------------------------------------------------------

pytest.importorskip("celery")

from helping_hands.server.celery_app import (  # noqa: E402
    _ProgressEmitter,
)


class TestProgressEmitter:
    """Tests for _ProgressEmitter class."""

    def _make_emitter(self, **kwargs):
        """Create a _ProgressEmitter with sensible defaults."""
        defaults = {
            "task_id": "test-task-123",
            "updates": [],
            "prompt": "test prompt",
            "pr_number": None,
            "backend": "codexcli",
            "runtime_backend": "codexcli",
            "repo_path": "/tmp/repo",
            "model": "gpt-4",
            "max_iterations": 6,
            "no_pr": False,
            "enable_execution": False,
            "enable_web": False,
            "use_native_cli_auth": False,
            "tools": ("filesystem",),
            "fix_ci": False,
            "fix_conflicts": False,
            "master_rebase": False,
            "ci_check_wait_minutes": 3.0,
            "reference_repos": None,
            "workspace": None,
            "started_at": "2026-03-16T00:00:00",
        }
        defaults.update(kwargs)
        task = MagicMock()
        return _ProgressEmitter(task, **defaults), task

    def test_emit_calls_update_progress(self) -> None:
        emitter, _task = self._make_emitter()
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("starting")
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args
            assert call_kwargs.kwargs["stage"] == "starting"
            assert call_kwargs.kwargs["task_id"] == "test-task-123"

    def test_emit_running_stage(self) -> None:
        emitter, _task = self._make_emitter()
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("running")
            assert mock_update.call_args.kwargs["stage"] == "running"

    def test_emit_with_model_override(self) -> None:
        emitter, _task = self._make_emitter(model="gpt-4")
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("running", model="claude-3")
            assert mock_update.call_args.kwargs["model"] == "claude-3"

    def test_emit_with_workspace_override(self) -> None:
        emitter, _task = self._make_emitter(workspace=None)
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("running", workspace="/tmp/workspace")
            assert mock_update.call_args.kwargs["workspace"] == "/tmp/workspace"

    def test_emit_preserves_defaults_without_overrides(self) -> None:
        emitter, _task = self._make_emitter(
            backend="claudecodecli",
            model="claude-3",
            max_iterations=10,
        )
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("running")
            kw = mock_update.call_args.kwargs
            assert kw["backend"] == "claudecodecli"
            assert kw["model"] == "claude-3"
            assert kw["max_iterations"] == 10

    def test_emit_forwards_task_object(self) -> None:
        emitter, task = self._make_emitter()
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("starting")
            assert mock_update.call_args.args[0] is task

    def test_emit_forwards_all_kwargs(self) -> None:
        updates = ["line1"]
        emitter, _task = self._make_emitter(
            task_id="tid",
            updates=updates,
            prompt="p",
            pr_number=42,
            backend="b",
            runtime_backend="rb",
            repo_path="/r",
            model="m",
            max_iterations=3,
            no_pr=True,
            enable_execution=True,
            enable_web=True,
            use_native_cli_auth=True,
            tools=("a", "b"),
            fix_ci=True,
            ci_check_wait_minutes=5.0,
            reference_repos=["ref/repo"],
            workspace="/ws",
            started_at="ts",
        )
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("starting")
            kw = mock_update.call_args.kwargs
            assert kw["task_id"] == "tid"
            assert kw["updates"] is updates
            assert kw["prompt"] == "p"
            assert kw["pr_number"] == 42
            assert kw["backend"] == "b"
            assert kw["runtime_backend"] == "rb"
            assert kw["repo_path"] == "/r"
            assert kw["model"] == "m"
            assert kw["max_iterations"] == 3
            assert kw["no_pr"] is True
            assert kw["enable_execution"] is True
            assert kw["enable_web"] is True
            assert kw["use_native_cli_auth"] is True
            assert kw["tools"] == ("a", "b")
            assert kw["fix_ci"] is True
            assert kw["ci_check_wait_minutes"] == 5.0
            assert kw["reference_repos"] == ["ref/repo"]
            assert kw["workspace"] == "/ws"
            assert kw["started_at"] == "ts"

    def test_emit_multiple_overrides(self) -> None:
        emitter, _task = self._make_emitter()
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("running", model="new-model", workspace="/new/ws")
            kw = mock_update.call_args.kwargs
            assert kw["model"] == "new-model"
            assert kw["workspace"] == "/new/ws"
            assert kw["stage"] == "running"

    def test_emit_sticky_fields_persist(self) -> None:
        """Sticky fields (model, workspace) persist across emit() calls."""
        emitter, _task = self._make_emitter(model="original")
        with patch("helping_hands.server.celery_app._update_progress"):
            emitter.emit("running", model="overridden")
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("running")
            assert mock_update.call_args.kwargs["model"] == "overridden"

    def test_emit_non_sticky_fields_do_not_persist(self) -> None:
        """Non-sticky fields are transient and revert to defaults."""
        emitter, _task = self._make_emitter(max_iterations=6)
        with patch("helping_hands.server.celery_app._update_progress"):
            emitter.emit("running", max_iterations=99)
        with patch("helping_hands.server.celery_app._update_progress") as mock_update:
            emitter.emit("running")
            assert mock_update.call_args.kwargs["max_iterations"] == 6

    def test_has_docstring(self) -> None:
        assert _ProgressEmitter.__doc__
        assert "progress" in _ProgressEmitter.__doc__.lower()

    def test_emit_has_docstring(self) -> None:
        assert _ProgressEmitter.emit.__doc__
        assert "stage" in _ProgressEmitter.emit.__doc__.lower()


# ---------------------------------------------------------------------------
# _collect_stream accepts emitter
# ---------------------------------------------------------------------------


class TestCollectStreamEmitter:
    """Verify _collect_stream uses emitter parameter."""

    def test_collect_stream_signature_has_emitter(self) -> None:
        from helping_hands.server.celery_app import _collect_stream

        sig = inspect.signature(_collect_stream)
        assert "emitter" in sig.parameters

    def test_collect_stream_signature_no_task(self) -> None:
        """_collect_stream should no longer accept individual kwargs like task."""
        from helping_hands.server.celery_app import _collect_stream

        sig = inspect.signature(_collect_stream)
        # These were the old parameters that should be removed
        for old_param in [
            "task",
            "task_id",
            "backend",
            "runtime_backend",
            "repo_path",
            "model",
            "max_iterations",
            "no_pr",
            "enable_execution",
            "enable_web",
            "use_native_cli_auth",
            "tools",
            "fix_ci",
            "ci_check_wait_minutes",
            "workspace",
            "started_at",
        ]:
            assert old_param not in sig.parameters, (
                f"_collect_stream still has old parameter {old_param!r}"
            )

    def test_collect_stream_has_docstring(self) -> None:
        from helping_hands.server.celery_app import _collect_stream

        assert _collect_stream.__doc__
        assert "emitter" in _collect_stream.__doc__.lower()
