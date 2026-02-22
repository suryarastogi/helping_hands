"""Placeholder hand backends that satisfy the Hand interface contract.

These classes provide stable backend names and return shapes for planned CLI
integrations (Claude Code, Codex CLI, Gemini CLI). They inherit from Hand so
callers can route to them today without special-case wiring, while keeping
implementation details as future work.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse


class ClaudeCodeHand(Hand):
    """Hand backed by Claude Code via a terminal/bash invocation.

    This backend would run the Claude Code CLI (or equivalent) as a
    subprocess: e.g. a terminal/bash call that passes the repo path and
    user prompt, then captures stdout/stderr. Not yet implemented; this
    class is scaffolding for future integration.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="claudecode",
            prompt=prompt,
            summary="ClaudeCode hand not yet implemented.",
        )
        return HandResponse(
            message="ClaudeCode hand not yet implemented.",
            metadata={
                "backend": "claudecode",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "ClaudeCode hand not yet implemented."


class CodexCLIHand(Hand):
    """Hand backed by Codex CLI via a terminal/bash invocation.

    This backend would run the Codex CLI as a subprocess with repo context
    and the user prompt, then capture stdout/stderr. Not yet implemented;
    this class is scaffolding for future integration.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="codexcli",
            prompt=prompt,
            summary="CodexCLI hand not yet implemented.",
        )
        return HandResponse(
            message="CodexCLI hand not yet implemented.",
            metadata={
                "backend": "codexcli",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "CodexCLI hand not yet implemented."


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
