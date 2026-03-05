"""Tests for command.py coverage gaps.

Covers _resolve_python_command, _run_command timeout, run_python_code empty
code validation, run_python_script/run_bash_script error paths.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta.tools.command import (
    _resolve_python_command,
    _run_command,
    run_bash_script,
    run_python_code,
    run_python_script,
)

# ---------------------------------------------------------------------------
# _resolve_python_command
# ---------------------------------------------------------------------------


class TestResolvePythonCommand:
    @patch("helping_hands.lib.meta.tools.command.shutil.which")
    def test_returns_uv_when_available(self, mock_which: MagicMock) -> None:
        mock_which.side_effect = lambda cmd: "/usr/bin/uv" if cmd == "uv" else None
        result = _resolve_python_command("3.13")
        assert result == ["uv", "run", "--python", "3.13", "python"]

    @patch("helping_hands.lib.meta.tools.command.shutil.which")
    def test_returns_direct_python_when_uv_missing(self, mock_which: MagicMock) -> None:
        def which_side_effect(cmd: str) -> str | None:
            if cmd == "uv":
                return None
            if cmd == "python3.12":
                return "/usr/bin/python3.12"
            return None

        mock_which.side_effect = which_side_effect
        result = _resolve_python_command("3.12")
        assert result == ["python3.12"]

    @patch("helping_hands.lib.meta.tools.command.shutil.which", return_value=None)
    def test_raises_when_neither_available(self, _mock: MagicMock) -> None:
        with pytest.raises(RuntimeError, match="Python runner unavailable"):
            _resolve_python_command("3.13")

    def test_raises_on_empty_version(self) -> None:
        with pytest.raises(ValueError, match="python_version is required"):
            _resolve_python_command("")

    def test_raises_on_whitespace_version(self) -> None:
        with pytest.raises(ValueError, match="python_version is required"):
            _resolve_python_command("   ")


# ---------------------------------------------------------------------------
# _run_command — timeout handling
# ---------------------------------------------------------------------------


class TestRunCommandTimeout:
    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_returns_timeout_result(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "100"], timeout=5, output="partial", stderr="err"
        )
        result = _run_command(["sleep", "100"], cwd=Path("/tmp"), timeout_s=5)
        assert result.timed_out is True
        assert result.exit_code == 124
        assert "timed out after 5s" in result.stderr

    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_handles_none_output_on_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["sleep"], timeout=10)
        result = _run_command(["sleep"], cwd=Path("/tmp"), timeout_s=10)
        assert result.timed_out is True
        assert result.stdout == ""
        assert "timed out after 10s" in result.stderr

    def test_raises_on_zero_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s must be > 0"):
            _run_command(["echo"], cwd=Path("/tmp"), timeout_s=0)

    def test_raises_on_negative_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s must be > 0"):
            _run_command(["echo"], cwd=Path("/tmp"), timeout_s=-1)


# ---------------------------------------------------------------------------
# run_python_code — empty code
# ---------------------------------------------------------------------------


class TestRunPythonCodeValidation:
    def test_rejects_empty_code(self) -> None:
        with pytest.raises(ValueError, match="code must be non-empty"):
            run_python_code(Path("/tmp"), code="")

    def test_rejects_whitespace_code(self) -> None:
        with pytest.raises(ValueError, match="code must be non-empty"):
            run_python_code(Path("/tmp"), code="   \n  ")


# ---------------------------------------------------------------------------
# run_python_script — error paths
# ---------------------------------------------------------------------------


class TestRunPythonScriptErrors:
    def test_rejects_missing_script(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="script not found"):
            run_python_script(tmp_path, script_path="nonexistent.py")

    def test_rejects_directory_as_script(self, tmp_path: Path) -> None:
        subdir = tmp_path / "scripts"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="script path is a directory"):
            run_python_script(tmp_path, script_path="scripts")


# ---------------------------------------------------------------------------
# run_bash_script — error paths
# ---------------------------------------------------------------------------


class TestRunBashScriptErrors:
    def test_rejects_missing_script(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="script not found"):
            run_bash_script(tmp_path, script_path="nonexistent.sh")

    def test_rejects_directory_as_script(self, tmp_path: Path) -> None:
        subdir = tmp_path / "scripts"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="script path is a directory"):
            run_bash_script(tmp_path, script_path="scripts")

    def test_rejects_both_sources_empty(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            run_bash_script(tmp_path, script_path="", inline_script="")

    def test_inline_script_passes_args(self, tmp_path: Path) -> None:
        result = run_bash_script(
            tmp_path,
            inline_script='echo "arg=$1"',
            args=["hello"],
        )
        assert result.success is True
        assert "arg=hello" in result.stdout
