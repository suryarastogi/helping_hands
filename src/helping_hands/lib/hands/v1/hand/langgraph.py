"""LangGraph-backed implementation of the Hand protocol.

This module provides ``LangGraphHand``, a direct (non-iterative) backend used
through the same ``run``/``stream`` interface exposed by ``Hand``. It is
referenced by the hand package export surface and can be selected by callers
that want LangChain/LangGraph execution semantics with shared final PR logic.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.model_provider import (
    build_langchain_chat_model,
    resolve_hand_model,
)


class LangGraphHand(Hand):
    """Hand backed by LangChain / LangGraph ``create_react_agent``.

    Requires the ``langchain`` extra to be installed.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        """Initialize the LangGraph hand with a resolved model and agent.

        Args:
            config: Application configuration (must include ``model``).
            repo_index: Repository index providing the file tree and root path.
        """
        super().__init__(config, repo_index)
        self._hand_model = resolve_hand_model(self.config.model)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        """Create the LangGraph ``create_react_agent`` instance.

        Requires the ``langchain`` extra.  Builds a LangChain chat model
        from ``self._hand_model`` with streaming enabled, then wraps it in
        a zero-tool react agent with the shared system prompt.

        Returns:
            A LangGraph agent object supporting ``invoke`` and
            ``astream_events``.
        """
        from langgraph.prebuilt import create_react_agent

        llm = build_langchain_chat_model(
            self._hand_model,
            streaming=True,
        )
        system_prompt = self._build_system_prompt()
        return create_react_agent(
            model=llm,
            tools=[],
            prompt=system_prompt,
        )

    def run(self, prompt: str) -> HandResponse:
        """Execute the prompt synchronously via the LangGraph agent.

        Invokes the agent, extracts the last assistant message content,
        finalizes the repo PR, and returns a ``HandResponse``.

        Args:
            prompt: The user task prompt.

        Returns:
            A ``HandResponse`` with the agent output and PR metadata.
        """
        result = self._agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        messages = result.get("messages") or []
        last_msg = messages[-1] if messages else None
        content = (
            last_msg.content
            if last_msg is not None and hasattr(last_msg, "content")
            else str(last_msg)
            if last_msg is not None
            else ""
        )
        pr_metadata = self._finalize_repo_pr(
            backend="langgraph",
            prompt=prompt,
            summary=content,
        )
        return HandResponse(
            message=content,
            metadata={
                "backend": "langgraph",
                "model": self._hand_model.model,
                "provider": self._hand_model.provider.name,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        parts: list[str] = []
        async for event in self._agent.astream_events(
            {"messages": [{"role": "user", "content": prompt}]},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream" and event["data"].get("chunk"):
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    text = str(chunk.content)
                    parts.append(text)
                    yield text
        pr_metadata = self._finalize_repo_pr(
            backend="langgraph",
            prompt=prompt,
            summary="".join(parts),
        )
        if pr_metadata.get("pr_url"):
            yield f"\nPR created: {pr_metadata['pr_url']}\n"
