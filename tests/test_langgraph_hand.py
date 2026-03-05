"""Tests for LangGraphHand construction, run(), and stream() methods."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import HandResponse
from helping_hands.lib.hands.v1.hand.langgraph import LangGraphHand
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hand(tmp_path, **config_kwargs):
    """Build a LangGraphHand with _build_agent mocked out."""
    (tmp_path / "main.py").write_text("")
    repo_index = RepoIndex.from_path(tmp_path)
    defaults = {"repo": str(tmp_path), "model": "openai/gpt-test"}
    defaults.update(config_kwargs)
    config = Config(**defaults)

    mock_agent = MagicMock()

    with patch.object(LangGraphHand, "_build_agent", return_value=mock_agent):
        hand = LangGraphHand(config, repo_index)

    return hand, mock_agent


# ---------------------------------------------------------------------------
# _build_agent
# ---------------------------------------------------------------------------


class TestBuildAgent:
    def test_build_agent_calls_create_react_agent(self, tmp_path) -> None:
        (tmp_path / "main.py").write_text("")
        repo_index = RepoIndex.from_path(tmp_path)
        config = Config(repo=str(tmp_path), model="openai/gpt-test")

        mock_create = MagicMock(return_value=MagicMock())
        mock_llm = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "langgraph": MagicMock(),
                    "langgraph.prebuilt": MagicMock(create_react_agent=mock_create),
                },
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.langgraph.build_langchain_chat_model",
                return_value=mock_llm,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.langgraph.resolve_hand_model",
                return_value=SimpleNamespace(
                    model="gpt-test",
                    provider=SimpleNamespace(name="openai"),
                ),
            ),
        ):
            _hand = LangGraphHand(config, repo_index)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs[1]["model"] is mock_llm


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestRun:
    def test_run_returns_hand_response(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        last_msg = MagicMock()
        last_msg.content = "AI response"
        mock_agent.invoke.return_value = {"messages": [last_msg]}

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            result = hand.run("do something")

        assert isinstance(result, HandResponse)
        assert result.message == "AI response"
        assert result.metadata["backend"] == "langgraph"

    def test_run_fallback_str_when_no_content_attr(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        last_msg = "plain string message"
        mock_agent.invoke.return_value = {"messages": [last_msg]}

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            result = hand.run("prompt")

        assert result.message == "plain string message"

    def test_run_includes_pr_metadata(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        last_msg = MagicMock()
        last_msg.content = "result"
        mock_agent.invoke.return_value = {"messages": [last_msg]}

        pr_meta = {"pr_url": "https://github.com/o/r/pull/5"}
        with patch.object(hand, "_finalize_repo_pr", return_value=pr_meta):
            result = hand.run("prompt")

        assert result.metadata["pr_url"] == "https://github.com/o/r/pull/5"


# ---------------------------------------------------------------------------
# stream()
# ---------------------------------------------------------------------------


class TestStream:
    def test_stream_yields_chunks(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        chunk1 = MagicMock()
        chunk1.content = "Hello "
        chunk2 = MagicMock()
        chunk2.content = "world"

        async def _fake_events(*args, **kwargs):
            for chunk in [chunk1, chunk2]:
                yield {
                    "event": "on_chat_model_stream",
                    "data": {"chunk": chunk},
                }

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert "Hello " in chunks
        assert "world" in chunks

    def test_stream_skips_non_chat_events(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        async def _fake_events(*args, **kwargs):
            yield {"event": "on_tool_start", "data": {}}
            chunk = MagicMock()
            chunk.content = "real"
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk},
            }

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert chunks == ["real"]

    def test_stream_skips_empty_content(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        chunk_empty = MagicMock()
        chunk_empty.content = ""
        chunk_real = MagicMock()
        chunk_real.content = "data"

        async def _fake_events(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk_empty},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk_real},
            }

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert chunks == ["data"]

    def test_stream_yields_pr_url(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        async def _fake_events(*args, **kwargs):
            chunk = MagicMock()
            chunk.content = "done"
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk},
            }

        mock_agent.astream_events = _fake_events

        pr_meta = {"pr_url": "https://github.com/o/r/pull/99"}
        with patch.object(hand, "_finalize_repo_pr", return_value=pr_meta):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert any("PR created" in c for c in chunks)

    def test_stream_no_pr_url_no_extra_yield(self, tmp_path) -> None:
        hand, mock_agent = _make_hand(tmp_path)

        async def _fake_events(*args, **kwargs):
            chunk = MagicMock()
            chunk.content = "done"
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk},
            }

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert not any("PR created" in c for c in chunks)


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


async def _collect_stream(hand, prompt: str) -> list[str]:
    chunks: list[str] = []
    async for chunk in hand.stream(prompt):
        chunks.append(chunk)
    return chunks
