"""Tests for OpenCodeCLIHand static/pure helper methods."""

from __future__ import annotations

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_opencode_hand(tmp_path, model="anthropic/claude-sonnet-4-6"):
    (tmp_path / "main.py").write_text("")
    config = Config(repo=str(tmp_path), model=model)
    repo_index = RepoIndex.from_path(tmp_path)
    return OpenCodeCLIHand(config=config, repo_index=repo_index)


@pytest.fixture()
def opencode_hand(tmp_path):
    return _make_opencode_hand(tmp_path)


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

    def test_preserves_bare_model(self, tmp_path) -> None:
        hand = _make_opencode_hand(tmp_path, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_default_model_returns_empty(self, tmp_path) -> None:
        hand = _make_opencode_hand(tmp_path, model="default")
        assert hand._resolve_cli_model() == ""

    def test_empty_model_returns_empty(self, tmp_path) -> None:
        hand = _make_opencode_hand(tmp_path, model="")
        assert hand._resolve_cli_model() == ""

    def test_whitespace_model_returns_empty(self, tmp_path) -> None:
        hand = _make_opencode_hand(tmp_path, model="  ")
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
