"""Tests for _build_inner() across LiteLLM, Google, and Anthropic providers.

This file focuses narrowly on the lazy-init path of three providers and
partially overlaps with the dedicated per-provider test files.  It exists as
an integration-style cross-check ensuring that the same SDK-absence, api-key,
and no-api-key behaviors hold consistently across providers when tested together.

# TODO: CLEANUP CANDIDATE
The three test classes here (TestLiteLLMBuildInner, TestGoogleBuildInner,
TestAnthropicBuildInner) duplicate tests that already exist in
test_litellm_provider.py, test_google_provider.py, and
test_anthropic_provider.py with identical assertions.  Consider removing this
file once coverage from those files is confirmed sufficient.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.anthropic import AnthropicProvider
from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.ai_providers.litellm import LiteLLMProvider

# ---------------------------------------------------------------------------
# LiteLLMProvider._build_inner
# ---------------------------------------------------------------------------


class TestLiteLLMBuildInner:
    def test_raises_runtime_error_when_litellm_missing(self) -> None:
        with patch.dict(sys.modules, {"litellm": None}):
            provider = LiteLLMProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_sets_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LITELLM_API_KEY", "test-key-123")

        fake_module = ModuleType("litellm")
        fake_module.api_key = None  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"litellm": fake_module}):
            provider = LiteLLMProvider()
            provider._inner = None
            result = provider.inner

        assert result is fake_module
        assert fake_module.api_key == "test-key-123"  # type: ignore[attr-defined]

    def test_no_api_key_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
# GoogleProvider._build_inner
# ---------------------------------------------------------------------------


class TestGoogleBuildInner:
    def test_raises_runtime_error_when_google_missing(self) -> None:
        with patch.dict(sys.modules, {"google": None, "google.genai": None}):
            provider = GoogleProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_creates_client_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-key-456")

        fake_client_cls = MagicMock()
        fake_genai = ModuleType("genai")
        fake_genai.Client = fake_client_cls  # type: ignore[attr-defined]

        fake_google = ModuleType("google")
        fake_google.genai = fake_genai  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {"google": fake_google, "google.genai": fake_genai},
        ):
            provider = GoogleProvider()
            provider._inner = None
            _ = provider.inner

        fake_client_cls.assert_called_once_with(api_key="goog-key-456")

    def test_creates_client_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        fake_client_cls = MagicMock()
        fake_genai = ModuleType("genai")
        fake_genai.Client = fake_client_cls  # type: ignore[attr-defined]

        fake_google = ModuleType("google")
        fake_google.genai = fake_genai  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {"google": fake_google, "google.genai": fake_genai},
        ):
            provider = GoogleProvider()
            provider._inner = None
            _ = provider.inner

        fake_client_cls.assert_called_once_with()


# ---------------------------------------------------------------------------
# AnthropicProvider._build_inner
# ---------------------------------------------------------------------------


class TestAnthropicBuildInner:
    def test_raises_runtime_error_when_anthropic_missing(self) -> None:
        with patch.dict(sys.modules, {"anthropic": None}):
            provider = AnthropicProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_creates_client_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key-789")

        fake_anthropic_cls = MagicMock()
        fake_module = ModuleType("anthropic")
        fake_module.Anthropic = fake_anthropic_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider()
            provider._inner = None
            _ = provider.inner

        fake_anthropic_cls.assert_called_once_with(api_key="ant-key-789")

    def test_creates_client_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        fake_anthropic_cls = MagicMock()
        fake_module = ModuleType("anthropic")
        fake_module.Anthropic = fake_anthropic_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider()
            provider._inner = None
            _ = provider.inner

        fake_anthropic_cls.assert_called_once_with()
