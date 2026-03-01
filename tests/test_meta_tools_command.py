"""Tests for helping_hands.lib.meta.tools.command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta.tools import command as command_tools

# ---------------------------------------------------------------------------
# Private helper tests
# ---------------------------------------------------------------------------


class TestNormalizeArgs:
    def test_none_returns_empty(self) -> None:
        assert command_tools._normalize_args(None) == []

    def test_empty_list_returns_empty(self) -> None:
        assert command_tools._normalize_args([]) == []

    def test_string_list_passes_through(self) -> None:
        assert command_tools._normalize_args(["a", "b"]) == ["a", "b"]

    def test_tuple_accepted(self) -> None:
        assert command_tools._normalize_args(("x", "y")) == ["x", "y"]

    def test_non_string_element_raises(self) -> None:
        with pytest.raises(TypeError, match="args must contain only strings"):
            command_tools._normalize_args([123])  # type: ignore[list-item]


class TestResolveCwd:
    def test_none_returns_root(self, tmp_path: Path) -> None:
        result = command_tools._resolve_cwd(tmp_path, None)
        assert result == tmp_path.resolve()

    def test_blank_returns_root(self, tmp_path: Path) -> None:
        result = command_tools._resolve_cwd(tmp_path, "  ")
        assert result == tmp_path.resolve()

    def test_valid_subdir(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        result = command_tools._resolve_cwd(tmp_path, "sub")
        assert result == sub.resolve()

    def test_nonexistent_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(NotADirectoryError):
            command_tools._resolve_cwd(tmp_path, "nope")

    def test_file_as_cwd_raises(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("x")
        with pytest.raises(NotADirectoryError):
            command_tools._resolve_cwd(tmp_path, "file.txt")


class TestResolvePythonCommand:
    def test_empty_version_raises(self) -> None:
        with pytest.raises(ValueError, match="python_version is required"):
            command_tools._resolve_python_command("")

    @patch("helping_hands.lib.meta.tools.command.shutil.which")
    def test_prefers_uv(self, mock_which: MagicMock) -> None:
        mock_which.side_effect = lambda cmd: "/usr/bin/uv" if cmd == "uv" else None
        result = command_tools._resolve_python_command("3.13")
        assert result == ["uv", "run", "--python", "3.13", "python"]

    @patch("helping_hands.lib.meta.tools.command.shutil.which")
    def test_falls_back_to_direct(self, mock_which: MagicMock) -> None:
        def which_lookup(cmd: str) -> str | None:
            if cmd == "uv":
                return None
            if cmd == "python3.13":
                return "/usr/bin/python3.13"
            return None

        mock_which.side_effect = which_lookup
        result = command_tools._resolve_python_command("3.13")
        assert result == ["python3.13"]

    @patch("helping_hands.lib.meta.tools.command.shutil.which")
    def test_raises_when_nothing_found(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        with pytest.raises(RuntimeError, match="Python runner unavailable"):
            command_tools._resolve_python_command("3.99")


class TestRunCommand:
    def test_successful_command(self, tmp_path: Path) -> None:
        result = command_tools._run_command(["echo", "ok"], cwd=tmp_path, timeout_s=10)
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout.strip() == "ok"
        assert result.timed_out is False

    def test_nonzero_exit_code(self, tmp_path: Path) -> None:
        result = command_tools._run_command(
            [sys.executable, "-c", "import sys; sys.exit(42)"],
            cwd=tmp_path,
            timeout_s=10,
        )
        assert result.success is False
        assert result.exit_code == 42
        assert result.timed_out is False

    def test_zero_timeout_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="timeout_s must be > 0"):
            command_tools._run_command(["echo"], cwd=tmp_path, timeout_s=0)

    def test_negative_timeout_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="timeout_s must be > 0"):
            command_tools._run_command(["echo"], cwd=tmp_path, timeout_s=-1)

    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_timeout_produces_timed_out_result(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "999"], timeout=1, output="partial", stderr="err"
        )
        result = command_tools._run_command(["sleep", "999"], cwd=tmp_path, timeout_s=1)
        assert result.timed_out is True
        assert result.exit_code == 124
        assert result.success is False
        assert "timed out" in result.stderr

    @patch("helping_hands.lib.meta.tools.command.subprocess.run")
    def test_timeout_with_none_output(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep"], timeout=1, output=None, stderr=None
        )
        result = command_tools._run_command(["sleep"], cwd=tmp_path, timeout_s=1)
        assert result.timed_out is True
        assert result.stdout == ""

    def test_captures_stderr(self, tmp_path: Path) -> None:
        result = command_tools._run_command(
            [sys.executable, "-c", "import sys; sys.stderr.write('warn\\n')"],
            cwd=tmp_path,
            timeout_s=10,
        )
        assert "warn" in result.stderr


class TestCommandResultSuccess:
    def test_success_when_zero_and_not_timed_out(self) -> None:
        r = command_tools.CommandResult(
            command=["echo"],
            cwd="/tmp",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
        )
        assert r.success is True

    def test_not_success_when_nonzero(self) -> None:
        r = command_tools.CommandResult(
            command=["false"],
            cwd="/tmp",
            exit_code=1,
            stdout="",
            stderr="",
            timed_out=False,
        )
        assert r.success is False

    def test_not_success_when_timed_out(self) -> None:
        r = command_tools.CommandResult(
            command=["sleep"],
            cwd="/tmp",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=True,
        )
        assert r.success is False


# ---------------------------------------------------------------------------
# Public API tests
# ---------------------------------------------------------------------------


class TestRunPythonCode:
    @patch("helping_hands.lib.meta.tools.command._resolve_python_command")
    def test_executes_inline_code(
        self,
        mock_resolve_python: MagicMock,
    ) -> None:
        mock_resolve_python.return_value = [sys.executable]
        result = command_tools.run_python_code(
            Path.cwd(),
            code="print('ok')",
            python_version="3.13",
        )
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout.strip() == "ok"

    @patch("helping_hands.lib.meta.tools.command._resolve_python_command")
    def test_passes_args_to_inline_code(
        self,
        mock_resolve_python: MagicMock,
    ) -> None:
        mock_resolve_python.return_value = [sys.executable]
        result = command_tools.run_python_code(
            Path.cwd(),
            code="import sys; print(sys.argv[1])",
            args=["hello"],
        )
        assert result.success is True
        assert result.stdout.strip() == "hello"

    def test_rejects_empty_code(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            command_tools.run_python_code(Path.cwd(), code="   ")


class TestRunPythonScript:
    @patch("helping_hands.lib.meta.tools.command._resolve_python_command")
    def test_executes_repo_relative_script(
        self,
        mock_resolve_python: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve_python.return_value = [sys.executable]
        script = tmp_path / "scripts" / "echo.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("import sys\nprint(sys.argv[1])\n", encoding="utf-8")

        result = command_tools.run_python_script(
            tmp_path,
            script_path="scripts/echo.py",
            args=["hi"],
        )
        assert result.success is True
        assert result.stdout.strip() == "hi"

    def test_rejects_path_escape(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            command_tools.run_python_script(tmp_path, script_path="../outside.py")

    def test_rejects_nonexistent_script(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="script not found"):
            command_tools.run_python_script(tmp_path, script_path="missing.py")

    def test_rejects_directory_as_script(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        with pytest.raises(IsADirectoryError, match="directory"):
            command_tools.run_python_script(tmp_path, script_path="subdir")


class TestRunBashScript:
    def test_executes_inline_script(self, tmp_path: Path) -> None:
        result = command_tools.run_bash_script(
            tmp_path,
            inline_script="echo inline-ok",
        )
        assert result.success is True
        assert result.stdout.strip() == "inline-ok"

    def test_executes_repo_relative_script(self, tmp_path: Path) -> None:
        script = tmp_path / "scripts" / "echo.sh"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("echo file-ok", encoding="utf-8")

        result = command_tools.run_bash_script(
            tmp_path,
            script_path="scripts/echo.sh",
        )
        assert result.success is True
        assert result.stdout.strip() == "file-ok"

    def test_requires_exactly_one_script_source(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            command_tools.run_bash_script(tmp_path)
        with pytest.raises(ValueError):
            command_tools.run_bash_script(
                tmp_path,
                script_path="scripts/echo.sh",
                inline_script="echo hi",
            )
