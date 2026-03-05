"""Tests for MCP server error paths and helper functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.lib.meta.tools.command import CommandResult
from helping_hands.server.mcp_server import (
    _command_result_to_dict,
    _repo_root,
    read_file,
    write_file,
)

# ---------------------------------------------------------------------------
# _repo_root
# ---------------------------------------------------------------------------


class TestRepoRoot:
    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        result = _repo_root(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_raises_on_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            _repo_root(str(tmp_path / "does-not-exist"))

    def test_raises_on_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "afile.txt"
        f.write_text("x")
        with pytest.raises(FileNotFoundError, match="not found"):
            _repo_root(str(f))


# ---------------------------------------------------------------------------
# _command_result_to_dict
# ---------------------------------------------------------------------------


class TestCommandResultToDict:
    def test_converts_all_fields(self) -> None:
        cr = CommandResult(
            command=["python", "-c", "1"],
            cwd="/tmp/repo",
            exit_code=0,
            stdout="ok\n",
            stderr="",
            timed_out=False,
        )
        d = _command_result_to_dict(cr)
        assert d == {
            "success": True,
            "command": ["python", "-c", "1"],
            "cwd": "/tmp/repo",
            "exit_code": 0,
            "timed_out": False,
            "stdout": "ok\n",
            "stderr": "",
        }

    def test_failure_case(self) -> None:
        cr = CommandResult(
            command=["false"],
            cwd="/tmp",
            exit_code=1,
            stdout="",
            stderr="error\n",
            timed_out=False,
        )
        d = _command_result_to_dict(cr)
        assert d["success"] is False
        assert d["exit_code"] == 1

    def test_timed_out_case(self) -> None:
        cr = CommandResult(
            command=["sleep", "999"],
            cwd="/tmp",
            exit_code=-1,
            stdout="",
            stderr="",
            timed_out=True,
        )
        d = _command_result_to_dict(cr)
        assert d["timed_out"] is True


# ---------------------------------------------------------------------------
# read_file error paths
# ---------------------------------------------------------------------------


class TestReadFileErrors:
    def test_is_a_directory_error(self, tmp_path: Path) -> None:
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="directory"):
            read_file(str(tmp_path), "subdir")

    def test_unicode_error(self, tmp_path: Path) -> None:
        (tmp_path / "binary.bin").write_bytes(b"\x80\x81\x82\xff\xfe")
        with (
            patch(
                "helping_hands.server.mcp_server.fs_tools.read_text_file",
                side_effect=UnicodeError("bad encoding"),
            ),
            pytest.raises(UnicodeError, match="not UTF-8"),
        ):
            read_file(str(tmp_path), "binary.bin")

    def test_value_error_wraps_path_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid file path"):
            read_file(str(tmp_path), "../../../etc/passwd")


# ---------------------------------------------------------------------------
# write_file error paths
# ---------------------------------------------------------------------------


class TestWriteFileErrors:
    def test_value_error_wraps_path_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid file path"):
            write_file(str(tmp_path), "../outside.txt", "content")
