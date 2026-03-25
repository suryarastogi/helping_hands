"""Tests for DevinCLIHand static/pure helper methods."""

from __future__ import annotations

import asyncio

import pytest

from helping_hands.lib.hands.v1.hand.cli.devin import DevinCLIHand

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def devin_hand(make_cli_hand):
    return make_cli_hand(DevinCLIHand, model="anthropic/claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# _build_devin_failure_message
# ---------------------------------------------------------------------------


class TestBuildDevinFailureMessage:
    def test_generic_failure(self) -> None:
        msg = DevinCLIHand._build_devin_failure_message(
            return_code=1, output="something broke"
        )
        assert "Devin CLI failed (exit=1)" in msg
        assert "something broke" in msg

    def test_auth_failure_401(self) -> None:
        msg = DevinCLIHand._build_devin_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg

    def test_auth_failure_invalid_key(self) -> None:
        msg = DevinCLIHand._build_devin_failure_message(
            return_code=1, output="invalid api key"
        )
        assert "authentication failed" in msg

    def test_output_truncated(self) -> None:
        long_output = "z" * 5000
        msg = DevinCLIHand._build_devin_failure_message(
            return_code=1, output=long_output
        )
        assert len(msg) < 5000


# ---------------------------------------------------------------------------
# _resolve_cli_model
# ---------------------------------------------------------------------------


class TestResolveCliModel:
    def test_preserves_provider_slash_model(self, devin_hand) -> None:
        result = devin_hand._resolve_cli_model()
        assert result == "anthropic/claude-sonnet-4-6"

    def test_preserves_bare_model(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_default_model_returns_empty(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="default")
        assert hand._resolve_cli_model() == ""

    def test_empty_model_returns_empty(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="")
        assert hand._resolve_cli_model() == ""

    def test_whitespace_model_returns_empty(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="  ")
        assert hand._resolve_cli_model() == ""

    def test_none_model_returns_empty(self, make_cli_hand) -> None:
        """str(None) produces 'None'; should fall back to _DEFAULT_MODEL."""
        hand = make_cli_hand(DevinCLIHand, model=None)
        assert hand._resolve_cli_model() == ""


# ---------------------------------------------------------------------------
# _command_not_found_message
# ---------------------------------------------------------------------------


class TestCommandNotFoundMessage:
    def test_includes_command_name(self, devin_hand) -> None:
        msg = devin_hand._command_not_found_message("devin")
        assert "devin" in msg
        assert "HELPING_HANDS_DEVIN_CLI_CMD" in msg


# ---------------------------------------------------------------------------
# _build_failure_message — delegates to static method
# ---------------------------------------------------------------------------


class TestBuildFailureMessage:
    def test_delegates_to_static(self, devin_hand) -> None:
        msg = devin_hand._build_failure_message(return_code=2, output="some error")
        assert "Devin CLI failed (exit=2)" in msg

    def test_auth_detection_via_instance(self, devin_hand) -> None:
        msg = devin_hand._build_failure_message(
            return_code=1, output="authentication failed"
        )
        assert "authentication failed" in msg


# ---------------------------------------------------------------------------
# _invoke_devin / _invoke_backend — async delegation
# ---------------------------------------------------------------------------


class TestInvokeDevinDelegation:
    def test_invoke_devin_delegates_to_invoke_cli(
        self, devin_hand, monkeypatch
    ) -> None:
        calls: list[str] = []

        async def fake_invoke_cli(prompt, *, emit):
            calls.append(prompt)
            return "cli result"

        monkeypatch.setattr(devin_hand, "_invoke_cli", fake_invoke_cli)

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(devin_hand._invoke_devin("fix it", emit=emit))
        assert result == "cli result"
        assert calls == ["fix it"]

    def test_invoke_backend_delegates_to_invoke_devin(
        self, devin_hand, monkeypatch
    ) -> None:
        calls: list[str] = []

        async def fake_invoke_devin(prompt, *, emit):
            calls.append(prompt)
            return "delegated"

        monkeypatch.setattr(devin_hand, "_invoke_devin", fake_invoke_devin)

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(devin_hand._invoke_backend("hello", emit=emit))
        assert result == "delegated"
        assert calls == ["hello"]
