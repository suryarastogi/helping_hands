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
    "PROVIDER_API_KEY_ENV",
    "_OLLAMA_MODEL_PREFIXES",
    "_OPENAI_MODEL_PREFIXES",
    "_PROVIDER_ANTHROPIC",
    "_PROVIDER_GOOGLE",
    "_PROVIDER_LITELLM",
    "_PROVIDER_OLLAMA",
    "_PROVIDER_OPENAI",
    "HandModel",
    "_require_langchain_class",
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

PROVIDER_API_KEY_ENV: dict[str, str] = {
    _PROVIDER_OPENAI: "OPENAI_API_KEY",
    _PROVIDER_ANTHROPIC: "ANTHROPIC_API_KEY",
    _PROVIDER_GOOGLE: "GOOGLE_API_KEY",
    _PROVIDER_OLLAMA: "OLLAMA_HOST",
}
"""Maps provider name to the environment variable holding its API key."""

_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
"""Default base URL for the Ollama OpenAI-compatible API endpoint."""

_DEFAULT_OLLAMA_API_KEY = "ollama"
"""Default API key used for Ollama (the server doesn't require real auth)."""


def _require_langchain_class(
    module_path: str,
    class_name: str,
    *,
    hint: str,
    install: str | None = None,
) -> type:
    """Import a LangChain chat-model class, raising ``RuntimeError`` on failure.

    Args:
        module_path: Dotted module path (e.g. ``"langchain_anthropic"``).
        class_name: Class to import from the module (e.g. ``"ChatAnthropic"``).
        hint: Human-readable requirement description for the error message.
        install: Explicit ``uv add`` packages string.  When *None*, derived
            from *module_path* by replacing underscores with hyphens.

    Returns:
        The imported class.

    Raises:
        RuntimeError: If the module is not installed.
    """
    try:
        mod = __import__(module_path, fromlist=[class_name])
    except ModuleNotFoundError as exc:
        pkg = install if install is not None else module_path.replace("_", "-")
        raise RuntimeError(f"{hint}. Install with: uv add {pkg}") from exc
    return getattr(mod, class_name)


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


_OLLAMA_MODEL_PREFIXES = (
    "llama",
    "mistral",
    "mixtral",
    "phi",
    "codellama",
    "deepseek",
    "qwen",
    "starcoder",
    "vicuna",
    "yi",
)
"""Model-name prefixes that indicate an Ollama-hosted open-source model."""

_OPENAI_MODEL_PREFIXES = ("gpt", "o1", "o3", "o4")
"""Model-name prefixes that indicate an OpenAI model."""


def _infer_provider_name(model: str) -> str:
    """Infer AI provider from a bare model name using prefix heuristics.

    Resolution order: Anthropic (``claude*``), Google (``gemini*``),
    Ollama (common open-source families), explicit OpenAI (``gpt*``,
    ``o1*``, ``o3*``, ``o4*``), then OpenAI as default fallback.
    """
    lowered = model.lower()
    if lowered.startswith("claude"):
        return _PROVIDER_ANTHROPIC
    if lowered.startswith("gemini"):
        return _PROVIDER_GOOGLE
    if any(lowered.startswith(p) for p in _OLLAMA_MODEL_PREFIXES):
        return _PROVIDER_OLLAMA
    if any(lowered.startswith(p) for p in _OPENAI_MODEL_PREFIXES):
        return _PROVIDER_OPENAI
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
        cls = _require_langchain_class(
            "langchain_anthropic",
            "ChatAnthropic",
            hint="anthropic models require langchain-anthropic",
        )
        return cls(model=hand_model.model, streaming=streaming)
    if provider == _PROVIDER_GOOGLE:
        cls = _require_langchain_class(
            "langchain_google_genai",
            "ChatGoogleGenerativeAI",
            hint="google models require langchain-google-genai",
        )
        return cls(model=hand_model.model, streaming=streaming)
    if provider == _PROVIDER_LITELLM:
        cls = _require_langchain_class(
            "langchain_community.chat_models",
            "ChatLiteLLM",
            hint="litellm models require langchain-community and litellm",
            install="langchain-community litellm",
        )
        return cls(model=hand_model.model, streaming=streaming)

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
