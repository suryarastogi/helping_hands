"""Tests for hhpy.helping_hands.hands.v1.hand."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from hhpy.helping_hands.hands.v1.hand import (
    AtomicHand,
    Hand,
    HandResponse,
    LangGraphHand,
)
from hhpy.helping_hands.lib.config import Config
from hhpy.helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> Config:
    return Config(repo="/tmp/fake", model="test-model")


@pytest.fixture()
def repo_index(tmp_path: Path) -> RepoIndex:
    (tmp_path / "main.py").write_text("")
    (tmp_path / "utils.py").write_text("")
    return RepoIndex.from_path(tmp_path)


# ---------------------------------------------------------------------------
# HandResponse
# ---------------------------------------------------------------------------


class TestHandResponse:
    def test_basic_response(self) -> None:
        resp = HandResponse(message="hello")
        assert resp.message == "hello"
        assert resp.metadata == {}

    def test_response_with_metadata(self) -> None:
        resp = HandResponse(message="hi", metadata={"backend": "test"})
        assert resp.metadata["backend"] == "test"


# ---------------------------------------------------------------------------
# Hand ABC
# ---------------------------------------------------------------------------


class TestHandABC:
    def test_cannot_instantiate_directly(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        with pytest.raises(TypeError):
            Hand(config, repo_index)  # type: ignore[abstract]

    def test_build_system_prompt(self, config: Config, repo_index: RepoIndex) -> None:
        class StubHand(Hand):
            def run(self, prompt: str) -> HandResponse:
                return HandResponse(message="")

            async def stream(self, prompt: str):  # type: ignore[override]
                yield ""

        hand = StubHand(config, repo_index)
        prompt = hand._build_system_prompt()
        assert "main.py" in prompt
        assert "utils.py" in prompt
        assert str(repo_index.root) in prompt

    def test_system_prompt_mentions_conventions(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        class StubHand(Hand):
            def run(self, prompt: str) -> HandResponse:
                return HandResponse(message="")

            async def stream(self, prompt: str):  # type: ignore[override]
                yield ""

        hand = StubHand(config, repo_index)
        prompt = hand._build_system_prompt()
        assert "conventions" in prompt.lower()


# ---------------------------------------------------------------------------
# LangGraphHand
# ---------------------------------------------------------------------------


class TestLangGraphHand:
    @patch.object(LangGraphHand, "_build_agent")
    def test_run(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        fake_msg = MagicMock()
        fake_msg.content = "Built your feature."
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_msg]}
        mock_build.return_value = mock_agent

        hand = LangGraphHand(config, repo_index)
        resp = hand.run("Add tests")

        assert resp.message == "Built your feature."
        assert resp.metadata["backend"] == "langgraph"
        assert resp.metadata["model"] == "test-model"
        mock_agent.invoke.assert_called_once()

    @patch.object(LangGraphHand, "_build_agent")
    def test_run_fallback_str(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        """When the last message has no .content attr, fall back to str()."""
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": ["plain string"]}
        mock_build.return_value = mock_agent

        hand = LangGraphHand(config, repo_index)
        resp = hand.run("hello")
        assert resp.message == "plain string"

    @patch.object(LangGraphHand, "_build_agent")
    def test_stream(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        chunk1 = MagicMock()
        chunk1.content = "Hello "
        chunk2 = MagicMock()
        chunk2.content = "world"

        async def fake_astream_events(*_a: Any, **_kw: Any):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk1},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk2},
            }
            yield {"event": "on_other_event", "data": {}}

        mock_agent = MagicMock()
        mock_agent.astream_events = fake_astream_events
        mock_build.return_value = mock_agent

        hand = LangGraphHand(config, repo_index)
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hi")
        )
        assert chunks == ["Hello ", "world"]


# ---------------------------------------------------------------------------
# AtomicHand
# ---------------------------------------------------------------------------


class _FakeInputSchema:
    """Stand-in for BasicChatInputSchema when atomic-agents isn't installed."""

    def __init__(self, chat_message: str = "") -> None:
        self.chat_message = chat_message


class TestAtomicHand:
    @patch.object(AtomicHand, "_build_agent")
    def test_run(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        fake_resp = MagicMock()
        fake_resp.chat_message = "Done building."
        mock_agent = MagicMock()
        mock_agent.run.return_value = fake_resp
        mock_build.return_value = mock_agent

        hand = AtomicHand(config, repo_index)
        hand._input_schema = _FakeInputSchema
        resp = hand.run("Add a feature")

        assert resp.message == "Done building."
        assert resp.metadata["backend"] == "atomic"
        assert resp.metadata["model"] == "test-model"
        mock_agent.run.assert_called_once()

    @patch.object(AtomicHand, "_build_agent")
    def test_stream(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        partial1 = MagicMock()
        partial1.chat_message = "Part 1"
        partial2 = MagicMock()
        partial2.chat_message = "Part 2"

        async def fake_run_async(_input: Any):
            yield partial1
            yield partial2

        mock_agent = MagicMock()
        mock_agent.run_async = fake_run_async
        mock_build.return_value = mock_agent

        hand = AtomicHand(config, repo_index)
        hand._input_schema = _FakeInputSchema
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        assert chunks == ["Part 1", "Part 2"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_stream(hand: Hand, prompt: str) -> list[str]:
    return [chunk async for chunk in hand.stream(prompt)]
