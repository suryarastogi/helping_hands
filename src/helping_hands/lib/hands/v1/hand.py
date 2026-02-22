"""Unified Hand interface with LangGraph, Atomic Agents, and CLI backends.

A Hand is the AI agent that operates on a repo. This module defines:
  - ``Hand``: abstract protocol that all backends implement.
  - ``HandResponse``: common response container.
  - ``LangGraphHand``: backend powered by LangChain / LangGraph.
  - ``AtomicHand``: backend powered by atomic-agents.
  - ``E2EHand``: concrete end-to-end hand (clone/edit/commit/push/PR).
  - ``ClaudeCodeHand``: backend that invokes Claude Code via a terminal/bash call.
  - ``CodexCLIHand``: backend that invokes Codex CLI via a terminal/bash call.
  - ``GeminiCLIHand``: backend that invokes Gemini CLI via a terminal/bash call.
"""

from __future__ import annotations

import abc
import os
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from helping_hands.lib.config import Config
    from helping_hands.lib.repo import RepoIndex


# ---------------------------------------------------------------------------
# Common types
# ---------------------------------------------------------------------------


@dataclass
class HandResponse:
    """Standardised response from any Hand backend."""

    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract Hand protocol
# ---------------------------------------------------------------------------


class Hand(abc.ABC):
    """Abstract base for all Hand backends.

    Every backend receives the same repo context and config, and exposes
    ``run`` (sync) and ``stream`` (async generator) for interaction.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        self.config = config
        self.repo_index = repo_index

    def _build_system_prompt(self) -> str:
        """Build a system prompt that includes repo context."""
        file_list = "\n".join(f"  - {f}" for f in self.repo_index.files[:200])
        return (
            "You are a helpful coding assistant working on a repository.\n"
            f"Repo root: {self.repo_index.root}\n"
            f"Files ({len(self.repo_index.files)} total):\n{file_list}\n\n"
            "Follow the repo's conventions. Propose focused, reviewable "
            "changes. Explain your reasoning."
        )

    @abc.abstractmethod
    def run(self, prompt: str) -> HandResponse:
        """Send a prompt and get a complete response."""

    @abc.abstractmethod
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Send a prompt and yield response chunks as they arrive."""


# ---------------------------------------------------------------------------
# LangGraph backend
# ---------------------------------------------------------------------------


class LangGraphHand(Hand):
    """Hand backed by LangChain / LangGraph ``create_react_agent``.

    Requires the ``langchain`` extra to be installed.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(
            model=self.config.model,
            streaming=True,
        )
        system_prompt = self._build_system_prompt()
        return create_react_agent(
            model=llm,
            tools=[],
            prompt=system_prompt,
        )

    def run(self, prompt: str) -> HandResponse:
        result = self._agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        last_msg = result["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        return HandResponse(
            message=content,
            metadata={"backend": "langgraph", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        async for event in self._agent.astream_events(
            {"messages": [{"role": "user", "content": prompt}]},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream" and event["data"].get("chunk"):
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content


# ---------------------------------------------------------------------------
# Atomic Agents backend
# ---------------------------------------------------------------------------


class AtomicHand(Hand):
    """Hand backed by the atomic-agents framework.

    Requires the ``atomic`` extra to be installed.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._input_schema: type[Any] = None  # type: ignore[assignment]
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        import instructor
        import openai
        from atomic_agents import AgentConfig, AtomicAgent, BasicChatInputSchema
        from atomic_agents.context import (
            ChatHistory,
            SystemPromptGenerator,
        )

        self._input_schema = BasicChatInputSchema

        client = instructor.from_openai(openai.OpenAI())
        history = ChatHistory()
        prompt_gen = SystemPromptGenerator(
            background=[self._build_system_prompt()],
        )
        return AtomicAgent(
            config=AgentConfig(
                client=client,
                model=self.config.model,
                history=history,
                system_prompt_generator=prompt_gen,
            )
        )

    def _make_input(self, prompt: str) -> Any:
        """Build an input schema instance. Uses mock-safe stored class."""
        return self._input_schema(chat_message=prompt)

    def run(self, prompt: str) -> HandResponse:
        response = self._agent.run(self._make_input(prompt))
        return HandResponse(
            message=response.chat_message,
            metadata={"backend": "atomic", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        user_input = self._make_input(prompt)
        async for partial in self._agent.run_async(user_input):
            if hasattr(partial, "chat_message") and partial.chat_message:
                yield partial.chat_message


# ---------------------------------------------------------------------------
# End-to-end backend (minimal working flow)
# ---------------------------------------------------------------------------


class E2EHand(Hand):
    """Minimal end-to-end hand for validating clone/edit/PR workflow."""

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    @staticmethod
    def _safe_repo_dir(repo: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", repo.strip("/"))

    @staticmethod
    def _work_base() -> Path:
        root = os.environ.get("HELPING_HANDS_WORK_ROOT", ".")
        return Path(root).expanduser()

    @staticmethod
    def _default_base_branch() -> str:
        return os.environ.get("HELPING_HANDS_BASE_BRANCH", "main")

    @staticmethod
    def _build_e2e_pr_comment(
        *,
        hand_uuid: str,
        prompt: str,
        stamp_utc: str,
        commit_sha: str,
    ) -> str:
        # E2E is deterministic; production hands should provide AI-authored
        # PR summaries/comments when they own the PR workflow.
        return (
            "## helping_hands E2E update\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- hand_uuid: `{hand_uuid}`\n"
            f"- commit: `{commit_sha}`\n"
            f"- prompt: {prompt}\n"
        )

    def run(
        self,
        prompt: str,
        hand_uuid: str | None = None,
        pr_number: int | None = None,
        dry_run: bool = False,
    ) -> HandResponse:
        from helping_hands.lib.github import GitHubClient

        repo = self.config.repo.strip()
        if not repo:
            raise ValueError("E2EHand requires config.repo set to a GitHub owner/repo.")

        hand_uuid = hand_uuid or str(uuid4())
        safe_repo = self._safe_repo_dir(self.config.repo)
        hand_root = self._work_base() / hand_uuid
        repo_dir = hand_root / "git" / safe_repo
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        base_branch = self._default_base_branch()
        branch = f"helping-hands/e2e-{hand_uuid[:8]}"
        e2e_file = "HELPING_HANDS_E2E.md"
        e2e_path = repo_dir / e2e_file

        with GitHubClient() as gh:
            pr_url = ""
            resumed_pr = False
            pr_info: dict[str, Any] | None = None
            if pr_number is not None:
                pr_info = gh.get_pr(repo, pr_number)
                base_branch = str(pr_info["base"])
                pr_url = str(pr_info["url"])
                if not dry_run:
                    branch = str(pr_info["head"])
                    resumed_pr = True

            gh.clone(repo, repo_dir, branch=base_branch, depth=1)
            repo_dir.mkdir(parents=True, exist_ok=True)
            if resumed_pr:
                gh.fetch_branch(repo_dir, branch)
                gh.switch_branch(repo_dir, branch)
            else:
                gh.create_branch(repo_dir, branch)

            stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
            e2e_path.write_text(
                (
                    "# helping_hands E2E marker\n\n"
                    f"- hand_uuid: `{hand_uuid}`\n"
                    f"- prompt: {prompt}\n"
                    f"- timestamp_utc: {stamp}\n"
                ),
                encoding="utf-8",
            )
            commit_sha = ""
            final_pr_number = pr_number
            if not dry_run:
                git_name = os.environ.get(
                    "HELPING_HANDS_GIT_USER_NAME", "helping-hands[bot]"
                )
                git_email = os.environ.get(
                    "HELPING_HANDS_GIT_USER_EMAIL",
                    "helping-hands-bot@users.noreply.github.com",
                )
                gh.set_local_identity(repo_dir, name=git_name, email=git_email)
                commit_sha = gh.add_and_commit(
                    repo_dir,
                    "test(e2e): minimal change from E2EHand",
                    paths=[e2e_file],
                )
                gh.push(repo_dir, branch=branch, set_upstream=True)
                if resumed_pr:
                    final_pr_number = pr_number
                else:
                    pr = gh.create_pr(
                        repo,
                        title="test(e2e): minimal edit by helping_hands",
                        body=(
                            "Automated E2E validation PR.\n\n"
                            f"- hand_uuid: `{hand_uuid}`\n"
                            f"- prompt: {prompt}\n"
                            f"- commit: `{commit_sha}`\n"
                        ),
                        head=branch,
                        base=base_branch,
                    )
                    pr_url = pr.url
                    final_pr_number = pr.number
                if final_pr_number is not None:
                    gh.upsert_pr_comment(
                        repo,
                        final_pr_number,
                        body=self._build_e2e_pr_comment(
                            hand_uuid=hand_uuid,
                            prompt=prompt,
                            stamp_utc=stamp,
                            commit_sha=commit_sha,
                        ),
                        marker="<!-- helping_hands:e2e-status -->",
                    )

        if dry_run:
            message = "E2EHand dry run complete. No push/PR performed."
        else:
            message = f"E2EHand complete. PR: {pr_url}"
        return HandResponse(
            message=message,
            metadata={
                "backend": "e2e",
                "model": self.config.model,
                "hand_uuid": hand_uuid,
                "hand_root": str(hand_root),
                "repo": repo,
                "workspace": str(repo_dir),
                "branch": branch,
                "base_branch": base_branch,
                "commit": commit_sha,
                "pr_number": "" if final_pr_number is None else str(final_pr_number),
                "pr_url": pr_url,
                "resumed_pr": str(resumed_pr).lower(),
                "dry_run": str(dry_run).lower(),
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield self.run(prompt).message


# ---------------------------------------------------------------------------
# Claude Code backend (scaffolding)
# ---------------------------------------------------------------------------


class ClaudeCodeHand(Hand):
    """Hand backed by Claude Code via a terminal/bash invocation.

    This backend would run the Claude Code CLI (or equivalent) as a
    subprocess: e.g. a terminal/bash call that passes the repo path and
    user prompt, then captures stdout/stderr. Not yet implemented; this
    class is scaffolding for future integration.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(
            message="ClaudeCode hand not yet implemented.",
            metadata={"backend": "claudecode", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "ClaudeCode hand not yet implemented."


# ---------------------------------------------------------------------------
# Codex CLI backend (scaffolding)
# ---------------------------------------------------------------------------


class CodexCLIHand(Hand):
    """Hand backed by Codex CLI via a terminal/bash invocation.

    This backend would run the Codex CLI as a subprocess with repo context
    and the user prompt, then capture stdout/stderr. Not yet implemented;
    this class is scaffolding for future integration.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(
            message="CodexCLI hand not yet implemented.",
            metadata={"backend": "codexcli", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "CodexCLI hand not yet implemented."


# ---------------------------------------------------------------------------
# Gemini CLI backend (scaffolding)
# ---------------------------------------------------------------------------


class GeminiCLIHand(Hand):
    """Hand backed by Gemini CLI via a terminal/bash invocation.

    This backend would run the Gemini CLI as a subprocess with repo context
    and the user prompt, then capture stdout/stderr. Not yet implemented;
    this class is scaffolding for future integration.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(
            message="GeminiCLI hand not yet implemented.",
            metadata={"backend": "geminicli", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "GeminiCLI hand not yet implemented."
