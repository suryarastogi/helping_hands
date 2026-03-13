"""Tests for v155 — Input validation and defensive coding hardening.

Covers:
- read_text_file() max_file_size positive validation
- Google provider _complete_impl() KeyError defense for missing content key
- _get_diff() fallback FileNotFoundError coverage
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta.tools.filesystem import read_text_file

# ---------------------------------------------------------------------------
# filesystem.py — read_text_file max_file_size validation
# ---------------------------------------------------------------------------


class TestReadTextFileMaxFileSizeValidation:
    """Verify read_text_file rejects non-positive max_file_size values."""

    def test_rejects_zero_max_file_size(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="max_file_size must be positive"):
            read_text_file(tmp_path, "file.txt", max_file_size=0)

    def test_rejects_negative_max_file_size(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="max_file_size must be positive"):
            read_text_file(tmp_path, "file.txt", max_file_size=-1)

    def test_rejects_large_negative_max_file_size(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="max_file_size must be positive"):
            read_text_file(tmp_path, "file.txt", max_file_size=-999)

    def test_error_message_includes_value(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="-42"):
            read_text_file(tmp_path, "file.txt", max_file_size=-42)

    def test_accepts_positive_max_file_size(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        text, truncated, _ = read_text_file(
            tmp_path, "file.txt", max_file_size=10 * 1024 * 1024
        )
        assert text == "hello"
        assert truncated is False

    def test_accepts_small_positive_max_file_size(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hi")
        text, _, _ = read_text_file(tmp_path, "file.txt", max_file_size=100)
        assert text == "hi"

    def test_validation_before_file_access(self, tmp_path: Path) -> None:
        """max_file_size validation happens before resolving the file path."""
        with pytest.raises(ValueError, match="max_file_size must be positive"):
            read_text_file(tmp_path, "nonexistent.txt", max_file_size=0)


# ---------------------------------------------------------------------------
# google.py — _complete_impl KeyError defense for missing content key
# ---------------------------------------------------------------------------


class TestGoogleProviderMissingContentKey:
    """Verify GoogleProvider._complete_impl handles missing 'content' key."""

    def test_missing_content_key_raises_value_error(self) -> None:
        """Messages without 'content' key are skipped; all-empty raises ValueError."""
        from helping_hands.lib.ai_providers.google import GoogleProvider

        provider = GoogleProvider()
        mock_inner = MagicMock()

        messages = [{"role": "user"}]  # Missing "content" key
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider._complete_impl(
                inner=mock_inner, messages=messages, model="gemini-2.0-flash"
            )

    def test_mixed_missing_and_valid_content(self) -> None:
        """Messages with missing 'content' are skipped; valid ones are used."""
        from helping_hands.lib.ai_providers.google import GoogleProvider

        provider = GoogleProvider()
        mock_inner = MagicMock()
        mock_inner.models.generate_content.return_value = "response"

        messages = [
            {"role": "system"},  # No content key
            {"role": "user", "content": "hello"},
        ]
        result = provider._complete_impl(
            inner=mock_inner, messages=messages, model="gemini-2.0-flash"
        )
        assert result == "response"
        # Only "hello" should be passed as contents
        call_kwargs = mock_inner.models.generate_content.call_args
        assert call_kwargs.kwargs["contents"] == ["hello"]

    def test_none_content_key_skipped(self) -> None:
        """Messages with content=None are skipped gracefully."""
        from helping_hands.lib.ai_providers.google import GoogleProvider

        provider = GoogleProvider()
        mock_inner = MagicMock()

        messages = [{"role": "user", "content": None}]
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider._complete_impl(
                inner=mock_inner, messages=messages, model="gemini-2.0-flash"
            )

    def test_empty_string_content_skipped(self) -> None:
        """Messages with content='' are skipped gracefully."""
        from helping_hands.lib.ai_providers.google import GoogleProvider

        provider = GoogleProvider()
        mock_inner = MagicMock()

        messages = [{"role": "user", "content": ""}]
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider._complete_impl(
                inner=mock_inner, messages=messages, model="gemini-2.0-flash"
            )


# ---------------------------------------------------------------------------
# pr_description.py — _get_diff fallback FileNotFoundError test coverage
# ---------------------------------------------------------------------------


class TestGetDiffFallbackFileNotFound:
    """Verify _get_diff fallback attempt handles FileNotFoundError."""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_fallback_file_not_found_after_base_branch_failure(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """First diff returns non-zero rc, fallback raises FileNotFoundError."""
        from helping_hands.lib.hands.v1.hand.pr_description import _get_diff

        mock_run.side_effect = [
            # First attempt: base_branch...HEAD returns non-zero
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
            # Second attempt: HEAD~1 HEAD — git not found
            FileNotFoundError("git not found"),
        ]
        assert _get_diff(tmp_path, base_branch="main") == ""
        assert mock_run.call_count == 2

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_fallback_file_not_found_after_base_branch_empty_stdout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """First diff returns rc=0 but empty stdout, fallback FileNotFoundError."""
        from helping_hands.lib.hands.v1.hand.pr_description import _get_diff

        mock_run.side_effect = [
            # First attempt: success but no output
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="  \n", stderr=""
            ),
            # Second attempt: git disappeared
            FileNotFoundError("git not found"),
        ]
        assert _get_diff(tmp_path, base_branch="main") == ""
        assert mock_run.call_count == 2

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_fallback_timeout_after_base_branch_failure(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """First diff returns non-zero rc, fallback times out."""
        from subprocess import TimeoutExpired

        from helping_hands.lib.hands.v1.hand.pr_description import _get_diff

        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
            TimeoutExpired(cmd=["git", "diff"], timeout=30),
        ]
        assert _get_diff(tmp_path, base_branch="main") == ""
        assert mock_run.call_count == 2
