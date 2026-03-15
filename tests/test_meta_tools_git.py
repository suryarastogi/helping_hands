"""Tests for helping_hands.lib.meta.tools.git."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from helping_hands.lib.meta.tools import git as git_tools


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo for testing."""
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    (tmp_path / "hello.py").write_text("print('hello')\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path


class TestGitStatus:
    def test_clean_repo(self, git_repo: Path) -> None:
        result = git_tools.git_status(git_repo)
        assert result.success
        assert result.stdout.strip() == ""

    def test_modified_file(self, git_repo: Path) -> None:
        (git_repo / "hello.py").write_text("print('modified')\n")
        result = git_tools.git_status(git_repo)
        assert result.success
        assert "hello.py" in result.stdout


class TestGitDiff:
    def test_no_changes(self, git_repo: Path) -> None:
        result = git_tools.git_diff(git_repo)
        assert result.success
        assert result.stdout.strip() == ""

    def test_unstaged_changes(self, git_repo: Path) -> None:
        (git_repo / "hello.py").write_text("print('changed')\n")
        result = git_tools.git_diff(git_repo)
        assert result.success
        assert "changed" in result.stdout

    def test_name_only(self, git_repo: Path) -> None:
        (git_repo / "hello.py").write_text("print('changed')\n")
        result = git_tools.git_diff(git_repo, name_only=True)
        assert result.success
        assert "hello.py" in result.stdout


class TestGitLog:
    def test_log_shows_commit(self, git_repo: Path) -> None:
        result = git_tools.git_log(git_repo)
        assert result.success
        assert "initial" in result.stdout


class TestGitGrep:
    def test_finds_pattern(self, git_repo: Path) -> None:
        result = git_tools.git_grep(git_repo, pattern="hello")
        assert result.success
        assert "hello.py" in result.stdout

    def test_empty_pattern_raises(self, git_repo: Path) -> None:
        with pytest.raises(ValueError, match="pattern must be non-empty"):
            git_tools.git_grep(git_repo, pattern="  ")

    def test_no_match(self, git_repo: Path) -> None:
        result = git_tools.git_grep(git_repo, pattern="nonexistent_xyz")
        # git grep returns exit code 1 when no matches found
        assert not result.success


class TestGitResultSuccess:
    def test_success_property(self) -> None:
        r = git_tools.GitResult(command=[], exit_code=0, stdout="", stderr="")
        assert r.success

    def test_failure_property(self) -> None:
        r = git_tools.GitResult(command=[], exit_code=1, stdout="", stderr="")
        assert not r.success


class TestRunGitErrors:
    def test_invalid_repo_root(self) -> None:
        with pytest.raises(ValueError, match="repo_root must be an existing directory"):
            git_tools.git_status(Path("/nonexistent/path"))
