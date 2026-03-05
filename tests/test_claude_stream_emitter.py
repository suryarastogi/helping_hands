"""Tests for _StreamJsonEmitter._summarize_tool in the Claude Code hand."""

from __future__ import annotations

from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter


class TestSummarizeTool:
    def test_read_includes_file_path(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Read", {"file_path": "/src/main.py"})
            == "Read /src/main.py"
        )

    def test_edit_includes_file_path(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Edit", {"file_path": "/src/app.py"})
            == "Edit /src/app.py"
        )

    def test_write_includes_file_path(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Write", {"file_path": "/out.txt"})
            == "Write /out.txt"
        )

    def test_bash_short_command(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("Bash", {"command": "ls -la"})
        assert result == "$ ls -la"

    def test_bash_truncates_long_command(self) -> None:
        long_cmd = "x" * 100
        result = _StreamJsonEmitter._summarize_tool("Bash", {"command": long_cmd})
        assert len(result) <= 82  # "$ " + 77 chars + "..."
        assert result.endswith("...")

    def test_glob_includes_pattern(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Glob", {"pattern": "**/*.py"})
            == "Glob **/*.py"
        )

    def test_grep_includes_pattern(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Grep", {"pattern": "def main"})
            == "Grep /def main/"
        )

    def test_unknown_tool_generic_format(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("CustomTool", {}) == "tool: CustomTool"
        )

    def test_missing_input_key_returns_empty_path(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("Read", {}) == "Read "
