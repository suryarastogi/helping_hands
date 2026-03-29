"""Tests for Anthropic provider _build_inner() and _complete_impl().

Protects the following behavioral invariants of `AnthropicProvider`:
- `_build_inner` raises a descriptive `RuntimeError` (not `ImportError`) when the
  `anthropic` SDK is absent, giving users an actionable install hint.
- When `ANTHROPIC_API_KEY` is set, the SDK client is constructed with that key;
  when absent, it is constructed without arguments so the SDK can apply its own
  fallback (e.g. env var re-lookup or interactive prompt).
- `_complete_impl` always forwards `max_tokens` to `inner.messages.create`
  (Anthropic requires it; omitting it raises an API error), defaulting to 1024
  but respecting any caller-supplied override.
- Extra kwargs such as `temperature` and `top_p` are passed through transparently.
- The module-level `ANTHROPIC_PROVIDER` singleton is stable across imports so
  lazy init state is not lost.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.anthropic import AnthropicProvider

# ---------------------------------------------------------------------------
# AnthropicProvider class attributes
# ---------------------------------------------------------------------------


class TestAnthropicProviderAttributes:
    def test_name(self) -> None:
        assert AnthropicProvider.name == "anthropic"

    def test_api_key_env_var(self) -> None:
        assert AnthropicProvider.api_key_env_var == "ANTHROPIC_API_KEY"

    def test_default_model(self) -> None:
        assert AnthropicProvider.default_model == "claude-3-5-sonnet-latest"

    def test_install_hint(self) -> None:
        assert "anthropic" in AnthropicProvider.install_hint


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
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")

        fake_anthropic_cls = MagicMock()
        fake_module = ModuleType("anthropic")
        fake_module.Anthropic = fake_anthropic_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider()
            provider._inner = None
            _ = provider.inner

        fake_anthropic_cls.assert_called_once_with(api_key="sk-ant-test-123")

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


# ---------------------------------------------------------------------------
# AnthropicProvider._complete_impl
# ---------------------------------------------------------------------------


class TestAnthropicCompleteImpl:
    def test_delegates_to_messages_create(self) -> None:
        provider = AnthropicProvider()
        mock_inner = MagicMock()
        mock_inner.messages.create.return_value = "response"

        messages = [{"role": "user", "content": "hello"}]
        result = provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="claude-3-5-sonnet-latest",
        )

        mock_inner.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-latest",
            max_tokens=1024,
            messages=messages,
        )
        assert result == "response"

    def test_uses_default_max_tokens_when_not_provided(self) -> None:
        provider = AnthropicProvider()
        mock_inner = MagicMock()
        mock_inner.messages.create.return_value = "response"

        messages = [{"role": "user", "content": "hi"}]
        provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="claude-3-5-sonnet-latest",
        )

        call_kwargs = mock_inner.messages.create.call_args
        assert (
            call_kwargs.kwargs.get("max_tokens", call_kwargs[1].get("max_tokens"))
            == 1024
        )

    def test_uses_custom_max_tokens_when_provided(self) -> None:
        provider = AnthropicProvider()
        mock_inner = MagicMock()
        mock_inner.messages.create.return_value = "response"

        messages = [{"role": "user", "content": "hi"}]
        provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="claude-3-5-sonnet-latest",
            max_tokens=4096,
        )

        mock_inner.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-latest",
            max_tokens=4096,
            messages=messages,
        )

    def test_passes_extra_kwargs(self) -> None:
        provider = AnthropicProvider()
        mock_inner = MagicMock()
        mock_inner.messages.create.return_value = "response"

        messages = [{"role": "user", "content": "hi"}]
        provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="claude-3-5-sonnet-latest",
            temperature=0.7,
        )

        mock_inner.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-latest",
            max_tokens=1024,
            messages=messages,
            temperature=0.7,
        )


# ---------------------------------------------------------------------------
# ANTHROPIC_PROVIDER singleton
# ---------------------------------------------------------------------------


class TestAnthropicProviderSingleton:
    def test_singleton_is_anthropic_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import ANTHROPIC_PROVIDER

        assert isinstance(ANTHROPIC_PROVIDER, AnthropicProvider)

    def test_singleton_identity_across_imports(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import (
            ANTHROPIC_PROVIDER as FIRST,
            ANTHROPIC_PROVIDER as SECOND,
        )

        assert FIRST is SECOND
