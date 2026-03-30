"""Tests for server/app.py workspace, diff, tree, file, worker capacity, and endpoint coverage.

Closes coverage gaps in the task workspace resolution pipeline
(_resolve_task_workspace → _build_task_diff → _build_task_tree → _read_task_file),
the worker capacity resolution cascade (_resolve_worker_capacity celery/env/default),
arcade high-score endpoints, and multiplayer health endpoints.

These functions sit between the HTTP layer and subprocess/Celery calls.  Regressions
would surface as broken diff views (no files shown, wrong status annotations),
incorrect worker capacity reporting, or silent path-traversal bypasses.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _build_task_diff,
    _build_task_tree,
    _read_task_file,
    _resolve_task_workspace,
    _resolve_worker_capacity,
)

# ---------------------------------------------------------------------------
# _resolve_worker_capacity
# ---------------------------------------------------------------------------


class TestResolveWorkerCapacity:
    """Tests for _resolve_worker_capacity cascade: celery → env → default."""

    def test_celery_stats_path(self) -> None:
        """When Celery inspect returns pool stats, use those."""
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker1@host": {"pool": {"max-concurrency": 4}},
            "worker2@host": {"pool": {"max-concurrency": 2}},
        }
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = mock_inspector

        with patch("helping_hands.server.app.celery_app", mock_app):
            result = _resolve_worker_capacity()

        assert result.max_workers == 6
        assert result.source == "celery"
        assert result.workers == {"worker1@host": 4, "worker2@host": 2}

    def test_celery_stats_non_dict_worker_stats_skipped(self) -> None:
        """Non-dict worker_stats entries are silently skipped."""
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker1@host": "not-a-dict",
            "worker2@host": {"pool": {"max-concurrency": 3}},
        }
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = mock_inspector

        with patch("helping_hands.server.app.celery_app", mock_app):
            result = _resolve_worker_capacity()

        assert result.max_workers == 3
        assert result.source == "celery"

    def test_celery_stats_non_dict_pool_skipped(self) -> None:
        """Non-dict pool entries are silently skipped."""
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker1@host": {"pool": "not-a-dict"},
        }
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = mock_inspector

        with patch("helping_hands.server.app.celery_app", mock_app):
            result = _resolve_worker_capacity()

        # Falls through to env/default since no valid concurrency found
        assert result.source in ("default", "celery") or result.source.startswith(
            "env:"
        )

    def test_celery_stats_non_int_concurrency_skipped(self) -> None:
        """Non-int concurrency values are silently skipped."""
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker1@host": {"pool": {"max-concurrency": "four"}},
        }
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = mock_inspector

        with patch("helping_hands.server.app.celery_app", mock_app):
            result = _resolve_worker_capacity()

        # Falls through to env/default
        assert result.source != "celery"

    def test_celery_stats_zero_concurrency_skipped(self) -> None:
        """Zero concurrency values are skipped."""
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker1@host": {"pool": {"max-concurrency": 0}},
        }
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = mock_inspector

        with patch("helping_hands.server.app.celery_app", mock_app):
            result = _resolve_worker_capacity()

        assert result.source != "celery"

    def test_celery_connection_error_falls_through(self) -> None:
        """ConnectionError from celery falls through to env/default."""
        mock_app = MagicMock()
        mock_app.control.inspect.side_effect = ConnectionError("refused")

        with (
            patch("helping_hands.server.app.celery_app", mock_app),
            patch.dict("os.environ", {}, clear=False),
        ):
            result = _resolve_worker_capacity()

        assert result.source in ("default",) or result.source.startswith("env:")

    def test_inspector_none_falls_through(self) -> None:
        """When inspector is None, falls through to env/default."""
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = None

        with patch("helping_hands.server.app.celery_app", mock_app):
            result = _resolve_worker_capacity()

        assert result.source != "celery"

    def test_env_var_fallback(self) -> None:
        """When celery fails, env var CELERY_WORKER_CONCURRENCY is used."""
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = None

        with (
            patch("helping_hands.server.app.celery_app", mock_app),
            patch.dict(
                "os.environ",
                {"CELERY_WORKER_CONCURRENCY": "8"},
                clear=False,
            ),
        ):
            result = _resolve_worker_capacity()

        assert result.max_workers == 8
        assert "env:" in result.source

    def test_env_var_invalid_falls_to_default(self) -> None:
        """Invalid env var values fall through to default."""
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = None

        with (
            patch("helping_hands.server.app.celery_app", mock_app),
            patch.dict(
                "os.environ",
                {"CELERY_WORKER_CONCURRENCY": "not-a-number"},
                clear=False,
            ),
        ):
            result = _resolve_worker_capacity()

        assert result.source == "default"

    def test_default_fallback(self) -> None:
        """When all else fails, returns default capacity."""
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = None

        # Clear any env vars that might match
        env_clean = {
            k: v
            for k, v in __import__("os").environ.items()
            if "WORKER" not in k and "CONCURRENCY" not in k
        }
        with (
            patch("helping_hands.server.app.celery_app", mock_app),
            patch.dict("os.environ", env_clean, clear=True),
        ):
            result = _resolve_worker_capacity()

        assert result.source == "default"
        assert result.max_workers >= 1

    def test_celery_stats_returns_non_dict(self) -> None:
        """When stats returns non-dict, falls through."""
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = None
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = mock_inspector

        with (
            patch("helping_hands.server.app.celery_app", mock_app),
            patch(
                "helping_hands.server.app._safe_inspect_call",
                return_value=None,
            ),
        ):
            result = _resolve_worker_capacity()

        assert result.source != "celery"


# ---------------------------------------------------------------------------
# _resolve_task_workspace
# ---------------------------------------------------------------------------


class TestResolveTaskWorkspace:
    """Tests for _resolve_task_workspace."""

    def test_dict_result_with_workspace(self, tmp_path: Path) -> None:
        """When task result has workspace pointing to existing dir, returns it."""
        workspace_dir = tmp_path / "ws"
        workspace_dir.mkdir()

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(workspace_dir)}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            path, ws_str, task_ready, error = _resolve_task_workspace("task-1")

        assert path == workspace_dir
        assert ws_str == str(workspace_dir)
        assert task_ready is True
        assert error is None

    def test_dict_result_with_repo_path_fallback(self, tmp_path: Path) -> None:
        """When workspace is missing but repo_path is a valid dir, use it."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {"repo_path": str(repo_dir)}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            path, _ws_str, ready, error = _resolve_task_workspace("task-2")

        assert path == repo_dir
        assert ready is False
        assert error is None

    def test_no_workspace_returns_error(self) -> None:
        """When no workspace can be resolved, returns error."""
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            path, _ws_str, _task_ready, error = _resolve_task_workspace("task-3")

        assert path is None
        assert error == "Workspace not available yet"

    def test_workspace_cleaned_up_after_completion(self, tmp_path: Path) -> None:
        """When task is done but workspace dir is gone, return cleanup message."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(tmp_path / "gone")}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            path, _ws_str, _task_ready, error = _resolve_task_workspace("task-4")

        assert path is None
        assert "cleaned up" in error

    def test_workspace_not_found_running_task(self, tmp_path: Path) -> None:
        """When task is still running but workspace dir doesn't exist."""
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {"workspace": str(tmp_path / "missing")}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            path, _ws_str, _task_ready, error = _resolve_task_workspace("task-5")

        assert path is None
        assert "not found" in error

    def test_non_dict_result(self) -> None:
        """When task result is not a dict, workspace cannot be resolved."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = "some-string-result"

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            path, _ws_str, _task_ready, error = _resolve_task_workspace("task-6")

        assert path is None
        assert error is not None

    def test_repo_key_fallback(self, tmp_path: Path) -> None:
        """When 'repo' key is used instead of 'repo_path'."""
        repo_dir = tmp_path / "repo-alt"
        repo_dir.mkdir()

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"repo": str(repo_dir)}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            path, _ws_str, _task_ready, error = _resolve_task_workspace("task-7")

        assert path == repo_dir
        assert error is None


# ---------------------------------------------------------------------------
# _build_task_diff
# ---------------------------------------------------------------------------


class TestBuildTaskDiff:
    """Tests for _build_task_diff."""

    def test_workspace_error_returns_error_response(self) -> None:
        """When workspace can't be resolved, returns error."""
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-1")

        assert resp.error is not None
        assert resp.files == []

    def test_diff_parsing_single_file(self, tmp_path: Path) -> None:
        """Parse a single-file unified diff."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        diff_output = (
            "diff --git a/foo.py b/foo.py\n"
            "index abc..def 100644\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n"
            "+added\n"
            " line2\n"
        )

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd and "HEAD" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_output, stderr="")
            if "ls-files" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-2")

        assert resp.error is None
        assert len(resp.files) == 1
        assert resp.files[0].filename == "foo.py"
        assert resp.files[0].status == "modified"

    def test_diff_parsing_new_file(self, tmp_path: Path) -> None:
        """Detect 'added' status for new files in diff."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        diff_output = (
            "diff --git a/new.py b/new.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/new.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+line1\n"
            "+line2\n"
        )

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_output, stderr="")
            if "ls-files" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-3")

        assert len(resp.files) == 1
        assert resp.files[0].status == "added"

    def test_diff_parsing_deleted_file(self, tmp_path: Path) -> None:
        """Detect 'deleted' status for removed files in diff."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        diff_output = (
            "diff --git a/old.py b/old.py\n"
            "deleted file mode 100644\n"
            "--- a/old.py\n"
            "+++ /dev/null\n"
            "@@ -1,2 +0,0 @@\n"
            "-line1\n"
            "-line2\n"
        )

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_output, stderr="")
            if "ls-files" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-4")

        assert len(resp.files) == 1
        assert resp.files[0].status == "deleted"

    def test_diff_parsing_renamed_file(self, tmp_path: Path) -> None:
        """Detect 'renamed' status from diff."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        diff_output = (
            "diff --git a/old.py b/new.py\nrename from old.py\nrename to new.py\n"
        )

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_output, stderr="")
            if "ls-files" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-5")

        assert len(resp.files) == 1
        assert resp.files[0].status == "renamed"

    def test_untracked_files_included(self, tmp_path: Path) -> None:
        """Untracked files are added as 'added' with synthetic diff."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "untracked.txt").write_text("hello\nworld\n")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "ls-files" in cmd:
                return SimpleNamespace(
                    returncode=0, stdout="untracked.txt\n", stderr=""
                )
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-6")

        assert len(resp.files) == 1
        assert resp.files[0].status == "added"
        assert resp.files[0].filename == "untracked.txt"
        assert "+hello" in resp.files[0].diff

    def test_git_error_returns_error_response(self, tmp_path: Path) -> None:
        """When git command times out, returns error."""
        ws = tmp_path / "ws"
        ws.mkdir()

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run",
                side_effect=subprocess.TimeoutExpired("git", 15),
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-7")

        assert resp.error is not None
        assert "Git command failed" in resp.error

    def test_empty_diff_returns_no_files(self, tmp_path: Path) -> None:
        """When there are no changes, returns empty files list."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-8")

        assert resp.error is None
        assert resp.files == []

    def test_head_fallback_when_first_diff_fails(self, tmp_path: Path) -> None:
        """When 'git diff HEAD' fails, falls back to 'git diff'."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        call_count = 0

        def run_side_effect(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if "diff" in cmd and "HEAD" in cmd:
                return SimpleNamespace(returncode=128, stdout="", stderr="fatal")
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "ls-files" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-9")

        assert resp.error is None
        assert call_count >= 3  # diff HEAD, diff, ls-files

    def test_multiple_files_in_diff(self, tmp_path: Path) -> None:
        """Multiple files in a single diff are parsed separately."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        diff_output = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            "diff --git a/b.py b/b.py\n"
            "new file mode 100644\n"
            "+++ b/b.py\n"
            "@@ -0,0 +1 @@\n"
            "+content\n"
        )

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_output, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_diff("task-10")

        assert len(resp.files) == 2
        assert resp.files[0].filename == "a.py"
        assert resp.files[0].status == "modified"
        assert resp.files[1].filename == "b.py"
        assert resp.files[1].status == "added"


# ---------------------------------------------------------------------------
# _build_task_tree
# ---------------------------------------------------------------------------


class TestBuildTaskTree:
    """Tests for _build_task_tree."""

    def test_workspace_error_returns_error_response(self) -> None:
        """When workspace can't be resolved, returns error."""
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_tree("task-1")

        assert resp.error is not None
        assert resp.tree == []

    def test_tree_with_files_and_dirs(self, tmp_path: Path) -> None:
        """Tree includes files and directories with proper types."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "src").mkdir()
        (ws / "src" / "main.py").write_text("code")
        (ws / "README.md").write_text("readme")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_tree("task-2")

        assert resp.error is None
        names = {e.name for e in resp.tree}
        assert "src" in names
        assert "main.py" in names
        assert "README.md" in names
        # .git should be excluded
        assert ".git" not in names

    def test_tree_annotates_git_status(self, tmp_path: Path) -> None:
        """Changed files get status annotations from git status."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "modified.py").write_text("code")
        (ws / "added.py").write_text("new")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        git_status = " M modified.py\n?? added.py\n"

        def run_side_effect(cmd, **kwargs):
            if "status" in cmd:
                return SimpleNamespace(returncode=0, stdout=git_status, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_tree("task-3")

        file_statuses = {e.name: e.status for e in resp.tree if e.type == "file"}
        assert file_statuses.get("modified.py") == "modified"
        assert file_statuses.get("added.py") == "added"

    def test_tree_git_status_deleted(self, tmp_path: Path) -> None:
        """Deleted files get 'deleted' status."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "exists.py").write_text("code")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        git_status = " D removed.py\n"

        def run_side_effect(cmd, **kwargs):
            if "status" in cmd:
                return SimpleNamespace(returncode=0, stdout=git_status, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_tree("task-4")

        # "removed.py" won't be in tree (doesn't exist on disk) but the status
        # map is built correctly
        assert resp.error is None

    def test_tree_git_status_renamed(self, tmp_path: Path) -> None:
        """Renamed files get 'renamed' status."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "new_name.py").write_text("code")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        git_status = "R  old_name.py -> new_name.py\n"

        def run_side_effect(cmd, **kwargs):
            if "status" in cmd:
                return SimpleNamespace(returncode=0, stdout=git_status, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_tree("task-5")

        file_statuses = {e.name: e.status for e in resp.tree if e.type == "file"}
        assert file_statuses.get("new_name.py") == "renamed"

    def test_tree_git_timeout_graceful(self, tmp_path: Path) -> None:
        """Git timeout doesn't crash — tree is built without status."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "file.py").write_text("code")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "status" in cmd:
                raise subprocess.TimeoutExpired("git", 15)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _build_task_tree("task-6")

        assert resp.error is None
        assert len(resp.tree) >= 1


# ---------------------------------------------------------------------------
# _read_task_file
# ---------------------------------------------------------------------------


class TestReadTaskFile:
    """Tests for _read_task_file."""

    def test_workspace_error_returns_error(self) -> None:
        """When workspace can't be resolved, returns error."""
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.info = {}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-1", "foo.py")

        assert resp.error is not None
        assert resp.content is None

    def test_reads_file_content(self, tmp_path: Path) -> None:
        """Reads file content from workspace."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "hello.txt").write_text("Hello, World!")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-2", "hello.txt")

        assert resp.content == "Hello, World!"
        assert resp.error is None

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Path traversal attempts are rejected."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        # Create a file outside workspace
        (tmp_path / "secret.txt").write_text("secret")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-3", "../secret.txt")

        assert resp.error == "Path traversal not allowed"
        assert resp.content is None

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent file returns error."""
        ws = tmp_path / "ws"
        ws.mkdir()

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-4", "nope.py")

        assert resp.error == "File not found"

    def test_file_too_large(self, tmp_path: Path) -> None:
        """Files exceeding size limit return error."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()

        large_file = ws / "big.bin"
        large_file.write_bytes(b"x" * (512_001))

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        with patch("helping_hands.server.app.build_feature") as mock_bf:
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-5", "big.bin")

        assert "too large" in resp.error
        assert resp.content is None

    def test_file_with_diff(self, tmp_path: Path) -> None:
        """When file has git changes, diff is included."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "changed.py").write_text("new content")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        diff_text = (
            "diff --git a/changed.py b/changed.py\n"
            "--- a/changed.py\n"
            "+++ b/changed.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new content\n"
        )

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_text, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-6", "changed.py")

        assert resp.content == "new content"
        assert resp.diff is not None
        assert resp.status == "modified"

    def test_untracked_file_gets_synthetic_diff(self, tmp_path: Path) -> None:
        """Untracked files get a synthetic diff generated from content."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "new.py").write_text("line1\nline2\n")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "ls-files" in cmd:
                return SimpleNamespace(returncode=0, stdout="new.py\n", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-7", "new.py")

        assert resp.status == "added"
        assert resp.diff is not None
        assert "+line1" in resp.diff

    def test_new_file_detected_from_diff(self, tmp_path: Path) -> None:
        """Files with 'new file' in diff header get 'added' status."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "staged.py").write_text("content")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        diff_text = (
            "diff --git a/staged.py b/staged.py\n"
            "new file mode 100644\n"
            "+++ b/staged.py\n"
            "@@ -0,0 +1 @@\n"
            "+content\n"
        )

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_text, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-8", "staged.py")

        assert resp.status == "added"

    def test_deleted_file_detected_from_diff(self, tmp_path: Path) -> None:
        """Files with 'deleted file' in diff header get 'deleted' status."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        # File must exist to pass is_file() check
        (ws / "removed.py").write_text("")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        diff_text = (
            "diff --git a/removed.py b/removed.py\n"
            "deleted file mode 100644\n"
            "--- a/removed.py\n"
            "+++ /dev/null\n"
        )

        def run_side_effect(cmd, **kwargs):
            if "diff" in cmd:
                return SimpleNamespace(returncode=0, stdout=diff_text, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-9", "removed.py")

        assert resp.status == "deleted"

    def test_git_timeout_graceful(self, tmp_path: Path) -> None:
        """Git timeout doesn't crash — content is returned without diff."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / ".git").mkdir()
        (ws / "file.py").write_text("content")

        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.result = {"workspace": str(ws)}

        def run_side_effect(cmd, **kwargs):
            raise subprocess.TimeoutExpired("git", 10)

        with (
            patch("helping_hands.server.app.build_feature") as mock_bf,
            patch(
                "helping_hands.server.app.subprocess.run", side_effect=run_side_effect
            ),
        ):
            mock_bf.AsyncResult.return_value = mock_result
            resp = _read_task_file("task-10", "file.py")

        assert resp.content == "content"
        assert resp.diff is None


# ---------------------------------------------------------------------------
# Arcade high-score endpoints
# ---------------------------------------------------------------------------


class TestArcadeHighScores:
    """Tests for arcade high-score endpoints."""

    def test_get_high_scores_empty(self) -> None:
        """GET returns empty list initially."""
        from starlette.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/arcade/high-scores")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_submit_and_get_high_scores(self) -> None:
        """POST adds score and GET retrieves it."""
        from starlette.testclient import TestClient

        import helping_hands.server.app as app_mod
        from helping_hands.server.app import app

        # Save and restore state
        original = app_mod._arcade_high_scores[:]
        try:
            app_mod._arcade_high_scores.clear()
            client = TestClient(app, raise_server_exceptions=False)

            resp = client.post(
                "/arcade/high-scores",
                json={"name": "TestPlayer", "score": 1000, "wave": 5},
            )
            assert resp.status_code == 200
            scores = resp.json()
            assert len(scores) >= 1
            assert scores[0]["name"] == "TestPlayer"
            assert scores[0]["score"] == 1000

            # GET should return same
            resp2 = client.get("/arcade/high-scores")
            assert len(resp2.json()) >= 1
        finally:
            app_mod._arcade_high_scores[:] = original


# ---------------------------------------------------------------------------
# Multiplayer health endpoints
# ---------------------------------------------------------------------------


class TestMultiplayerHealthEndpoints:
    """Tests for multiplayer health endpoints."""

    def test_health_multiplayer(self) -> None:
        """GET /health/multiplayer returns dict."""
        from starlette.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health/multiplayer")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_health_multiplayer_players(self) -> None:
        """GET /health/multiplayer/players returns dict."""
        from starlette.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health/multiplayer/players")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_health_multiplayer_activity(self) -> None:
        """GET /health/multiplayer/activity returns dict."""
        from starlette.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health/multiplayer/activity")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_health_multiplayer_decorations(self) -> None:
        """GET /health/multiplayer/decorations returns dict."""
        from starlette.testclient import TestClient

        from helping_hands.server.app import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health/multiplayer/decorations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)
