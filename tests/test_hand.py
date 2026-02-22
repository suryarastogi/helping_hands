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
    BasicAtomicHand,
    BasicLangGraphHand,
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

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_configure_authenticated_push_remote(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        Hand._configure_authenticated_push_remote(
            tmp_path,
            "owner/repo",
            "ghp_test_token",
        )
        cmd = mock_run.call_args.args[0]
        assert cmd[:5] == ["git", "remote", "set-url", "--push", "origin"]
        assert (
            cmd[5] == "https://x-access-token:ghp_test_token@github.com/owner/repo.git"
        )

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_configure_authenticated_push_remote_failure_raises(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="fatal: no such remote",
        )
        with pytest.raises(RuntimeError, match="authenticated push remote"):
            Hand._configure_authenticated_push_remote(
                tmp_path,
                "owner/repo",
                "ghp_test_token",
            )


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
# BasicLangGraphHand
# ---------------------------------------------------------------------------


class TestBasicLangGraphHand:
    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_iterates_until_satisfied(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        first = MagicMock()
        first.content = "Working.\nSATISFIED: no"
        second = MagicMock()
        second.content = "Done.\nSATISFIED: yes"
        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = [
            {"messages": [first]},
            {"messages": [second]},
        ]
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index, max_iterations=5)
        resp = hand.run("implement feature")

        assert resp.metadata["backend"] == "basic-langgraph"
        assert resp.metadata["status"] == "satisfied"
        assert resp.metadata["iterations"] == 2
        assert "SATISFIED: yes" in resp.message
        assert mock_agent.invoke.call_count == 2

    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_applies_inline_file_edits(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        msg = MagicMock()
        msg.content = (
            "@@FILE: main.py\n```python\nprint('updated')\n```\nSATISFIED: yes"
        )
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [msg]}
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index)
        resp = hand.run("update main")

        assert "files updated" in resp.message
        assert (repo_index.root / "main.py").read_text(encoding="utf-8") == (
            "print('updated')"
        )

    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_preserves_dotfile_path(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        msg = MagicMock()
        msg.content = (
            "@@FILE: .pre-commit-config.yaml\n```yaml\nrepos: []\n```\nSATISFIED: yes"
        )
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [msg]}
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index)
        hand.run("update dotfile")

        assert (repo_index.root / ".pre-commit-config.yaml").is_file()
        assert not (repo_index.root / "pre-commit-config.yaml").exists()

    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_respects_auto_pr_disabled(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        msg = MagicMock()
        msg.content = "Done.\nSATISFIED: yes"
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [msg]}
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index)
        hand.auto_pr = False
        resp = hand.run("implement feature")

        assert resp.metadata["pr_status"] == "disabled"

    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_supports_read_requests(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        (repo_index.root / "main.py").write_text("print('before')\n", encoding="utf-8")
        call_count = 0

        def fake_invoke(payload: dict[str, Any]) -> dict[str, list[Any]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = MagicMock()
                msg.content = "@@READ: main.py\nSATISFIED: no"
                return {"messages": [msg]}
            prompt = payload["messages"][0]["content"]
            assert "@@READ_RESULT: main.py" in prompt
            assert "print('before')" in prompt
            msg = MagicMock()
            msg.content = (
                "@@FILE: main.py\n```python\nprint('after')\n```\nSATISFIED: yes"
            )
            return {"messages": [msg]}

        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = fake_invoke
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index, max_iterations=3)
        resp = hand.run("update main")

        assert resp.metadata["iterations"] == 2
        assert "@@READ_RESULT: main.py" in resp.message
        assert (repo_index.root / "main.py").read_text(encoding="utf-8") == (
            "print('after')"
        )

    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_honors_interrupt(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        msg = MagicMock()
        msg.content = "Still working.\nSATISFIED: no"
        mock_agent = MagicMock()

        def fake_invoke(*_a: Any, **_kw: Any):
            hand.interrupt()
            return {"messages": [msg]}

        mock_agent.invoke.side_effect = fake_invoke
        mock_build.return_value = mock_agent
        hand = BasicLangGraphHand(config, repo_index)
        resp = hand.run("implement feature")

        assert resp.metadata["status"] == "interrupted"
        assert resp.metadata["iterations"] == 1


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

    @patch.object(AtomicHand, "_build_agent")
    def test_stream_handles_coroutine_result(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        async def fake_run_async(_input: Any):
            partial = MagicMock()
            partial.chat_message = "Single result"
            return partial

        mock_agent = MagicMock()
        mock_agent.run_async = fake_run_async
        mock_build.return_value = mock_agent

        hand = AtomicHand(config, repo_index)
        hand._input_schema = _FakeInputSchema
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        assert chunks == ["Single result"]

    @patch.object(AtomicHand, "_build_agent")
    def test_stream_falls_back_to_sync_run_when_async_not_supported(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        def fake_run(_input: Any):
            partial = MagicMock()
            partial.chat_message = "Sync fallback result"
            return partial

        def fake_run_async(_input: Any):
            raise AssertionError("The run_async method is for async clients.")

        mock_agent = MagicMock()
        mock_agent.run_async = fake_run_async
        mock_agent.run = fake_run
        mock_build.return_value = mock_agent

        hand = AtomicHand(config, repo_index)
        hand._input_schema = _FakeInputSchema
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        assert chunks == ["Sync fallback result"]


# ---------------------------------------------------------------------------
# BasicAtomicHand
# ---------------------------------------------------------------------------


class TestBasicAtomicHand:
    @patch.object(BasicAtomicHand, "_build_agent")
    def test_run_iterates_until_satisfied(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        mock_agent = MagicMock()
        first = MagicMock()
        first.chat_message = "Working.\nSATISFIED: no"
        second = MagicMock()
        second.chat_message = "Done.\nSATISFIED: yes"
        mock_agent.run.side_effect = [first, second]
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index, max_iterations=5)
        hand._input_schema = _FakeInputSchema
        resp = hand.run("implement feature")

        assert resp.metadata["backend"] == "basic-atomic"
        assert resp.metadata["status"] == "satisfied"
        assert resp.metadata["iterations"] == 2
        assert "SATISFIED: yes" in resp.message
        assert mock_agent.run.call_count == 2

    @patch.object(BasicAtomicHand, "_build_agent")
    def test_run_supports_read_requests(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        (repo_index.root / "main.py").write_text("print('before')\n", encoding="utf-8")
        call_count = 0

        def fake_run(step_input: Any):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                first = MagicMock()
                first.chat_message = "@@READ: main.py\nSATISFIED: no"
                return first
            assert "@@READ_RESULT: main.py" in step_input.chat_message
            assert "print('before')" in step_input.chat_message
            second = MagicMock()
            second.chat_message = (
                "@@FILE: main.py\n```python\nprint('after')\n```\nSATISFIED: yes"
            )
            return second

        mock_agent = MagicMock()
        mock_agent.run.side_effect = fake_run
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index, max_iterations=3)
        hand._input_schema = _FakeInputSchema
        resp = hand.run("update main")

        assert resp.metadata["iterations"] == 2
        assert "@@READ_RESULT: main.py" in resp.message
        assert (repo_index.root / "main.py").read_text(encoding="utf-8") == (
            "print('after')"
        )

    @patch.object(BasicAtomicHand, "_build_agent")
    def test_run_supports_natural_language_read_request(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        (repo_index.root / "main.py").write_text("print('before')\n", encoding="utf-8")
        call_count = 0

        def fake_run(step_input: Any):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                first = MagicMock()
                first.chat_message = (
                    "Please provide the content of file `main.py`.\nSATISFIED: no"
                )
                return first
            assert "@@READ_RESULT: main.py" in step_input.chat_message
            second = MagicMock()
            second.chat_message = (
                "@@FILE: main.py\n```python\nprint('after')\n```\nSATISFIED: yes"
            )
            return second

        mock_agent = MagicMock()
        mock_agent.run.side_effect = fake_run
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index, max_iterations=3)
        hand._input_schema = _FakeInputSchema
        resp = hand.run("update main")

        assert resp.metadata["iterations"] == 2
        assert "@@READ_RESULT: main.py" in resp.message
        assert (repo_index.root / "main.py").read_text(encoding="utf-8") == (
            "print('after')"
        )

    @patch.object(BasicAtomicHand, "_build_agent")
    def test_stream_interrupts(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        hand: BasicAtomicHand

        async def fake_run_async(_input: Any):
            partial = MagicMock()
            partial.chat_message = "Working..."
            yield partial
            hand.interrupt()
            second = MagicMock()
            second.chat_message = "more output"
            yield second

        mock_agent = MagicMock()
        mock_agent.run_async = fake_run_async
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index)
        hand._input_schema = _FakeInputSchema
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        assert "[interrupted]" in "".join(chunks)

    @patch.object(BasicAtomicHand, "_build_agent")
    def test_stream_handles_coroutine_result(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        async def fake_run_async(_input: Any):
            partial = MagicMock()
            partial.chat_message = "Done.\nSATISFIED: yes"
            return partial

        mock_agent = MagicMock()
        mock_agent.run_async = fake_run_async
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index)
        hand._input_schema = _FakeInputSchema
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        text = "".join(chunks)
        assert "SATISFIED: yes" in text
        assert "Task marked satisfied." in text

    @patch.object(BasicAtomicHand, "_build_agent")
    def test_stream_falls_back_to_sync_run_when_async_not_supported(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        def fake_run(_input: Any):
            partial = MagicMock()
            partial.chat_message = "Done.\nSATISFIED: yes"
            return partial

        def fake_run_async(_input: Any):
            raise AssertionError("The run_async method is for async clients.")

        mock_agent = MagicMock()
        mock_agent.run_async = fake_run_async
        mock_agent.run = fake_run
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index)
        hand._input_schema = _FakeInputSchema
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_stream(hand, "hello")
        )
        text = "".join(chunks)
        assert "SATISFIED: yes" in text
        assert "Task marked satisfied." in text


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
