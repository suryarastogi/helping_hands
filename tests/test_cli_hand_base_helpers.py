"""Tests for _TwoPhaseCLIHand helper methods not covered in other test files.

Covers: _resolve_cli_model, _inject_prompt_argument, _normalize_base_command,
_build_failure_message, _describe_auth, _effective_container_env_names,
_build_subprocess_env, _interrupted_pr_metadata.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Minimal stub that skips the full __init__ chain
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _COMMAND_ENV_VAR = "STUB_CMD"
    _DEFAULT_CLI_CMD = "stub-cli"
    _DEFAULT_MODEL = "stub-model-1"
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ("--json",)

    def __init__(
        self,
        *,
        model: str = "default",
        verbose: bool = False,
        use_native_cli_auth: bool = False,
    ) -> None:
        # Bypass Hand.__init__ entirely — we only test helper methods.
        self.config = SimpleNamespace(
            model=model,
            verbose=verbose,
            use_native_cli_auth=use_native_cli_auth,
        )
        self.auto_pr = True


# ---------------------------------------------------------------------------
# _resolve_cli_model
# ---------------------------------------------------------------------------


class TestResolveCliModel:
    def test_default_returns_backend_model(self) -> None:
        stub = _Stub(model="default")
        assert stub._resolve_cli_model() == "stub-model-1"

    def test_empty_returns_backend_model(self) -> None:
        stub = _Stub(model="")
        assert stub._resolve_cli_model() == "stub-model-1"

    def test_whitespace_only_returns_backend_model(self) -> None:
        stub = _Stub(model="   ")
        assert stub._resolve_cli_model() == "stub-model-1"

    def test_bare_model_returned_as_is(self) -> None:
        stub = _Stub(model="gpt-5.2")
        assert stub._resolve_cli_model() == "gpt-5.2"

    def test_provider_slash_model_strips_provider(self) -> None:
        stub = _Stub(model="anthropic/claude-sonnet-4-5")
        assert stub._resolve_cli_model() == "claude-sonnet-4-5"

    def test_provider_slash_empty_returns_full_string(self) -> None:
        # When provider_model is empty after partition, falls through to return model
        stub = _Stub(model="anthropic/")
        assert stub._resolve_cli_model() == "anthropic/"

    def test_multiple_slashes_takes_after_first(self) -> None:
        stub = _Stub(model="a/b/c")
        assert stub._resolve_cli_model() == "b/c"


# ---------------------------------------------------------------------------
# _inject_prompt_argument (static)
# ---------------------------------------------------------------------------


class TestInjectPromptArgument:
    def test_dash_p_flag_replaces_next_token(self) -> None:
        cmd = ["cli", "-p", "old_prompt"]
        result = _TwoPhaseCLIHand._inject_prompt_argument(cmd, "new prompt")
        assert result is True
        assert cmd == ["cli", "-p", "new prompt"]

    def test_dash_p_flag_inserts_when_missing_value(self) -> None:
        cmd = ["cli", "-p", "-v"]
        result = _TwoPhaseCLIHand._inject_prompt_argument(cmd, "my prompt")
        assert result is True
        assert cmd == ["cli", "-p", "my prompt", "-v"]

    def test_dash_p_flag_at_end_inserts(self) -> None:
        cmd = ["cli", "-p"]
        result = _TwoPhaseCLIHand._inject_prompt_argument(cmd, "prompt text")
        assert result is True
        assert cmd == ["cli", "-p", "prompt text"]

    def test_double_dash_prompt_flag(self) -> None:
        cmd = ["cli", "--prompt", "old"]
        result = _TwoPhaseCLIHand._inject_prompt_argument(cmd, "new")
        assert result is True
        assert cmd == ["cli", "--prompt", "new"]

    def test_prompt_equals_format(self) -> None:
        cmd = ["cli", "--prompt=old"]
        result = _TwoPhaseCLIHand._inject_prompt_argument(cmd, "new")
        assert result is True
        assert cmd == ["cli", "--prompt=new"]

    def test_dash_p_equals_format(self) -> None:
        cmd = ["cli", "-p=old"]
        result = _TwoPhaseCLIHand._inject_prompt_argument(cmd, "new")
        assert result is True
        assert cmd == ["cli", "-p=new"]

    def test_no_prompt_flag_returns_false(self) -> None:
        cmd = ["cli", "--verbose"]
        result = _TwoPhaseCLIHand._inject_prompt_argument(cmd, "prompt")
        assert result is False
        assert cmd == ["cli", "--verbose"]


# ---------------------------------------------------------------------------
# _normalize_base_command
# ---------------------------------------------------------------------------


class TestNormalizeBaseCommand:
    def test_single_token_appends_defaults(self) -> None:
        stub = _Stub()
        result = stub._normalize_base_command(["stub-cli"])
        assert result == ["stub-cli", "--json"]

    def test_multi_token_passes_through(self) -> None:
        stub = _Stub()
        result = stub._normalize_base_command(["stub-cli", "--custom"])
        assert result == ["stub-cli", "--custom"]

    def test_no_default_args(self) -> None:
        stub = _Stub()
        stub._DEFAULT_APPEND_ARGS = ()
        result = stub._normalize_base_command(["stub-cli"])
        assert result == ["stub-cli"]


# ---------------------------------------------------------------------------
# _build_failure_message
# ---------------------------------------------------------------------------


class TestBuildFailureMessage:
    def test_includes_exit_code(self) -> None:
        stub = _Stub()
        msg = stub._build_failure_message(return_code=42, output="some error")
        assert "exit=42" in msg
        assert "Stub CLI" in msg
        assert "some error" in msg

    def test_truncates_long_output(self) -> None:
        stub = _Stub()
        long_output = "x" * 5000
        msg = stub._build_failure_message(return_code=1, output=long_output)
        # Only last 2000 chars of output are included
        assert len(msg) < 5000
        assert "...[truncated]" not in msg  # it just takes the tail


# ---------------------------------------------------------------------------
# _describe_auth
# ---------------------------------------------------------------------------


class TestDescribeAuth:
    class _AuthStub(_Stub):
        def _native_cli_auth_env_names(self) -> tuple[str, ...]:
            return ("MY_API_KEY",)

    def test_no_native_env_names_returns_empty(self) -> None:
        stub = _Stub()
        assert stub._describe_auth() == ""

    def test_native_cli_auth_enabled(self) -> None:
        stub = self._AuthStub(use_native_cli_auth=True)
        msg = stub._describe_auth()
        assert "auth=native-cli" in msg
        assert "MY_API_KEY stripped" in msg

    def test_env_var_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_API_KEY", "sk-123")
        stub = self._AuthStub(use_native_cli_auth=False)
        msg = stub._describe_auth()
        assert "auth=MY_API_KEY" in msg

    def test_no_env_var_set(self) -> None:
        stub = self._AuthStub(use_native_cli_auth=False)
        msg = stub._describe_auth()
        assert "auth=native-cli" in msg
        assert "no MY_API_KEY set" in msg


# ---------------------------------------------------------------------------
# _effective_container_env_names
# ---------------------------------------------------------------------------


class TestEffectiveContainerEnvNames:
    class _ContainerStub(_Stub):
        def _container_env_names(self) -> tuple[str, ...]:
            return ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")

        def _native_cli_auth_env_names(self) -> tuple[str, ...]:
            return ("ANTHROPIC_API_KEY",)

    def test_no_native_auth_returns_all(self) -> None:
        stub = self._ContainerStub(use_native_cli_auth=False)
        names = stub._effective_container_env_names()
        assert "OPENAI_API_KEY" in names
        assert "ANTHROPIC_API_KEY" in names
        assert "GEMINI_API_KEY" in names

    def test_native_auth_filters_blocked(self) -> None:
        stub = self._ContainerStub(use_native_cli_auth=True)
        names = stub._effective_container_env_names()
        assert "OPENAI_API_KEY" in names
        assert "ANTHROPIC_API_KEY" not in names
        assert "GEMINI_API_KEY" in names


# ---------------------------------------------------------------------------
# _build_subprocess_env
# ---------------------------------------------------------------------------


class TestBuildSubprocessEnv:
    class _EnvStub(_Stub):
        def _native_cli_auth_env_names(self) -> tuple[str, ...]:
            return ("MY_SECRET_KEY",)

    def test_no_native_auth_preserves_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MY_SECRET_KEY", "secret")
        stub = self._EnvStub(use_native_cli_auth=False)
        env = stub._build_subprocess_env()
        assert env.get("MY_SECRET_KEY") == "secret"

    def test_native_auth_strips_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_SECRET_KEY", "secret")
        stub = self._EnvStub(use_native_cli_auth=True)
        env = stub._build_subprocess_env()
        assert "MY_SECRET_KEY" not in env


# ---------------------------------------------------------------------------
# _interrupted_pr_metadata
# ---------------------------------------------------------------------------


class TestInterruptedPrMetadata:
    def test_returns_correct_shape(self) -> None:
        stub = _Stub()
        meta = stub._interrupted_pr_metadata()
        assert meta["auto_pr"] == "true"
        assert meta["pr_status"] == "interrupted"
        assert meta["pr_url"] == ""
        assert meta["pr_number"] == ""
        assert meta["pr_branch"] == ""
        assert meta["pr_commit"] == ""

    def test_auto_pr_false(self) -> None:
        stub = _Stub()
        stub.auto_pr = False
        meta = stub._interrupted_pr_metadata()
        assert meta["auto_pr"] == "false"
