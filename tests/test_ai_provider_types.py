"""Tests for helping_hands.lib.ai_providers.types: normalize_messages and AIProvider.

Protects the core provider abstraction contract:
- ``normalize_messages`` must turn plain strings into ``[{role, content}]``,
  pass through valid sequences, and reject non-Mapping / non-str content.
- ``AIProvider.inner`` must lazily build and cache the SDK client.
- ``_require_sdk`` must raise ``RuntimeError`` with install hint on ImportError.
- ``complete()`` must validate model and non-empty content before dispatching.
- ``acomplete()`` must delegate to ``complete`` via ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any
from unittest.mock import MagicMock

import pytest

from helping_hands.lib.ai_providers.types import (
    AIProvider,
    normalize_messages,
)

# ---------------------------------------------------------------------------
# normalize_messages
# ---------------------------------------------------------------------------


class TestNormalizeMessages:
    """Tests for the normalize_messages helper."""

    def test_string_input_wraps_as_user_message(self) -> None:
        result = normalize_messages("hello")
        assert result == [{"role": "user", "content": "hello"}]

    def test_empty_string_wraps_as_user_message(self) -> None:
        result = normalize_messages("")
        assert result == [{"role": "user", "content": ""}]

    def test_sequence_of_dicts_passes_through(self) -> None:
        msgs = [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hi"},
        ]
        result = normalize_messages(msgs)
        assert result == msgs

    def test_sequence_of_ordered_dicts(self) -> None:
        msgs = [OrderedDict(role="user", content="hi")]
        result = normalize_messages(msgs)
        assert result == [{"role": "user", "content": "hi"}]

    def test_missing_role_defaults_to_user(self) -> None:
        result = normalize_messages([{"content": "hi"}])
        assert result[0]["role"] == "user"

    def test_missing_content_defaults_to_empty(self) -> None:
        result = normalize_messages([{"role": "assistant"}])
        assert result[0]["content"] == ""

    def test_none_content_normalized_to_empty(self) -> None:
        result = normalize_messages([{"role": "user", "content": None}])
        assert result[0]["content"] == ""

    def test_non_mapping_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match=r"Expected a Mapping.*index 0"):
            normalize_messages(["not a dict"])

    def test_non_mapping_at_later_index(self) -> None:
        with pytest.raises(TypeError, match="index 1"):
            normalize_messages([{"role": "user", "content": "ok"}, 42])

    def test_non_string_content_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match=r"Expected str or None.*index 0"):
            normalize_messages([{"role": "user", "content": 123}])

    def test_empty_sequence_returns_empty_list(self) -> None:
        assert normalize_messages([]) == []


# ---------------------------------------------------------------------------
# Concrete AIProvider subclass for testing
# ---------------------------------------------------------------------------


class _StubProvider(AIProvider):
    """Minimal concrete AIProvider for testing the base class."""

    name = "stub"
    api_key_env_var = "STUB_API_KEY"
    default_model = "stub-v1"

    def __init__(self, *, inner: Any | None = None, build_result: Any = None) -> None:
        super().__init__(inner=inner)
        self._build_result = build_result or MagicMock()

    @property
    def install_hint(self) -> str:
        return "pip install stub-sdk"

    def _build_inner(self) -> Any:
        return self._build_result

    def _complete_impl(
        self, *, inner: Any, messages: list[dict[str, str]], model: str, **kwargs: Any
    ) -> str:
        return f"response from {model}"


# ---------------------------------------------------------------------------
# AIProvider.inner lazy loading
# ---------------------------------------------------------------------------


class TestAIProviderInner:
    """Tests for the lazy inner property."""

    def test_inner_uses_injected_value(self) -> None:
        sentinel = object()
        provider = _StubProvider(inner=sentinel)
        assert provider.inner is sentinel

    def test_inner_builds_on_first_access(self) -> None:
        build_result = MagicMock()
        provider = _StubProvider(build_result=build_result)
        assert provider.inner is build_result

    def test_inner_caches_result(self) -> None:
        provider = _StubProvider()
        first = provider.inner
        second = provider.inner
        assert first is second


# ---------------------------------------------------------------------------
# _require_sdk
# ---------------------------------------------------------------------------


class TestRequireSdk:
    """Tests for the _require_sdk import helper."""

    def test_successful_import(self) -> None:
        provider = _StubProvider()
        mod = provider._require_sdk("json")
        import json

        assert mod is json

    def test_missing_module_raises_runtime_error(self) -> None:
        provider = _StubProvider()
        with pytest.raises(RuntimeError, match="pip install stub-sdk"):
            provider._require_sdk("nonexistent_module_xyz_1234")


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------


class TestComplete:
    """Tests for AIProvider.complete validation and dispatch."""

    def test_complete_with_string_prompt(self) -> None:
        provider = _StubProvider()
        result = provider.complete("hello")
        assert result == "response from stub-v1"

    def test_complete_with_explicit_model(self) -> None:
        provider = _StubProvider()
        result = provider.complete("hello", model="custom-model")
        assert result == "response from custom-model"

    def test_complete_no_model_no_default_raises(self) -> None:
        provider = _StubProvider()
        provider.default_model = ""
        with pytest.raises(ValueError, match="No model specified"):
            provider.complete("hello")

    def test_complete_whitespace_model_raises(self) -> None:
        provider = _StubProvider()
        with pytest.raises(ValueError, match="No model specified"):
            provider.complete("hello", model="   ")

    def test_complete_empty_content_raises(self) -> None:
        provider = _StubProvider()
        with pytest.raises(ValueError, match="empty content"):
            provider.complete([{"role": "user", "content": ""}])

    def test_complete_all_none_content_raises(self) -> None:
        provider = _StubProvider()
        with pytest.raises(ValueError, match="empty content"):
            provider.complete([{"role": "user", "content": None}])


# ---------------------------------------------------------------------------
# acomplete()
# ---------------------------------------------------------------------------


class TestAcomplete:
    """Tests for the async completion wrapper."""

    def test_acomplete_delegates_to_complete(self) -> None:
        provider = _StubProvider()
        result = asyncio.run(provider.acomplete("hello"))
        assert result == "response from stub-v1"

    def test_acomplete_passes_model_kwarg(self) -> None:
        provider = _StubProvider()
        result = asyncio.run(provider.acomplete("hello", model="custom"))
        assert result == "response from custom"


# ---------------------------------------------------------------------------
# Docstrings
# ---------------------------------------------------------------------------


class TestDocstrings:
    """Verify public API has docstrings."""

    def test_normalize_messages_has_docstring(self) -> None:
        assert normalize_messages.__doc__ is not None

    def test_ai_provider_has_docstring(self) -> None:
        assert AIProvider.__doc__ is not None

    def test_complete_has_docstring(self) -> None:
        assert AIProvider.complete.__doc__ is not None

    def test_acomplete_has_docstring(self) -> None:
        assert AIProvider.acomplete.__doc__ is not None

    def test_require_sdk_has_docstring(self) -> None:
        assert AIProvider._require_sdk.__doc__ is not None
