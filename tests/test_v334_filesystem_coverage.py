"""v334 — Additional filesystem.py coverage tests.

Covers: normalize_relative_path type errors, read_text_file max_file_size
enforcement and max_chars validation, mkdir_path OSError wrapping,
and write_text_file / read_text_file edge cases.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.lib.meta.tools.filesystem import (
    mkdir_path,
    normalize_relative_path,
    read_text_file,
    write_text_file,
)


class TestNormalizeRelativePathTypeErrors:
    """TypeError branches for non-string input."""

    def test_int_input_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            normalize_relative_path(42)  # type: ignore[arg-type]

    def test_none_input_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            normalize_relative_path(None)  # type: ignore[arg-type]

    def test_list_input_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            normalize_relative_path(["src"])  # type: ignore[arg-type]

    def test_bool_input_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            normalize_relative_path(True)  # type: ignore[arg-type]


class TestReadTextFileMaxFileSize:
    """max_file_size enforcement and validation."""

    def test_file_exceeding_max_size_raises(self, tmp_path: Path) -> None:
        big = tmp_path / "big.txt"
        big.write_text("x" * 200, encoding="utf-8")
        with pytest.raises(ValueError, match="too large"):
            read_text_file(tmp_path, "big.txt", max_file_size=100)

    def test_file_exactly_at_limit_passes(self, tmp_path: Path) -> None:
        content = "a" * 50
        (tmp_path / "exact.txt").write_text(content, encoding="utf-8")
        text, truncated, _ = read_text_file(tmp_path, "exact.txt", max_file_size=50)
        assert text == content
        assert truncated is False

    def test_max_file_size_zero_raises_validation(self, tmp_path: Path) -> None:
        (tmp_path / "any.txt").write_text("data", encoding="utf-8")
        with pytest.raises(ValueError, match="must be positive"):
            read_text_file(tmp_path, "any.txt", max_file_size=0)

    def test_max_file_size_negative_raises_validation(self, tmp_path: Path) -> None:
        (tmp_path / "any.txt").write_text("data", encoding="utf-8")
        with pytest.raises(ValueError, match="must be positive"):
            read_text_file(tmp_path, "any.txt", max_file_size=-1)

    def test_error_message_includes_mb_values(self, tmp_path: Path) -> None:
        big = tmp_path / "big.txt"
        # Write 2 MB of data
        big.write_bytes(b"x" * (2 * 1024 * 1024))
        with pytest.raises(ValueError, match=r"2\.0 MB.*limit 1\.0 MB"):
            read_text_file(tmp_path, "big.txt", max_file_size=1 * 1024 * 1024)


class TestReadTextFileMaxCharsValidation:
    """max_chars parameter validation."""

    def test_max_chars_zero_raises(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("data", encoding="utf-8")
        with pytest.raises(ValueError, match="must be positive"):
            read_text_file(tmp_path, "f.txt", max_chars=0)

    def test_max_chars_negative_raises(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("data", encoding="utf-8")
        with pytest.raises(ValueError, match="must be positive"):
            read_text_file(tmp_path, "f.txt", max_chars=-5)

    def test_max_chars_none_reads_full_file(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("hello world", encoding="utf-8")
        text, truncated, _ = read_text_file(tmp_path, "f.txt", max_chars=None)
        assert text == "hello world"
        assert truncated is False


class TestMkdirPathOSError:
    """mkdir_path wraps OSError in RuntimeError."""

    def test_permission_error_wrapped(self, tmp_path: Path) -> None:
        with (
            patch.object(Path, "mkdir", side_effect=PermissionError("denied")),
            pytest.raises(RuntimeError, match="cannot create directory"),
        ):
            mkdir_path(tmp_path, "blocked")

    def test_error_includes_display_path(self, tmp_path: Path) -> None:
        with (
            patch.object(Path, "mkdir", side_effect=OSError("disk full")),
            pytest.raises(RuntimeError, match="blocked") as exc_info,
        ):
            mkdir_path(tmp_path, "blocked")
        assert "disk full" in str(exc_info.value)


class TestWriteTextFileEdgeCases:
    """Additional write_text_file coverage."""

    def test_writes_empty_content(self, tmp_path: Path) -> None:
        result = write_text_file(tmp_path, "empty.txt", "")
        assert result == "empty.txt"
        assert (tmp_path / "empty.txt").read_text(encoding="utf-8") == ""

    def test_writes_unicode_content(self, tmp_path: Path) -> None:
        content = "héllo wörld 日本語"
        result = write_text_file(tmp_path, "unicode.txt", content)
        assert result == "unicode.txt"
        assert (tmp_path / "unicode.txt").read_text(encoding="utf-8") == content
