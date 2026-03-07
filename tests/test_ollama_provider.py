"""Tests for the Ollama provider wrapper."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.ollama import OllamaProvider


class TestOllamaProviderBuildInner:
    def test_uses_default_api_key_and_base_url(self, monkeypatch) -> None:
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

        fake_openai_cls = MagicMock()
        fake_module = ModuleType("openai")
        fake_module.OpenAI = fake_openai_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"openai": fake_module}):
            provider = OllamaProvider()
            provider._inner = None
            _ = provider.inner

        fake_openai_cls.assert_called_once_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )

    def test_uses_custom_env_vars(self, monkeypatch) -> None:
        monkeypatch.setenv("OLLAMA_API_KEY", "my-key")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:8080/v1")

        fake_openai_cls = MagicMock()
        fake_module = ModuleType("openai")
        fake_module.OpenAI = fake_openai_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"openai": fake_module}):
            provider = OllamaProvider()
            provider._inner = None
            _ = provider.inner

        fake_openai_cls.assert_called_once_with(
            api_key="my-key",
            base_url="http://custom:8080/v1",
        )

    def test_raises_runtime_error_when_openai_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

        with patch.dict(sys.modules, {"openai": None}):
            provider = OllamaProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="OpenAI SDK is not installed"):
                _ = provider.inner


class TestOllamaProviderCompleteImpl:
    def test_delegates_to_chat_completions_create(self) -> None:
        mock_inner = MagicMock()
        mock_inner.chat.completions.create.return_value = "response"

        provider = OllamaProvider()
        messages: list[dict[str, str]] = [{"role": "user", "content": "hello"}]
        result = provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="llama3.2:latest",
        )

        mock_inner.chat.completions.create.assert_called_once_with(
            model="llama3.2:latest",
            messages=messages,
        )
        assert result == "response"

    def test_passes_extra_kwargs_to_inner(self) -> None:
        mock_inner = MagicMock()
        mock_inner.chat.completions.create.return_value = {"choices": []}

        provider = OllamaProvider()
        messages: list[dict[str, str]] = [{"role": "user", "content": "hi"}]
        result = provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="llama3.2:latest",
            temperature=0.5,
            max_tokens=100,
        )

        mock_inner.chat.completions.create.assert_called_once_with(
            model="llama3.2:latest",
            messages=messages,
            temperature=0.5,
            max_tokens=100,
        )
        assert result == {"choices": []}


class TestOllamaProviderClassAttrs:
    def test_name(self) -> None:
        assert OllamaProvider.name == "ollama"

    def test_api_key_env_var(self) -> None:
        assert OllamaProvider.api_key_env_var == "OLLAMA_API_KEY"

    def test_default_model(self) -> None:
        assert OllamaProvider.default_model == "llama3.2:latest"

    def test_install_hint(self) -> None:
        assert OllamaProvider.install_hint == "uv add openai"

    def test_base_url_env_var(self) -> None:
        assert OllamaProvider.base_url_env_var == "OLLAMA_BASE_URL"

    def test_default_base_url(self) -> None:
        assert OllamaProvider.default_base_url == "http://localhost:11434/v1"


# ---------------------------------------------------------------------------
# OLLAMA_PROVIDER singleton
# ---------------------------------------------------------------------------


class TestOllamaProviderSingleton:
    def test_singleton_is_ollama_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.ollama import OLLAMA_PROVIDER

        assert isinstance(OLLAMA_PROVIDER, OllamaProvider)

    def test_singleton_identity_across_imports(self) -> None:
        from helping_hands.lib.ai_providers.ollama import OLLAMA_PROVIDER as FIRST
        from helping_hands.lib.ai_providers.ollama import OLLAMA_PROVIDER as SECOND

        assert FIRST is SECOND
