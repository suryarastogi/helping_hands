"""Tests for helping_hands.lib.meta.tools.filesystem."""

from __future__ import annotations

from pathlib import Path

import pytest

from helping_hands.lib.meta.tools.filesystem import (
    mkdir_path,
    normalize_relative_path,
    path_exists,
    read_text_file,
    resolve_repo_target,
    write_text_file,
)


class TestNormalizeRelativePath:
    def test_strips_whitespace(self) -> None:
        assert normalize_relative_path("  foo/bar.py  ") == "foo/bar.py"

    def test_converts_backslashes(self) -> None:
        assert normalize_relative_path("src\\main\\app.py") == "src/main/app.py"

    def test_strips_dot_slash_prefix(self) -> None:
        assert normalize_relative_path("./src/app.py") == "src/app.py"

    def test_plain_path_unchanged(self) -> None:
        assert normalize_relative_path("src/app.py") == "src/app.py"


class TestResolveRepoTarget:
    def test_valid_relative_path(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hi")
        result = resolve_repo_target(tmp_path, "file.txt")
        assert result == (tmp_path / "file.txt").resolve()

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "/etc/passwd")

    def test_rejects_empty_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "")

    def test_rejects_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "../../../etc/passwd")

    def test_rejects_traversal_in_middle(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "src/../../etc/passwd")

    def test_nested_path(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "c.py").write_text("x")
        result = resolve_repo_target(tmp_path, "a/b/c.py")
        assert result == (nested / "c.py").resolve()


class TestReadTextFile:
    def test_reads_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("world")
        content, truncated, display = read_text_file(tmp_path, "hello.txt")
        assert content == "world"
        assert truncated is False
        assert display == "hello.txt"

    def test_truncation(self, tmp_path: Path) -> None:
        (tmp_path / "big.txt").write_text("abcdefghij")
        content, truncated, _display = read_text_file(tmp_path, "big.txt", max_chars=5)
        assert content == "abcde"
        assert truncated is True

    def test_no_truncation_when_under_limit(self, tmp_path: Path) -> None:
        (tmp_path / "small.txt").write_text("hi")
        content, truncated, _ = read_text_file(tmp_path, "small.txt", max_chars=100)
        assert content == "hi"
        assert truncated is False

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_text_file(tmp_path, "nope.txt")

    def test_raises_on_directory(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        with pytest.raises(IsADirectoryError):
            read_text_file(tmp_path, "subdir")

    def test_raises_on_binary_file(self, tmp_path: Path) -> None:
        (tmp_path / "bin.dat").write_bytes(b"\x80\x81\x82\x83")
        with pytest.raises(UnicodeError):
            read_text_file(tmp_path, "bin.dat")

    def test_display_path_uses_posix(self, tmp_path: Path) -> None:
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "c.txt").write_text("x")
        _, _, display = read_text_file(tmp_path, "a/b/c.txt")
        assert display == "a/b/c.txt"


class TestWriteTextFile:
    def test_writes_file(self, tmp_path: Path) -> None:
        result = write_text_file(tmp_path, "out.txt", "hello")
        assert result == "out.txt"
        assert (tmp_path / "out.txt").read_text() == "hello"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        result = write_text_file(tmp_path, "a/b/c.txt", "nested")
        assert result == "a/b/c.txt"
        assert (tmp_path / "a" / "b" / "c.txt").read_text() == "nested"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        (tmp_path / "x.txt").write_text("old")
        write_text_file(tmp_path, "x.txt", "new")
        assert (tmp_path / "x.txt").read_text() == "new"


class TestMkdirPath:
    def test_creates_directory(self, tmp_path: Path) -> None:
        result = mkdir_path(tmp_path, "newdir")
        assert result == "newdir"
        assert (tmp_path / "newdir").is_dir()

    def test_creates_nested_dirs(self, tmp_path: Path) -> None:
        result = mkdir_path(tmp_path, "a/b/c")
        assert result == "a/b/c"
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_idempotent(self, tmp_path: Path) -> None:
        mkdir_path(tmp_path, "exists")
        mkdir_path(tmp_path, "exists")  # should not raise
        assert (tmp_path / "exists").is_dir()


class TestPathExists:
    def test_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("x")
        assert path_exists(tmp_path, "f.txt") is True

    def test_existing_dir(self, tmp_path: Path) -> None:
        (tmp_path / "d").mkdir()
        assert path_exists(tmp_path, "d") is True

    def test_nonexistent(self, tmp_path: Path) -> None:
        assert path_exists(tmp_path, "nope") is False

    def test_traversal_returns_false(self, tmp_path: Path) -> None:
        assert path_exists(tmp_path, "../../../etc/passwd") is False
