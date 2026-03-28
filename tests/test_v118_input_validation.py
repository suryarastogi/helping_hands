"""Tests for v118: read_text_file enforces a configurable file-size cap.

AI tools that read repository files without a size limit can send multi-megabyte
blobs to the model context window, exhausting token quotas and causing OOM spikes.
The max_file_size parameter must reject files that exceed the limit with a clear
ValueError that includes both the actual and limit sizes so callers can distinguish
"file too large" from other I/O errors.

The default cap is 10 MB; changing it accidentally would silently break context
budgeting for all hands that use read_text_file.

_float_env must warn (not crash) when an environment variable contains a
non-numeric value, so misconfigured deployments degrade gracefully.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

# --- filesystem.py: file size limit ---


class TestReadTextFileMaxFileSize:
    """Verify read_text_file rejects files exceeding max_file_size."""

    def test_rejects_file_over_size_limit(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        big = tmp_path / "big.txt"
        big.write_text("x" * 200, encoding="utf-8")
        with pytest.raises(ValueError, match="file is too large"):
            read_text_file(tmp_path, "big.txt", max_file_size=100)

    def test_accepts_file_at_size_limit(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        f = tmp_path / "ok.txt"
        f.write_text("hello", encoding="utf-8")
        content, truncated, display = read_text_file(
            tmp_path, "ok.txt", max_file_size=1024
        )
        assert content == "hello"
        assert truncated is False
        assert display == "ok.txt"

    def test_error_message_includes_sizes(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        big = tmp_path / "big.txt"
        big.write_bytes(b"x" * (2 * 1024 * 1024))  # 2 MB
        with pytest.raises(ValueError, match=r"2\.0 MB.*limit 1\.0 MB"):
            read_text_file(tmp_path, "big.txt", max_file_size=1 * 1024 * 1024)

    def test_default_limit_is_10mb(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import _MAX_FILE_SIZE_BYTES

        assert _MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024

    def test_exactly_at_limit_is_accepted(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        f = tmp_path / "exact.txt"
        f.write_bytes(b"a" * 50)
        content, truncated, _ = read_text_file(tmp_path, "exact.txt", max_file_size=50)
        assert content == "a" * 50
        assert truncated is False

    def test_one_byte_over_limit_is_rejected(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        f = tmp_path / "over.txt"
        f.write_bytes(b"a" * 51)
        with pytest.raises(ValueError, match="file is too large"):
            read_text_file(tmp_path, "over.txt", max_file_size=50)


# --- cli/base.py: _float_env warning logging ---


class TestFloatEnvLogging:
    """Verify _float_env logs warnings for invalid environment values."""

    def test_logs_warning_for_non_numeric(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        monkeypatch.setenv("__TEST_FLOAT_LOG__", "abc")
        with caplog.at_level(logging.WARNING):
            result = _TwoPhaseCLIHand._float_env("__TEST_FLOAT_LOG__", default=5.0)
        assert result == 5.0
        assert "non-numeric" in caplog.text
        assert "abc" in caplog.text

    def test_logs_warning_for_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        monkeypatch.setenv("__TEST_FLOAT_LOG__", "0")
        with caplog.at_level(logging.WARNING):
            result = _TwoPhaseCLIHand._float_env("__TEST_FLOAT_LOG__", default=3.0)
        assert result == 3.0
        assert "non-positive" in caplog.text

    def test_logs_warning_for_negative(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        monkeypatch.setenv("__TEST_FLOAT_LOG__", "-2.5")
        with caplog.at_level(logging.WARNING):
            result = _TwoPhaseCLIHand._float_env("__TEST_FLOAT_LOG__", default=4.0)
        assert result == 4.0
        assert "non-positive" in caplog.text
        assert "-2.5" in caplog.text

    def test_no_warning_for_valid_value(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        monkeypatch.setenv("__TEST_FLOAT_LOG__", "7.5")
        with caplog.at_level(logging.WARNING):
            result = _TwoPhaseCLIHand._float_env("__TEST_FLOAT_LOG__", default=1.0)
        assert result == 7.5
        assert caplog.text == ""

    def test_no_warning_when_not_set(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        with caplog.at_level(logging.WARNING):
            result = _TwoPhaseCLIHand._float_env("__NOT_SET_FLOAT_LOG__", default=9.0)
        assert result == 9.0
        assert caplog.text == ""
