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


class LangGraphHand(Hand):
    """Hand backed by LangChain / LangGraph ``create_react_agent``.

    Requires the ``langchain`` extra to be installed.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(
            model_name=self.config.model,
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
        pr_metadata = self._finalize_repo_pr(
            backend="langgraph",
            prompt=prompt,
            summary=content,
        )
        return HandResponse(
            message=content,
            metadata={
                "backend": "langgraph",
                "model": self.config.model,
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
