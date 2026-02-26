"""Gemini CLI hand scaffold."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse


class GeminiCLIHand(Hand):
    """Hand backed by Gemini CLI via a terminal/bash invocation.

    This backend would run the Gemini CLI as a subprocess with repo context
    and the user prompt, then capture stdout/stderr. Not yet implemented;
    this class is scaffolding for future integration.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="geminicli",
            prompt=prompt,
            summary="GeminiCLI hand not yet implemented.",
        )
        return HandResponse(
            message="GeminiCLI hand not yet implemented.",
            metadata={
                "backend": "geminicli",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "GeminiCLI hand not yet implemented."
