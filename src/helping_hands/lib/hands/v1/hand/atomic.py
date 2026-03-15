"""Atomic-agents implementation of the Hand protocol.

This module provides ``AtomicHand``, which conforms to the same public
``run``/``stream`` interface as other hand backends while delegating model
execution to ``atomic-agents``. It includes async compatibility fallbacks so
callers can stream output even when the underlying client is sync-only.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.model_provider import (
    build_atomic_client,
    resolve_hand_model,
)
from helping_hands.lib.repo import RepoIndex

logger = logging.getLogger(__name__)

__all__ = ["AtomicHand"]


class AtomicHand(Hand):
    """Hand backed by the atomic-agents framework.

    Requires the ``atomic`` extra to be installed.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        """Initialize the Atomic hand with a resolved model and agent.

        Args:
            config: Application configuration (must include ``model``).
            repo_index: Repository index providing the file tree and root path.
        """
        super().__init__(config, repo_index)
        self._input_schema: type[Any] | None = None
        self._hand_model = resolve_hand_model(self.config.model)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        from atomic_agents import AgentConfig, AtomicAgent, BasicChatInputSchema
        from atomic_agents.context import (
            ChatHistory,
            SystemPromptGenerator,
        )

        self._input_schema = BasicChatInputSchema

        client = build_atomic_client(self._hand_model)
        history = ChatHistory()
        prompt_gen = SystemPromptGenerator(
            background=[self._build_system_prompt()],
        )
        return AtomicAgent(
            config=AgentConfig(
                client=client,
                model=self._hand_model.model,
                history=history,
                system_prompt_generator=prompt_gen,
            )
        )

    def _make_input(self, prompt: str) -> Any:
        """Build an input schema instance. Uses mock-safe stored class."""
        assert self._input_schema is not None, "_build_agent must run first"
        return self._input_schema(chat_message=prompt)

    def run(self, prompt: str) -> HandResponse:
        """Execute the prompt synchronously via the Atomic agent.

        Runs the agent, extracts the chat message from the response,
        finalizes the repo PR, and returns a ``HandResponse``.

        Args:
            prompt: The user task prompt.

        Returns:
            A ``HandResponse`` with the agent output and PR metadata.
        """
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
                "model": self._hand_model.model,
                "provider": self._hand_model.provider.name,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream the Atomic agent response asynchronously.

        Attempts ``run_async`` first; falls back to running the sync
        ``run`` in a thread if the client raises ``AssertionError``.
        After streaming completes, finalizes the repo PR and yields
        the PR URL if one was created.

        Args:
            prompt: The user task prompt.

        Yields:
            Response text chunks, followed by the PR URL line if applicable.
        """
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
            logger.debug("run_async raised non-AssertionError", exc_info=True)
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
