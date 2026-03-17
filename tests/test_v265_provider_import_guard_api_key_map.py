"""Tests for v265: _require_sdk() helper and PROVIDER_API_KEY_ENV constant."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any
from unittest.mock import patch

import pytest

from helping_hands.lib.ai_providers.anthropic import AnthropicProvider
from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.ai_providers.litellm import LiteLLMProvider
from helping_hands.lib.ai_providers.ollama import OllamaProvider
from helping_hands.lib.ai_providers.openai import OpenAIProvider
from helping_hands.lib.ai_providers.types import AIProvider
from helping_hands.lib.hands.v1.hand.cli.opencode import _PROVIDER_ENV_MAP
from helping_hands.lib.hands.v1.hand.model_provider import (
    _PROVIDER_ANTHROPIC,
    _PROVIDER_GOOGLE,
    _PROVIDER_OLLAMA,
    _PROVIDER_OPENAI,
    PROVIDER_API_KEY_ENV,
)

# ---------------------------------------------------------------------------
# _require_sdk() base class method
# ---------------------------------------------------------------------------


class _ConcreteProvider(AIProvider):
    """Minimal concrete provider for testing _require_sdk."""

    name = "test"
    api_key_env_var = "TEST_API_KEY"
    default_model = "test-model"
    install_hint = "pip install test-sdk"  # type: ignore[assignment]

    def _build_inner(self) -> Any:
        return self._require_sdk("test_sdk")

    def _complete_impl(  # type: ignore[override]
        self, *, inner: Any, messages: list[dict[str, str]], model: str, **kwargs: Any
    ) -> None:
        return None


class TestRequireSdk:
    """Tests for AIProvider._require_sdk()."""

    def test_returns_module_when_installed(self) -> None:
        fake_mod = ModuleType("test_sdk")
        with patch.dict(sys.modules, {"test_sdk": fake_mod}):
            provider = _ConcreteProvider()
            result = provider._require_sdk("test_sdk")
        assert result is fake_mod

    def test_raises_runtime_error_when_missing(self) -> None:
        with patch.dict(sys.modules, {"test_sdk": None}):
            provider = _ConcreteProvider()
            with pytest.raises(RuntimeError, match="is not installed"):
                provider._require_sdk("test_sdk")

    def test_error_message_includes_install_hint(self) -> None:
        with patch.dict(sys.modules, {"test_sdk": None}):
            provider = _ConcreteProvider()
            with pytest.raises(RuntimeError, match="pip install test-sdk"):
                provider._require_sdk("test_sdk")

    def test_error_message_includes_module_name(self) -> None:
        with patch.dict(sys.modules, {"test_sdk": None}):
            provider = _ConcreteProvider()
            with pytest.raises(RuntimeError, match="test_sdk"):
                provider._require_sdk("test_sdk")

    def test_chains_import_error(self) -> None:
        with patch.dict(sys.modules, {"test_sdk": None}):
            provider = _ConcreteProvider()
            with pytest.raises(RuntimeError) as exc_info:
                provider._require_sdk("test_sdk")
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, ImportError)

    def test_works_with_dotted_module_name(self) -> None:
        fake_genai = ModuleType("google.genai")
        fake_google = ModuleType("google")
        with patch.dict(
            sys.modules, {"google": fake_google, "google.genai": fake_genai}
        ):
            provider = _ConcreteProvider()
            result = provider._require_sdk("google.genai")
        assert result is fake_genai


# ---------------------------------------------------------------------------
# Providers use _require_sdk (integration)
# ---------------------------------------------------------------------------


class TestProvidersUseRequireSdk:
    """Verify all 5 providers delegate to _require_sdk via _build_inner."""

    def test_anthropic_uses_require_sdk(self) -> None:
        with patch.dict(sys.modules, {"anthropic": None}):
            provider = AnthropicProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_openai_uses_require_sdk(self) -> None:
        with patch.dict(sys.modules, {"openai": None}):
            provider = OpenAIProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_google_uses_require_sdk(self) -> None:
        with patch.dict(sys.modules, {"google": None, "google.genai": None}):
            provider = GoogleProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_litellm_uses_require_sdk(self) -> None:
        with patch.dict(sys.modules, {"litellm": None}):
            provider = LiteLLMProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_ollama_uses_require_sdk(self) -> None:
        with patch.dict(sys.modules, {"openai": None}):
            provider = OllamaProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_anthropic_error_includes_hint(self) -> None:
        with patch.dict(sys.modules, {"anthropic": None}):
            provider = AnthropicProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="uv add anthropic"):
                _ = provider.inner

    def test_openai_error_includes_hint(self) -> None:
        with patch.dict(sys.modules, {"openai": None}):
            provider = OpenAIProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="uv add openai"):
                _ = provider.inner

    def test_google_error_includes_hint(self) -> None:
        with patch.dict(sys.modules, {"google": None, "google.genai": None}):
            provider = GoogleProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="uv add google-genai"):
                _ = provider.inner

    def test_litellm_error_includes_hint(self) -> None:
        with patch.dict(sys.modules, {"litellm": None}):
            provider = LiteLLMProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="uv add litellm"):
                _ = provider.inner


# ---------------------------------------------------------------------------
# PROVIDER_API_KEY_ENV constant
# ---------------------------------------------------------------------------


class TestProviderApiKeyEnv:
    """Tests for the shared PROVIDER_API_KEY_ENV mapping."""

    def test_has_all_four_providers(self) -> None:
        assert _PROVIDER_OPENAI in PROVIDER_API_KEY_ENV
        assert _PROVIDER_ANTHROPIC in PROVIDER_API_KEY_ENV
        assert _PROVIDER_GOOGLE in PROVIDER_API_KEY_ENV
        assert _PROVIDER_OLLAMA in PROVIDER_API_KEY_ENV

    def test_maps_openai_to_correct_env(self) -> None:
        assert PROVIDER_API_KEY_ENV[_PROVIDER_OPENAI] == "OPENAI_API_KEY"

    def test_maps_anthropic_to_correct_env(self) -> None:
        assert PROVIDER_API_KEY_ENV[_PROVIDER_ANTHROPIC] == "ANTHROPIC_API_KEY"

    def test_maps_google_to_correct_env(self) -> None:
        assert PROVIDER_API_KEY_ENV[_PROVIDER_GOOGLE] == "GOOGLE_API_KEY"

    def test_maps_ollama_to_correct_env(self) -> None:
        assert PROVIDER_API_KEY_ENV[_PROVIDER_OLLAMA] == "OLLAMA_HOST"

    def test_values_are_strings(self) -> None:
        for key, value in PROVIDER_API_KEY_ENV.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_opencode_reexport_is_same_object(self) -> None:
        """_PROVIDER_ENV_MAP in opencode.py is the same dict."""
        assert _PROVIDER_ENV_MAP is PROVIDER_API_KEY_ENV
