"""Tests for _LinePrefixEmitter line buffering and prefixing.

_LinePrefixEmitter wraps a streaming emitter to prefix every output line with
``[label] ``.  Correct behavior matters because it controls how CLI subprocess
output is presented to users — double-prefixing clutters output, while missing
prefixes make it impossible to tell which backend produced a line.
"""

from __future__ import annotations

import asyncio

from helping_hands.lib.hands.v1.hand.cli.base import _LinePrefixEmitter


def _run(coro):
    return asyncio.run(coro)


class TestLinePrefixEmitterCall:
    """Test __call__ — buffering and line emission."""

    def test_prefixes_complete_line(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "test")
        _run(emitter("hello world\n"))
        assert emitted == ["[test] hello world\n"]

    def test_blank_line_emitted_without_prefix(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "test")
        _run(emitter("\n"))
        assert emitted == ["\n"]

    def test_whitespace_only_line_treated_as_blank(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "test")
        _run(emitter("   \n"))
        assert emitted == ["\n"]

    def test_already_prefixed_line_not_doubled(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "test")
        _run(emitter("[test] already prefixed\n"))
        assert emitted == ["[test] already prefixed\n"]

    def test_multiple_lines_in_one_chunk(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "x")
        _run(emitter("line1\nline2\n"))
        assert emitted == ["[x] line1\n", "[x] line2\n"]

    def test_partial_chunk_buffered_until_newline(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "buf")
        _run(emitter("partial"))
        assert emitted == []
        _run(emitter(" rest\n"))
        assert emitted == ["[buf] partial rest\n"]


class TestLinePrefixEmitterFlush:
    """Test flush — emit remaining buffer."""

    def test_flush_prefixes_remaining_text(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "f")
        _run(emitter("trailing"))
        assert emitted == []
        _run(emitter.flush())
        assert emitted == ["[f] trailing"]

    def test_flush_already_prefixed_buffer(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "f")
        _run(emitter("[f] control msg"))
        _run(emitter.flush())
        assert emitted == ["[f] control msg"]

    def test_flush_empty_buffer_emits_nothing(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "f")
        _run(emitter.flush())
        assert emitted == []

    def test_flush_whitespace_only_buffer_emits_nothing(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        emitter = _LinePrefixEmitter(emit, "f")
        _run(emitter("   "))
        _run(emitter.flush())
        assert emitted == []
