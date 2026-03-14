"""Tests for helping_hands.lib.hands.v1.hand."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand import (
    AtomicHand,
    ClaudeCodeHand,
    CodexCLIHand,
    GeminiCLIHand,
    Hand,
    HandResponse,
    LangGraphHand,
    create_hand,
)
from helping_hands.lib.repo import RepoIndex

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
# ClaudeCodeHand (subprocess)
# ---------------------------------------------------------------------------


class TestClaudeCodeHand:
    def test_build_command(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_CLI_CMD", raising=False)
        hand = ClaudeCodeHand(config, repo_index)
        cmd = hand._build_command("hello world")
        assert cmd == ["claude", "--print", "hello world"]

    def test_custom_cli_cmd(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CLI_CMD", "my-claude")
        hand = ClaudeCodeHand(config, repo_index)
        assert hand._cmd == "my-claude"
        cmd = hand._build_command("test")
        assert cmd[0] == "my-claude"

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_run_success(
        self,
        mock_run: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude", "--print", "hello"],
            returncode=0,
            stdout="AI response here",
            stderr="",
        )
        hand = ClaudeCodeHand(config, repo_index)
        resp = hand.run("hello")

        assert resp.message == "AI response here"
        assert resp.metadata["backend"] == "claudecode"
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["cwd"] == str(repo_index.root)

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_run_nonzero_exit(
        self,
        mock_run: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude", "--print", "hello"],
            returncode=1,
            stdout="",
            stderr="error: something went wrong",
        )
        hand = ClaudeCodeHand(config, repo_index)
        resp = hand.run("hello")

        assert "something went wrong" in resp.message
        assert resp.metadata["returncode"] == 1

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_run_cli_not_found(
        self,
        mock_run: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        mock_run.side_effect = FileNotFoundError()
        hand = ClaudeCodeHand(config, repo_index)
        resp = hand.run("hello")

        assert "not found" in resp.message.lower()
        assert resp.metadata["error"] == "cli_not_found"

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_run_timeout(
        self,
        mock_run: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)
        hand = ClaudeCodeHand(config, repo_index)
        resp = hand.run("hello")

        assert "timed out" in resp.message.lower()
        assert resp.metadata["error"] == "timeout"


# ---------------------------------------------------------------------------
# CodexCLIHand (scaffolding)
# ---------------------------------------------------------------------------


class TestCodexCLIHand:
    def test_run_returns_placeholder(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = CodexCLIHand(config, repo_index)
        resp = hand.run("do something")
        assert "not yet implemented" in resp.message
        assert resp.metadata["backend"] == "codexcli"

    def test_stream_yields_placeholder(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = CodexCLIHand(config, repo_index)
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        assert len(chunks) == 1
        assert "not yet implemented" in chunks[0]


# ---------------------------------------------------------------------------
# GeminiCLIHand (scaffolding)
# ---------------------------------------------------------------------------


class TestGeminiCLIHand:
    def test_run_returns_placeholder(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = GeminiCLIHand(config, repo_index)
        resp = hand.run("do something")
        assert "not yet implemented" in resp.message
        assert resp.metadata["backend"] == "geminicli"

    def test_stream_yields_placeholder(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = GeminiCLIHand(config, repo_index)
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        assert len(chunks) == 1
        assert "not yet implemented" in chunks[0]


# ---------------------------------------------------------------------------
# create_hand factory
# ---------------------------------------------------------------------------


class TestCreateHand:
    @patch.object(LangGraphHand, "_build_agent")
    def test_creates_langgraph(
        self, mock_build: MagicMock, repo_index: RepoIndex
    ) -> None:
        cfg = Config(repo="/tmp/fake", model="test", backend="langgraph")
        hand = create_hand(cfg, repo_index)
        assert isinstance(hand, LangGraphHand)

    @patch.object(AtomicHand, "_build_agent")
    def test_creates_atomic(self, mock_build: MagicMock, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="test", backend="atomic")
        hand = create_hand(cfg, repo_index)
        assert isinstance(hand, AtomicHand)

    def test_creates_claudecode(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="test", backend="claudecode")
        hand = create_hand(cfg, repo_index)
        assert isinstance(hand, ClaudeCodeHand)

    def test_creates_codexcli(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="test", backend="codexcli")
        hand = create_hand(cfg, repo_index)
        assert isinstance(hand, CodexCLIHand)

    def test_creates_geminicli(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="test", backend="geminicli")
        hand = create_hand(cfg, repo_index)
        assert isinstance(hand, GeminiCLIHand)

    def test_unknown_backend_raises(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="test", backend="nonexistent")
        with pytest.raises(ValueError, match="Unknown backend"):
            create_hand(cfg, repo_index)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_stream(hand: Hand, prompt: str) -> list[str]:
    return [chunk async for chunk in hand.stream(prompt)]
