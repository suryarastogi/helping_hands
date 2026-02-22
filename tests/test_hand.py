"""Tests for helping_hands.lib.hands.v1.hand."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand import (
    AtomicHand,
    ClaudeCodeHand,
    CodexCLIHand,
    E2EHand,
    GeminiCLIHand,
    Hand,
    HandResponse,
    LangGraphHand,
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
# ClaudeCodeHand (scaffolding)
# ---------------------------------------------------------------------------


class TestClaudeCodeHand:
    def test_run_returns_placeholder(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = ClaudeCodeHand(config, repo_index)
        resp = hand.run("do something")
        assert "not yet implemented" in resp.message
        assert resp.metadata["backend"] == "claudecode"

    def test_stream_yields_placeholder(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = ClaudeCodeHand(config, repo_index)
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        assert len(chunks) == 1
        assert "not yet implemented" in chunks[0]


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
# E2EHand
# ---------------------------------------------------------------------------


class TestE2EHand:
    @patch("helping_hands.lib.github.GitHubClient")
    def test_run_happy_path(
        self,
        mock_gh_cls: MagicMock,
        config: Config,
        repo_index: RepoIndex,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = Config(repo="owner/repo", model="test-model")
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))

        mock_gh = MagicMock()
        mock_gh.create_pr.return_value = MagicMock(number=7, url="https://example/pr/7")
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        hand = E2EHand(config, repo_index)
        resp = hand.run("add a minimal change", hand_uuid="task-123")

        assert resp.metadata["backend"] == "e2e"
        assert resp.metadata["hand_uuid"] == "task-123"
        assert resp.metadata["repo"] == "owner/repo"
        assert resp.metadata["pr_url"] == "https://example/pr/7"

        mock_gh.clone.assert_called_once()
        mock_gh.create_branch.assert_called_once()
        mock_gh.set_local_identity.assert_called_once()
        mock_gh.add_and_commit.assert_called_once()
        mock_gh.push.assert_called_once()
        mock_gh.create_pr.assert_called_once()
        mock_gh.update_pr_body.assert_called_once()
        mock_gh.upsert_pr_comment.assert_called_once()
        body = mock_gh.upsert_pr_comment.call_args.kwargs["body"]
        assert "latest_updated_utc" in body

    def test_run_requires_repo(self, config: Config, repo_index: RepoIndex) -> None:
        hand = E2EHand(Config(repo="", model="test-model"), repo_index)
        with pytest.raises(ValueError):
            hand.run("test")

    @patch("helping_hands.lib.github.GitHubClient")
    def test_run_resumes_existing_pr(
        self,
        mock_gh_cls: MagicMock,
        repo_index: RepoIndex,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = Config(repo="owner/repo", model="test-model")
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "number": 1,
            "url": "https://example/pr/1",
            "head": "helping-hands/e2e-shared",
            "base": "master",
        }
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        hand = E2EHand(config, repo_index)
        resp = hand.run("update existing pr", hand_uuid="task-124", pr_number=1)

        assert resp.metadata["pr_number"] == "1"
        assert resp.metadata["pr_url"] == "https://example/pr/1"
        assert resp.metadata["resumed_pr"] == "true"
        mock_gh.get_pr.assert_called_once_with("owner/repo", 1)
        mock_gh.fetch_branch.assert_called_once()
        mock_gh.switch_branch.assert_called_once()
        mock_gh.create_branch.assert_not_called()
        mock_gh.set_local_identity.assert_called_once()
        mock_gh.create_pr.assert_not_called()
        mock_gh.update_pr_body.assert_called_once()
        mock_gh.upsert_pr_comment.assert_called_once()
        args = mock_gh.upsert_pr_comment.call_args.args
        kwargs = mock_gh.upsert_pr_comment.call_args.kwargs
        assert args == ("owner/repo", 1)
        assert kwargs["marker"] == "<!-- helping_hands:e2e-status -->"
        assert "latest_updated_utc" in kwargs["body"]

    @patch("helping_hands.lib.github.GitHubClient")
    def test_run_dry_run_skips_push_and_pr(
        self,
        mock_gh_cls: MagicMock,
        repo_index: RepoIndex,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = Config(repo="owner/repo", model="test-model")
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))

        mock_gh = MagicMock()
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        hand = E2EHand(config, repo_index)
        resp = hand.run("dry test", hand_uuid="task-125", dry_run=True)

        assert resp.metadata["dry_run"] == "true"
        assert resp.metadata["commit"] == ""
        assert resp.metadata["pr_url"] == ""
        mock_gh.set_local_identity.assert_not_called()
        mock_gh.add_and_commit.assert_not_called()
        mock_gh.push.assert_not_called()
        mock_gh.create_pr.assert_not_called()
        mock_gh.update_pr_body.assert_not_called()
        mock_gh.upsert_pr_comment.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_stream(hand: Hand, prompt: str) -> list[str]:
    return [chunk async for chunk in hand.stream(prompt)]
