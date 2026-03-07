"""Tests for helping_hands.lib.ai_providers package-level re-exports."""

from __future__ import annotations

import helping_hands.lib.ai_providers as pkg
from helping_hands.lib.ai_providers import (
    ANTHROPIC_PROVIDER,
    GOOGLE_PROVIDER,
    LITELLM_PROVIDER,
    OLLAMA_PROVIDER,
    OPENAI_PROVIDER,
    PROVIDERS,
    AIProvider,
    AnthropicProvider,
    GoogleProvider,
    LiteLLMProvider,
    OllamaProvider,
    OpenAIProvider,
    __all__,
)


class TestProvidersDict:
    """Verify PROVIDERS dict is complete and correct."""

    def test_providers_has_all_five_backends(self) -> None:
        assert set(PROVIDERS) == {"openai", "anthropic", "google", "litellm", "ollama"}

    def test_providers_values_are_ai_provider_instances(self) -> None:
        for name, provider in PROVIDERS.items():
            assert isinstance(provider, AIProvider), f"{name} not an AIProvider"

    def test_providers_name_matches_key(self) -> None:
        for key, provider in PROVIDERS.items():
            assert provider.name == key

    def test_providers_singletons_match_module_constants(self) -> None:
        assert PROVIDERS["openai"] is OPENAI_PROVIDER
        assert PROVIDERS["anthropic"] is ANTHROPIC_PROVIDER
        assert PROVIDERS["google"] is GOOGLE_PROVIDER
        assert PROVIDERS["litellm"] is LITELLM_PROVIDER
        assert PROVIDERS["ollama"] is OLLAMA_PROVIDER


class TestProviderClassIdentity:
    """Verify re-exported classes match their source modules."""

    def test_openai_identity(self) -> None:
        from helping_hands.lib.ai_providers.openai import (
            OpenAIProvider as Src,
        )

        assert OpenAIProvider is Src

    def test_anthropic_identity(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import (
            AnthropicProvider as Src,
        )

        assert AnthropicProvider is Src

    def test_google_identity(self) -> None:
        from helping_hands.lib.ai_providers.google import (
            GoogleProvider as Src,
        )

        assert GoogleProvider is Src

    def test_litellm_identity(self) -> None:
        from helping_hands.lib.ai_providers.litellm import (
            LiteLLMProvider as Src,
        )

        assert LiteLLMProvider is Src

    def test_ollama_identity(self) -> None:
        from helping_hands.lib.ai_providers.ollama import (
            OllamaProvider as Src,
        )

        assert OllamaProvider is Src

    def test_ai_provider_base_identity(self) -> None:
        from helping_hands.lib.ai_providers.types import (
            AIProvider as SrcBase,
        )

        assert AIProvider is SrcBase


class TestPackageAll:
    """Verify __all__ lists all public symbols."""

    def test_all_contains_expected_symbols(self) -> None:
        expected = {
            "ANTHROPIC_PROVIDER",
            "GOOGLE_PROVIDER",
            "LITELLM_PROVIDER",
            "OLLAMA_PROVIDER",
            "OPENAI_PROVIDER",
            "PROVIDERS",
            "AIProvider",
            "AnthropicProvider",
            "GoogleProvider",
            "LiteLLMProvider",
            "OllamaProvider",
            "OpenAIProvider",
        }
        assert set(__all__) == expected

    def test_all_entries_are_importable(self) -> None:
        for name in __all__:
            assert hasattr(pkg, name), f"{name} listed in __all__ but not importable"


class TestProviderSingletonInstances:
    """Verify singleton constants are correct types."""

    def test_openai_provider_type(self) -> None:
        assert isinstance(OPENAI_PROVIDER, OpenAIProvider)

    def test_anthropic_provider_type(self) -> None:
        assert isinstance(ANTHROPIC_PROVIDER, AnthropicProvider)

    def test_google_provider_type(self) -> None:
        assert isinstance(GOOGLE_PROVIDER, GoogleProvider)

    def test_litellm_provider_type(self) -> None:
        assert isinstance(LITELLM_PROVIDER, LiteLLMProvider)

    def test_ollama_provider_type(self) -> None:
        assert isinstance(OLLAMA_PROVIDER, OllamaProvider)
