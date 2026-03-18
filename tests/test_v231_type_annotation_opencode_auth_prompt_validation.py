"""Tests for v231 — type annotation fix, OpenCode auth, CLI prompt validation."""

from __future__ import annotations

import pytest

from helping_hands.lib.hands.v1.hand.cli.opencode import (
    _PROVIDER_ENV_MAP,
    OpenCodeCLIHand,
)

# ---------------------------------------------------------------------------
# _input_schema type annotation (atomic.py / iterative.py)
# ---------------------------------------------------------------------------


class TestInputSchemaTypeAnnotation:
    """Verify _input_schema accepts None without type: ignore."""

    def test_atomic_input_schema_starts_none(self, make_cli_hand) -> None:
        """AtomicHand._input_schema is None before _build_agent assigns it."""
        # We can't instantiate AtomicHand without atomic-agents installed,
        # so verify the annotation allows None by checking the source.
        import inspect

        from helping_hands.lib.hands.v1.hand import atomic

        source = inspect.getsource(atomic.AtomicHand.__init__)
        assert "type: ignore" not in source
        assert "type[Any] | None" in source

    def test_iterative_input_schema_starts_none(self) -> None:
        """BasicAtomicHand._input_schema annotation allows None."""
        import inspect

        from helping_hands.lib.hands.v1.hand import iterative

        source = inspect.getsource(iterative.BasicAtomicHand.__init__)
        assert "type: ignore" not in source
        assert "type[Any] | None" in source


# ---------------------------------------------------------------------------
# _PROVIDER_ENV_MAP constant
# ---------------------------------------------------------------------------


class TestProviderEnvMap:
    """_PROVIDER_ENV_MAP maps provider names to env var names."""

    def test_has_expected_providers(self) -> None:
        assert "openai" in _PROVIDER_ENV_MAP
        assert "anthropic" in _PROVIDER_ENV_MAP
        assert "google" in _PROVIDER_ENV_MAP
        assert "ollama" in _PROVIDER_ENV_MAP

    def test_values_are_strings(self) -> None:
        for key, value in _PROVIDER_ENV_MAP.items():
            assert isinstance(key, str), f"key {key!r} is not a string"
            assert isinstance(value, str), f"value {value!r} is not a string"


# ---------------------------------------------------------------------------
# OpenCodeCLIHand._describe_auth
# ---------------------------------------------------------------------------


@pytest.fixture()
def opencode_hand(make_cli_hand):
    return make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-5")


class TestOpenCodeDescribeAuth:
    """_describe_auth reports provider and API key status."""

    def test_anthropic_provider_key_set(self, opencode_hand, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        result = opencode_hand._describe_auth()
        assert result == "auth=provider=anthropic (ANTHROPIC_API_KEY set)"

    def test_anthropic_provider_key_not_set(self, opencode_hand, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = opencode_hand._describe_auth()
        assert result == "auth=provider=anthropic (ANTHROPIC_API_KEY not set)"

    def test_anthropic_provider_key_whitespace(
        self, opencode_hand, monkeypatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        result = opencode_hand._describe_auth()
        assert result == "auth=provider=anthropic (ANTHROPIC_API_KEY not set)"

    def test_openai_provider(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="openai/gpt-5.2")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        result = hand._describe_auth()
        assert result == "auth=provider=openai (OPENAI_API_KEY set)"

    def test_google_provider(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="google/gemini-2.5-pro")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        result = hand._describe_auth()
        assert result == "auth=provider=google (GOOGLE_API_KEY not set)"

    def test_unknown_provider_no_env_var(self, make_cli_hand) -> None:
        """Unknown provider returns provider name without env check."""
        hand = make_cli_hand(OpenCodeCLIHand, model="xai/grok-3")
        result = hand._describe_auth()
        assert result == "auth=provider=xai"

    def test_no_provider_slash_returns_empty(self, make_cli_hand) -> None:
        """Model without provider/ prefix returns empty string."""
        hand = make_cli_hand(OpenCodeCLIHand, model="claude-sonnet-4-5")
        result = hand._describe_auth()
        assert result == ""

    def test_empty_model_returns_empty(self, make_cli_hand) -> None:
        """Empty model returns empty string."""
        hand = make_cli_hand(OpenCodeCLIHand, model="")
        result = hand._describe_auth()
        assert result == ""

    def test_default_model_returns_empty(self, make_cli_hand) -> None:
        """'default' model returns empty string."""
        hand = make_cli_hand(OpenCodeCLIHand, model="default")
        result = hand._describe_auth()
        assert result == ""


# ---------------------------------------------------------------------------
# _TwoPhaseCLIHand.run() / stream() prompt validation
# ---------------------------------------------------------------------------


class TestCLIHandPromptValidation:
    """run() and stream() reject empty/whitespace prompts."""

    def test_run_empty_prompt_raises(self, make_cli_hand) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-5")
        with pytest.raises((ValueError, TypeError)):
            hand.run("")

    def test_run_whitespace_prompt_raises(self, make_cli_hand) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-5")
        with pytest.raises((ValueError, TypeError)):
            hand.run("   ")

    def test_run_non_string_prompt_raises(self, make_cli_hand) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-5")
        with pytest.raises((ValueError, TypeError)):
            hand.run(123)  # type: ignore[arg-type]

    def test_stream_empty_prompt_raises(self, make_cli_hand) -> None:
        import asyncio

        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-5")
        with pytest.raises((ValueError, TypeError)):
            asyncio.run(hand.stream("").__anext__())

    def test_stream_whitespace_prompt_raises(self, make_cli_hand) -> None:
        import asyncio

        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-5")
        with pytest.raises((ValueError, TypeError)):
            asyncio.run(hand.stream("  \t  ").__anext__())
