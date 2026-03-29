"""Tests for the AIProvider base class and all five concrete provider wrappers.

Protects the following behavioral invariants:
- `normalize_messages` correctly coerces bare strings and message dicts,
  rejects non-Mapping items with a TypeError that includes the offending index,
  and defaults missing `role`/`content` fields rather than raising KeyError.
- `AIProvider.complete` falls back to `default_model`, rejects blank models,
  and raises ValueError when all messages carry empty content.
- Lazy `inner` initialization calls `_build_inner` exactly once regardless of
  how many times `.inner` is accessed; re-testing prevents silent double-init.
- `acomplete` wraps `complete` via `asyncio.to_thread` so async callers get the
  same result as synchronous ones.
- Each concrete provider (OpenAI, Anthropic, Google, LiteLLM, Ollama) routes
  the right keyword arguments to the right SDK method; a regression here causes
  the provider to silently call the wrong API endpoint or miss required params.
- The `PROVIDERS` registry maps every provider name to the correct singleton so
  CLI/server model-resolution (`provider/model` format) remains consistent.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# AIProvider base class: lazy init, acomplete, error handling
# ---------------------------------------------------------------------------


def test_provider_lazy_init_calls_build_inner_once() -> None:
    """Accessing .inner multiple times only calls _build_inner once."""
    build_count = 0

    class _CountingProvider(AIProvider):
        name = "counting"
        api_key_env_var = "FAKE"
        default_model = "fake"
        install_hint = "none"

        def _build_inner(self) -> Any:
            nonlocal build_count
            build_count += 1
            return {"built": True}

        def _complete_impl(
            self, *, inner: Any, messages: Any, model: str, **kw: Any
        ) -> Any:
            return inner

    p = _CountingProvider()
    _ = p.inner
    _ = p.inner
    assert build_count == 1


def test_provider_complete_overrides_model() -> None:
    """Passing model= to complete() overrides default_model."""
    provider = _FakeProvider(inner={"client": "x"})
    result = provider.complete("hi", model="custom-model")
    assert result["model"] == "custom-model"


def test_provider_acomplete_returns_same_as_complete() -> None:
    """acomplete() wraps complete() via asyncio.to_thread."""
    import asyncio

    provider = _FakeProvider(inner={"client": "x"})
    result = asyncio.run(provider.acomplete("hi", model="async-model"))
    assert result["model"] == "async-model"
    assert result["messages"] == [{"role": "user", "content": "hi"}]


def test_normalize_messages_empty_sequence() -> None:
    """Empty input sequence returns empty list."""
    assert normalize_messages([]) == []


def test_normalize_messages_missing_role_defaults_to_user() -> None:
    """Messages missing 'role' key default to 'user'."""
    result = normalize_messages([{"content": "hello"}])
    assert result == [{"role": "user", "content": "hello"}]


def test_normalize_messages_missing_content_defaults_to_empty() -> None:
    """Messages missing 'content' key default to empty string."""
    result = normalize_messages([{"role": "system"}])
    assert result == [{"role": "system", "content": ""}]


def test_normalize_messages_rejects_non_mapping_string() -> None:
    """A bare string item in the sequence raises TypeError."""
    with pytest.raises(TypeError, match=r"index 0.*got str"):
        normalize_messages(["hello"])  # type: ignore[list-item]


def test_normalize_messages_rejects_non_mapping_int() -> None:
    """An int item in the sequence raises TypeError."""
    with pytest.raises(TypeError, match=r"index 0.*got int"):
        normalize_messages([42])  # type: ignore[list-item]


def test_normalize_messages_rejects_none_item() -> None:
    """A None item in the sequence raises TypeError."""
    with pytest.raises(TypeError, match=r"index 0.*got NoneType"):
        normalize_messages([None])  # type: ignore[list-item]


def test_normalize_messages_rejects_non_mapping_at_later_index() -> None:
    """Error message includes correct index for non-first items."""
    with pytest.raises(TypeError, match=r"index 1.*got list"):
        normalize_messages([{"role": "user", "content": "ok"}, []])  # type: ignore[list-item]


def test_complete_rejects_empty_model_no_default() -> None:
    """complete() raises ValueError when no model specified and default is empty."""

    class _NoModelProvider(_FakeProvider):
        default_model = ""

    provider = _NoModelProvider(inner={"client": "x"})
    with pytest.raises(ValueError, match="No model specified"):
        provider.complete("hello")


def test_complete_rejects_whitespace_model() -> None:
    """complete() raises ValueError when model resolves to whitespace-only."""

    class _WhitespaceModelProvider(_FakeProvider):
        default_model = "   "

    provider = _WhitespaceModelProvider(inner={"client": "x"})
    with pytest.raises(ValueError, match="No model specified"):
        provider.complete("hello")


def test_complete_accepts_explicit_model_with_empty_default() -> None:
    """Explicit model= overrides empty default and works fine."""

    class _NoModelProvider(_FakeProvider):
        default_model = ""

    provider = _NoModelProvider(inner={"client": "x"})
    result = provider.complete("hello", model="gpt-4")
    assert result["model"] == "gpt-4"


def test_anthropic_provider_complete_custom_max_tokens() -> None:
    """Passing max_tokens kwarg overrides the 1024 default."""
    calls: dict[str, Any] = {}

    class _Messages:
        def create(self, **kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    class _Inner:
        messages = _Messages()

    provider = AnthropicProvider(inner=_Inner())
    provider.complete("hi", max_tokens=4096)
    assert calls["max_tokens"] == 4096


def test_google_provider_filters_empty_content() -> None:
    """Google provider filters out messages with empty content."""
    calls: dict[str, Any] = {}

    class _Models:
        def generate_content(self, **kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    class _Inner:
        models = _Models()

    provider = GoogleProvider(inner=_Inner())
    provider.complete(
        [
            {"role": "system", "content": ""},
            {"role": "user", "content": "hello"},
        ]
    )
    assert calls["contents"] == ["hello"]


def test_provider_class_attributes() -> None:
    """Each provider has required class attributes set correctly."""
    for name, provider in PROVIDERS.items():
        assert provider.name == name
        assert provider.api_key_env_var
        assert provider.default_model
        assert provider.install_hint


def test_anthropic_complete_impl_forwards_extra_kwargs() -> None:
    """Extra kwargs (e.g. temperature) are forwarded to inner.messages.create."""
    calls: dict[str, Any] = {}

    class _Messages:
        def create(self, **kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    class _Inner:
        messages = _Messages()

    provider = AnthropicProvider(inner=_Inner())
    provider.complete("hi", temperature=0.7, top_p=0.9)
    assert calls["temperature"] == 0.7
    assert calls["top_p"] == 0.9
    assert calls["max_tokens"] == 1024  # default preserved


def test_litellm_complete_impl_forwards_extra_kwargs() -> None:
    """Extra kwargs (e.g. temperature) are forwarded to inner.completion."""
    calls: dict[str, Any] = {}

    class _Inner:
        @staticmethod
        def completion(**kwargs: Any) -> dict[str, Any]:
            calls.update(kwargs)
            return {"ok": True}

    provider = LiteLLMProvider(inner=_Inner())
    provider.complete("hi", temperature=0.5, top_k=40)
    assert calls["temperature"] == 0.5
    assert calls["top_k"] == 40
