"""Tests for _StreamJsonEmitter helpers in the Claude Code hand.

Protects the stream-JSON parsing layer that bridges the `claude --output-format
stream-json` subprocess to the hand's async emit callback:
- `_summarize_tool` must produce human-readable one-liners for every tool class
  the Claude CLI emits (Read/Edit/Write/Glob/Grep/Bash/unknown); regressions
  cause the UI progress feed to show raw JSON blobs instead of readable labels.
- Bash commands are truncated to 80 chars to prevent flooding the progress feed
  with long shell invocations.
- `_label_msg` prefixes every emitted string with `[backend_label]` so that
  when multiple hands run concurrently their output streams are distinguishable.
- End-to-end: a tool_use event in the stream must trigger a labelled tool
  summary, and a text event must trigger a labelled text preview, verifying that
  the emitter correctly parses the `assistant` event JSON envelope.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

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


class TestStreamJsonEmitterLabelMsg:
    """v268: _label_msg prefixes messages with the backend label."""

    def _make_emitter(self, label: str = "test") -> _StreamJsonEmitter:
        return _StreamJsonEmitter(AsyncMock(), label)

    def test_basic_prefix(self) -> None:
        emitter = self._make_emitter("claude")
        assert emitter._label_msg("hello") == "[claude] hello"

    def test_empty_message(self) -> None:
        emitter = self._make_emitter("x")
        assert emitter._label_msg("") == "[x] "

    def test_preserves_inner_brackets(self) -> None:
        emitter = self._make_emitter("lab")
        assert emitter._label_msg("[info] done") == "[lab] [info] done"

    def test_label_used_in_tool_use_event(self) -> None:
        """Verify _label_msg is used when emitting tool use summaries."""
        collected: list[str] = []

        async def capture(text: str) -> None:
            collected.append(text)

        async def run() -> None:
            emitter = _StreamJsonEmitter(capture, "myhand")
            event = '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/a.py"}}]}}'
            await emitter(event + "\n")

        asyncio.run(run())
        assert any("[myhand] Read /a.py" in c for c in collected)

    def test_label_used_in_text_event(self) -> None:
        """Verify _label_msg is used when emitting text previews."""
        collected: list[str] = []

        async def capture(text: str) -> None:
            collected.append(text)

        async def run() -> None:
            emitter = _StreamJsonEmitter(capture, "back")
            event = '{"type":"assistant","message":{"content":[{"type":"text","text":"hi there"}]}}'
            await emitter(event + "\n")

        asyncio.run(run())
        assert any("[back] hi there" in c for c in collected)
