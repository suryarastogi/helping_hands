"""Unit tests for ``server.task_runs``.

Coverage spans the pure git-diff/tree compute helpers (against a tmp_path repo)
and the snapshot writer/reader paths with psycopg2 + redis mocked, so the suite
runs without a live DB or Redis.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from helping_hands.server import task_runs

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestSafeStr:
    def test_strips_whitespace(self) -> None:
        assert task_runs._safe_str("  foo  ") == "foo"

    def test_none_returns_none(self) -> None:
        assert task_runs._safe_str(None) is None

    def test_empty_returns_none(self) -> None:
        assert task_runs._safe_str("   ") is None

    def test_int_coerced(self) -> None:
        assert task_runs._safe_str(42) == "42"


class TestToIso:
    def test_none(self) -> None:
        assert task_runs._to_iso(None) is None

    def test_datetime_uses_isoformat(self) -> None:
        from datetime import datetime

        dt = datetime(2026, 5, 1, 12, 0, 0)
        assert task_runs._to_iso(dt) == "2026-05-01T12:00:00"

    def test_string_passthrough(self) -> None:
        assert task_runs._to_iso("2026-05-01") == "2026-05-01"


# ---------------------------------------------------------------------------
# compute_diff_files / compute_tree_entries (real git repo on tmp_path)
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "PATH": "/usr/bin:/bin",
        },
    )


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """A git repo with one committed file and one staged modification."""
    _git("init", "-q", cwd=tmp_path)
    (tmp_path / "a.txt").write_text("hello\n")
    _git("add", "a.txt", cwd=tmp_path)
    _git("commit", "-q", "-m", "init", cwd=tmp_path)
    return tmp_path


class TestComputeDiffFiles:
    def test_modified_file(self, git_repo: Path) -> None:
        (git_repo / "a.txt").write_text("hello\nworld\n")
        files = task_runs.compute_diff_files(git_repo)
        assert len(files) == 1
        entry = files[0]
        assert entry["filename"].endswith("a.txt")
        assert entry["status"] == "modified"
        assert "+world" in entry["diff"]

    def test_added_untracked_file(self, git_repo: Path) -> None:
        (git_repo / "b.txt").write_text("brand new\n")
        files = task_runs.compute_diff_files(git_repo)
        # Should include synthesized diff for untracked b.txt as "added".
        added = [f for f in files if f["filename"] == "b.txt"]
        assert len(added) == 1
        assert added[0]["status"] == "added"
        assert "+brand new" in added[0]["diff"]

    def test_no_changes_returns_empty(self, git_repo: Path) -> None:
        assert task_runs.compute_diff_files(git_repo) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path) -> None:
        # git diff in a non-repo dir errors out; helper should swallow.
        bogus = tmp_path / "does-not-exist"
        assert task_runs.compute_diff_files(bogus) == []


class TestComputeTreeEntries:
    def test_includes_files_and_dirs(self, git_repo: Path) -> None:
        (git_repo / "sub").mkdir()
        (git_repo / "sub" / "c.txt").write_text("nested\n")
        entries = task_runs.compute_tree_entries(git_repo)
        paths = {e["path"] for e in entries}
        assert "a.txt" in paths
        assert "sub" in paths
        assert "sub/c.txt" in paths

    def test_skips_git_internals(self, git_repo: Path) -> None:
        entries = task_runs.compute_tree_entries(git_repo)
        for entry in entries:
            assert not entry["path"].startswith(".git")

    def test_marks_modified_status(self, git_repo: Path) -> None:
        (git_repo / "a.txt").write_text("changed\n")
        entries = task_runs.compute_tree_entries(git_repo)
        a = next(e for e in entries if e["path"] == "a.txt")
        assert a["status"] == "modified"


# ---------------------------------------------------------------------------
# snapshot_task_run / read_task_run with mocked psycopg2 + redis
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []
        self._rows = rows or []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> Any:
        return self._rows.pop(0) if self._rows else None


class _FakeConn:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.cursor_obj = _FakeCursor(rows)
        self.committed = False
        self.closed = False

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def fake_redis() -> MagicMock:
    """A mock that patches the module-level redis client used for cache reads/writes."""
    client = MagicMock()
    client.get.return_value = None
    return client


class TestSnapshotTaskRun:
    def test_writes_db_and_cache_on_success(
        self,
        git_repo: Path,
        fake_redis: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/test")
        fake_conn = _FakeConn()
        monkeypatch.setattr(task_runs, "_connect", lambda: fake_conn)
        monkeypatch.setattr(task_runs, "_redis_client", lambda: fake_redis)

        ok = task_runs.snapshot_task_run(
            task_id="abc-123",
            status="success",
            params={"repo_path": "owner/repo", "backend": "claude"},
            output={"status": "ok", "updates": ["x", "y"]},
            workspace_path=git_repo,
            error=None,
            finished_at="2026-05-01T00:00:00Z",
        )

        assert ok is True
        assert fake_conn.committed
        # First execute call should be the upsert.
        assert any(
            "INSERT INTO task_runs" in sql for sql, _ in fake_conn.cursor_obj.executed
        )
        # Cache write should occur with the right key and TTL.
        fake_redis.set.assert_called_once()
        args, kwargs = fake_redis.set.call_args
        assert args[0] == "task_run:abc-123"
        assert kwargs["ex"] == 24 * 60 * 60
        # Body should be JSON.
        json.loads(args[1])

    def test_no_database_url_skips_silently(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        ok = task_runs.snapshot_task_run(
            task_id="abc-123",
            status="success",
            params={},
            output={},
            workspace_path=git_repo,
        )
        assert ok is False

    def test_empty_task_id_returns_false(self) -> None:
        assert (
            task_runs.snapshot_task_run(
                task_id="",
                status="success",
                params={},
                output={},
                workspace_path=None,
            )
            is False
        )

    def test_does_not_persist_github_token(
        self,
        git_repo: Path,
        fake_redis: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Even if a caller foolishly leaks the token into params, snapshot
        # serializes whatever it's given. The defense lives in celery_app's
        # *_snapshot_params* construction, which omits github_token. This
        # test just asserts the writer doesn't add extra fields.
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/test")
        fake_conn = _FakeConn()
        monkeypatch.setattr(task_runs, "_connect", lambda: fake_conn)
        monkeypatch.setattr(task_runs, "_redis_client", lambda: fake_redis)

        task_runs.snapshot_task_run(
            task_id="t1",
            status="success",
            params={"backend": "claude"},
            output={},
            workspace_path=git_repo,
        )
        # Pull serialized params from the upsert call; assert no surprise keys.
        upsert_call = next(
            params
            for sql, params in fake_conn.cursor_obj.executed
            if "INSERT INTO task_runs" in sql
        )
        assert upsert_call is not None
        params_json = upsert_call[6]  # 7th column = params
        loaded = json.loads(params_json)
        assert "github_token" not in loaded


class TestReadTaskRun:
    def test_cache_hit_short_circuits_db(
        self, fake_redis: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cached = {"uuid": "abc", "status": "success", "params": {}, "output": {}}
        fake_redis.get.return_value = json.dumps(cached)
        monkeypatch.setattr(task_runs, "_redis_client", lambda: fake_redis)

        # _connect should NEVER be called on cache hit.
        def boom() -> None:
            raise AssertionError("DB should not be touched on cache hit")

        monkeypatch.setattr(task_runs, "_connect", boom)
        result = task_runs.read_task_run("abc")
        assert result == cached

    def test_cache_miss_falls_to_db(
        self,
        fake_redis: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_redis.get.return_value = None
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/test")
        # Row shape mirrors the SELECT column order in _TASK_RUNS_SELECT.
        row = (
            "abc",
            "success",
            None,  # created_at
            None,  # finished_at
            "owner/repo",
            "claude",
            "claude-sonnet-4-5",
            {"prompt": "hi"},
            {"status": "ok", "updates": []},
            [{"filename": "a.txt", "status": "modified", "diff": "..."}],
            [{"path": "a.txt", "name": "a.txt", "type": "file", "status": "modified"}],
            None,
        )
        fake_conn = _FakeConn(rows=[row])
        monkeypatch.setattr(task_runs, "_connect", lambda: fake_conn)
        monkeypatch.setattr(task_runs, "_redis_client", lambda: fake_redis)

        result = task_runs.read_task_run("abc")
        assert result is not None
        assert result["uuid"] == "abc"
        assert result["status"] == "success"
        assert result["repo_path"] == "owner/repo"
        assert result["diff_files"][0]["filename"] == "a.txt"
        # On miss-then-fetch, the cache should be populated.
        fake_redis.set.assert_called_once()

    def test_missing_row_returns_none(
        self,
        fake_redis: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_redis.get.return_value = None
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/test")
        fake_conn = _FakeConn(rows=[])
        monkeypatch.setattr(task_runs, "_connect", lambda: fake_conn)
        monkeypatch.setattr(task_runs, "_redis_client", lambda: fake_redis)

        assert task_runs.read_task_run("nope") is None

    def test_empty_task_id(self) -> None:
        assert task_runs.read_task_run("") is None


class TestInitSchema:
    def test_no_database_url_is_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Should not raise; should not call _connect.
        called = {"connect": False}

        def fake_connect() -> Any:
            called["connect"] = True
            raise AssertionError("should not connect")

        monkeypatch.setattr(task_runs, "_connect", fake_connect)
        task_runs.init_task_runs_schema()
        assert called["connect"] is False

    def test_runs_ddl_when_db_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/test")
        fake_conn = _FakeConn()
        monkeypatch.setattr(task_runs, "_connect", lambda: fake_conn)
        task_runs.init_task_runs_schema()
        assert fake_conn.committed
        assert any(
            "CREATE TABLE IF NOT EXISTS task_runs" in sql
            for sql, _ in fake_conn.cursor_obj.executed
        )

    def test_connect_failure_is_swallowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import psycopg2

        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/test")

        def boom() -> Any:
            raise psycopg2.OperationalError("simulated")

        monkeypatch.setattr(task_runs, "_connect", boom)
        # Must not raise.
        task_runs.init_task_runs_schema()


# ---------------------------------------------------------------------------
# Endpoint snapshot fallback (server.app)
# ---------------------------------------------------------------------------


class TestEndpointFallback:
    def test_diff_falls_back_to_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server import app as app_mod

        snapshot = {
            "uuid": "abc",
            "status": "success",
            "diff_files": [
                {"filename": "a.txt", "status": "modified", "diff": "diff body"},
            ],
            "tree_entries": [],
        }

        def fake_build_diff(task_id: str) -> Any:
            return app_mod.TaskDiffResponse(
                task_id=task_id,
                workspace="/tmp/gone",
                error="Workspace was cleaned up after task completed",
            )

        monkeypatch.setattr(app_mod, "_build_task_diff", fake_build_diff)
        monkeypatch.setattr(app_mod, "read_task_run", lambda _id: snapshot)

        result = app_mod.get_task_diff("abc")
        assert result.from_snapshot is True
        assert len(result.files) == 1
        assert result.files[0].filename == "a.txt"

    def test_diff_no_snapshot_returns_live_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server import app as app_mod

        def fake_build_diff(task_id: str) -> Any:
            return app_mod.TaskDiffResponse(
                task_id=task_id,
                workspace=None,
                error="Workspace not available yet",
            )

        monkeypatch.setattr(app_mod, "_build_task_diff", fake_build_diff)
        monkeypatch.setattr(app_mod, "read_task_run", lambda _id: None)

        result = app_mod.get_task_diff("abc")
        assert result.from_snapshot is False
        assert result.error == "Workspace not available yet"

    def test_diff_live_success_skips_snapshot(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server import app as app_mod

        live = app_mod.TaskDiffResponse(
            task_id="abc",
            workspace="/tmp/live",
            files=[
                app_mod.TaskDiffFile(
                    filename="live.txt", status="modified", diff="..."
                ),
            ],
        )
        monkeypatch.setattr(app_mod, "_build_task_diff", lambda _id: live)

        # Snapshot reader should not be called when live succeeds.
        def boom(_id: str) -> Any:
            raise AssertionError("read_task_run called even though live had data")

        monkeypatch.setattr(app_mod, "read_task_run", boom)
        result = app_mod.get_task_diff("abc")
        assert result.from_snapshot is False
        assert result.files[0].filename == "live.txt"

    def test_tree_falls_back_to_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server import app as app_mod

        snapshot = {
            "tree_entries": [
                {
                    "path": "a.txt",
                    "name": "a.txt",
                    "type": "file",
                    "status": "modified",
                },
            ],
        }

        def fake_build_tree(task_id: str) -> Any:
            return app_mod.TaskFileTreeResponse(
                task_id=task_id,
                workspace="/tmp/gone",
                error="Workspace was cleaned up after task completed",
            )

        monkeypatch.setattr(app_mod, "_build_task_tree", fake_build_tree)
        monkeypatch.setattr(app_mod, "read_task_run", lambda _id: snapshot)

        result = app_mod.get_task_tree("abc")
        assert result.from_snapshot is True
        assert len(result.tree) == 1
        assert result.tree[0].path == "a.txt"

    def test_status_falls_back_when_pending_and_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server import app as app_mod

        # Mock AsyncResult to return PENDING with no info.
        fake_async = MagicMock()
        fake_async.status = "PENDING"
        fake_async.info = None
        fake_async.result = None
        fake_async.ready.return_value = False

        with patch.object(
            app_mod.build_feature, "AsyncResult", return_value=fake_async
        ):
            monkeypatch.setattr(
                app_mod,
                "read_task_run",
                lambda _id: {
                    "uuid": "abc",
                    "status": "success",
                    "output": {"status": "ok", "updates": []},
                },
            )
            result = app_mod._build_task_status("abc")
            assert result.from_snapshot is True
            assert result.status == "SUCCESS"

    def test_status_does_not_fall_back_when_live_data_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server import app as app_mod

        fake_async = MagicMock()
        fake_async.status = "STARTED"
        fake_async.info = {"updates": ["live"]}
        fake_async.result = None
        fake_async.ready.return_value = False

        with patch.object(
            app_mod.build_feature, "AsyncResult", return_value=fake_async
        ):

            def boom(_id: str) -> Any:
                raise AssertionError("read_task_run called for live STARTED task")

            monkeypatch.setattr(app_mod, "read_task_run", boom)
            result = app_mod._build_task_status("abc")
            assert result.from_snapshot is False
            assert result.status == "STARTED"
