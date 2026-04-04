"""Tests for DevinCLIHand static/pure helper methods.

DevinCLIHand wraps the `devin` CLI and overrides model resolution to preserve
the full "provider/model" string (unlike most CLI hands that strip the prefix).
This is intentional: Devin's CLI accepts provider-qualified model names. A
regression in _resolve_cli_model that strips the provider prefix would silently
route requests to a wrong or unavailable model. The env-var override tests
guard the HELPING_HANDS_DEVIN_MODEL escape hatch used in deployments where the
config-level model must be overridden without rebuilding. Auth failure detection
ensures actionable error messages for the Devin-specific 401/invalid-key
patterns.
"""

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

    def test_default_model_returns_opus(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="default")
        assert hand._resolve_cli_model() == "claude-opus-4-6"

    def test_empty_model_returns_opus(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="")
        assert hand._resolve_cli_model() == "claude-opus-4-6"

    def test_whitespace_model_returns_opus(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="  ")
        assert hand._resolve_cli_model() == "claude-opus-4-6"

    def test_none_model_returns_opus(self, make_cli_hand) -> None:
        """str(None) produces 'None'; should fall back to _DEFAULT_MODEL."""
        hand = make_cli_hand(DevinCLIHand, model=None)
        assert hand._resolve_cli_model() == "claude-opus-4-6"

    def test_env_var_overrides_config(self, make_cli_hand, monkeypatch) -> None:
        """HELPING_HANDS_DEVIN_MODEL env var takes precedence."""
        monkeypatch.setenv("HELPING_HANDS_DEVIN_MODEL", "openai/gpt-5.4")
        hand = make_cli_hand(DevinCLIHand, model="claude-sonnet-4-6")
        assert hand._resolve_cli_model() == "openai/gpt-5.4"

    def test_env_var_empty_falls_through(self, make_cli_hand, monkeypatch) -> None:
        """Empty env var defers to config model."""
        monkeypatch.setenv("HELPING_HANDS_DEVIN_MODEL", "")
        hand = make_cli_hand(DevinCLIHand, model="claude-sonnet-4-6")
        assert hand._resolve_cli_model() == "claude-sonnet-4-6"


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


# ---------------------------------------------------------------------------
# _inject_prompt_argument
# ---------------------------------------------------------------------------


class TestInjectPromptArgument:
    def test_appends_double_dash_and_prompt(self, devin_hand) -> None:
        cmd: list[str] = ["devin", "-p"]
        result = devin_hand._inject_prompt_argument(cmd, "fix the bug")
        assert result is True
        assert cmd == ["devin", "-p", "--", "fix the bug"]

    def test_always_returns_true(self, devin_hand) -> None:
        cmd: list[str] = []
        assert devin_hand._inject_prompt_argument(cmd, "") is True

    def test_prompt_with_special_chars(self, devin_hand) -> None:
        cmd: list[str] = ["devin", "-p"]
        devin_hand._inject_prompt_argument(cmd, "say 'hello' && exit")
        assert cmd[-1] == "say 'hello' && exit"


# ---------------------------------------------------------------------------
# _normalize_base_command
# ---------------------------------------------------------------------------


class TestNormalizeBaseCommand:
    def test_bare_devin_gets_dash_p(self, devin_hand) -> None:
        result = devin_hand._normalize_base_command(["devin"])
        assert result == ["devin", "-p"]

    def test_devin_with_args_unchanged(self, devin_hand) -> None:
        result = devin_hand._normalize_base_command(["devin", "-p"])
        assert result == ["devin", "-p"]

    def test_non_devin_command_unchanged(self, devin_hand) -> None:
        result = devin_hand._normalize_base_command(["custom-devin"])
        assert result == ["custom-devin"]


# ---------------------------------------------------------------------------
# _native_cli_auth_env_names
# ---------------------------------------------------------------------------


class TestNativeCliAuthEnvNames:
    def test_returns_devin_api_key(self, devin_hand) -> None:
        result = devin_hand._native_cli_auth_env_names()
        assert result == ("DEVIN_API_KEY",)


# ---------------------------------------------------------------------------
# _describe_auth
# ---------------------------------------------------------------------------


class TestDescribeAuth:
    def test_native_cli_auth(self, devin_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DEVIN_USE_NATIVE_CLI_AUTH", "1")
        msg = devin_hand._describe_auth()
        assert "native-cli" in msg
        assert "DEVIN_API_KEY stripped" in msg

    def test_non_native_auth_key_set(self, devin_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DEVIN_USE_NATIVE_CLI_AUTH", raising=False)
        monkeypatch.setenv("DEVIN_API_KEY", "sk-test")
        msg = devin_hand._describe_auth()
        assert "auth=DEVIN_API_KEY" in msg

    def test_non_native_auth_key_unset(self, devin_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DEVIN_USE_NATIVE_CLI_AUTH", raising=False)
        monkeypatch.delenv("DEVIN_API_KEY", raising=False)
        msg = devin_hand._describe_auth()
        assert "auth=DEVIN_API_KEY" in msg


# ---------------------------------------------------------------------------
# _permission_mode
# ---------------------------------------------------------------------------


class TestPermissionMode:
    def test_default_is_dangerous(self, devin_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DEVIN_PERMISSION_MODE", raising=False)
        assert devin_hand._permission_mode() == "dangerous"

    def test_env_var_override(self, devin_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DEVIN_PERMISSION_MODE", "auto")
        assert devin_hand._permission_mode() == "auto"

    def test_empty_env_var_returns_default(self, devin_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DEVIN_PERMISSION_MODE", "  ")
        assert devin_hand._permission_mode() == "dangerous"


# ---------------------------------------------------------------------------
# _apply_backend_defaults
# ---------------------------------------------------------------------------


class TestApplyBackendDefaults:
    def test_injects_permission_mode(self, devin_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DEVIN_PERMISSION_MODE", raising=False)
        result = devin_hand._apply_backend_defaults(["devin", "-p"])
        assert result == ["devin", "--permission-mode", "dangerous", "-p"]

    def test_preserves_existing_permission_mode(self, devin_hand) -> None:
        cmd = ["devin", "--permission-mode", "auto", "-p"]
        result = devin_hand._apply_backend_defaults(cmd)
        assert result == cmd

    def test_non_devin_command_passthrough(self, devin_hand) -> None:
        result = devin_hand._apply_backend_defaults(["other-cli", "-p"])
        assert result == ["other-cli", "-p"]

    def test_empty_command_passthrough(self, devin_hand) -> None:
        result = devin_hand._apply_backend_defaults([])
        assert result == []

    def test_custom_permission_mode_from_env(self, devin_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DEVIN_PERMISSION_MODE", "auto")
        result = devin_hand._apply_backend_defaults(["devin", "-p"])
        assert result == ["devin", "--permission-mode", "auto", "-p"]


# ---------------------------------------------------------------------------
# _invoke_devin / _invoke_backend — async delegation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# _pr_description_cmd
# ---------------------------------------------------------------------------


class TestPrDescriptionCmd:
    def test_returns_cmd_when_devin_on_path(self, devin_hand, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/devin")
        result = devin_hand._pr_description_cmd()
        assert result == ["devin", "-p", "--"]

    def test_returns_none_when_devin_not_on_path(self, devin_hand, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = devin_hand._pr_description_cmd()
        assert result is None


# ---------------------------------------------------------------------------
# _pr_description_prompt_as_arg
# ---------------------------------------------------------------------------


class TestPrDescriptionPromptAsArg:
    def test_returns_true(self, devin_hand) -> None:
        assert devin_hand._pr_description_prompt_as_arg() is True


# ---------------------------------------------------------------------------
# _resolve_cli_model — env var edge cases
# ---------------------------------------------------------------------------


class TestResolveCliModelEnvEdge:
    def test_env_var_default_marker_falls_through(
        self, make_cli_hand, monkeypatch
    ) -> None:
        """Env var set to 'default' is treated as empty marker."""
        monkeypatch.setenv("HELPING_HANDS_DEVIN_MODEL", "default")
        hand = make_cli_hand(DevinCLIHand, model="anthropic/claude-sonnet-4-6")
        assert hand._resolve_cli_model() == "anthropic/claude-sonnet-4-6"

    def test_env_var_none_marker_falls_through(
        self, make_cli_hand, monkeypatch
    ) -> None:
        """Env var set to 'None' is treated as empty marker."""
        monkeypatch.setenv("HELPING_HANDS_DEVIN_MODEL", "None")
        hand = make_cli_hand(DevinCLIHand, model="anthropic/claude-sonnet-4-6")
        assert hand._resolve_cli_model() == "anthropic/claude-sonnet-4-6"

    def test_env_var_whitespace_falls_through(self, make_cli_hand, monkeypatch) -> None:
        """Whitespace-only env var defers to config model."""
        monkeypatch.setenv("HELPING_HANDS_DEVIN_MODEL", "   ")
        hand = make_cli_hand(DevinCLIHand, model="claude-sonnet-4-6")
        assert hand._resolve_cli_model() == "claude-sonnet-4-6"

    def test_env_var_unset_uses_config(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DEVIN_MODEL", raising=False)
        hand = make_cli_hand(DevinCLIHand, model="openai/gpt-5.2")
        assert hand._resolve_cli_model() == "openai/gpt-5.2"

    def test_env_var_and_config_both_empty_returns_default(
        self, make_cli_hand, monkeypatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_DEVIN_MODEL", "")
        hand = make_cli_hand(DevinCLIHand, model="")
        assert hand._resolve_cli_model() == "claude-opus-4-6"


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
