"""Tests for helping_hands.lib.meta.tools.filesystem.

Protects the security boundary that prevents AI-driven file operations from
escaping the repository root. resolve_repo_target is the primary defence:
it must reject absolute paths, traversal sequences (../), and empty paths
with distinct, actionable error messages, and must also validate that the
repo root itself is a real directory. Failures here would allow AI agents to
read or overwrite files outside the checked-out repo. Also tests the
read/write/mkdir helpers for correct truncation, binary-file rejection,
parent-directory creation, and OSError wrapping.
"""

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
        with pytest.raises(ValueError, match="non-empty"):
            normalize_relative_path("   ")

    def test_backslash_and_dot_combined(self) -> None:
        assert normalize_relative_path(".\\src\\main.py") == "src/main.py"


class TestResolveRepoTarget:
    def test_resolves_valid_path(self, tmp_path: Path) -> None:
        target = resolve_repo_target(tmp_path, "src/main.py")
        assert target == tmp_path / "src" / "main.py"

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty relative path"):
            resolve_repo_target(tmp_path, "/etc/passwd")

    def test_rejects_empty_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            resolve_repo_target(tmp_path, "")

    def test_rejects_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes repository root"):
            resolve_repo_target(tmp_path, "../../../etc/passwd")

    def test_rejects_dot_dot_within_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes repository root"):
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

    def test_wraps_permission_error_in_runtime_error(self, tmp_path: Path) -> None:
        """OSError (e.g. permission denied) is wrapped in RuntimeError."""
        from unittest.mock import patch

        with (
            patch.object(Path, "write_text", side_effect=PermissionError("denied")),
            pytest.raises(RuntimeError, match="cannot write file"),
        ):
            write_text_file(tmp_path, "blocked.txt", "data")

    def test_wraps_oserror_includes_file_path(self, tmp_path: Path) -> None:
        """RuntimeError message includes the display path of the file."""
        from unittest.mock import patch

        with (
            patch.object(
                Path, "write_text", side_effect=OSError("No space left on device")
            ),
            pytest.raises(RuntimeError, match=r"blocked\.txt") as exc_info,
        ):
            write_text_file(tmp_path, "blocked.txt", "data")
        assert "No space left on device" in str(exc_info.value)


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


class TestNormalizeRelativePathTypeCheck:
    """Non-string input raises TypeError."""

    def test_int_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            normalize_relative_path(42)  # type: ignore[arg-type]

    def test_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            normalize_relative_path(None)  # type: ignore[arg-type]


class TestReadTextFileLargeFile:
    """File exceeding max_file_size raises ValueError with MB sizes."""

    def test_rejects_file_exceeding_size_limit(self, tmp_path: Path) -> None:
        big = tmp_path / "big.bin"
        big.write_bytes(b"x" * 200)
        with pytest.raises(ValueError, match="too large"):
            read_text_file(tmp_path, "big.bin", max_file_size=100)


class TestMkdirPathOSError:
    """OSError during mkdir is wrapped in RuntimeError."""

    def test_wraps_oserror_in_runtime_error(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        with (
            patch.object(Path, "mkdir", side_effect=PermissionError("denied")),
            pytest.raises(RuntimeError, match="cannot create directory"),
        ):
            mkdir_path(tmp_path, "blocked_dir")


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


class TestResolveRepoTargetErrorMessages:
    """Verify that empty/absolute vs traversal produce distinct error messages."""

    def test_empty_path_message_differs_from_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            resolve_repo_target(tmp_path, "")

    def test_absolute_path_message_differs_from_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty relative path"):
            resolve_repo_target(tmp_path, "/etc/passwd")

    def test_whitespace_only_path_message(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            resolve_repo_target(tmp_path, "   ")

    def test_traversal_mentions_repository_root(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes repository root"):
            resolve_repo_target(tmp_path, "../../../etc/passwd")

    def test_embedded_traversal_mentions_repository_root(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes repository root"):
            resolve_repo_target(tmp_path, "a/b/../../../../etc/passwd")

    def test_dot_slash_only_is_non_empty_relative(self, tmp_path: Path) -> None:
        # "./" normalizes to "" which triggers the non-empty check
        with pytest.raises(ValueError, match="non-empty relative path"):
            resolve_repo_target(tmp_path, "./")


class TestResolveRepoTargetRootValidation:
    """Verify that resolve_repo_target rejects non-directory repo_root."""

    def test_rejects_nonexistent_root(self, tmp_path: Path) -> None:
        fake_root = tmp_path / "does-not-exist"
        with pytest.raises(ValueError, match="existing directory"):
            resolve_repo_target(fake_root, "file.txt")

    def test_rejects_file_as_root(self, tmp_path: Path) -> None:
        file_path = tmp_path / "a-file.txt"
        file_path.write_text("hello")
        with pytest.raises(ValueError, match="existing directory"):
            resolve_repo_target(file_path, "file.txt")

    def test_accepts_valid_directory_root(self, tmp_path: Path) -> None:
        target = resolve_repo_target(tmp_path, "file.txt")
        assert target == tmp_path / "file.txt"
