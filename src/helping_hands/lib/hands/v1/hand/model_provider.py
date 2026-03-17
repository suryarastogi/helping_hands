"""Hand-facing provider/model resolution and backend adapters.

This module bridges generic provider wrappers from ``lib.ai_providers`` into
backend-specific runtime objects used by hand implementations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from helping_hands.lib.ai_providers import PROVIDERS, AIProvider
from helping_hands.lib.validation import require_non_empty_string

__all__ = [
    "_PROVIDER_ANTHROPIC",
    "_PROVIDER_GOOGLE",
    "_PROVIDER_LITELLM",
    "_PROVIDER_OLLAMA",
    "_PROVIDER_OPENAI",
    "HandModel",
    "build_atomic_client",
    "build_langchain_chat_model",
    "resolve_hand_model",
]

_PROVIDER_OPENAI = "openai"
"""Provider name constant for OpenAI."""

_PROVIDER_ANTHROPIC = "anthropic"
"""Provider name constant for Anthropic."""

_PROVIDER_GOOGLE = "google"
"""Provider name constant for Google."""

_PROVIDER_OLLAMA = "ollama"
"""Provider name constant for Ollama."""

_PROVIDER_LITELLM = "litellm"
"""Provider name constant for LiteLLM."""

_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
"""Default base URL for the Ollama OpenAI-compatible API endpoint."""

_DEFAULT_OLLAMA_API_KEY = "ollama"
"""Default API key used for Ollama (the server doesn't require real auth)."""


@dataclass(frozen=True)
class HandModel:
    """Resolved model selection for hand backends.

    Attributes:
        provider: Resolved AI provider instance for API calls.
        model: Concrete model identifier passed to the provider.
        raw: Original user-supplied model string before resolution.
    """

    provider: AIProvider
    model: str
    raw: str


def resolve_hand_model(model: str | None) -> HandModel:
    """Resolve user model input into a provider wrapper + concrete model name.

    Supported forms:
    - ``default`` or empty: defaults to Ollama provider default model.
    - ``provider``: provider default model (e.g. ``ollama``).
    - ``provider/model``: explicit provider selection (e.g. ``anthropic/claude...``).
    - bare model names: provider inferred by common model prefix heuristics.
    """
    raw = (model or "").strip() or "default"

    if raw == "default":
        provider = PROVIDERS[_PROVIDER_OLLAMA]
        return HandModel(provider=provider, model=provider.default_model, raw=raw)

    direct_provider = PROVIDERS.get(raw)
    if direct_provider is not None:
        return HandModel(
            provider=direct_provider,
            model=direct_provider.default_model,
            raw=raw,
        )

    if "/" in raw:
        maybe_provider, maybe_model = raw.split("/", 1)
        provider = PROVIDERS.get(maybe_provider)
        if provider is not None:
            resolved_model = maybe_model.strip() or provider.default_model
            return HandModel(provider=provider, model=resolved_model, raw=raw)

    inferred = _infer_provider_name(raw)
    provider = PROVIDERS[inferred]
    return HandModel(provider=provider, model=raw, raw=raw)


def _infer_provider_name(model: str) -> str:
    lowered = model.lower()
    if lowered.startswith("claude"):
        return _PROVIDER_ANTHROPIC
    if lowered.startswith("gemini"):
        return _PROVIDER_GOOGLE
    if lowered.startswith("llama"):
        return _PROVIDER_OLLAMA
    return _PROVIDER_OPENAI


def build_langchain_chat_model(hand_model: HandModel, *, streaming: bool) -> Any:
    """Build a LangChain chat model from a resolved hand model."""
    require_non_empty_string(hand_model.model, "hand_model.model")
    provider = hand_model.provider.name
    if provider == _PROVIDER_OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model_name=hand_model.model, streaming=streaming)
    if provider == _PROVIDER_OLLAMA:
        from langchain_openai import ChatOpenAI

        base_url = os.environ.get("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)
        api_key = os.environ.get("OLLAMA_API_KEY", _DEFAULT_OLLAMA_API_KEY)
        extra: dict[str, Any] = {"base_url": base_url, "api_key": api_key}
        return ChatOpenAI(
            model_name=hand_model.model,
            streaming=streaming,
            **extra,
        )
    if provider == _PROVIDER_ANTHROPIC:
        try:
            from langchain_anthropic import ChatAnthropic
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "anthropic models require langchain-anthropic. "
                "Install with: uv add langchain-anthropic"
            ) from exc
        return ChatAnthropic(model=hand_model.model, streaming=streaming)
    if provider == _PROVIDER_GOOGLE:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "google models require langchain-google-genai. "
                "Install with: uv add langchain-google-genai"
            ) from exc
        return ChatGoogleGenerativeAI(model=hand_model.model, streaming=streaming)
    if provider == _PROVIDER_LITELLM:
        try:
            from langchain_community.chat_models import ChatLiteLLM
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "litellm models require langchain-community and litellm. "
                "Install with: uv add langchain-community litellm"
            ) from exc
        return ChatLiteLLM(model=hand_model.model, streaming=streaming)

    raise RuntimeError(f"unsupported provider for LangGraph backend: {provider}")


def build_atomic_client(hand_model: HandModel) -> Any:
    """Build an atomic-agents instructor client from a resolved hand model."""
    require_non_empty_string(hand_model.model, "hand_model.model")
    import instructor

    provider = hand_model.provider.name
    if provider == _PROVIDER_OPENAI:
        return instructor.from_openai(hand_model.provider.inner)
    if provider == _PROVIDER_LITELLM:
        if hasattr(instructor, "from_litellm"):
            return instructor.from_litellm(hand_model.provider.inner.completion)
        raise RuntimeError(
            "litellm provider is not supported by this instructor version. "
            "Upgrade instructor or use an OpenAI model."
        )
    raise RuntimeError(
        f"{provider} provider is not supported by atomic backend. "
        "Use an OpenAI-compatible model/provider for "
        "--backend basic-atomic/basic-agent."
    )
