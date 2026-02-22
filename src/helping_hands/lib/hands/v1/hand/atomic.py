"""Atomic-agents implementation of the Hand protocol.

This module provides ``AtomicHand``, which conforms to the same public
``run``/``stream`` interface as other hand backends while delegating model
execution to ``atomic-agents``. It includes async compatibility fallbacks so
callers can stream output even when the underlying client is sync-only.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse


class AtomicHand(Hand):
    """Hand backed by the atomic-agents framework.

    Requires the ``atomic`` extra to be installed.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
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
        message = response.chat_message
        pr_metadata = self._finalize_repo_pr(
            backend="atomic",
            prompt=prompt,
            summary=message,
        )
        return HandResponse(
            message=message,
            metadata={
                "backend": "atomic",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        parts: list[str] = []
        user_input = self._make_input(prompt)
        try:
            async_result = self._agent.run_async(user_input)
        except AssertionError:
            partial = await asyncio.to_thread(self._agent.run, user_input)
            if hasattr(partial, "chat_message") and partial.chat_message:
                text = str(partial.chat_message)
                parts.append(text)
                yield text
            async_result = None
        except Exception:
            raise
        if async_result is None:
            pass
        elif hasattr(async_result, "__aiter__"):
            async for partial in async_result:
                if hasattr(partial, "chat_message") and partial.chat_message:
                    text = str(partial.chat_message)
                    parts.append(text)
                    yield text
        else:
            try:
                partial = await async_result
            except AssertionError:
                partial = await asyncio.to_thread(self._agent.run, user_input)
            if hasattr(partial, "chat_message") and partial.chat_message:
                text = str(partial.chat_message)
                parts.append(text)
                yield text
        pr_metadata = self._finalize_repo_pr(
            backend="atomic",
            prompt=prompt,
            summary="".join(parts),
        )
        if pr_metadata.get("pr_url"):
            yield f"\nPR created: {pr_metadata['pr_url']}\n"
