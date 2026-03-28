"""Tests for v217 provider consistency fixes across AI backends.

Protects three independent behavioural invariants: (1) the Google LangChain
provider must forward the `streaming` kwarg to ChatGoogleGenerativeAI so
callers receive tokens incrementally rather than a single blocked response;
(2) the Google provider must raise ValueError before calling the API when all
message contents are empty, preventing a confusing remote error; (3) the
Claude CLI hand must log a warning and filter out OpenAI-namespaced models
(openai/…) rather than passing them verbatim to the Claude binary, which would
fail silently or produce a misleading error.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand
from helping_hands.lib.hands.v1.hand.model_provider import build_langchain_chat_model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_hand_model(provider_name: str, model: str = "test-model"):
    provider = MagicMock()
    provider.name = provider_name
    return SimpleNamespace(provider=provider, model=model, raw=model)


# ---------------------------------------------------------------------------
# Google LangChain streaming parameter
# ---------------------------------------------------------------------------


class TestGoogleLangchainStreaming:
    """Verify ChatGoogleGenerativeAI receives streaming kwarg."""

    def test_streaming_true_passed_to_google(self) -> None:
        mock_cls = MagicMock()
        hm = _fake_hand_model("google", "gemini-2.0-flash")
        with patch.dict(
            "sys.modules",
            {
                "langchain_google_genai": SimpleNamespace(
                    ChatGoogleGenerativeAI=mock_cls
                )
            },
        ):
            build_langchain_chat_model(hm, streaming=True)
        mock_cls.assert_called_once_with(model="gemini-2.0-flash", streaming=True)

    def test_streaming_false_passed_to_google(self) -> None:
        mock_cls = MagicMock()
        hm = _fake_hand_model("google", "gemini-2.0-flash")
        with patch.dict(
            "sys.modules",
            {
                "langchain_google_genai": SimpleNamespace(
                    ChatGoogleGenerativeAI=mock_cls
                )
            },
        ):
            build_langchain_chat_model(hm, streaming=False)
        mock_cls.assert_called_once_with(model="gemini-2.0-flash", streaming=False)


# ---------------------------------------------------------------------------
# Google provider empty-contents validation
# ---------------------------------------------------------------------------


class TestGoogleEmptyContentsValidation:
    """Verify clear error when all messages have empty content."""

    def test_all_empty_content_raises_value_error(self) -> None:
        provider = GoogleProvider()
        provider._inner = MagicMock()
        messages = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": ""},
        ]
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider._complete_impl(
                inner=provider._inner,
                messages=messages,
                model="gemini-2.0-flash",
            )

    def test_all_none_content_raises_value_error(self) -> None:
        provider = GoogleProvider()
        provider._inner = MagicMock()
        messages: list[dict[str, str]] = [
            {"role": "user"},
            {"role": "assistant"},
        ]
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider._complete_impl(
                inner=provider._inner,
                messages=messages,
                model="gemini-2.0-flash",
            )

    def test_mixed_empty_and_nonempty_succeeds(self) -> None:
        provider = GoogleProvider()
        mock_inner = MagicMock()
        mock_inner.models.generate_content.return_value = "ok"
        messages = [
            {"role": "user", "content": ""},
            {"role": "user", "content": "hello"},
        ]
        result = provider._complete_impl(
            inner=mock_inner,
            messages=messages,
            model="gemini-2.0-flash",
        )
        assert result == "ok"
        mock_inner.models.generate_content.assert_called_once_with(
            model="gemini-2.0-flash",
            contents=["hello"],
        )

    def test_empty_messages_list_raises_value_error(self) -> None:
        provider = GoogleProvider()
        provider._inner = MagicMock()
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider._complete_impl(
                inner=provider._inner,
                messages=[],
                model="gemini-2.0-flash",
            )


# ---------------------------------------------------------------------------
# Claude CLI GPT model filter warning
# ---------------------------------------------------------------------------


class TestClaudeCliGptModelWarning:
    """Verify warning is logged when GPT model is filtered out."""

    def test_gpt_model_logs_warning(
        self, make_cli_hand, caplog: pytest.LogCaptureFixture
    ) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="gpt-5.2")
        with caplog.at_level(logging.WARNING):
            result = hand._resolve_cli_model()
        assert result == ""
        assert "Model" in caplog.text
        assert "gpt-5.2" in caplog.text
        assert "falling back" in caplog.text

    def test_gpt_4o_model_logs_warning(
        self, make_cli_hand, caplog: pytest.LogCaptureFixture
    ) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="gpt-4o")
        with caplog.at_level(logging.WARNING):
            result = hand._resolve_cli_model()
        assert result == ""
        assert "gpt-4o" in caplog.text

    def test_claude_model_no_warning(
        self, make_cli_hand, caplog: pytest.LogCaptureFixture
    ) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
        with caplog.at_level(logging.WARNING):
            result = hand._resolve_cli_model()
        assert result == "claude-sonnet-4-5"
        assert "GPT model" not in caplog.text

    def test_empty_model_no_warning(
        self, make_cli_hand, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Empty model falls back to _DEFAULT_MODEL (non-GPT), no warning."""
        hand = make_cli_hand(ClaudeCodeHand, model="")
        with caplog.at_level(logging.WARNING):
            result = hand._resolve_cli_model()
        # Base class returns _DEFAULT_MODEL for empty input
        assert result == ClaudeCodeHand._DEFAULT_MODEL
        assert "GPT model" not in caplog.text
