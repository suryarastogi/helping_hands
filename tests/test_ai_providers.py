from __future__ import annotations

import asyncio
import sys
from typing import Any
from unittest import mock

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
    assert isinstance(OLLAMA_PROVIDER, OllamaProvider)
    assert set(PROVIDERS) == {"openai", "anthropic", "google", "litellm", "ollama"}


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


# --------------- Provider attribute tests ---------------


@pytest.mark.parametrize(
    ("provider", "name", "env_var", "default_model", "hint"),
    [
        (OPENAI_PROVIDER, "openai", "OPENAI_API_KEY", "gpt-5.2", "uv add openai"),
        (
            ANTHROPIC_PROVIDER,
            "anthropic",
            "ANTHROPIC_API_KEY",
            "claude-3-5-sonnet-latest",
            "uv add anthropic",
        ),
        (
            GOOGLE_PROVIDER,
            "google",
            "GOOGLE_API_KEY",
            "gemini-2.0-flash",
            "uv add google-genai",
        ),
        (
            OLLAMA_PROVIDER,
            "ollama",
            "OLLAMA_API_KEY",
            "llama3.2:latest",
            "uv add openai",
        ),
        (
            LITELLM_PROVIDER,
            "litellm",
            "LITELLM_API_KEY",
            "gpt-5.2",
            "uv add litellm",
        ),
    ],
)
def test_provider_attributes(
    provider: AIProvider,
    name: str,
    env_var: str,
    default_model: str,
    hint: str,
) -> None:
    assert provider.name == name
    assert provider.api_key_env_var == env_var
    assert provider.default_model == default_model
    assert provider.install_hint == hint


# --------------- _build_inner ImportError tests ---------------


def test_openai_build_inner_import_error() -> None:
    provider = OpenAIProvider()
    with (
        mock.patch.dict(sys.modules, {"openai": None}),
        pytest.raises(RuntimeError, match="OpenAI SDK is not installed"),
    ):
        provider._build_inner()


def test_anthropic_build_inner_import_error() -> None:
    provider = AnthropicProvider()
    with (
        mock.patch.dict(sys.modules, {"anthropic": None}),
        pytest.raises(RuntimeError, match="Anthropic SDK is not installed"),
    ):
        provider._build_inner()


def test_google_build_inner_import_error() -> None:
    provider = GoogleProvider()
    with (
        mock.patch.dict(sys.modules, {"google": None, "google.genai": None}),
        pytest.raises(RuntimeError, match="Google GenAI SDK is not installed"),
    ):
        provider._build_inner()


def test_litellm_build_inner_import_error() -> None:
    provider = LiteLLMProvider()
    with (
        mock.patch.dict(sys.modules, {"litellm": None}),
        pytest.raises(RuntimeError, match="LiteLLM is not installed"),
    ):
        provider._build_inner()


def test_ollama_build_inner_import_error() -> None:
    provider = OllamaProvider()
    with (
        mock.patch.dict(sys.modules, {"openai": None}),
        pytest.raises(RuntimeError, match="OpenAI SDK is not installed"),
    ):
        provider._build_inner()


# --------------- Lazy inner initialization ---------------


def test_inner_property_lazy_initialization() -> None:
    provider = _FakeProvider()
    assert provider._inner is None
    inner = provider.inner
    assert inner == {"client": "fake"}
    assert provider._inner is inner
    # Second access returns same object
    assert provider.inner is inner


def test_inner_property_uses_injected_value() -> None:
    injected = {"client": "custom"}
    provider = _FakeProvider(inner=injected)
    assert provider.inner is injected


# --------------- complete with explicit model ---------------


def test_complete_with_explicit_model() -> None:
    provider = _FakeProvider(inner={"client": "test"})
    result = provider.complete("work", model="custom-model")
    assert result["model"] == "custom-model"


# --------------- acomplete async wrapper ---------------


def test_acomplete_calls_complete() -> None:
    provider = _FakeProvider(inner={"client": "test"})
    result = asyncio.run(provider.acomplete("async work"))
    assert result["messages"] == [{"role": "user", "content": "async work"}]
    assert result["model"] == "fake-model"


# --------------- Ollama URL configuration ---------------


def test_ollama_provider_default_base_url() -> None:
    assert OllamaProvider.base_url_env_var == "OLLAMA_BASE_URL"
    assert OllamaProvider.default_base_url == "http://localhost:11434/v1"


# --------------- normalize_messages edge cases ---------------


def test_normalize_messages_empty_sequence() -> None:
    assert normalize_messages([]) == []


def test_normalize_messages_missing_role() -> None:
    result = normalize_messages([{"content": "hi"}])
    assert result == [{"role": "user", "content": "hi"}]


def test_normalize_messages_missing_content() -> None:
    result = normalize_messages([{"role": "assistant"}])
    assert result == [{"role": "assistant", "content": ""}]
