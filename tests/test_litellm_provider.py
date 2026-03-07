"""Tests for LiteLLM provider _build_inner() and _complete_impl()."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.litellm import LiteLLMProvider

# ---------------------------------------------------------------------------
# LiteLLMProvider class attributes
# ---------------------------------------------------------------------------


class TestLiteLLMProviderAttributes:
    def test_name(self) -> None:
        assert LiteLLMProvider.name == "litellm"

    def test_api_key_env_var(self) -> None:
        assert LiteLLMProvider.api_key_env_var == "LITELLM_API_KEY"

    def test_default_model(self) -> None:
        assert LiteLLMProvider.default_model == "gpt-5.2"

    def test_install_hint(self) -> None:
        assert "litellm" in LiteLLMProvider.install_hint


# ---------------------------------------------------------------------------
# LiteLLMProvider._build_inner
# ---------------------------------------------------------------------------


class TestLiteLLMBuildInner:
    def test_raises_runtime_error_when_litellm_missing(self) -> None:
        with patch.dict(sys.modules, {"litellm": None}):
            provider = LiteLLMProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="LiteLLM is not installed"):
                _ = provider.inner

    def test_returns_litellm_module_with_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LITELLM_API_KEY", "test-key-123")

        fake_module = ModuleType("litellm")
        fake_module.api_key = None  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"litellm": fake_module}):
            provider = LiteLLMProvider()
            provider._inner = None
            result = provider.inner

        assert result is fake_module
        assert fake_module.api_key == "test-key-123"  # type: ignore[attr-defined]

    def test_returns_litellm_module_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)

        fake_module = ModuleType("litellm")
        fake_module.api_key = None  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"litellm": fake_module}):
            provider = LiteLLMProvider()
            provider._inner = None
            result = provider.inner

        assert result is fake_module
        assert fake_module.api_key is None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# LiteLLMProvider._complete_impl
# ---------------------------------------------------------------------------


class TestLiteLLMCompleteImpl:
    def test_delegates_to_completion(self) -> None:
        provider = LiteLLMProvider()
        mock_inner = MagicMock()
        mock_inner.completion.return_value = "response"

        messages = [{"role": "user", "content": "hello"}]
        result = provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gpt-5.2",
        )

        mock_inner.completion.assert_called_once_with(
            model="gpt-5.2",
            messages=messages,
        )
        assert result == "response"

    def test_passes_extra_kwargs(self) -> None:
        provider = LiteLLMProvider()
        mock_inner = MagicMock()
        mock_inner.completion.return_value = "response"

        messages = [{"role": "user", "content": "hi"}]
        provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gpt-5.2",
            temperature=0.7,
            max_tokens=100,
        )

        mock_inner.completion.assert_called_once_with(
            model="gpt-5.2",
            messages=messages,
            temperature=0.7,
            max_tokens=100,
        )


# ---------------------------------------------------------------------------
# LITELLM_PROVIDER singleton
# ---------------------------------------------------------------------------


class TestLiteLLMProviderSingleton:
    def test_singleton_is_litellm_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.litellm import LITELLM_PROVIDER

        assert isinstance(LITELLM_PROVIDER, LiteLLMProvider)

    def test_singleton_identity_across_imports(self) -> None:
        from helping_hands.lib.ai_providers.litellm import LITELLM_PROVIDER as FIRST
        from helping_hands.lib.ai_providers.litellm import LITELLM_PROVIDER as SECOND

        assert FIRST is SECOND
