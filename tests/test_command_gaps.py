"""Tests for command.py error paths and edge cases.

Protects the safety and reliability boundaries of the command-execution tools
that hands use to run AI-generated code inside the repo workspace:
- `_resolve_python_command` must prefer `uv run --python` when `uv` is
  available (ensuring version pinning), fall back to a bare `python3.x`
  binary, and raise `RuntimeError` rather than silently running the wrong
  interpreter or `ValueError` on blank version strings.
- `_run_command` must translate `subprocess.TimeoutExpired` into a
  `CommandResult` with `timed_out=True` and exit code 124 (coreutils convention)
  so callers can detect hangs without catching exceptions; it must also map
  `FileNotFoundError` → exit 127 and `OSError` → exit 126, preserving Unix
  conventions that downstream tooling (e.g. CI reporters) may depend on.
- `run_python_code` must reject empty or whitespace-only code strings before
  spawning a subprocess; omitting this check wastes a process and may confuse
  the AI with an uninformative empty-output result.
- `run_python_script` and `run_bash_script` must raise typed errors
  (`FileNotFoundError`, `IsADirectoryError`, `ValueError`) for missing scripts,
  directory paths, and ambiguous dual-source invocations before touching the
  filesystem or spawning processes.
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
        with pytest.raises(ValueError, match="timeout_s must be positive"):
            _run_command(["echo"], cwd=Path("/tmp"), timeout_s=0)

    def test_raises_on_negative_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s must be positive"):
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

    def test_rejects_both_sources_none(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            run_bash_script(tmp_path, script_path=None, inline_script=None)


# ---------------------------------------------------------------------------
# _run_command — FileNotFoundError / OSError handling
# ---------------------------------------------------------------------------


class TestRunCommandExecErrors:
    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_returns_127_for_missing_executable(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = _run_command(["nonexistent-binary"], cwd=Path("/tmp"), timeout_s=10)
        assert result.exit_code == 127
        assert result.timed_out is False
        assert "command not found" in result.stderr
        assert "nonexistent-binary" in result.stderr
        assert result.stdout == ""

    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_returns_126_for_os_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("Permission denied")
        result = _run_command(["restricted-cmd"], cwd=Path("/tmp"), timeout_s=10)
        assert result.exit_code == 126
        assert result.timed_out is False
        assert "cannot execute command" in result.stderr
        assert "Permission denied" in result.stderr
        assert result.stdout == ""

    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_command_not_found_preserves_command_list(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = _run_command(
            ["missing", "--flag", "arg"], cwd=Path("/tmp"), timeout_s=5
        )
        assert result.command == ["missing", "--flag", "arg"]
        assert result.cwd == "/tmp"

    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_command_not_found_not_successful(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = _run_command(["nope"], cwd=Path("/tmp"), timeout_s=5)
        assert result.success is False

    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_os_error_not_successful(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("Exec format error")
        result = _run_command(["bad-binary"], cwd=Path("/tmp"), timeout_s=5)
        assert result.success is False


# ---------------------------------------------------------------------------
# run_bash_script — inline passthrough
# ---------------------------------------------------------------------------


class TestRunBashScriptInline:
    def test_inline_script_passes_args(self, tmp_path: Path) -> None:
        result = run_bash_script(
            tmp_path,
            inline_script='echo "arg=$1"',
            args=["hello"],
        )
        assert result.success is True
        assert "arg=hello" in result.stdout
