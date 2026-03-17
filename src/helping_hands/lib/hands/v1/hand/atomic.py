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

from helping_hands.lib.hands.v1.hand.base import (
    _META_BACKEND,
    _META_MODEL,
    _META_PR_URL,
    _META_PROVIDER,
    Hand,
    HandResponse,
)
from helping_hands.lib.hands.v1.hand.iterative import (
    _RUN_ASYNC_ERRORS,
)
from helping_hands.lib.hands.v1.hand.model_provider import (
    build_atomic_client,
    resolve_hand_model,
)

logger = logging.getLogger(__name__)

__all__ = ["AtomicHand"]


class AtomicHand(Hand):
    """Hand backed by the atomic-agents framework.

    Requires the ``atomic`` extra to be installed.
    """

    _BACKEND_NAME = "atomic"
    """Backend identifier used in PR metadata and response dicts."""

    def __init__(self, config: Any, repo_index: Any) -> None:
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
        if self._input_schema is None:
            raise RuntimeError("_input_schema not initialised; call _build_agent first")
        return self._input_schema(chat_message=prompt)

    @staticmethod
    def _extract_message(response: Any) -> str:
        """Extract the chat message text from an Atomic Agents response.

        Unlike ``BasicAtomicHand._extract_message`` (which falls back to
        ``str(response)``), this variant returns ``""`` when no truthy
        ``chat_message`` is found.  This matches the single-shot stream
        pattern where only real content should be yielded.

        Args:
            response: Atomic Agents agent response object.

        Returns:
            String content from ``chat_message`` if present and truthy,
            otherwise ``""``.
        """
        if hasattr(response, "chat_message") and response.chat_message:
            return str(response.chat_message)
        return ""

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
        message = self._extract_message(response)
        pr_metadata = self._finalize_repo_pr(
            backend=self._BACKEND_NAME,
            prompt=prompt,
            summary=message,
        )
        return HandResponse(
            message=message,
            metadata={
                _META_BACKEND: self._BACKEND_NAME,
                _META_MODEL: self._hand_model.model,
                _META_PROVIDER: self._hand_model.provider.name,
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
            text = self._extract_message(partial)
            if text:
                parts.append(text)
                yield text
            async_result = None
        except _RUN_ASYNC_ERRORS:
            logger.debug("run_async raised non-AssertionError", exc_info=True)
            raise
        if async_result is None:
            pass
        elif hasattr(async_result, "__aiter__"):
            async for partial in async_result:
                text = self._extract_message(partial)
                if text:
                    parts.append(text)
                    yield text
        else:
            try:
                partial = await async_result
            except AssertionError:
                partial = await asyncio.to_thread(self._agent.run, user_input)
            text = self._extract_message(partial)
            if text:
                parts.append(text)
                yield text
        pr_metadata = self._finalize_repo_pr(
            backend=self._BACKEND_NAME,
            prompt=prompt,
            summary="".join(parts),
        )
        if pr_metadata.get(_META_PR_URL):
            yield f"\nPR created: {pr_metadata[_META_PR_URL]}\n"
