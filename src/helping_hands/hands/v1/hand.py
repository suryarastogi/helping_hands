"""Unified Hand interface with LangGraph and Atomic Agents backends.

A Hand is the AI agent that operates on a repo. This module defines:
  - ``Hand``: abstract protocol that all backends implement.
  - ``HandResponse``: common response container.
  - ``LangGraphHand``: backend powered by LangChain / LangGraph.
  - ``AtomicHand``: backend powered by atomic-agents.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

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
