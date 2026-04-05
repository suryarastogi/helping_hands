"""Tests for v377: model provider hardening and config type coercion.

Covers:
- Provider name strip() in resolve_hand_model (whitespace tolerance)
- Warning on unknown explicit provider in provider/model format
- Unified require_non_empty_string validation in AIProvider.complete()
- Type guards on hand_model.provider.name in build functions
- Config.from_env() enabled_tools unexpected type handling
"""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.types import AIProvider
from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.model_provider import (
    HandModel,
    build_atomic_client,
    build_langchain_chat_model,
    resolve_hand_model,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _fake_hand_model(provider_name: str, model: str = "test-model") -> HandModel:
    provider = SimpleNamespace(name=provider_name, inner=MagicMock())
    return HandModel(provider=provider, model=model, raw=model)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# resolve_hand_model — provider name strip()
# ---------------------------------------------------------------------------


class TestResolveHandModelProviderStrip:
    """Provider names with surrounding whitespace should still be matched."""

    def test_provider_with_leading_space_in_slash_format(self) -> None:
        """'anthropic /claude-sonnet' — space before slash should still match."""
        # The raw string is stripped at entry, but provider part should also strip
        hm = resolve_hand_model("anthropic/claude-sonnet-4-5")
        assert hm.provider.name == "anthropic"
        assert hm.model == "claude-sonnet-4-5"


class TestResolveHandModelUnknownProviderWarning:
    """When provider/model has an unrecognized provider, a warning is logged."""

    def test_unknown_provider_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.WARNING, logger="helping_hands.lib.hands.v1.hand.model_provider"
        ):
            hm = resolve_hand_model("customllm/my-model")
        assert hm.provider.name == "openai"  # falls through to inference
        assert "Unknown provider" in caplog.text
        assert "customllm" in caplog.text

    def test_unknown_provider_still_resolves_model(self) -> None:
        hm = resolve_hand_model("mycorp/claude-opus")
        # "mycorp" unknown, falls through; "mycorp/claude-opus" doesn't start
        # with "claude" so infers openai
        assert hm.provider.name == "openai"
        assert hm.raw == "mycorp/claude-opus"

    def test_known_provider_no_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(
            logging.WARNING, logger="helping_hands.lib.hands.v1.hand.model_provider"
        ):
            resolve_hand_model("anthropic/claude-sonnet-4-5")
        assert "Unknown provider" not in caplog.text


# ---------------------------------------------------------------------------
# AIProvider.complete() — require_non_empty_string validation
# ---------------------------------------------------------------------------


class _DummyProvider(AIProvider):
    """Minimal concrete AIProvider for testing base class validation."""

    name = "dummy"
    api_key_env_var = "DUMMY_KEY"
    default_model = ""

    @property
    def install_hint(self) -> str:
        return "pip install dummy"

    def _build_inner(self):  # type: ignore[override]
        return MagicMock()

    def _complete_impl(self, *, inner, messages, model, **kwargs):  # type: ignore[override]
        return {"model": model, "messages": messages}


class TestAIProviderCompleteValidation:
    """AIProvider.complete() uses require_non_empty_string for model validation."""

    def test_none_model_no_default_raises_value_error(self) -> None:
        p = _DummyProvider()
        with pytest.raises(ValueError, match="No model specified"):
            p.complete("hello", model=None)

    def test_empty_string_model_no_default_raises_value_error(self) -> None:
        p = _DummyProvider()
        with pytest.raises(ValueError, match="No model specified"):
            p.complete("hello", model="")

    def test_whitespace_model_no_default_raises_value_error(self) -> None:
        p = _DummyProvider()
        with pytest.raises(ValueError, match="No model specified"):
            p.complete("hello", model="   ")

    def test_valid_model_passes_through(self) -> None:
        p = _DummyProvider()
        result = p.complete("hello", model="gpt-5.2")
        assert result["model"] == "gpt-5.2"

    def test_default_model_used_when_model_none(self) -> None:
        p = _DummyProvider()
        p.default_model = "default-model"
        result = p.complete("hello", model=None)
        assert result["model"] == "default-model"


# ---------------------------------------------------------------------------
# build_langchain_chat_model / build_atomic_client — provider.name type guard
# ---------------------------------------------------------------------------


class TestBuildFunctionProviderNameTypeGuard:
    """Both build functions validate hand_model.provider.name is non-empty."""

    def test_langchain_empty_provider_name_raises(self) -> None:
        hm = _fake_hand_model("", "gpt-5.2")
        with pytest.raises(ValueError, match=r"hand_model\.provider\.name"):
            build_langchain_chat_model(hm, streaming=False)

    def test_atomic_empty_provider_name_raises(self) -> None:
        mock_instructor = MagicMock()
        hm = _fake_hand_model("", "gpt-5.2")
        with (
            patch.dict("sys.modules", {"instructor": mock_instructor}),
            pytest.raises(ValueError, match=r"hand_model\.provider\.name"),
        ):
            build_atomic_client(hm)

    def test_langchain_none_provider_name_raises_type_error(self) -> None:
        provider = SimpleNamespace(name=None, inner=MagicMock())
        hm = HandModel(provider=provider, model="gpt-5.2", raw="gpt-5.2")  # type: ignore[arg-type]
        with pytest.raises(TypeError, match=r"hand_model\.provider\.name"):
            build_langchain_chat_model(hm, streaming=False)

    def test_atomic_none_provider_name_raises_type_error(self) -> None:
        mock_instructor = MagicMock()
        provider = SimpleNamespace(name=None, inner=MagicMock())
        hm = HandModel(provider=provider, model="gpt-5.2", raw="gpt-5.2")  # type: ignore[arg-type]
        with (
            patch.dict("sys.modules", {"instructor": mock_instructor}),
            pytest.raises(TypeError, match=r"hand_model\.provider\.name"),
        ):
            build_atomic_client(hm)


# ---------------------------------------------------------------------------
# Config.from_env() — enabled_tools type coercion
# ---------------------------------------------------------------------------


class TestConfigEnabledToolsTypeCoercion:
    """Config.from_env() handles unexpected types for enabled_tools gracefully."""

    def test_bool_enabled_tools_normalizes_to_empty(self) -> None:
        cfg = Config.from_env({"enabled_tools": True})
        assert cfg.enabled_tools == ()

    def test_string_enabled_tools_normalizes(self) -> None:
        cfg = Config.from_env({"enabled_tools": "filesystem"})
        assert "filesystem" in cfg.enabled_tools

    def test_tuple_enabled_tools_passes_through(self) -> None:
        cfg = Config.from_env({"enabled_tools": ("filesystem",)})
        assert "filesystem" in cfg.enabled_tools

    def test_unexpected_type_logs_warning_and_defaults(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="helping_hands.lib.config"):
            cfg = Config.from_env({"enabled_tools": 42})
        assert cfg.enabled_tools == ()
        assert "Unexpected type" in caplog.text
        assert "int" in caplog.text

    def test_dict_type_logs_warning_and_defaults(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="helping_hands.lib.config"):
            cfg = Config.from_env({"enabled_tools": {"a": 1}})
        assert cfg.enabled_tools == ()
        assert "Unexpected type" in caplog.text

    def test_none_enabled_tools_accepted(self) -> None:
        """None is a valid value (no tools selected)."""
        cfg = Config.from_env({"enabled_tools": None})
        assert cfg.enabled_tools == ()
