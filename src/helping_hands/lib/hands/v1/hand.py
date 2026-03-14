"""Unified Hand interface with LangGraph, Atomic Agents, and Claude Code backends.

A Hand is the AI agent that operates on a repo. This module defines:
  - ``Hand``: abstract protocol that all backends implement.
  - ``HandResponse``: common response container.
  - ``LangGraphHand``: backend powered by LangChain / LangGraph.
  - ``AtomicHand``: backend powered by atomic-agents.
  - ``ClaudeCodeHand``: backend that invokes Claude Code via a terminal/bash call.
  - ``CodexCLIHand``: backend that invokes Codex CLI via a terminal/bash call.
  - ``GeminiCLIHand``: backend that invokes Gemini CLI via a terminal/bash call.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import os
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helping_hands.lib.config import Config
    from helping_hands.lib.repo import RepoIndex

logger = logging.getLogger(__name__)


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
# Claude Code backend
# ---------------------------------------------------------------------------

_DEFAULT_CLAUDE_CMD = "claude"
_DEFAULT_TIMEOUT = 300


class ClaudeCodeHand(Hand):
    """Hand backed by Claude Code via a subprocess invocation.

    Runs the Claude Code CLI as a subprocess, passing the user prompt via
    the ``--print`` flag for non-interactive use. The working directory is
    set to the repo root so Claude Code picks up repo context.

    The CLI command is configurable via ``HELPING_HANDS_CLAUDE_CLI_CMD``
    (default: ``claude``).
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._cmd = os.environ.get("HELPING_HANDS_CLAUDE_CLI_CMD", _DEFAULT_CLAUDE_CMD)
        self._timeout = int(
            os.environ.get("HELPING_HANDS_CLAUDE_TIMEOUT", str(_DEFAULT_TIMEOUT))
        )

    def _build_command(self, prompt: str) -> list[str]:
        """Build the CLI command list for a given prompt."""
        return [self._cmd, "--print", prompt]

    def run(self, prompt: str) -> HandResponse:
        """Run Claude Code CLI and return the complete response."""
        cmd = self._build_command(prompt)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_index.root),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except FileNotFoundError:
            msg = (
                f"Claude CLI not found: {self._cmd!r}. "
                "Install it or set HELPING_HANDS_CLAUDE_CLI_CMD."
            )
            return HandResponse(
                message=msg,
                metadata={"backend": "claudecode", "error": "cli_not_found"},
            )
        except subprocess.TimeoutExpired:
            return HandResponse(
                message=f"Claude CLI timed out after {self._timeout}s.",
                metadata={"backend": "claudecode", "error": "timeout"},
            )

        if result.returncode != 0:
            logger.warning(
                "Claude CLI exited %d: %s", result.returncode, result.stderr.strip()
            )
            err_msg = (
                result.stderr.strip()
                or f"Claude CLI exited with code {result.returncode}."
            )
            return HandResponse(
                message=err_msg,
                metadata={
                    "backend": "claudecode",
                    "model": self.config.model,
                    "returncode": result.returncode,
                },
            )

        return HandResponse(
            message=result.stdout,
            metadata={"backend": "claudecode", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Run Claude Code CLI and yield output lines as they arrive."""
        cmd = self._build_command(prompt)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo_index.root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            yield (
                f"Claude CLI not found: {self._cmd!r}. "
                "Install it or set HELPING_HANDS_CLAUDE_CLI_CMD."
            )
            return

        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace")

        await proc.wait()


# ---------------------------------------------------------------------------
# Codex CLI backend
# ---------------------------------------------------------------------------

_DEFAULT_CODEX_CMD = "codex"


class CodexCLIHand(Hand):
    """Hand backed by Codex CLI via a subprocess invocation.

    Runs the Codex CLI as a subprocess, passing the user prompt via
    the ``--quiet`` flag for non-interactive use. The working directory is
    set to the repo root so Codex picks up repo context.

    The CLI command is configurable via ``HELPING_HANDS_CODEX_CLI_CMD``
    (default: ``codex``).
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._cmd = os.environ.get("HELPING_HANDS_CODEX_CLI_CMD", _DEFAULT_CODEX_CMD)
        self._timeout = int(
            os.environ.get("HELPING_HANDS_CODEX_TIMEOUT", str(_DEFAULT_TIMEOUT))
        )

    def _build_command(self, prompt: str) -> list[str]:
        """Build the CLI command list for a given prompt."""
        return [self._cmd, "--quiet", prompt]

    def run(self, prompt: str) -> HandResponse:
        """Run Codex CLI and return the complete response."""
        cmd = self._build_command(prompt)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_index.root),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except FileNotFoundError:
            msg = (
                f"Codex CLI not found: {self._cmd!r}. "
                "Install it or set HELPING_HANDS_CODEX_CLI_CMD."
            )
            return HandResponse(
                message=msg,
                metadata={"backend": "codexcli", "error": "cli_not_found"},
            )
        except subprocess.TimeoutExpired:
            return HandResponse(
                message=f"Codex CLI timed out after {self._timeout}s.",
                metadata={"backend": "codexcli", "error": "timeout"},
            )

        if result.returncode != 0:
            logger.warning(
                "Codex CLI exited %d: %s", result.returncode, result.stderr.strip()
            )
            err_msg = (
                result.stderr.strip()
                or f"Codex CLI exited with code {result.returncode}."
            )
            return HandResponse(
                message=err_msg,
                metadata={
                    "backend": "codexcli",
                    "model": self.config.model,
                    "returncode": result.returncode,
                },
            )

        return HandResponse(
            message=result.stdout,
            metadata={"backend": "codexcli", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Run Codex CLI and yield output lines as they arrive."""
        cmd = self._build_command(prompt)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo_index.root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            yield (
                f"Codex CLI not found: {self._cmd!r}. "
                "Install it or set HELPING_HANDS_CODEX_CLI_CMD."
            )
            return

        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace")

        await proc.wait()


# ---------------------------------------------------------------------------
# Gemini CLI backend
# ---------------------------------------------------------------------------

_DEFAULT_GEMINI_CMD = "gemini"


class GeminiCLIHand(Hand):
    """Hand backed by Gemini CLI via a subprocess invocation.

    Runs the Gemini CLI as a subprocess, passing the user prompt via
    the ``--prompt`` flag for non-interactive use. The working directory is
    set to the repo root so Gemini picks up repo context.

    The CLI command is configurable via ``HELPING_HANDS_GEMINI_CLI_CMD``
    (default: ``gemini``).
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._cmd = os.environ.get("HELPING_HANDS_GEMINI_CLI_CMD", _DEFAULT_GEMINI_CMD)
        self._timeout = int(
            os.environ.get("HELPING_HANDS_GEMINI_TIMEOUT", str(_DEFAULT_TIMEOUT))
        )

    def _build_command(self, prompt: str) -> list[str]:
        """Build the CLI command list for a given prompt."""
        return [self._cmd, "--prompt", prompt]

    def run(self, prompt: str) -> HandResponse:
        """Run Gemini CLI and return the complete response."""
        cmd = self._build_command(prompt)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_index.root),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except FileNotFoundError:
            msg = (
                f"Gemini CLI not found: {self._cmd!r}. "
                "Install it or set HELPING_HANDS_GEMINI_CLI_CMD."
            )
            return HandResponse(
                message=msg,
                metadata={"backend": "geminicli", "error": "cli_not_found"},
            )
        except subprocess.TimeoutExpired:
            return HandResponse(
                message=f"Gemini CLI timed out after {self._timeout}s.",
                metadata={"backend": "geminicli", "error": "timeout"},
            )

        if result.returncode != 0:
            logger.warning(
                "Gemini CLI exited %d: %s", result.returncode, result.stderr.strip()
            )
            err_msg = (
                result.stderr.strip()
                or f"Gemini CLI exited with code {result.returncode}."
            )
            return HandResponse(
                message=err_msg,
                metadata={
                    "backend": "geminicli",
                    "model": self.config.model,
                    "returncode": result.returncode,
                },
            )

        return HandResponse(
            message=result.stdout,
            metadata={"backend": "geminicli", "model": self.config.model},
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Run Gemini CLI and yield output lines as they arrive."""
        cmd = self._build_command(prompt)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo_index.root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            yield (
                f"Gemini CLI not found: {self._cmd!r}. "
                "Install it or set HELPING_HANDS_GEMINI_CLI_CMD."
            )
            return

        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace")

        await proc.wait()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_BACKEND_MAP: dict[str, type[Hand]] = {
    "langgraph": LangGraphHand,
    "atomic": AtomicHand,
    "claudecode": ClaudeCodeHand,
    "codexcli": CodexCLIHand,
    "geminicli": GeminiCLIHand,
}


def create_hand(config: Config, repo_index: RepoIndex) -> Hand:
    """Create a Hand instance based on the configured backend.

    Args:
        config: Application configuration with ``backend`` field.
        repo_index: Indexed repository.

    Returns:
        A Hand subclass instance for the configured backend.

    Raises:
        ValueError: If the backend name is not recognised.
    """
    hand_cls = _BACKEND_MAP.get(config.backend)
    if hand_cls is None:
        msg = (
            f"Unknown backend {config.backend!r}. "
            f"Valid options: {', '.join(_BACKEND_MAP)}"
        )
        raise ValueError(msg)
    return hand_cls(config, repo_index)
