from __future__ import annotations

from typing import Any

from helping_hands.lib.ai_providers import (
    ANTHROPIC_PROVIDER,
    GOOGLE_PROVIDER,
    LITELLM_PROVIDER,
    OPENAI_PROVIDER,
    PROVIDERS,
)
from helping_hands.lib.ai_providers.anthropic import AnthropicProvider
from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.ai_providers.litellm import LiteLLMProvider
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


def test_base_provider_complete_uses_default_model() -> None:
    provider = _FakeProvider(inner={"client": "injected"})
    result = provider.complete("do work", temperature=0.1)
    assert result["messages"] == [{"role": "user", "content": "do work"}]
    assert result["model"] == "fake-model"
    assert result["inner"] == {"client": "injected"}
    assert result["kwargs"]["temperature"] == 0.1


def test_provider_registry_contains_all_wrappers() -> None:
    assert isinstance(OPENAI_PROVIDER, OpenAIProvider)
    assert isinstance(ANTHROPIC_PROVIDER, AnthropicProvider)
    assert isinstance(GOOGLE_PROVIDER, GoogleProvider)
    assert isinstance(LITELLM_PROVIDER, LiteLLMProvider)
    assert set(PROVIDERS) == {"openai", "anthropic", "google", "litellm"}


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
