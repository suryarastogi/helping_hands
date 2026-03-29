"""Tests for Google provider _build_inner() and _complete_impl().

Protects the following behavioral invariants of `GoogleProvider`:
- `_build_inner` raises a descriptive `RuntimeError` when `google-genai` is absent,
  with an install hint; both `google` and `google.genai` must be patched because
  the SDK uses a nested namespace package.
- API key injection mirrors the Anthropic pattern: present key → `Client(api_key=…)`,
  absent key → `Client()` so the SDK can apply its own lookup.
- `_complete_impl` maps messages to a flat list of content strings (Google's API
  does not accept role-keyed dicts), and silently drops entries with empty content
  to prevent API rejections; a regression would either pass role dicts the SDK
  cannot parse or send empty strings that trigger 400 errors.
- When ALL messages have empty content the base class raises `ValueError` before
  the provider-level call, ensuring we never fire an empty request.
- Extra kwargs are forwarded to `generate_content` unchanged.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.google import GoogleProvider

# ---------------------------------------------------------------------------
# GoogleProvider class attributes
# ---------------------------------------------------------------------------


class TestGoogleProviderAttributes:
    def test_name(self) -> None:
        assert GoogleProvider.name == "google"

    def test_api_key_env_var(self) -> None:
        assert GoogleProvider.api_key_env_var == "GOOGLE_API_KEY"

    def test_default_model(self) -> None:
        assert GoogleProvider.default_model == "gemini-2.0-flash"

    def test_install_hint(self) -> None:
        assert "google-genai" in GoogleProvider.install_hint


# ---------------------------------------------------------------------------
# GoogleProvider._build_inner
# ---------------------------------------------------------------------------


class TestGoogleBuildInner:
    def test_raises_runtime_error_when_google_genai_missing(self) -> None:
        with patch.dict(sys.modules, {"google": None, "google.genai": None}):
            provider = GoogleProvider()
            provider._inner = None
            with pytest.raises(RuntimeError, match="is not installed"):
                _ = provider.inner

    def test_creates_client_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key-123")

        fake_client_cls = MagicMock()
        fake_genai = ModuleType("genai")
        fake_genai.Client = fake_client_cls  # type: ignore[attr-defined]
        fake_google = ModuleType("google")
        fake_google.genai = fake_genai  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules, {"google": fake_google, "google.genai": fake_genai}
        ):
            provider = GoogleProvider()
            provider._inner = None
            _ = provider.inner

        fake_client_cls.assert_called_once_with(api_key="test-google-key-123")

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
            sys.modules, {"google": fake_google, "google.genai": fake_genai}
        ):
            provider = GoogleProvider()
            provider._inner = None
            _ = provider.inner

        fake_client_cls.assert_called_once_with()


# ---------------------------------------------------------------------------
# GoogleProvider._complete_impl
# ---------------------------------------------------------------------------


class TestGoogleCompleteImpl:
    def test_delegates_to_generate_content(self) -> None:
        provider = GoogleProvider()
        mock_inner = MagicMock()
        mock_inner.models.generate_content.return_value = "response"

        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gemini-2.0-flash",
        )

        mock_inner.models.generate_content.assert_called_once_with(
            model="gemini-2.0-flash",
            contents=["hello", "hi"],
        )
        assert result == "response"

    def test_filters_empty_content(self) -> None:
        provider = GoogleProvider()
        mock_inner = MagicMock()
        mock_inner.models.generate_content.return_value = "response"

        messages = [
            {"role": "user", "content": "hello"},
            {"role": "system", "content": ""},
            {"role": "user", "content": "world"},
        ]
        provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gemini-2.0-flash",
        )

        mock_inner.models.generate_content.assert_called_once_with(
            model="gemini-2.0-flash",
            contents=["hello", "world"],
        )

    def test_rejects_all_empty_content_via_complete(self) -> None:
        """Empty content rejection now happens in AIProvider.complete() base class."""
        provider = GoogleProvider(inner=MagicMock())

        with pytest.raises(ValueError, match="empty content"):
            provider.complete(
                [
                    {"role": "user", "content": ""},
                    {"role": "assistant", "content": ""},
                ]
            )

    def test_rejects_single_empty_message_via_complete(self) -> None:
        """Single empty message rejection happens in AIProvider.complete() base class."""
        provider = GoogleProvider(inner=MagicMock())

        with pytest.raises(ValueError, match="empty content"):
            provider.complete([{"role": "user", "content": ""}])

    def test_passes_extra_kwargs(self) -> None:
        provider = GoogleProvider()
        mock_inner = MagicMock()
        mock_inner.models.generate_content.return_value = "response"

        messages = [{"role": "user", "content": "hi"}]
        provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gemini-2.0-flash",
            temperature=0.7,
        )

        mock_inner.models.generate_content.assert_called_once_with(
            model="gemini-2.0-flash",
            contents=["hi"],
            temperature=0.7,
        )


# ---------------------------------------------------------------------------
# GOOGLE_PROVIDER singleton
# ---------------------------------------------------------------------------


class TestGoogleProviderSingleton:
    def test_singleton_is_google_provider_instance(self) -> None:
        from helping_hands.lib.ai_providers.google import GOOGLE_PROVIDER

        assert isinstance(GOOGLE_PROVIDER, GoogleProvider)

    def test_singleton_identity_across_imports(self) -> None:
        from helping_hands.lib.ai_providers.google import (
            GOOGLE_PROVIDER as FIRST,
            GOOGLE_PROVIDER as SECOND,
        )

        assert FIRST is SECOND
