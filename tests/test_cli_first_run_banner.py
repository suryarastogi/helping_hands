"""Tests for the first-run welcome banner in helping_hands.cli.main.

Covers ``_maybe_show_first_run_banner()``: banner shown on first run,
suppressed on subsequent runs, and graceful handling of filesystem errors.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from helping_hands.cli.main import (
    _WELCOME_BANNER,
    _maybe_show_first_run_banner,
)


class TestMaybeShowFirstRunBanner:
    """Tests for _maybe_show_first_run_banner()."""

    def test_shows_banner_on_first_run(self, tmp_path: Path, capsys) -> None:
        marker = tmp_path / ".first_run_done"
        with (
            patch("helping_hands.cli.main._FIRST_RUN_DIR", tmp_path),
            patch("helping_hands.cli.main._FIRST_RUN_MARKER", marker),
        ):
            result = _maybe_show_first_run_banner()

        assert result is True
        assert marker.exists()
        assert _WELCOME_BANNER in capsys.readouterr().out

    def test_suppressed_on_subsequent_run(self, tmp_path: Path, capsys) -> None:
        marker = tmp_path / ".first_run_done"
        marker.write_text("")
        with (
            patch("helping_hands.cli.main._FIRST_RUN_DIR", tmp_path),
            patch("helping_hands.cli.main._FIRST_RUN_MARKER", marker),
        ):
            result = _maybe_show_first_run_banner()

        assert result is False
        assert capsys.readouterr().out == ""

    def test_creates_parent_directory(self, tmp_path: Path, capsys) -> None:
        nested = tmp_path / "sub" / "dir"
        marker = nested / ".first_run_done"
        with (
            patch("helping_hands.cli.main._FIRST_RUN_DIR", nested),
            patch("helping_hands.cli.main._FIRST_RUN_MARKER", marker),
        ):
            result = _maybe_show_first_run_banner()

        assert result is True
        assert nested.is_dir()
        assert marker.exists()

    def test_returns_false_on_permission_error(self, tmp_path: Path, capsys) -> None:
        marker = tmp_path / ".first_run_done"
        with (
            patch("helping_hands.cli.main._FIRST_RUN_DIR", tmp_path),
            patch("helping_hands.cli.main._FIRST_RUN_MARKER", marker),
            patch.object(Path, "exists", side_effect=OSError("denied")),
        ):
            result = _maybe_show_first_run_banner()

        assert result is False
        assert capsys.readouterr().out == ""

    def test_returns_false_on_write_error(self, tmp_path: Path, capsys) -> None:
        marker = tmp_path / ".first_run_done"
        with (
            patch("helping_hands.cli.main._FIRST_RUN_DIR", tmp_path),
            patch("helping_hands.cli.main._FIRST_RUN_MARKER", marker),
            patch.object(Path, "write_text", side_effect=OSError("read-only")),
        ):
            result = _maybe_show_first_run_banner()

        assert result is False
