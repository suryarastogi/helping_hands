"""LangGraph-backed implementation of the Hand protocol.

This module provides ``LangGraphHand``, a direct (non-iterative) backend used
through the same ``run``/``stream`` interface exposed by ``Hand``. It is
referenced by the hand package export surface and can be selected by callers
that want LangChain/LangGraph execution semantics with shared final PR logic.
"""

from __future__ import annotations

__all__ = ["LangGraphHand"]

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helping_hands.lib.config import Config
    from helping_hands.lib.repo import RepoIndex

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.model_provider import (
    build_langchain_chat_model,
    resolve_hand_model,
)


class LangGraphHand(Hand):
    """Hand backed by LangChain / LangGraph ``create_react_agent``.

    Requires the ``langchain`` extra to be installed.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._hand_model = resolve_hand_model(self.config.model)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        """Build a LangGraph react agent with the resolved chat model."""
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
        """Send a prompt and return a complete response via LangGraph agent."""
        result = self._agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        last_msg = result["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
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
        """Send a prompt and yield response chunks as they arrive."""
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
