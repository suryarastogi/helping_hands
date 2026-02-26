"""Tests for helping_hands.lib.meta.tools.command."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta.tools import command as command_tools


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
