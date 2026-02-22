"""Tests for helping_hands.server.mcp_server."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.server.mcp_server import (
    _indexed_repos,
    get_config,
    get_task_status,
    index_repo,
    list_indexed_repos,
    mkdir,
    path_exists,
    read_file,
    write_file,
)

# ---------------------------------------------------------------------------
# index_repo
# ---------------------------------------------------------------------------


class TestIndexRepo:
    def test_indexes_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")

        result = index_repo(str(tmp_path))

        assert result["file_count"] == 2
        assert "a.py" in result["files"]
        assert "b.py" in result["files"]
        assert result["root"] == str(tmp_path.resolve())

    def test_stores_in_cache(self, tmp_path: Path) -> None:
        (tmp_path / "c.py").write_text("")
        _indexed_repos.clear()

        index_repo(str(tmp_path))

        assert str(tmp_path.resolve()) in _indexed_repos

    def test_raises_on_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            index_repo(str(tmp_path / "nonexistent"))


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


class TestReadFile:
    def test_reads_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("hello world")

        content = read_file(str(tmp_path), "hello.txt")
        assert content == "hello world"

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_file(str(tmp_path), "nope.txt")

    def test_rejects_path_escape(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            read_file(str(tmp_path), "../outside.txt")

    def test_respects_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("abcdef")
        content = read_file(str(tmp_path), "hello.txt", max_chars=3)
        assert content == "abc"


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


class TestWriteFile:
    def test_writes_file(self, tmp_path: Path) -> None:
        result = write_file(str(tmp_path), "nested/hello.txt", "hello world")
        assert result["path"] == "nested/hello.txt"
        assert result["bytes"] == len(b"hello world")
        assert (tmp_path / "nested" / "hello.txt").read_text(encoding="utf-8") == (
            "hello world"
        )

    def test_rejects_invalid_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            write_file(str(tmp_path), "../outside.txt", "x")


# ---------------------------------------------------------------------------
# mkdir
# ---------------------------------------------------------------------------


class TestMkdir:
    def test_creates_directory(self, tmp_path: Path) -> None:
        result = mkdir(str(tmp_path), "a/b/c")
        assert result["path"] == "a/b/c"
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_rejects_invalid_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            mkdir(str(tmp_path), "../outside")


# ---------------------------------------------------------------------------
# path_exists
# ---------------------------------------------------------------------------


class TestPathExists:
    def test_true_for_existing_path(self, tmp_path: Path) -> None:
        (tmp_path / "exists.txt").write_text("x")
        assert path_exists(str(tmp_path), "exists.txt") is True

    def test_false_for_missing_path(self, tmp_path: Path) -> None:
        assert path_exists(str(tmp_path), "missing.txt") is False

    def test_false_for_invalid_relative_path(self, tmp_path: Path) -> None:
        assert path_exists(str(tmp_path), "../outside.txt") is False


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------


class TestGetConfig:
    def test_returns_defaults(self) -> None:
        result = get_config()
        assert result["model"] == "default"
        assert result["verbose"] is False

    def test_picks_up_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "gpt-test")
        result = get_config()
        assert result["model"] == "gpt-test"


# ---------------------------------------------------------------------------
# build_feature (enqueues via Celery — mock it)
# ---------------------------------------------------------------------------


def _mock_celery_module() -> MagicMock:
    """Create a mock that stands in for helping_hands.server.celery_app."""
    mock_mod = MagicMock()
    return mock_mod


class TestBuildFeature:
    def test_enqueues_task(self) -> None:
        mock_mod = _mock_celery_module()
        fake_task = MagicMock()
        fake_task.id = "task-abc-123"
        mock_mod.build_feature.delay.return_value = fake_task

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature("/tmp/repo", "add tests")

        assert result["task_id"] == "task-abc-123"
        assert result["status"] == "queued"
        assert result["backend"] == "e2e"


# ---------------------------------------------------------------------------
# get_task_status (reads Celery result — mock it)
# ---------------------------------------------------------------------------


class TestGetTaskStatus:
    def test_pending_task(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "PENDING"
        fake_result.ready.return_value = False
        fake_result.info = None
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "PENDING"
        assert result["result"] is None

    def test_progress_task_returns_update_meta(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "PROGRESS"
        fake_result.ready.return_value = False
        fake_result.info = {"stage": "running", "updates": ["step 1"]}
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "PROGRESS"
        assert result["result"] == {"stage": "running", "updates": ["step 1"]}

    def test_completed_task(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "SUCCESS"
        fake_result.ready.return_value = True
        fake_result.result = {"greeting": "done"}
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "SUCCESS"
        assert result["result"] == {"greeting": "done"}

    def test_failed_task_normalizes_exception_result(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "FAILURE"
        fake_result.ready.return_value = True
        fake_result.result = RuntimeError("boom")
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "FAILURE"
        assert result["result"] == {
            "error": "boom",
            "error_type": "RuntimeError",
            "status": "FAILURE",
        }


# ---------------------------------------------------------------------------
# list_indexed_repos (resource)
# ---------------------------------------------------------------------------


class TestListIndexedRepos:
    def test_empty(self) -> None:
        _indexed_repos.clear()
        text = list_indexed_repos()
        assert "No repositories" in text

    def test_with_repos(self, tmp_path: Path) -> None:
        _indexed_repos.clear()
        (tmp_path / "f.py").write_text("")
        index_repo(str(tmp_path))

        text = list_indexed_repos()
        assert str(tmp_path.resolve()) in text
        assert "1 files" in text
