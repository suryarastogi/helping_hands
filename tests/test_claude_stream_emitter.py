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


class TestStreamJsonEmitterEdgeCases:
    """Tests for non-dict JSON events and non-dict blocks in _StreamJsonEmitter."""

    def test_json_primitive_string_passes_through(self) -> None:
        """A JSON string literal (not a dict) should be passed through verbatim."""
        collected: list[str] = []

        async def capture(text: str) -> None:
            collected.append(text)

        async def run() -> None:
            emitter = _StreamJsonEmitter(capture, "test")
            # A valid JSON string (not an object)
            await emitter('"hello world"\n')

        asyncio.run(run())
        assert any('"hello world"' in c for c in collected)

    def test_json_primitive_number_passes_through(self) -> None:
        """A JSON number (not a dict) should be passed through verbatim."""
        collected: list[str] = []

        async def capture(text: str) -> None:
            collected.append(text)

        async def run() -> None:
            emitter = _StreamJsonEmitter(capture, "test")
            await emitter("42\n")

        asyncio.run(run())
        assert any("42" in c for c in collected)

    def test_non_dict_block_in_assistant_message_skipped(self) -> None:
        """Non-dict blocks in assistant message content should be skipped."""
        collected: list[str] = []

        async def capture(text: str) -> None:
            collected.append(text)

        async def run() -> None:
            emitter = _StreamJsonEmitter(capture, "hand")
            # Content array has a string block (non-dict) mixed with a valid tool_use
            event = '{"type":"assistant","message":{"content":["stray string",{"type":"tool_use","name":"Read","input":{"file_path":"/b.py"}}]}}'
            await emitter(event + "\n")

        asyncio.run(run())
        # The valid tool_use should still be emitted
        assert any("[hand] Read /b.py" in c for c in collected)
        # The stray string should not appear as a labelled message
        assert not any("stray string" in c for c in collected)

    def test_non_dict_block_in_user_message_skipped(self) -> None:
        """Non-dict blocks in user message content should be skipped."""
        collected: list[str] = []

        async def capture(text: str) -> None:
            collected.append(text)

        async def run() -> None:
            emitter = _StreamJsonEmitter(capture, "hand")
            # Content has a non-dict element followed by a valid tool_result
            event = '{"type":"user","message":{"content":[123,{"type":"tool_result","content":"done ok"}]}}'
            await emitter(event + "\n")

        asyncio.run(run())
        # The tool result content should be emitted
        assert any("done ok" in c for c in collected)
        # The raw number should not appear as a labelled message
        assert not any("123" in c for c in collected)
