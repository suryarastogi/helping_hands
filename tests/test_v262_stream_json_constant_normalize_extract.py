"""Guards the Claude CLI streaming pipeline against format drift and
malformed events that would silently break real-time progress output.

_OUTPUT_FORMAT_STREAM_JSON must equal "stream-json"; any drift causes the
Claude binary to emit non-streaming output or fail to start.
_normalize_preview() must strip/collapse newlines so multi-line assistant
text renders as a clean one-line progress update in the task status UI.
_extract_message_blocks() must return [] (not raise) for non-dict message
values the stream legitimately produces, otherwise _process_line crashes
and the entire streaming session is lost.
"""

from __future__ import annotations

import asyncio
import json


# ===========================================================================
# _OUTPUT_FORMAT_STREAM_JSON constant
# ===========================================================================
class TestOutputFormatStreamJson:
    """Verify the _OUTPUT_FORMAT_STREAM_JSON constant."""

    def test_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _OUTPUT_FORMAT_STREAM_JSON,
        )

        assert _OUTPUT_FORMAT_STREAM_JSON == "stream-json"

    def test_is_str(
        self,
    ) -> None:  # TODO: CLEANUP CANDIDATE — asserts type, not behavior; test_value already covers this
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _OUTPUT_FORMAT_STREAM_JSON,
        )

        assert isinstance(_OUTPUT_FORMAT_STREAM_JSON, str)

    def test_in_all(self) -> None:  # TODO: CLEANUP CANDIDATE — stylistic __all__ check
        from helping_hands.lib.hands.v1.hand.cli.claude import __all__

        assert "_OUTPUT_FORMAT_STREAM_JSON" in __all__

    def test_importable_from_docker_sandbox(self) -> None:
        """Verify docker_sandbox_claude can import the constant."""
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (  # noqa: F401
            _OUTPUT_FORMAT_STREAM_JSON,
        )


# ===========================================================================
# _StreamJsonEmitter._normalize_preview
# ===========================================================================
class TestNormalizePreview:
    """Verify the _normalize_preview static method."""

    def test_strips_whitespace(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._normalize_preview("  hello  ") == "hello"

    def test_replaces_newlines_with_space(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._normalize_preview("a\nb\nc") == "a b c"

    def test_strips_and_replaces(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._normalize_preview("  a\nb  ") == "a b"

    def test_empty_string(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._normalize_preview("") == ""

    def test_only_whitespace(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._normalize_preview("   \n  ") == ""

    def test_no_change_needed(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._normalize_preview("hello world") == "hello world"

    def test_multiple_newlines(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._normalize_preview("a\n\nb") == "a  b"

    def test_tabs_preserved(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        # strip() removes leading/trailing tabs, but internal tabs are preserved
        assert _StreamJsonEmitter._normalize_preview("\ta\tb\t") == "a\tb"


# ===========================================================================
# _StreamJsonEmitter._extract_message_blocks
# ===========================================================================
class TestExtractMessageBlocks:
    """Verify the _extract_message_blocks static method."""

    def test_valid_message_with_content(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        event = {"message": {"content": [{"type": "text", "text": "hi"}]}}
        blocks = _StreamJsonEmitter._extract_message_blocks(event)
        assert blocks == [{"type": "text", "text": "hi"}]

    def test_message_not_dict_returns_empty(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert (
            _StreamJsonEmitter._extract_message_blocks({"message": "not a dict"}) == []
        )

    def test_message_is_none_returns_empty(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._extract_message_blocks({"message": None}) == []

    def test_no_message_key_returns_empty(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._extract_message_blocks({}) == []

    def test_message_dict_no_content_returns_empty_list(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._extract_message_blocks({"message": {}}) == []

    def test_message_is_list_returns_empty(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._extract_message_blocks({"message": [1, 2]}) == []

    def test_message_is_int_returns_empty(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        assert _StreamJsonEmitter._extract_message_blocks({"message": 42}) == []

    def test_multiple_blocks(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        blocks = [{"type": "text"}, {"type": "tool_use"}]
        event = {"message": {"content": blocks}}
        assert _StreamJsonEmitter._extract_message_blocks(event) == blocks

    def test_empty_content_list(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        event = {"message": {"content": []}}
        assert _StreamJsonEmitter._extract_message_blocks(event) == []


# ===========================================================================
# Integration: verify _process_line still works after refactoring
# ===========================================================================
class TestProcessLineIntegration:
    """Smoke tests verifying _process_line uses the new helpers correctly."""

    @staticmethod
    def _make_emitter():
        """Return a list and an async emitter that appends to it."""
        lines: list[str] = []

        async def emit(text: str) -> None:
            lines.append(text)

        return lines, emit

    def test_assistant_text_uses_normalize(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        lines, emit = self._make_emitter()
        parser = _StreamJsonEmitter(emit, "test")
        event = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "  hello\nworld  "}],
            },
        }
        asyncio.run(parser._process_line(json.dumps(event)))
        assert any("hello world" in line for line in lines)

    def test_user_tool_result_uses_normalize(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        lines, emit = self._make_emitter()
        parser = _StreamJsonEmitter(emit, "test")
        event = {
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "content": "  line1\nline2  "}],
            },
        }
        asyncio.run(parser._process_line(json.dumps(event)))
        assert any("line1 line2" in line for line in lines)

    def test_non_dict_message_skipped(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        lines, emit = self._make_emitter()
        parser = _StreamJsonEmitter(emit, "test")
        event = {"type": "assistant", "message": "not a dict"}
        asyncio.run(parser._process_line(json.dumps(event)))
        # No output emitted for non-dict message
        assert lines == []
