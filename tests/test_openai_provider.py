"""Tests for OpenAI provider _build_inner() and _complete_impl()."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.openai import OpenAIProvider

# ---------------------------------------------------------------------------
# OpenAIProvider._build_inner
# ---------------------------------------------------------------------------


class TestOpenAIBuildInner:
    def test_raises_runtime_error_when_openai_missing(self) -> None:
        with patch.dict(sys.modules, {"openai": None}):
            provider = OpenAIProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_creates_client_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")

        fake_openai_cls = MagicMock()
        fake_module = ModuleType("openai")
        fake_module.OpenAI = fake_openai_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"openai": fake_module}):
            provider = OpenAIProvider()
            provider._inner = None
            _ = provider.inner

        fake_openai_cls.assert_called_once_with(api_key="sk-test-key-123")

    def test_creates_client_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_openai_cls = MagicMock()
        fake_module = ModuleType("openai")
        fake_module.OpenAI = fake_openai_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"openai": fake_module}):
            provider = OpenAIProvider()
            provider._inner = None
            _ = provider.inner

        fake_openai_cls.assert_called_once_with()


# ---------------------------------------------------------------------------
# OpenAIProvider._complete_impl
# ---------------------------------------------------------------------------


class TestOpenAICompleteImpl:
    def test_delegates_to_responses_create(self) -> None:
        provider = OpenAIProvider()
        mock_inner = MagicMock()
        mock_inner.responses.create.return_value = "response"

        messages = [{"role": "user", "content": "hello"}]
        result = provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gpt-5.2",
        )

        mock_inner.responses.create.assert_called_once_with(
            model="gpt-5.2",
            input=messages,
        )
        assert result == "response"

    def test_passes_extra_kwargs(self) -> None:
        provider = OpenAIProvider()
        mock_inner = MagicMock()
        mock_inner.responses.create.return_value = "response"

        messages = [{"role": "user", "content": "hi"}]
        provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gpt-5.2",
            temperature=0.5,
        )

        mock_inner.responses.create.assert_called_once_with(
            model="gpt-5.2",
            input=messages,
            temperature=0.5,
        )
