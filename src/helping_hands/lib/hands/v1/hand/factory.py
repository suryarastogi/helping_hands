"""Hand factory: backend name constants and unified hand instantiation.

Centralises the backend-name → Hand-class mapping so that ``cli/main.py``
and ``server/celery_app.py`` share a single dispatch table instead of
duplicating identical ``if/elif`` chains.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helping_hands.lib.config import Config
    from helping_hands.lib.hands.v1.hand.base import Hand
    from helping_hands.lib.repo import RepoIndex

__all__ = [
    "BACKEND_BASIC_AGENT",
    "BACKEND_BASIC_ATOMIC",
    "BACKEND_BASIC_LANGGRAPH",
    "BACKEND_CLAUDECODECLI",
    "BACKEND_CODEXCLI",
    "BACKEND_DEVINCLI",
    "BACKEND_DOCKER_SANDBOX_CLAUDE",
    "BACKEND_E2E",
    "BACKEND_GEMINICLI",
    "BACKEND_GOOSE",
    "BACKEND_OPENCODECLI",
    "SUPPORTED_BACKENDS",
    "create_hand",
    "get_enabled_backends",
]

# --- Backend name constants ---------------------------------------------------

BACKEND_E2E = "e2e"
"""End-to-end integration test backend."""

BACKEND_BASIC_LANGGRAPH = "basic-langgraph"
"""LangGraph agent loop backend."""

BACKEND_BASIC_ATOMIC = "basic-atomic"
"""Atomic Agents loop backend."""

BACKEND_BASIC_AGENT = "basic-agent"
"""Alias for basic-atomic backend."""

BACKEND_CODEXCLI = "codexcli"
"""OpenAI Codex CLI backend."""

BACKEND_CLAUDECODECLI = "claudecodecli"
"""Claude Code CLI backend."""

BACKEND_DOCKER_SANDBOX_CLAUDE = "docker-sandbox-claude"
"""Docker-sandboxed Claude Code CLI backend."""

BACKEND_GOOSE = "goose"
"""Goose CLI backend."""

BACKEND_GEMINICLI = "geminicli"
"""Gemini CLI backend."""

BACKEND_OPENCODECLI = "opencodecli"
"""OpenCode CLI backend."""

BACKEND_DEVINCLI = "devincli"
"""Devin CLI backend."""

SUPPORTED_BACKENDS: frozenset[str] = frozenset(
    {
        BACKEND_E2E,
        BACKEND_BASIC_LANGGRAPH,
        BACKEND_BASIC_ATOMIC,
        BACKEND_BASIC_AGENT,
        BACKEND_CODEXCLI,
        BACKEND_CLAUDECODECLI,
        BACKEND_DEVINCLI,
        BACKEND_DOCKER_SANDBOX_CLAUDE,
        BACKEND_GOOSE,
        BACKEND_GEMINICLI,
        BACKEND_OPENCODECLI,
    }
)
"""All recognised backend name strings."""

_BACKEND_ENABLED_ENV_VARS: dict[str, str] = {
    BACKEND_E2E: "HELPING_HANDS_E2E_ENABLED",
    BACKEND_BASIC_LANGGRAPH: "HELPING_HANDS_LANGGRAPH_ENABLED",
    BACKEND_BASIC_ATOMIC: "HELPING_HANDS_ATOMIC_ENABLED",
    BACKEND_BASIC_AGENT: "HELPING_HANDS_ATOMIC_ENABLED",
    BACKEND_CODEXCLI: "HELPING_HANDS_CODEXCLI_ENABLED",
    BACKEND_CLAUDECODECLI: "HELPING_HANDS_CLAUDECODECLI_ENABLED",
    BACKEND_DOCKER_SANDBOX_CLAUDE: "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
    BACKEND_GOOSE: "HELPING_HANDS_GOOSE_ENABLED",
    BACKEND_GEMINICLI: "HELPING_HANDS_GEMINICLI_ENABLED",
    BACKEND_OPENCODECLI: "HELPING_HANDS_OPENCODECLI_ENABLED",
    BACKEND_DEVINCLI: "HELPING_HANDS_DEVINCLI_ENABLED",
}
"""Mapping of backend name to its ``*_ENABLED`` env var."""

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def get_enabled_backends() -> list[str]:
    """Return the list of backends that are explicitly enabled via env vars.

    If **no** ``*_ENABLED`` env var is set for any backend, all backends are
    considered enabled (backwards-compatible default).  Otherwise only backends
    whose env var resolves to a truthy value are returned.

    Returns:
        Sorted list of enabled backend name strings.
    """
    has_any = False
    enabled: list[str] = []
    for backend, env_var in _BACKEND_ENABLED_ENV_VARS.items():
        raw = os.environ.get(env_var, "").strip().lower()
        if raw:
            has_any = True
            if raw in _TRUTHY:
                enabled.append(backend)
    if not has_any:
        return sorted(SUPPORTED_BACKENDS)
    return sorted(enabled)


def create_hand(
    backend: str,
    config: Config,
    repo_index: RepoIndex,
    *,
    max_iterations: int | None = None,
) -> Hand:
    """Instantiate a Hand subclass for *backend*.

    Args:
        backend: Backend name string (one of the ``BACKEND_*`` constants).
        config: Resolved run configuration.
        repo_index: Pre-built repository index.
        max_iterations: Optional iteration cap for iterative backends
            (``basic-langgraph`` and ``basic-atomic``/``basic-agent``).

    Returns:
        A concrete ``Hand`` instance ready for ``run()`` or ``stream()``.

    Raises:
        ValueError: If *backend* is not a recognised backend name.
        ModuleNotFoundError: If the backend requires an optional extra
            that is not installed.
    """
    if backend == BACKEND_BASIC_LANGGRAPH:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        kwargs: dict[str, Any] = {}
        if max_iterations is not None:
            kwargs["max_iterations"] = max_iterations
        return BasicLangGraphHand(config, repo_index, **kwargs)

    if backend == BACKEND_CODEXCLI:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        return CodexCLIHand(config, repo_index)

    if backend == BACKEND_CLAUDECODECLI:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        return ClaudeCodeHand(config, repo_index)

    if backend == BACKEND_DOCKER_SANDBOX_CLAUDE:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        return DockerSandboxClaudeCodeHand(config, repo_index)

    if backend == BACKEND_GOOSE:
        from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

        return GooseCLIHand(config, repo_index)

    if backend == BACKEND_GEMINICLI:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        return GeminiCLIHand(config, repo_index)

    if backend == BACKEND_OPENCODECLI:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        return OpenCodeCLIHand(config, repo_index)

    if backend == BACKEND_DEVINCLI:
        from helping_hands.lib.hands.v1.hand.cli.devin import DevinCLIHand

        return DevinCLIHand(config, repo_index)

    if backend in {BACKEND_BASIC_ATOMIC, BACKEND_BASIC_AGENT}:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        kwargs: dict[str, Any] = {}
        if max_iterations is not None:
            kwargs["max_iterations"] = max_iterations
        return BasicAtomicHand(config, repo_index, **kwargs)

    raise ValueError(
        f"Unknown backend: {backend!r}. "
        f"Supported backends: {', '.join(sorted(SUPPORTED_BACKENDS))}"
    )
