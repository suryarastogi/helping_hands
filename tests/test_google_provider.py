"""Tests for Google provider _complete_impl()."""

from __future__ import annotations

from unittest.mock import MagicMock

from helping_hands.lib.ai_providers.google import GoogleProvider


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
