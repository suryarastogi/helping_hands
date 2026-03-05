"""Tests for AtomicHand construction, run(), and stream() methods."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


# ---------------------------------------------------------------------------
# _build_agent
# ---------------------------------------------------------------------------


class TestBuildAgent:
    def test_build_agent_constructs_atomic_agent(self, tmp_path) -> None:
        """_build_agent should import atomic_agents and build an agent."""
        (tmp_path / "main.py").write_text("")
        repo_index = RepoIndex.from_path(tmp_path)
        config = Config(repo=str(tmp_path), model="openai/gpt-test")

        mock_atomic_agent = MagicMock()
        mock_config = MagicMock()
        mock_schema = MagicMock()
        mock_history = MagicMock()
        mock_prompt_gen = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "atomic_agents": MagicMock(
                        AgentConfig=mock_config,
                        AtomicAgent=mock_atomic_agent,
                        BasicChatInputSchema=mock_schema,
                    ),
                    "atomic_agents.context": MagicMock(
                        ChatHistory=MagicMock(return_value=mock_history),
                        SystemPromptGenerator=MagicMock(return_value=mock_prompt_gen),
                    ),
                },
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.atomic.build_atomic_client",
                return_value=MagicMock(),
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.atomic.resolve_hand_model",
                return_value=SimpleNamespace(
                    model="gpt-test",
                    provider=SimpleNamespace(name="openai"),
                ),
            ),
        ):
            hand = AtomicHand(config, repo_index)

        assert hand._input_schema is mock_schema
        mock_atomic_agent.assert_called_once()


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestRun:
    def test_run_returns_hand_response(self, tmp_path) -> None:
        hand, mock_agent, _mock_input_schema = _make_hand(tmp_path)
        mock_response = MagicMock()
        mock_response.chat_message = "Done!"
        mock_agent.run.return_value = mock_response

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            result = hand.run("do something")

        assert isinstance(result, HandResponse)
        assert result.message == "Done!"
        assert result.metadata["backend"] == "atomic"

    def test_run_includes_pr_metadata(self, tmp_path) -> None:
        hand, mock_agent, _ = _make_hand(tmp_path)
        mock_response = MagicMock()
        mock_response.chat_message = "Result"
        mock_agent.run.return_value = mock_response

        pr_meta = {"pr_url": "https://github.com/o/r/pull/1"}
        with patch.object(hand, "_finalize_repo_pr", return_value=pr_meta):
            result = hand.run("prompt")

        assert result.metadata["pr_url"] == "https://github.com/o/r/pull/1"


# ---------------------------------------------------------------------------
# stream()
# ---------------------------------------------------------------------------


class TestStream:
    def test_stream_assertion_error_fallback(self, tmp_path) -> None:
        """When run_async raises AssertionError, stream falls back to sync."""
        hand, mock_agent, _mock_input_schema = _make_hand(tmp_path)

        mock_agent.run_async.side_effect = AssertionError("no async")
        sync_response = MagicMock()
        sync_response.chat_message = "sync result"
        mock_agent.run.return_value = sync_response

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert "sync result" in chunks

    def test_stream_async_iterator_path(self, tmp_path) -> None:
        """When run_async returns an async iterable, stream yields chunks."""
        hand, mock_agent, _ = _make_hand(tmp_path)

        async def _fake_aiter():
            for msg in ["chunk1", "chunk2"]:
                obj = MagicMock()
                obj.chat_message = msg
                yield obj

        mock_agent.run_async.return_value = _fake_aiter()

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert "chunk1" in chunks
        assert "chunk2" in chunks

    def test_stream_awaitable_path(self, tmp_path) -> None:
        """When run_async returns a non-iterable awaitable, stream awaits it."""
        hand, mock_agent, _ = _make_hand(tmp_path)

        async def _fake_coro():
            result = MagicMock()
            result.chat_message = "awaited"
            return result

        mock_agent.run_async.return_value = _fake_coro()

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert "awaited" in chunks

    def test_stream_awaitable_assertion_error_fallback(self, tmp_path) -> None:
        """When awaiting run_async result raises AssertionError, fall back to sync."""
        hand, mock_agent, _ = _make_hand(tmp_path)

        async def _failing_coro():
            raise AssertionError("no async support")

        mock_agent.run_async.return_value = _failing_coro()
        sync_response = MagicMock()
        sync_response.chat_message = "sync fallback"
        mock_agent.run.return_value = sync_response

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert "sync fallback" in chunks

    def test_stream_yields_pr_url(self, tmp_path) -> None:
        """When finalization produces a PR URL, stream yields it."""
        hand, mock_agent, _ = _make_hand(tmp_path)
        mock_agent.run_async.side_effect = AssertionError("no async")
        sync_response = MagicMock()
        sync_response.chat_message = "done"
        mock_agent.run.return_value = sync_response

        pr_meta = {"pr_url": "https://github.com/o/r/pull/42"}
        with patch.object(hand, "_finalize_repo_pr", return_value=pr_meta):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert any("PR created" in c for c in chunks)

    def test_stream_no_pr_url_no_extra_yield(self, tmp_path) -> None:
        """When no PR URL, stream should not yield the PR message."""
        hand, mock_agent, _ = _make_hand(tmp_path)
        mock_agent.run_async.side_effect = AssertionError("no async")
        sync_response = MagicMock()
        sync_response.chat_message = "done"
        mock_agent.run.return_value = sync_response

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "prompt"))

        assert not any("PR created" in c for c in chunks)


# ---------------------------------------------------------------------------
# _make_input
# ---------------------------------------------------------------------------


class TestMakeInput:
    def test_make_input_calls_schema(self, tmp_path) -> None:
        hand, _, mock_input_schema = _make_hand(tmp_path)
        hand._make_input("hello")
        mock_input_schema.assert_called_once_with(chat_message="hello")


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


async def _collect_stream(hand, prompt: str) -> list[str]:
    chunks: list[str] = []
    async for chunk in hand.stream(prompt):
        chunks.append(chunk)
    return chunks
