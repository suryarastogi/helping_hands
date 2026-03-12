"""Tests for OpenCodeCLIHand static/pure helper methods."""

from __future__ import annotations

import asyncio

import pytest

from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def opencode_hand(make_cli_hand):
    return make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# _build_opencode_failure_message
# ---------------------------------------------------------------------------


class TestBuildOpenCodeFailureMessage:
    def test_generic_failure(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="something broke"
        )
        assert "OpenCode CLI failed (exit=1)" in msg
        assert "something broke" in msg

    def test_auth_failure_401(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg

    def test_auth_failure_invalid_key(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="invalid api key"
        )
        assert "authentication failed" in msg

    def test_auth_failure_not_valid(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="API key not valid for this service"
        )
        assert "authentication failed" in msg

    def test_auth_failure_unauthorized(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="Request unauthorized"
        )
        assert "authentication failed" in msg

    def test_output_truncated(self) -> None:
        long_output = "z" * 5000
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output=long_output
        )
        assert len(msg) < 5000


# ---------------------------------------------------------------------------
# _resolve_cli_model
# ---------------------------------------------------------------------------


class TestResolveCliModel:
    def test_preserves_provider_slash_model(self, opencode_hand) -> None:
        result = opencode_hand._resolve_cli_model()
        assert result == "anthropic/claude-sonnet-4-6"

    def test_preserves_bare_model(self, make_cli_hand) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_default_model_returns_empty(self, make_cli_hand) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="default")
        assert hand._resolve_cli_model() == ""

    def test_empty_model_returns_empty(self, make_cli_hand) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="")
        assert hand._resolve_cli_model() == ""

    def test_whitespace_model_returns_empty(self, make_cli_hand) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="  ")
        assert hand._resolve_cli_model() == ""

    def test_none_model_returns_empty(self, make_cli_hand) -> None:
        """str(None) produces 'None'; should fall back to _DEFAULT_MODEL."""
        hand = make_cli_hand(OpenCodeCLIHand, model=None)
        assert hand._resolve_cli_model() == ""


# ---------------------------------------------------------------------------
# _command_not_found_message
# ---------------------------------------------------------------------------


class TestCommandNotFoundMessage:
    def test_includes_command_name(self, opencode_hand) -> None:
        msg = opencode_hand._command_not_found_message("opencode")
        assert "opencode" in msg
        assert "HELPING_HANDS_OPENCODE_CLI_CMD" in msg


# ---------------------------------------------------------------------------
# _build_failure_message — delegates to static method
# ---------------------------------------------------------------------------


class TestBuildFailureMessage:
    def test_delegates_to_static(self, opencode_hand) -> None:
        msg = opencode_hand._build_failure_message(return_code=2, output="some error")
        assert "OpenCode CLI failed (exit=2)" in msg

    def test_auth_detection_via_instance(self, opencode_hand) -> None:
        msg = opencode_hand._build_failure_message(
            return_code=1, output="authentication failed"
        )
        assert "authentication failed" in msg


# ---------------------------------------------------------------------------
# _build_opencode_failure_message — additional auth token variations
# ---------------------------------------------------------------------------


class TestBuildOpenCodeFailureMessageExtraTokens:
    def test_authentication_failed_token(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="Error: authentication failed please retry"
        )
        assert "authentication failed" in msg
        assert "opencode auth login" in msg.lower() or "API key" in msg

    def test_case_insensitive_detection(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="INVALID API KEY provided"
        )
        assert "authentication failed" in msg

    def test_non_auth_error_does_not_match(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output="connection timeout"
        )
        assert "authentication failed" not in msg
        assert "OpenCode CLI failed" in msg

    def test_exit_code_in_generic(self) -> None:
        msg = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=42, output="kaboom"
        )
        assert "exit=42" in msg


# ---------------------------------------------------------------------------
# _invoke_opencode / _invoke_backend — async delegation
# ---------------------------------------------------------------------------


class TestInvokeOpenCodeDelegation:
    def test_invoke_opencode_delegates_to_invoke_cli(
        self, opencode_hand, monkeypatch
    ) -> None:
        calls: list[str] = []

        async def fake_invoke_cli(prompt, *, emit):
            calls.append(prompt)
            return "cli result"

        monkeypatch.setattr(opencode_hand, "_invoke_cli", fake_invoke_cli)

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(opencode_hand._invoke_opencode("fix it", emit=emit))
        assert result == "cli result"
        assert calls == ["fix it"]

    def test_invoke_backend_delegates_to_invoke_opencode(
        self, opencode_hand, monkeypatch
    ) -> None:
        calls: list[str] = []

        async def fake_invoke_opencode(prompt, *, emit):
            calls.append(prompt)
            return "delegated"

        monkeypatch.setattr(opencode_hand, "_invoke_opencode", fake_invoke_opencode)

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(opencode_hand._invoke_backend("hello", emit=emit))
        assert result == "delegated"
        assert calls == ["hello"]
