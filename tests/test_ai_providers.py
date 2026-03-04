from __future__ import annotations

import asyncio
from typing import Any

import pytest

from helping_hands.lib.ai_providers import (
    ANTHROPIC_PROVIDER,
    GOOGLE_PROVIDER,
    LITELLM_PROVIDER,
    OLLAMA_PROVIDER,
    OPENAI_PROVIDER,
    PROVIDERS,
)
from helping_hands.lib.ai_providers.anthropic import AnthropicProvider
from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.ai_providers.litellm import LiteLLMProvider
from helping_hands.lib.ai_providers.ollama import OllamaProvider
from helping_hands.lib.ai_providers.openai import OpenAIProvider
from helping_hands.lib.ai_providers.types import AIProvider, normalize_messages


class _FakeProvider(AIProvider):
    name = "fake"
    api_key_env_var = "FAKE_API_KEY"
    default_model = "fake-model"
    install_hint = "none"

    def _build_inner(self) -> Any:
        return {"client": "fake"}

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        return {
            "inner": inner,
            "messages": messages,
            "model": model,
            "kwargs": kwargs,
        }


def test_normalize_messages_from_string() -> None:
    assert normalize_messages("hello") == [{"role": "user", "content": "hello"}]


def test_normalize_messages_from_sequence() -> None:
    messages = [{"role": "system", "content": "rules"}, {"content": "hi"}]
    assert normalize_messages(messages) == [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "hi"},
    ]


def test_normalize_messages_empty_content() -> None:
    """Messages with empty content are preserved."""
    result = normalize_messages([{"role": "user", "content": ""}])
    assert result == [{"role": "user", "content": ""}]


def test_normalize_messages_missing_role_defaults_to_user() -> None:
    """Messages without a role key default to 'user'."""
    result = normalize_messages([{"content": "test"}])
    assert result[0]["role"] == "user"


def test_normalize_messages_missing_content_defaults_to_empty() -> None:
    """Messages without content key default to empty string."""
    result = normalize_messages([{"role": "system"}])
    assert result[0]["content"] == ""


def test_base_provider_complete_uses_default_model() -> None:
    provider = _FakeProvider(inner={"client": "injected"})
    result = provider.complete("do work", temperature=0.1)
    assert result["messages"] == [{"role": "user", "content": "do work"}]
    assert result["model"] == "fake-model"
    assert result["inner"] == {"client": "injected"}
    assert result["kwargs"]["temperature"] == 0.1


def test_base_provider_complete_with_explicit_model() -> None:
    """Explicit model parameter overrides the default."""
    provider = _FakeProvider(inner={"client": "x"})
    result = provider.complete("hi", model="custom-model")
    assert result["model"] == "custom-model"


def test_base_provider_lazy_inner_construction() -> None:
    """inner property calls _build_inner lazily."""
    provider = _FakeProvider()
    assert provider._inner is None
    inner = provider.inner
    assert inner == {"client": "fake"}
    # Second access returns the same object
    assert provider.inner is inner


def test_base_provider_acomplete() -> None:
    """acomplete wraps complete in asyncio.to_thread."""
    provider = _FakeProvider(inner={"client": "async"})
    result = asyncio.run(provider.acomplete("async-test", model="m1"))
    assert result["messages"] == [{"role": "user", "content": "async-test"}]
    assert result["model"] == "m1"


def test_provider_registry_contains_all_wrappers() -> None:
    assert isinstance(OPENAI_PROVIDER, OpenAIProvider)
    assert isinstance(ANTHROPIC_PROVIDER, AnthropicProvider)
    assert isinstance(GOOGLE_PROVIDER, GoogleProvider)
    assert isinstance(LITELLM_PROVIDER, LiteLLMProvider)
    assert isinstance(OLLAMA_PROVIDER, OllamaProvider)
    assert set(PROVIDERS) == {"openai", "anthropic", "google", "litellm", "ollama"}


def test_provider_install_hints() -> None:
    """Each provider exposes a non-empty install_hint."""
    for name, provider in PROVIDERS.items():
        assert provider.install_hint, f"{name} has empty install_hint"


def test_provider_api_key_env_vars() -> None:
    """Each provider has a distinct api_key_env_var."""
    env_vars = [p.api_key_env_var for p in PROVIDERS.values()]
    assert len(set(env_vars)) == len(env_vars)


def test_openai_provider_complete_uses_inner_client() -> None:
    calls: dict[str, Any] = {}

    class _Responses:
        def create(self, **kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    class _Inner:
        responses = _Responses()

    provider = OpenAIProvider(inner=_Inner())
    result = provider.complete("hello")
    assert result == {"ok": True}
    assert calls["model"] == "gpt-5.2"
    assert calls["input"] == [{"role": "user", "content": "hello"}]


def test_anthropic_provider_complete_uses_inner_client() -> None:
    calls: dict[str, Any] = {}

    class _Messages:
        def create(self, **kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    class _Inner:
        messages = _Messages()

    provider = AnthropicProvider(inner=_Inner())
    result = provider.complete("hello")
    assert result == {"ok": True}
    assert calls["model"] == "claude-3-5-sonnet-latest"
    assert calls["messages"] == [{"role": "user", "content": "hello"}]
    assert calls["max_tokens"] == 1024


def test_google_provider_complete_uses_inner_client() -> None:
    calls: dict[str, Any] = {}

    class _Models:
        def generate_content(self, **kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    class _Inner:
        models = _Models()

    provider = GoogleProvider(inner=_Inner())
    result = provider.complete("hello")
    assert result == {"ok": True}
    assert calls["model"] == "gemini-2.0-flash"
    assert calls["contents"] == ["hello"]


def test_litellm_provider_complete_uses_inner_library() -> None:
    calls: dict[str, Any] = {}

    class _Inner:
        @staticmethod
        def completion(**kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    provider = LiteLLMProvider(inner=_Inner())
    result = provider.complete("hello")
    assert result == {"ok": True}
    assert calls["model"] == "gpt-5.2"
    assert calls["messages"] == [{"role": "user", "content": "hello"}]


def test_ollama_provider_complete_uses_inner_client() -> None:
    calls: dict[str, Any] = {}

    class _ChatCompletions:
        def create(self, **kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    class _Chat:
        completions = _ChatCompletions()

    class _Inner:
        chat = _Chat()

    provider = OllamaProvider(inner=_Inner())
    result = provider.complete("hello")
    assert result == {"ok": True}
    assert calls["model"] == "llama3.2:latest"
    assert calls["messages"] == [{"role": "user", "content": "hello"}]


# ---------------------------------------------------------------------------
# Error path tests (TD-003)
# ---------------------------------------------------------------------------


def test_openai_build_inner_without_sdk_raises() -> None:
    """OpenAI _build_inner raises RuntimeError when SDK is not installed."""
    import sys

    provider = OpenAIProvider()
    # Temporarily hide the openai module
    saved = sys.modules.get("openai")
    sys.modules["openai"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(RuntimeError, match="OpenAI SDK is not installed"):
            provider._build_inner()
    finally:
        if saved is not None:
            sys.modules["openai"] = saved
        else:
            sys.modules.pop("openai", None)
