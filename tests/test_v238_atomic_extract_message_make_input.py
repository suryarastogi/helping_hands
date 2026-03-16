"""Tests for v238: AtomicHand._extract_message DRY, _make_input None guard.

Validates:
- AtomicHand._extract_message static method (new)
- _make_input RuntimeError when _input_schema is None (both AtomicHand and BasicAtomicHand)
- run() uses _extract_message (not direct .chat_message access)
- stream() uses _extract_message (replaces inline hasattr checks)
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.atomic import AtomicHand
from helping_hands.lib.hands.v1.hand.base import HandResponse
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hand(tmp_path, **config_kwargs):
    """Build an AtomicHand with all heavy deps mocked out."""
    (tmp_path / "main.py").write_text("")
    repo_index = RepoIndex.from_path(tmp_path)
    defaults = {"repo": str(tmp_path), "model": "openai/gpt-test"}
    defaults.update(config_kwargs)
    config = Config(**defaults)

    mock_agent = MagicMock()
    mock_input_schema = MagicMock()

    with patch.object(AtomicHand, "_build_agent", return_value=mock_agent):
        hand = AtomicHand(config, repo_index)

    hand._input_schema = mock_input_schema
    return hand, mock_agent, mock_input_schema


async def _collect_stream(hand, prompt: str) -> list[str]:
    chunks: list[str] = []
    async for chunk in hand.stream(prompt):
        chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# AtomicHand._extract_message
# ---------------------------------------------------------------------------


class TestAtomicHandExtractMessage:
    """Tests for the new _extract_message static method on AtomicHand.

    Unlike BasicAtomicHand._extract_message (which falls back to str(response)),
    AtomicHand._extract_message returns "" when chat_message is absent or falsy.
    """

    def test_extracts_chat_message_attribute(self) -> None:
        """Returns str(chat_message) when attribute exists and is truthy."""
        response = SimpleNamespace(chat_message="hello world")
        assert AtomicHand._extract_message(response) == "hello world"

    def test_returns_empty_when_no_chat_message(self) -> None:
        """Returns empty string when no chat_message attribute."""
        assert AtomicHand._extract_message({"key": "value"}) == ""

    def test_returns_empty_when_chat_message_falsy(self) -> None:
        """Returns empty string when chat_message is falsy."""
        response = SimpleNamespace(chat_message="")
        assert AtomicHand._extract_message(response) == ""

    def test_returns_empty_when_chat_message_none(self) -> None:
        """Returns empty string when chat_message is None."""
        response = SimpleNamespace(chat_message=None)
        assert AtomicHand._extract_message(response) == ""

    def test_plain_string_input_returns_empty(self) -> None:
        """Plain string input without chat_message returns empty string."""
        assert AtomicHand._extract_message("plain text") == ""

    def test_numeric_chat_message_coerced_to_str(self) -> None:
        """Numeric chat_message is coerced to string."""
        response = SimpleNamespace(chat_message=42)
        assert AtomicHand._extract_message(response) == "42"


# ---------------------------------------------------------------------------
# _make_input RuntimeError guard
# ---------------------------------------------------------------------------


class TestMakeInputNoneGuard:
    """Tests for _make_input when _input_schema is None."""

    def test_atomic_hand_make_input_raises_when_schema_none(self, tmp_path) -> None:
        """AtomicHand._make_input raises RuntimeError if _input_schema is None."""
        hand, _, _ = _make_hand(tmp_path)
        hand._input_schema = None

        with pytest.raises(RuntimeError, match="_input_schema not initialised"):
            hand._make_input("test prompt")

    def test_basic_atomic_hand_make_input_raises_when_schema_none(
        self, tmp_path
    ) -> None:
        """BasicAtomicHand._make_input raises RuntimeError if _input_schema is None."""
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        (tmp_path / "main.py").write_text("")
        repo_index = RepoIndex.from_path(tmp_path)
        config = Config(repo=str(tmp_path), model="openai/gpt-test")

        with patch.object(BasicAtomicHand, "_build_agent", return_value=MagicMock()):
            hand = BasicAtomicHand(config, repo_index)

        hand._input_schema = None

        with pytest.raises(RuntimeError, match="_input_schema not initialised"):
            hand._make_input("test prompt")


# ---------------------------------------------------------------------------
# run() uses _extract_message
# ---------------------------------------------------------------------------


class TestRunUsesExtractMessage:
    """Verify run() delegates to _extract_message instead of direct attribute access."""

    def test_run_uses_extract_message_for_response(self, tmp_path) -> None:
        """run() should call _extract_message, not access .chat_message directly."""
        hand, mock_agent, _ = _make_hand(tmp_path)
        # Response without chat_message — _extract_message returns ""
        mock_response = SimpleNamespace(data="no chat_message here")
        mock_agent.run.return_value = mock_response

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            result = hand.run("prompt")

        assert isinstance(result, HandResponse)
        # AtomicHand._extract_message returns "" for no chat_message
        assert result.message == ""

    def test_run_extract_message_with_chat_message(self, tmp_path) -> None:
        """run() extracts chat_message via _extract_message."""
        hand, mock_agent, _ = _make_hand(tmp_path)
        mock_response = SimpleNamespace(chat_message="extracted!")
        mock_agent.run.return_value = mock_response

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            result = hand.run("prompt")

        assert result.message == "extracted!"


# ---------------------------------------------------------------------------
# stream() uses _extract_message
# ---------------------------------------------------------------------------


class TestStreamUsesExtractMessage:
    """Verify stream() delegates to _extract_message for all code paths."""

    def test_stream_assertion_fallback_uses_extract_message(self, tmp_path) -> None:
        """AssertionError fallback path uses _extract_message."""
        hand, mock_agent, _ = _make_hand(tmp_path)
        mock_agent.run_async.side_effect = AssertionError("no async")
        # Response with chat_message
        mock_agent.run.return_value = SimpleNamespace(chat_message="fallback content")

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert any("fallback content" in c for c in chunks)

    def test_stream_assertion_fallback_skips_no_chat_message(self, tmp_path) -> None:
        """AssertionError fallback with no chat_message yields nothing."""
        hand, mock_agent, _ = _make_hand(tmp_path)
        mock_agent.run_async.side_effect = AssertionError("no async")
        mock_agent.run.return_value = SimpleNamespace(data="no chat")

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        # No text content should be yielded
        assert not any(c.strip() and "PR" not in c for c in chunks)

    def test_stream_async_iter_uses_extract_message(self, tmp_path) -> None:
        """Async iterator path uses _extract_message."""
        hand, mock_agent, _ = _make_hand(tmp_path)

        async def _fake_aiter():
            yield SimpleNamespace(chat_message="chunk1")
            yield SimpleNamespace(data="no chat")  # no chat_message — skipped

        mock_agent.run_async.return_value = _fake_aiter()

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert "chunk1" in chunks
        # Second item has no chat_message, so _extract_message returns ""
        assert not any("no chat" in c for c in chunks)

    def test_stream_awaitable_uses_extract_message(self, tmp_path) -> None:
        """Awaitable path uses _extract_message."""
        hand, mock_agent, _ = _make_hand(tmp_path)

        async def _fake_coro():
            return SimpleNamespace(chat_message="awaited message")

        mock_agent.run_async.return_value = _fake_coro()

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert "awaited message" in chunks


# ---------------------------------------------------------------------------
# _extract_message consistency between AtomicHand and BasicAtomicHand
# ---------------------------------------------------------------------------


class TestExtractMessageConsistency:
    """Verify _extract_message behavior differences between AtomicHand and BasicAtomicHand.

    AtomicHand returns "" for no/falsy chat_message (single-shot stream pattern).
    BasicAtomicHand returns str(response) fallback (iterative delta pattern).
    Both agree when chat_message is present and truthy.
    """

    def test_both_agree_on_truthy_chat_message(self) -> None:
        """Both classes return the same result for a response with chat_message."""
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        response = SimpleNamespace(chat_message="test output")
        assert AtomicHand._extract_message(
            response
        ) == BasicAtomicHand._extract_message(response)

    def test_atomic_returns_empty_basic_returns_str_for_no_chat(self) -> None:
        """AtomicHand returns '' while BasicAtomicHand returns str(response)."""
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        response = {"key": "value"}
        assert AtomicHand._extract_message(response) == ""
        assert BasicAtomicHand._extract_message(response) == str(response)

    def test_atomic_returns_empty_basic_returns_str_for_falsy_chat(self) -> None:
        """AtomicHand returns '' while BasicAtomicHand returns str(response)."""
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        response = SimpleNamespace(chat_message="")
        assert AtomicHand._extract_message(response) == ""
        assert BasicAtomicHand._extract_message(response) == str(response)
