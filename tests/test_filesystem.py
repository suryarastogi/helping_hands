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
        assert normalize_relative_path("  foo/bar  ") == "foo/bar"

    def test_converts_backslashes(self) -> None:
        assert normalize_relative_path("foo\\bar\\baz") == "foo/bar/baz"

    def test_strips_dot_slash_prefix(self) -> None:
        assert normalize_relative_path("./src/main.py") == "src/main.py"

    def test_passthrough_normal_path(self) -> None:
        assert normalize_relative_path("src/main.py") == "src/main.py"

    def test_only_dot_slash(self) -> None:
        assert normalize_relative_path("./") == ""

    def test_double_dot_slash_prefix(self) -> None:
        assert normalize_relative_path("././src/main.py") == "./src/main.py"

    def test_trailing_slash_preserved(self) -> None:
        result = normalize_relative_path("src/main/")
        assert result == "src/main/"

    def test_bare_dot(self) -> None:
        assert normalize_relative_path(".") == "."

    def test_only_whitespace(self) -> None:
        assert normalize_relative_path("   ") == ""

    def test_backslash_and_dot_combined(self) -> None:
        assert normalize_relative_path(".\\src\\main.py") == "src/main.py"


class TestResolveRepoTarget:
    def test_resolves_valid_path(self, tmp_path: Path) -> None:
        target = resolve_repo_target(tmp_path, "src/main.py")
        assert target == tmp_path / "src" / "main.py"

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "/etc/passwd")

    def test_rejects_empty_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "")

    def test_rejects_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "../../../etc/passwd")

    def test_rejects_dot_dot_within_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "src/../../etc/passwd")

    def test_normalizes_dot_slash(self, tmp_path: Path) -> None:
        target = resolve_repo_target(tmp_path, "./src/main.py")
        assert target == tmp_path / "src" / "main.py"


class TestReadTextFile:
    def test_reads_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
        content, truncated, display = read_text_file(tmp_path, "hello.txt")
        assert content == "hello world"
        assert truncated is False
        assert display == "hello.txt"

    def test_truncates_with_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "big.txt").write_text("a" * 100, encoding="utf-8")
        content, truncated, display = read_text_file(tmp_path, "big.txt", max_chars=10)
        assert content == "a" * 10
        assert truncated is True
        assert display == "big.txt"

    def test_no_truncation_when_under_limit(self, tmp_path: Path) -> None:
        (tmp_path / "small.txt").write_text("abc", encoding="utf-8")
        content, truncated, _ = read_text_file(tmp_path, "small.txt", max_chars=100)
        assert content == "abc"
        assert truncated is False

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="file not found"):
            read_text_file(tmp_path, "missing.txt")

    def test_raises_is_a_directory(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        with pytest.raises(IsADirectoryError, match="path is a directory"):
            read_text_file(tmp_path, "subdir")

    def test_raises_on_binary_file(self, tmp_path: Path) -> None:
        (tmp_path / "binary.bin").write_bytes(b"\x80\x81\x82\x83")
        with pytest.raises(UnicodeError, match="not UTF-8"):
            read_text_file(tmp_path, "binary.bin")

    def test_display_path_for_nested_file(self, tmp_path: Path) -> None:
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "app.py").write_text("pass", encoding="utf-8")
        _, _, display = read_text_file(tmp_path, "src/app.py")
        assert display == "src/app.py"


class TestWriteTextFile:
    def test_writes_file(self, tmp_path: Path) -> None:
        result = write_text_file(tmp_path, "output.txt", "content here")
        assert result == "output.txt"
        assert (tmp_path / "output.txt").read_text(encoding="utf-8") == "content here"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        result = write_text_file(tmp_path, "a/b/c.txt", "deep")
        assert result == "a/b/c.txt"
        assert (tmp_path / "a" / "b" / "c.txt").read_text(encoding="utf-8") == "deep"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("old", encoding="utf-8")
        write_text_file(tmp_path, "file.txt", "new")
        assert (tmp_path / "file.txt").read_text(encoding="utf-8") == "new"


class TestMkdirPath:
    def test_creates_directory(self, tmp_path: Path) -> None:
        result = mkdir_path(tmp_path, "new_dir")
        assert result == "new_dir"
        assert (tmp_path / "new_dir").is_dir()

    def test_creates_nested_dirs(self, tmp_path: Path) -> None:
        result = mkdir_path(tmp_path, "a/b/c")
        assert result == "a/b/c"
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_idempotent_on_existing(self, tmp_path: Path) -> None:
        (tmp_path / "existing").mkdir()
        result = mkdir_path(tmp_path, "existing")
        assert result == "existing"


class TestPathExists:
    def test_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "exists.txt").write_text("yes")
        assert path_exists(tmp_path, "exists.txt") is True

    def test_existing_dir(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        assert path_exists(tmp_path, "subdir") is True

    def test_missing_path(self, tmp_path: Path) -> None:
        assert path_exists(tmp_path, "nope.txt") is False

    def test_traversal_returns_false(self, tmp_path: Path) -> None:
        assert path_exists(tmp_path, "../../../etc/passwd") is False
