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
    read_file,
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


# ---------------------------------------------------------------------------
# get_task_status (reads Celery result — mock it)
# ---------------------------------------------------------------------------


class TestGetTaskStatus:
    def test_pending_task(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "PENDING"
        fake_result.ready.return_value = False
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "PENDING"
        assert result["result"] is None

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
