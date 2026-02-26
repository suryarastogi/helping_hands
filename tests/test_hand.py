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
    GooseCLIHand,
    Hand,
    HandResponse,
    LangGraphHand,
)
from helping_hands.lib.meta.tools.command import CommandResult
from helping_hands.lib.meta.tools.web import (
    WebSearchItem,
    WebSearchResult,
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


class _StubFinalizeHand(Hand):
    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


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

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_run_precommit_checks_and_fixes_retries_once_after_failure(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="files were reformatted",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="all hooks passed",
                stderr="",
            ),
        ]

        Hand._run_precommit_checks_and_fixes(tmp_path)

        assert mock_run.call_count == 2
        cmd = mock_run.call_args_list[0].args[0]
        assert cmd == ["uv", "run", "pre-commit", "run", "--all-files"]

    @patch("helping_hands.lib.hands.v1.hand.subprocess.run")
    def test_run_precommit_checks_and_fixes_raises_after_second_failure(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="reformatted one file",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="ruff failed",
            ),
        ]

        with pytest.raises(RuntimeError, match="pre-commit checks failed"):
            Hand._run_precommit_checks_and_fixes(tmp_path)

    @patch("helping_hands.lib.github.GitHubClient")
    def test_finalize_repo_pr_runs_precommit_when_execution_enabled(
        self,
        mock_gh_cls: MagicMock,
        repo_index: RepoIndex,
    ) -> None:
        config = Config(
            repo=str(repo_index.root),
            model="test-model",
            enable_execution=True,
        )
        hand = _StubFinalizeHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        mock_gh = MagicMock()
        mock_gh.token = "ghp_test"
        mock_gh.add_and_commit.return_value = "abc123"
        mock_gh.create_pr.return_value = MagicMock(
            number=1,
            url="https://example/pr/1",
        )
        mock_gh.get_repo.return_value = MagicMock(default_branch="main")
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(Hand, "_configure_authenticated_push_remote"),
            patch.object(Hand, "_run_precommit_checks_and_fixes") as mock_precommit,
        ):
            metadata = hand._finalize_repo_pr(
                backend="stub",
                prompt="implement",
                summary="done",
            )

        assert metadata["pr_status"] == "created"
        mock_precommit.assert_called_once_with(repo_index.root.resolve())

    @patch("helping_hands.lib.github.GitHubClient")
    def test_finalize_repo_pr_skips_precommit_when_execution_disabled(
        self,
        mock_gh_cls: MagicMock,
        repo_index: RepoIndex,
    ) -> None:
        config = Config(
            repo=str(repo_index.root),
            model="test-model",
            enable_execution=False,
        )
        hand = _StubFinalizeHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        mock_gh = MagicMock()
        mock_gh.token = "ghp_test"
        mock_gh.add_and_commit.return_value = "abc123"
        mock_gh.create_pr.return_value = MagicMock(
            number=1,
            url="https://example/pr/1",
        )
        mock_gh.get_repo.return_value = MagicMock(default_branch="main")
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(Hand, "_configure_authenticated_push_remote"),
            patch.object(Hand, "_run_precommit_checks_and_fixes") as mock_precommit,
        ):
            metadata = hand._finalize_repo_pr(
                backend="stub",
                prompt="implement",
                summary="done",
            )

        assert metadata["pr_status"] == "created"
        mock_precommit.assert_not_called()

    @patch("helping_hands.lib.github.GitHubClient")
    def test_finalize_repo_pr_sets_precommit_failed_status(
        self,
        mock_gh_cls: MagicMock,
        repo_index: RepoIndex,
    ) -> None:
        config = Config(
            repo=str(repo_index.root),
            model="test-model",
            enable_execution=True,
        )
        hand = _StubFinalizeHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(
                Hand,
                "_run_precommit_checks_and_fixes",
                side_effect=RuntimeError("pre-commit checks failed"),
            ),
        ):
            metadata = hand._finalize_repo_pr(
                backend="stub",
                prompt="implement",
                summary="done",
            )

        assert metadata["pr_status"] == "precommit_failed"
        assert "pre-commit checks failed" in metadata["pr_error"]
        mock_gh_cls.assert_not_called()


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
        chunks = asyncio.run(_collect_stream(hand, "hi"))
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

    @patch(
        "helping_hands.lib.hands.v1.hand.iterative.system_exec_tools.run_python_code"
    )
    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_supports_tool_requests(
        self,
        mock_build: MagicMock,
        mock_run_python_code: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        config = Config(
            repo=config.repo,
            model=config.model,
            enable_execution=True,
        )
        mock_run_python_code.return_value = CommandResult(
            command=["uv", "run", "--python", "3.13", "python", "-c", "print('ok')"],
            cwd=str(repo_index.root.resolve()),
            exit_code=0,
            stdout="ok\n",
            stderr="",
            timed_out=False,
        )
        call_count = 0

        def fake_invoke(payload: dict[str, Any]) -> dict[str, list[Any]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = MagicMock()
                msg.content = (
                    "@@TOOL: python.run_code\n"
                    "```json\n"
                    '{"code":"print(\\"ok\\")","python_version":"3.13"}\n'
                    "```\n"
                    "SATISFIED: no"
                )
                return {"messages": [msg]}
            prompt = payload["messages"][0]["content"]
            assert "@@TOOL_RESULT: python.run_code" in prompt
            assert "status: success" in prompt
            assert "ok" in prompt
            msg = MagicMock()
            msg.content = "Done.\nSATISFIED: yes"
            return {"messages": [msg]}

        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = fake_invoke
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index, max_iterations=3)
        resp = hand.run("run python helper")

        assert resp.metadata["iterations"] == 2
        assert "@@TOOL_RESULT: python.run_code" in resp.message
        mock_run_python_code.assert_called_once()

    @patch(
        "helping_hands.lib.hands.v1.hand.iterative.system_exec_tools.run_python_code"
    )
    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_rejects_execution_tools_when_disabled(
        self,
        mock_build: MagicMock,
        mock_run_python_code: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        msg = MagicMock()
        msg.content = (
            "@@TOOL: python.run_code\n"
            "```json\n"
            '{"code":"print(\\"blocked\\")","python_version":"3.13"}\n'
            "```\n"
            "SATISFIED: yes"
        )
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [msg]}
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index, max_iterations=1)
        resp = hand.run("run blocked tool")

        assert "enable_execution=true" in resp.message
        mock_run_python_code.assert_not_called()

    @patch("helping_hands.lib.hands.v1.hand.iterative.system_web_tools.search_web")
    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_supports_web_search_tools(
        self,
        mock_build: MagicMock,
        mock_search_web: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        config = Config(
            repo=config.repo,
            model=config.model,
            enable_web=True,
        )
        mock_search_web.return_value = WebSearchResult(
            query="python release",
            results=[
                WebSearchItem(
                    title="Python release",
                    url="https://example.com/python",
                    snippet="Python release notes",
                )
            ],
        )
        call_count = 0

        def fake_invoke(payload: dict[str, Any]) -> dict[str, list[Any]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = MagicMock()
                msg.content = (
                    "@@TOOL: web.search\n"
                    "```json\n"
                    '{"query":"python release","max_results":1}\n'
                    "```\n"
                    "SATISFIED: no"
                )
                return {"messages": [msg]}
            prompt = payload["messages"][0]["content"]
            assert "@@TOOL_RESULT: web.search" in prompt
            assert "result_count: 1" in prompt
            msg = MagicMock()
            msg.content = "Done.\nSATISFIED: yes"
            return {"messages": [msg]}

        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = fake_invoke
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index, max_iterations=3)
        resp = hand.run("run web search")

        assert resp.metadata["iterations"] == 2
        assert "@@TOOL_RESULT: web.search" in resp.message
        mock_search_web.assert_called_once()

    @patch.object(BasicLangGraphHand, "_build_agent")
    def test_run_bootstraps_readme_agent_and_tree(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        (repo_index.root / "README.md").write_text("Project intro", encoding="utf-8")
        (repo_index.root / "AGENT.md").write_text("Team conventions", encoding="utf-8")

        msg = MagicMock()
        msg.content = "Done.\nSATISFIED: yes"

        def fake_invoke(payload: dict[str, Any]) -> dict[str, list[Any]]:
            prompt = payload["messages"][0]["content"]
            assert "Bootstrap repository context:" in prompt
            assert "README.md" in prompt
            assert "Project intro" in prompt
            assert "AGENT.md" in prompt
            assert "Team conventions" in prompt
            assert "Repository tree snapshot (depth <= 4)" in prompt
            assert "- main.py" in prompt
            return {"messages": [msg]}

        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = fake_invoke
        mock_build.return_value = mock_agent

        hand = BasicLangGraphHand(config, repo_index, max_iterations=2)
        resp = hand.run("implement feature")

        assert resp.metadata["status"] == "satisfied"
        assert mock_agent.invoke.call_count == 1

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
        chunks = asyncio.run(_collect_stream(hand, "hello"))
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
        chunks = asyncio.run(_collect_stream(hand, "hello"))
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
        chunks = asyncio.run(_collect_stream(hand, "hello"))
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

    @patch(
        "helping_hands.lib.hands.v1.hand.iterative.system_exec_tools.run_python_code"
    )
    @patch.object(BasicAtomicHand, "_build_agent")
    def test_run_supports_tool_requests(
        self,
        mock_build: MagicMock,
        mock_run_python_code: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        config = Config(
            repo=config.repo,
            model=config.model,
            enable_execution=True,
        )
        mock_run_python_code.return_value = CommandResult(
            command=["uv", "run", "--python", "3.13", "python", "-c", "print('ok')"],
            cwd=str(repo_index.root.resolve()),
            exit_code=0,
            stdout="ok\n",
            stderr="",
            timed_out=False,
        )
        call_count = 0

        def fake_run(step_input: Any):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                first = MagicMock()
                first.chat_message = (
                    "@@TOOL: python.run_code\n"
                    "```json\n"
                    '{"code":"print(\\"ok\\")","python_version":"3.13"}\n'
                    "```\n"
                    "SATISFIED: no"
                )
                return first
            assert "@@TOOL_RESULT: python.run_code" in step_input.chat_message
            assert "status: success" in step_input.chat_message
            second = MagicMock()
            second.chat_message = "Done.\nSATISFIED: yes"
            return second

        mock_agent = MagicMock()
        mock_agent.run.side_effect = fake_run
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index, max_iterations=3)
        hand._input_schema = _FakeInputSchema
        resp = hand.run("run python helper")

        assert resp.metadata["iterations"] == 2
        assert "@@TOOL_RESULT: python.run_code" in resp.message
        mock_run_python_code.assert_called_once()

    @patch.object(BasicAtomicHand, "_build_agent")
    def test_run_bootstraps_readme_agent_and_tree(
        self,
        mock_build: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        (repo_index.root / "README.md").write_text("Project intro", encoding="utf-8")
        (repo_index.root / "AGENT.md").write_text("Team conventions", encoding="utf-8")

        def fake_run(step_input: Any) -> Any:
            prompt = step_input.chat_message
            assert "Bootstrap repository context:" in prompt
            assert "README.md" in prompt
            assert "Project intro" in prompt
            assert "AGENT.md" in prompt
            assert "Team conventions" in prompt
            assert "Repository tree snapshot (depth <= 4)" in prompt
            assert "- main.py" in prompt
            partial = MagicMock()
            partial.chat_message = "Done.\nSATISFIED: yes"
            return partial

        mock_agent = MagicMock()
        mock_agent.run.side_effect = fake_run
        mock_build.return_value = mock_agent

        hand = BasicAtomicHand(config, repo_index, max_iterations=2)
        hand._input_schema = _FakeInputSchema
        resp = hand.run("implement feature")

        assert resp.metadata["status"] == "satisfied"
        assert mock_agent.run.call_count == 1

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
        chunks = asyncio.run(_collect_stream(hand, "hello"))
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
        chunks = asyncio.run(_collect_stream(hand, "hello"))
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
        chunks = asyncio.run(_collect_stream(hand, "hello"))
        text = "".join(chunks)
        assert "SATISFIED: yes" in text
        assert "Task marked satisfied." in text


# ---------------------------------------------------------------------------
# ClaudeCodeHand
# ---------------------------------------------------------------------------


class TestClaudeCodeHand:
    def test_build_claude_failure_message_for_auth_error(
        self,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        hand = ClaudeCodeHand(config, repo_index)
        msg = hand._build_claude_failure_message(
            return_code=1,
            output="ERROR: unauthorized: missing ANTHROPIC_API_KEY",
        )
        assert "authentication failed" in msg
        assert "ANTHROPIC_API_KEY" in msg

    def test_render_command_defaults_to_claude_prompt_mode(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CLI_CMD", "claude")
        hand = ClaudeCodeHand(config, repo_index)
        cmd = hand._render_command("hello world")
        assert cmd[:3] == ["claude", "--dangerously-skip-permissions", "-p"]
        assert cmd[-1] == "hello world"

    def test_render_command_skips_openai_default_model(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CLI_CMD", "claude -p")
        config = Config(repo="/tmp/fake", model="gpt-5.2")
        hand = ClaudeCodeHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)
        assert "--model" not in joined

    def test_build_subprocess_env_strips_anthropic_key_in_native_auth_mode(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anth-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        config = Config(
            repo="/tmp/fake",
            model="default",
            use_native_cli_auth=True,
        )
        hand = ClaudeCodeHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert "ANTHROPIC_API_KEY" not in env
        assert env["OPENAI_API_KEY"] == "sk-test"

    def test_render_command_can_disable_dangerous_skip_permissions(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CLI_CMD", "claude -p")
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", "0")
        hand = ClaudeCodeHand(config, repo_index)
        cmd = hand._render_command("hello world")
        assert "--dangerously-skip-permissions" not in cmd

    @patch("helping_hands.lib.hands.v1.hand.placeholders.os.geteuid")
    def test_render_command_skips_dangerous_permissions_when_root(
        self,
        mock_geteuid: MagicMock,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_geteuid.return_value = 0
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CLI_CMD", "claude -p")
        hand = ClaudeCodeHand(config, repo_index)
        cmd = hand._render_command("hello world")
        assert "--dangerously-skip-permissions" not in cmd

    @patch("helping_hands.lib.hands.v1.hand.placeholders.shutil.which")
    def test_fallback_command_when_claude_missing_uses_npx(
        self,
        mock_which: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        mock_which.return_value = "/usr/bin/npx"
        hand = ClaudeCodeHand(config, repo_index)
        original = ["claude", "--dangerously-skip-permissions", "-p", "hello world"]
        fallback = hand._fallback_command_when_not_found(original)
        assert fallback is not None
        assert fallback[:3] == ["npx", "-y", "@anthropic-ai/claude-code"]
        assert fallback[3:] == original[1:]

    @patch("helping_hands.lib.hands.v1.hand.placeholders.shutil.which")
    def test_fallback_command_when_npx_missing_returns_none(
        self,
        mock_which: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        mock_which.return_value = None
        hand = ClaudeCodeHand(config, repo_index)
        assert (
            hand._fallback_command_when_not_found(
                ["claude", "--dangerously-skip-permissions", "-p", "hello world"]
            )
            is None
        )

    def test_retry_command_after_root_permission_error_strips_flag(
        self,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        hand = ClaudeCodeHand(config, repo_index)
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "-p",
            "hello world",
        ]
        retry = hand._retry_command_after_failure(
            cmd,
            output=(
                "--dangerously-skip-permissions cannot be used with root/sudo "
                "privileges for security reasons"
            ),
            return_code=1,
        )
        assert retry is not None
        assert "--dangerously-skip-permissions" not in retry

    @patch(
        "helping_hands.lib.hands.v1.hand.placeholders.asyncio.create_subprocess_exec"
    )
    def test_invoke_cli_uses_non_interactive_stdin(
        self,
        mock_create: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        class _Stdout:
            async def read(self, _size: int) -> bytes:
                return b""

        class _Process:
            def __init__(self) -> None:
                self.stdout = _Stdout()
                self.returncode: int | None = 0

            async def wait(self) -> int:
                return 0

            def terminate(self) -> None:
                self.returncode = 143

            def kill(self) -> None:
                self.returncode = -9

        mock_create.return_value = _Process()
        hand = ClaudeCodeHand(config, repo_index)

        async def _emit(_chunk: str) -> None:
            return None

        asyncio.run(
            hand._invoke_cli_with_cmd(
                ["claude", "-p", "hello world"],
                emit=_emit,
            )
        )
        assert mock_create.call_args.kwargs["stdin"] == asyncio.subprocess.DEVNULL

    @patch(
        "helping_hands.lib.hands.v1.hand.placeholders.asyncio.create_subprocess_exec"
    )
    def test_invoke_cli_emits_heartbeat_and_times_out_on_idle(
        self,
        mock_create: MagicMock,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class _SlowStdout:
            async def read(self, _size: int) -> bytes:
                await asyncio.sleep(1.0)
                return b""

        class _SlowProcess:
            def __init__(self) -> None:
                self.stdout = _SlowStdout()
                self.returncode: int | None = None
                self.terminate_called = False

            async def wait(self) -> int:
                if self.returncode is None:
                    self.returncode = 143
                return self.returncode

            def terminate(self) -> None:
                self.terminate_called = True
                self.returncode = 143

            def kill(self) -> None:
                self.returncode = -9

        proc = _SlowProcess()
        mock_create.return_value = proc
        monkeypatch.setenv("HELPING_HANDS_CLI_IO_POLL_SECONDS", "0.01")
        monkeypatch.setenv("HELPING_HANDS_CLI_HEARTBEAT_SECONDS", "0.01")
        monkeypatch.setenv("HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS", "0.05")
        hand = ClaudeCodeHand(config, repo_index)
        emitted: list[str] = []

        async def _emit(chunk: str) -> None:
            emitted.append(chunk)

        with pytest.raises(RuntimeError, match="produced no output"):
            asyncio.run(
                hand._invoke_cli_with_cmd(
                    ["claude", "-p", "hello world"],
                    emit=_emit,
                )
            )

        assert proc.terminate_called is True
        assert any("still running" in chunk for chunk in emitted)

    @patch.object(ClaudeCodeHand, "_finalize_repo_pr")
    @patch.object(ClaudeCodeHand, "_invoke_claude", autospec=True)
    def test_run_executes_init_then_task(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        prompts: list[str] = []

        async def fake_invoke(
            _self: ClaudeCodeHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            text = "Init summary.\n" if len(prompts) == 1 else "Task output.\n"
            await emit(text)
            return text

        mock_invoke.side_effect = fake_invoke
        mock_finalize.return_value = {
            "auto_pr": "true",
            "pr_status": "created",
            "pr_url": "https://example/pr/55",
            "pr_number": "55",
            "pr_branch": "helping-hands/claudecodecli-test",
            "pr_commit": "abc123",
        }

        hand = ClaudeCodeHand(config, repo_index)
        resp = hand.run("do something")

        assert len(prompts) == 2
        assert "Initialization phase" in prompts[0]
        assert "User task request" in prompts[1]
        assert "Init summary." in prompts[1]
        assert "Task output." in resp.message
        assert resp.metadata["backend"] == "claudecodecli"
        mock_finalize.assert_called_once()

    @patch.object(ClaudeCodeHand, "_finalize_repo_pr")
    @patch.object(ClaudeCodeHand, "_invoke_claude", autospec=True)
    def test_stream_runs_two_phases_and_emits_pr_result(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        prompts: list[str] = []

        async def fake_invoke(
            _self: ClaudeCodeHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            text = "init output\n" if len(prompts) == 1 else "task output\n"
            await emit(text)
            return text

        mock_invoke.side_effect = fake_invoke
        mock_finalize.return_value = {
            "auto_pr": "true",
            "pr_status": "created",
            "pr_url": "https://example/pr/3",
            "pr_number": "3",
            "pr_branch": "helping-hands/claudecodecli-test",
            "pr_commit": "abc123",
        }

        hand = ClaudeCodeHand(config, repo_index)
        chunks = asyncio.run(_collect_stream(hand, "hello"))
        text = "".join(chunks)

        assert "[phase 1/2]" in text
        assert "[phase 2/2]" in text
        assert "init output" in text
        assert "task output" in text
        assert "PR created" in text
        assert len(prompts) == 2

    @patch.object(ClaudeCodeHand, "_repo_has_changes", return_value=False)
    @patch.object(ClaudeCodeHand, "_finalize_repo_pr")
    @patch.object(ClaudeCodeHand, "_invoke_claude", autospec=True)
    def test_run_retries_apply_when_no_file_changes_for_edit_prompt(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        _mock_has_changes: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        prompts: list[str] = []

        async def fake_invoke(
            _self: ClaudeCodeHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            if len(prompts) == 1:
                text = "Init summary.\n"
            elif len(prompts) == 2:
                text = "I've prepared an update but have not applied it yet.\n"
            else:
                text = "Applied update to README.md.\n"
            await emit(text)
            return text

        mock_invoke.side_effect = fake_invoke
        mock_finalize.return_value = {
            "auto_pr": "true",
            "pr_status": "no_changes",
            "pr_url": "",
            "pr_number": "",
            "pr_branch": "",
            "pr_commit": "",
        }

        hand = ClaudeCodeHand(config, repo_index)
        resp = hand.run("Update README with date")

        assert len(prompts) == 3
        assert "Follow-up enforcement phase" in prompts[2]
        assert "Applied update to README.md." in resp.message
        mock_finalize.assert_called_once()

    @patch.object(ClaudeCodeHand, "_repo_has_changes", return_value=False)
    @patch.object(ClaudeCodeHand, "_finalize_repo_pr")
    @patch.object(ClaudeCodeHand, "_invoke_claude", autospec=True)
    def test_run_fails_when_edit_is_blocked_by_permission_prompt(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        _mock_has_changes: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        prompts: list[str] = []

        async def fake_invoke(
            _self: ClaudeCodeHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            if len(prompts) == 1:
                text = "Init summary.\n"
            elif len(prompts) == 2:
                text = (
                    "Could you approve the write operation to `/tmp/repo/README.md`?\n"
                )
            else:
                text = (
                    "The edit was blocked pending your approval. "
                    "Please approve the write operation.\n"
                )
            await emit(text)
            return text

        mock_invoke.side_effect = fake_invoke
        hand = ClaudeCodeHand(config, repo_index)

        with pytest.raises(RuntimeError, match="could not apply edits"):
            hand.run("Update README with MCP section")

        assert len(prompts) == 3
        mock_finalize.assert_not_called()


# ---------------------------------------------------------------------------
# CodexCLIHand
# ---------------------------------------------------------------------------


class TestCodexCLIHand:
    def test_build_codex_failure_message_for_auth_error(
        self,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        hand = CodexCLIHand(config, repo_index)
        msg = hand._build_codex_failure_message(
            return_code=1,
            output=(
                "ERROR: unexpected status 401 Unauthorized: "
                "Missing bearer or basic authentication in header"
            ),
        )
        assert "authentication failed" in msg
        assert "OPENAI_API_KEY" in msg
        assert "recreate server/worker containers" in msg

    def test_render_command_defaults_to_codex_exec(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_CLI_CMD", "codex")
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        assert cmd[:2] == ["codex", "exec"]
        assert "--sandbox" in cmd
        assert "workspace-write" in cmd or "danger-full-access" in cmd
        assert "--skip-git-repo-check" in cmd
        assert cmd[-1] == "hello world"

    def test_render_command_uses_safe_default_model(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_CLI_CMD", "codex")
        config = Config(repo="/tmp/fake", model="default")
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)
        assert "--model gpt-5.2" in joined

    def test_render_command_normalizes_provider_prefixed_model(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_CLI_CMD", "codex")
        config = Config(repo="/tmp/fake", model="openai/gpt-5.2")
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)
        assert "--model gpt-5.2" in joined
        assert "openai/gpt-5.2" not in joined

    def test_build_subprocess_env_strips_openai_key_in_native_auth_mode(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anth-test")
        config = Config(
            repo="/tmp/fake",
            model="default",
            use_native_cli_auth=True,
        )
        hand = CodexCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert "OPENAI_API_KEY" not in env
        assert env["ANTHROPIC_API_KEY"] == "anth-test"

    def test_render_command_expands_placeholders(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "HELPING_HANDS_CODEX_CLI_CMD",
            'codex exec --model {model} --repo {repo} --prompt "{prompt}"',
        )
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)
        assert "--model test-model" in joined
        assert f"--repo {repo_index.root.resolve()}" in joined
        assert "--prompt hello world" in joined
        assert "--sandbox" in joined
        assert "--skip-git-repo-check" in joined
        assert cmd.count("hello world") == 1

    @patch("helping_hands.lib.hands.v1.hand.placeholders.Path.exists")
    def test_render_command_uses_container_default_sandbox(
        self,
        mock_exists: MagicMock,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_exists.return_value = True
        monkeypatch.setenv("HELPING_HANDS_CODEX_CLI_CMD", "codex")
        monkeypatch.delenv("HELPING_HANDS_CODEX_SANDBOX_MODE", raising=False)
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)
        assert "--sandbox danger-full-access" in joined

    def test_render_command_respects_explicit_sandbox(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "HELPING_HANDS_CODEX_CLI_CMD",
            "codex exec --sandbox read-only",
        )
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)
        assert "--sandbox read-only" in joined
        assert "workspace-write" not in joined
        assert "--skip-git-repo-check" in joined

    def test_render_command_skip_git_repo_check_can_be_disabled(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_CLI_CMD", "codex exec")
        monkeypatch.setenv("HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK", "0")
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)
        assert "--skip-git-repo-check" not in joined

    @patch("helping_hands.lib.hands.v1.hand.placeholders.shutil.which")
    def test_render_command_wraps_docker_when_enabled(
        self,
        mock_which: MagicMock,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_which.return_value = "/usr/bin/docker"
        monkeypatch.setenv("HELPING_HANDS_CODEX_CLI_CMD", "codex")
        monkeypatch.setenv("HELPING_HANDS_CODEX_CONTAINER", "1")
        monkeypatch.setenv(
            "HELPING_HANDS_CODEX_CONTAINER_IMAGE",
            "ghcr.io/example/codex:latest",
        )
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        hand = CodexCLIHand(config, repo_index)
        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)

        assert cmd[:4] == ["docker", "run", "--rm", "-i"]
        assert f"{repo_index.root.resolve()}:/workspace" in joined
        assert "-e OPENAI_API_KEY=sk-test" in joined
        assert "ghcr.io/example/codex:latest" in cmd
        assert "codex exec" in joined
        assert "--sandbox" in joined
        assert "--skip-git-repo-check" in joined

    @patch("helping_hands.lib.hands.v1.hand.placeholders.shutil.which")
    def test_render_command_container_omits_openai_key_in_native_auth_mode(
        self,
        mock_which: MagicMock,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_which.return_value = "/usr/bin/docker"
        monkeypatch.setenv("HELPING_HANDS_CODEX_CLI_CMD", "codex")
        monkeypatch.setenv("HELPING_HANDS_CODEX_CONTAINER", "1")
        monkeypatch.setenv(
            "HELPING_HANDS_CODEX_CONTAINER_IMAGE",
            "ghcr.io/example/codex:latest",
        )
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        config = Config(
            repo="/tmp/fake",
            model="default",
            use_native_cli_auth=True,
        )
        hand = CodexCLIHand(config, repo_index)

        cmd = hand._render_command("hello world")
        joined = " ".join(cmd)

        assert "-e OPENAI_API_KEY=sk-test" not in joined

    def test_render_command_container_missing_image_raises(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CODEX_CONTAINER", "1")
        monkeypatch.delenv("HELPING_HANDS_CODEX_CONTAINER_IMAGE", raising=False)
        hand = CodexCLIHand(config, repo_index)
        with pytest.raises(RuntimeError, match="HELPING_HANDS_CODEX_CONTAINER_IMAGE"):
            hand._render_command("hello world")

    @patch.object(CodexCLIHand, "_finalize_repo_pr")
    @patch.object(CodexCLIHand, "_invoke_codex", autospec=True)
    def test_run_executes_init_then_task(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        prompts: list[str] = []

        async def fake_invoke(
            _self: CodexCLIHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            text = "Init summary.\n" if len(prompts) == 1 else "Task output.\n"
            await emit(text)
            return text

        mock_invoke.side_effect = fake_invoke
        mock_finalize.return_value = {
            "auto_pr": "true",
            "pr_status": "created",
            "pr_url": "https://example/pr/99",
            "pr_number": "99",
            "pr_branch": "helping-hands/codexcli-test",
            "pr_commit": "abc123",
        }

        hand = CodexCLIHand(config, repo_index)
        resp = hand.run("do something")

        assert len(prompts) == 2
        assert "Initialization phase" in prompts[0]
        assert "User task request" in prompts[1]
        assert "Init summary." in prompts[1]
        assert "Task output." in resp.message
        assert resp.metadata["backend"] == "codexcli"
        mock_finalize.assert_called_once()

    @patch.object(CodexCLIHand, "_finalize_repo_pr")
    @patch.object(CodexCLIHand, "_invoke_codex", autospec=True)
    def test_stream_runs_two_phases_and_emits_pr_result(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        prompts: list[str] = []

        async def fake_invoke(
            _self: CodexCLIHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            text = "init output\n" if len(prompts) == 1 else "task output\n"
            await emit(text)
            return text

        mock_invoke.side_effect = fake_invoke
        mock_finalize.return_value = {
            "auto_pr": "true",
            "pr_status": "created",
            "pr_url": "https://example/pr/7",
            "pr_number": "7",
            "pr_branch": "helping-hands/codexcli-test",
            "pr_commit": "abc123",
        }

        hand = CodexCLIHand(config, repo_index)
        chunks = asyncio.run(_collect_stream(hand, "hello"))
        text = "".join(chunks)

        assert "[phase 1/2]" in text
        assert "[phase 2/2]" in text
        assert "init output" in text
        assert "task output" in text
        assert "PR created" in text
        assert len(prompts) == 2

    @patch.object(CodexCLIHand, "_finalize_repo_pr")
    @patch.object(CodexCLIHand, "_invoke_codex", autospec=True)
    def test_stream_emits_non_created_pr_status(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        prompts: list[str] = []

        async def fake_invoke(
            _self: CodexCLIHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            text = "init output\n" if len(prompts) == 1 else "task output\n"
            await emit(text)
            return text

        mock_invoke.side_effect = fake_invoke
        mock_finalize.return_value = {
            "auto_pr": "true",
            "pr_status": "missing_token",
            "pr_url": "",
            "pr_number": "",
            "pr_branch": "",
            "pr_commit": "",
            "pr_error": "GITHUB_TOKEN or GH_TOKEN is required",
        }

        hand = CodexCLIHand(config, repo_index)
        chunks = asyncio.run(_collect_stream(hand, "hello"))
        text = "".join(chunks)

        assert len(prompts) == 2
        assert "PR status: missing_token" in text
        assert "GITHUB_TOKEN or GH_TOKEN is required" in text

    @patch.object(CodexCLIHand, "_finalize_repo_pr")
    @patch.object(CodexCLIHand, "_invoke_codex", autospec=True)
    def test_stream_stops_after_interrupt(
        self,
        mock_invoke: MagicMock,
        mock_finalize: MagicMock,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        hand = CodexCLIHand(config, repo_index)
        prompts: list[str] = []

        async def fake_invoke(
            _self: CodexCLIHand,
            prompt: str,
            *,
            emit: Any,
        ) -> str:
            prompts.append(prompt)
            await emit("init output\n")
            hand.interrupt()
            return "init output\n"

        mock_invoke.side_effect = fake_invoke
        mock_finalize.return_value = {
            "auto_pr": "true",
            "pr_status": "created",
            "pr_url": "https://example/pr/7",
            "pr_number": "7",
            "pr_branch": "helping-hands/codexcli-test",
            "pr_commit": "abc123",
        }

        chunks = asyncio.run(_collect_stream(hand, "hello"))
        text = "".join(chunks)

        assert "Interrupted during initialization" in text
        assert "[phase 2/2]" not in text
        assert len(prompts) == 1
        mock_finalize.assert_not_called()


# ---------------------------------------------------------------------------
# GooseCLIHand
# ---------------------------------------------------------------------------


class TestGooseCLIHand:
    def test_command_not_found_message_mentions_docker_rebuild(
        self,
        config: Config,
        repo_index: RepoIndex,
    ) -> None:
        hand = GooseCLIHand(config, repo_index)
        msg = hand._command_not_found_message("goose")
        assert "HELPING_HANDS_GOOSE_CLI_CMD" in msg
        assert "rebuild worker images" in msg

    def test_render_command_defaults_to_goose_run_text(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_GOOSE_CLI_CMD", raising=False)
        config = Config(repo="/tmp/fake", model="default")
        hand = GooseCLIHand(config, repo_index)

        cmd = hand._render_command("hello world")

        assert cmd[:5] == ["goose", "run", "--with-builtin", "developer", "--text"]
        assert cmd[-1] == "hello world"

    def test_render_command_normalizes_instructions_flag_to_text(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GOOSE_CLI_CMD", "goose run --instructions")
        config = Config(repo="/tmp/fake", model="default")
        hand = GooseCLIHand(config, repo_index)

        cmd = hand._render_command("hello world")

        assert cmd[:5] == ["goose", "run", "--with-builtin", "developer", "--text"]
        assert cmd[-1] == "hello world"

    def test_render_command_injects_developer_builtin_when_missing(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GOOSE_CLI_CMD", "goose run --text")
        config = Config(repo="/tmp/fake", model="default")
        hand = GooseCLIHand(config, repo_index)

        cmd = hand._render_command("hello world")

        assert cmd[:5] == ["goose", "run", "--with-builtin", "developer", "--text"]
        assert cmd[-1] == "hello world"

    def test_render_command_does_not_append_generic_model_flag(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_GOOSE_CLI_CMD", raising=False)
        config = Config(repo="/tmp/fake", model="gpt-5.2")
        hand = GooseCLIHand(config, repo_index)

        cmd = hand._render_command("hello world")

        assert cmd[:5] == ["goose", "run", "--with-builtin", "developer", "--text"]
        assert "--model" not in cmd
        assert cmd[-2:] == ["--text", "hello world"]

    def test_build_subprocess_env_uses_github_token_when_gh_token_missing(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        hand = GooseCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert env["GH_TOKEN"] == "ghp_test"
        assert env["GITHUB_TOKEN"] == "ghp_test"

    def test_build_subprocess_env_sets_default_provider_and_model(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GH_TOKEN", "ghp_primary")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        config = Config(repo="/tmp/fake", model="default")
        hand = GooseCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert env["GOOSE_PROVIDER"] == "ollama"
        assert env["GOOSE_MODEL"] == "llama3.2:latest"
        assert env["OLLAMA_HOST"] == "http://localhost:11434"

    def test_build_subprocess_env_uses_explicit_ollama_host(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GH_TOKEN", "ghp_primary")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        monkeypatch.setenv("OLLAMA_HOST", "192.168.1.143:11434")
        config = Config(repo="/tmp/fake", model="default")
        hand = GooseCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert env["GOOSE_PROVIDER"] == "ollama"
        assert env["OLLAMA_HOST"] == "http://192.168.1.143:11434"

    def test_build_subprocess_env_derives_ollama_host_from_base_url(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GH_TOKEN", "ghp_primary")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://192.168.1.143:11434/v1")
        config = Config(repo="/tmp/fake", model="default")
        hand = GooseCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert env["GOOSE_PROVIDER"] == "ollama"
        assert env["OLLAMA_HOST"] == "http://192.168.1.143:11434"

    def test_build_subprocess_env_maps_provider_model_from_helping_hands_model(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GH_TOKEN", "ghp_primary")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        config = Config(repo="/tmp/fake", model="anthropic/claude-sonnet-4-5")
        hand = GooseCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert env["GOOSE_PROVIDER"] == "anthropic"
        assert env["GOOSE_MODEL"] == "claude-sonnet-4-5"

    def test_build_subprocess_env_respects_explicit_goose_provider_and_model(
        self,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GH_TOKEN", "ghp_primary")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GOOSE_PROVIDER", "anthropic")
        monkeypatch.setenv("GOOSE_MODEL", "claude-sonnet-4-5")
        config = Config(repo="/tmp/fake", model="default")
        hand = GooseCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert env["GOOSE_PROVIDER"] == "anthropic"
        assert env["GOOSE_MODEL"] == "claude-sonnet-4-5"

    def test_build_subprocess_env_prefers_gh_token(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GH_TOKEN", "ghp_primary")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_secondary")
        hand = GooseCLIHand(config, repo_index)

        env = hand._build_subprocess_env()

        assert env["GH_TOKEN"] == "ghp_primary"
        assert env["GITHUB_TOKEN"] == "ghp_primary"

    def test_build_subprocess_env_requires_token(
        self,
        config: Config,
        repo_index: RepoIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        hand = GooseCLIHand(config, repo_index)

        with pytest.raises(RuntimeError, match="GH_TOKEN or GITHUB_TOKEN"):
            hand._build_subprocess_env()


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
        chunks = asyncio.run(_collect_stream(hand, "hello"))
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

    @patch("helping_hands.lib.github.GitHubClient")
    def test_run_uses_repo_default_branch_when_base_not_configured(
        self,
        mock_gh_cls: MagicMock,
        repo_index: RepoIndex,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = Config(repo="owner/repo", model="test-model")
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)

        mock_gh = MagicMock()
        mock_gh.default_branch.return_value = "master"
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        hand = E2EHand(config, repo_index)
        resp = hand.run("dry test", hand_uuid="task-126", dry_run=True)

        assert resp.metadata["base_branch"] == "master"
        mock_gh.default_branch.assert_called_once_with("owner/repo")
        clone_kwargs = mock_gh.clone.call_args.kwargs
        assert clone_kwargs["branch"] == "master"

    @patch("helping_hands.lib.github.GitHubClient")
    def test_run_falls_back_to_clone_default_branch_when_lookup_fails(
        self,
        mock_gh_cls: MagicMock,
        repo_index: RepoIndex,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = Config(repo="owner/repo", model="test-model")
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)

        mock_gh = MagicMock()
        mock_gh.default_branch.side_effect = RuntimeError("api unavailable")
        mock_gh.current_branch.return_value = "master"
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        hand = E2EHand(config, repo_index)
        resp = hand.run("dry test", hand_uuid="task-127", dry_run=True)

        assert resp.metadata["base_branch"] == "master"
        clone_kwargs = mock_gh.clone.call_args.kwargs
        assert clone_kwargs["branch"] is None
        mock_gh.current_branch.assert_called_once()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_stream(hand: Hand, prompt: str) -> list[str]:
    return [chunk async for chunk in hand.stream(prompt)]
