"""Tests for helping_hands.lib.meta.tools.filesystem path-safe utilities."""

from __future__ import annotations

import os
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

# ---------------------------------------------------------------------------
# normalize_relative_path
# ---------------------------------------------------------------------------


class TestNormalizeRelativePath:
    def test_strips_leading_dot_slash(self) -> None:
        assert normalize_relative_path("./src/main.py") == "src/main.py"

    def test_converts_backslashes(self) -> None:
        assert normalize_relative_path("src\\lib\\file.py") == "src/lib/file.py"

    def test_strips_whitespace(self) -> None:
        assert normalize_relative_path("  src/main.py  ") == "src/main.py"

    def test_empty_string(self) -> None:
        assert normalize_relative_path("") == ""

    def test_plain_filename(self) -> None:
        assert normalize_relative_path("README.md") == "README.md"

    def test_nested_dot_slash_only_strips_leading(self) -> None:
        assert normalize_relative_path("./a/./b") == "a/./b"

    def test_double_dot_preserved(self) -> None:
        # normalize_relative_path only strips leading ./ and backslashes;
        # traversal prevention is handled by resolve_repo_target
        assert normalize_relative_path("../escape") == "../escape"


# ---------------------------------------------------------------------------
# resolve_repo_target
# ---------------------------------------------------------------------------


class TestResolveRepoTarget:
    def test_valid_relative_path(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        target = resolve_repo_target(tmp_path, "src")
        assert target == (tmp_path / "src").resolve()

    def test_nested_path(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        target = resolve_repo_target(tmp_path, "a/b")
        assert target == nested.resolve()

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "/etc/passwd")

    def test_rejects_empty_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "")

    def test_rejects_parent_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "../escape")

    def test_rejects_deep_traversal(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "sub/../../escape")

    def test_rejects_symlink_escape(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside_target"
        outside.mkdir(exist_ok=True)
        link = tmp_path / "sneaky_link"
        link.symlink_to(outside)
        with pytest.raises(ValueError, match="invalid path"):
            resolve_repo_target(tmp_path, "sneaky_link")

    def test_nonexistent_but_confined_path_resolves(self, tmp_path: Path) -> None:
        # resolve_repo_target does not require the path to exist,
        # only that it would be inside repo_root after resolution
        target = resolve_repo_target(tmp_path, "does/not/exist.txt")
        assert str(target).startswith(str(tmp_path.resolve()))


# ---------------------------------------------------------------------------
# read_text_file
# ---------------------------------------------------------------------------


class TestReadTextFile:
    def test_reads_file_content(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("Hello, world!", encoding="utf-8")
        content, truncated, display = read_text_file(tmp_path, "hello.txt")
        assert content == "Hello, world!"
        assert truncated is False
        assert display == "hello.txt"

    def test_truncates_with_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "long.txt").write_text("a" * 100, encoding="utf-8")
        content, truncated, display = read_text_file(tmp_path, "long.txt", max_chars=10)
        assert content == "a" * 10
        assert truncated is True
        assert display == "long.txt"

    def test_no_truncation_when_under_limit(self, tmp_path: Path) -> None:
        (tmp_path / "short.txt").write_text("abc", encoding="utf-8")
        content, truncated, _ = read_text_file(tmp_path, "short.txt", max_chars=100)
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
        (tmp_path / "binary.bin").write_bytes(b"\xff\xfe\x00\x01" * 100)
        with pytest.raises(UnicodeError, match="not UTF-8"):
            read_text_file(tmp_path, "binary.bin")

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            read_text_file(tmp_path, "../secret.txt")

    def test_display_path_is_posix(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("x", encoding="utf-8")
        _, _, display = read_text_file(tmp_path, "a/b/file.txt")
        assert display == "a/b/file.txt"


# ---------------------------------------------------------------------------
# write_text_file
# ---------------------------------------------------------------------------


class TestWriteTextFile:
    def test_writes_new_file(self, tmp_path: Path) -> None:
        result = write_text_file(tmp_path, "out.txt", "content")
        assert result == "out.txt"
        assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "content"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        result = write_text_file(tmp_path, "a/b/c/deep.txt", "nested")
        assert result == "a/b/c/deep.txt"
        assert (tmp_path / "a" / "b" / "c" / "deep.txt").read_text(
            encoding="utf-8"
        ) == "nested"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "exists.txt").write_text("old", encoding="utf-8")
        write_text_file(tmp_path, "exists.txt", "new")
        assert (tmp_path / "exists.txt").read_text(encoding="utf-8") == "new"

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            write_text_file(tmp_path, "../escape.txt", "malicious")

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            write_text_file(tmp_path, "/tmp/escape.txt", "malicious")


# ---------------------------------------------------------------------------
# mkdir_path
# ---------------------------------------------------------------------------


class TestMkdirPath:
    def test_creates_directory(self, tmp_path: Path) -> None:
        result = mkdir_path(tmp_path, "new_dir")
        assert result == "new_dir"
        assert (tmp_path / "new_dir").is_dir()

    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        result = mkdir_path(tmp_path, "a/b/c")
        assert result == "a/b/c"
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_idempotent_on_existing(self, tmp_path: Path) -> None:
        (tmp_path / "existing").mkdir()
        result = mkdir_path(tmp_path, "existing")
        assert result == "existing"
        assert (tmp_path / "existing").is_dir()

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="invalid path"):
            mkdir_path(tmp_path, "../escape_dir")


# ---------------------------------------------------------------------------
# path_exists
# ---------------------------------------------------------------------------


class TestPathExists:
    def test_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "present.txt").write_text("x", encoding="utf-8")
        assert path_exists(tmp_path, "present.txt") is True

    def test_existing_directory(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        assert path_exists(tmp_path, "subdir") is True

    def test_missing_path(self, tmp_path: Path) -> None:
        assert path_exists(tmp_path, "ghost.txt") is False

    def test_traversal_returns_false(self, tmp_path: Path) -> None:
        assert path_exists(tmp_path, "../outside") is False

    def test_absolute_path_returns_false(self, tmp_path: Path) -> None:
        assert path_exists(tmp_path, "/etc/passwd") is False


# ---------------------------------------------------------------------------
# Symlink edge cases (combined)
# ---------------------------------------------------------------------------


class TestSymlinkEdgeCases:
    def test_symlink_within_repo_is_allowed(self, tmp_path: Path) -> None:
        real = tmp_path / "real.txt"
        real.write_text("content", encoding="utf-8")
        link = tmp_path / "link.txt"
        link.symlink_to(real)
        content, _, _ = read_text_file(tmp_path, "link.txt")
        assert content == "content"

    def test_symlink_escaping_repo_is_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside_file.txt"
        outside.write_text("secret", encoding="utf-8")
        try:
            link = tmp_path / "escape_link.txt"
            link.symlink_to(outside)
            with pytest.raises(ValueError, match="invalid path"):
                read_text_file(tmp_path, "escape_link.txt")
        finally:
            outside.unlink(missing_ok=True)

    def test_write_through_escaping_symlink_rejected(self, tmp_path: Path) -> None:
        outside_dir = tmp_path.parent / "outside_write_target"
        outside_dir.mkdir(exist_ok=True)
        try:
            link = tmp_path / "escape_dir"
            link.symlink_to(outside_dir)
            with pytest.raises(ValueError, match="invalid path"):
                write_text_file(tmp_path, "escape_dir/payload.txt", "malicious")
        finally:
            os.rmdir(outside_dir)
