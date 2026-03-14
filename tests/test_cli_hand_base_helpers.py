"""Tests for _TwoPhaseCLIHand helper methods not covered in other test files.

Covers: _resolve_cli_model, _inject_prompt_argument, _normalize_base_command,
_build_failure_message, _describe_auth, _effective_container_env_names,
_build_subprocess_env, _interrupted_pr_metadata.
"""

from __future__ import annotations

from pathlib import Path
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

    def test_none_model_returns_backend_model(self) -> None:
        """str(None) produces 'None'; should fall back to _DEFAULT_MODEL."""
        stub = _Stub(model=None)
        assert stub._resolve_cli_model() == "stub-model-1"


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
        long_output = "x" * 8000
        msg = stub._build_failure_message(return_code=1, output=long_output)
        # Only last _SUMMARY_CHAR_LIMIT (6000) chars of output are included
        assert len(msg) < 8000
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

    def test_native_auth_empty_blocked_returns_all(self) -> None:
        """When _native_cli_auth_env_names returns empty, all env names pass through."""

        class _EmptyBlockedStub(self._ContainerStub):
            def _native_cli_auth_env_names(self) -> tuple[str, ...]:
                return ()

        stub = _EmptyBlockedStub(use_native_cli_auth=True)
        names = stub._effective_container_env_names()
        assert "OPENAI_API_KEY" in names
        assert "ANTHROPIC_API_KEY" in names
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


# ---------------------------------------------------------------------------
# _base_command
# ---------------------------------------------------------------------------


class TestBaseCommand:
    def test_default_command(self) -> None:
        stub = _Stub()
        cmd = stub._base_command()
        # Default is "stub-cli" + _DEFAULT_APPEND_ARGS ("--json")
        assert cmd == ["stub-cli", "--json"]

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CMD", "custom-bin --flag")
        stub = _Stub()
        cmd = stub._base_command()
        assert cmd == ["custom-bin", "--flag"]

    def test_empty_env_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CMD", "")
        stub = _Stub()
        with pytest.raises(RuntimeError, match="empty command"):
            stub._base_command()


# ---------------------------------------------------------------------------
# _io_poll_seconds / _heartbeat_seconds / _idle_timeout_seconds
# ---------------------------------------------------------------------------


class TestTimingDefaults:
    def test_io_poll_default(self) -> None:
        stub = _Stub()
        result = stub._io_poll_seconds()
        assert result == _TwoPhaseCLIHand._DEFAULT_IO_POLL_SECONDS

    def test_io_poll_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLI_IO_POLL_SECONDS", "0.5")
        stub = _Stub()
        assert stub._io_poll_seconds() == 0.5

    def test_heartbeat_default_not_verbose(self) -> None:
        stub = _Stub(verbose=False)
        result = stub._heartbeat_seconds()
        assert result == _TwoPhaseCLIHand._DEFAULT_HEARTBEAT_SECONDS

    def test_heartbeat_default_verbose(self) -> None:
        stub = _Stub(verbose=True)
        result = stub._heartbeat_seconds()
        assert result == _TwoPhaseCLIHand._DEFAULT_HEARTBEAT_SECONDS_VERBOSE

    def test_heartbeat_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLI_HEARTBEAT_SECONDS", "10.0")
        stub = _Stub()
        assert stub._heartbeat_seconds() == 10.0

    def test_idle_timeout_default(self) -> None:
        stub = _Stub()
        result = stub._idle_timeout_seconds()
        assert result == _TwoPhaseCLIHand._DEFAULT_IDLE_TIMEOUT_SECONDS

    def test_idle_timeout_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS", "120.0")
        stub = _Stub()
        assert stub._idle_timeout_seconds() == 120.0


# ---------------------------------------------------------------------------
# _repo_has_changes
# ---------------------------------------------------------------------------


class TestRepoHasChanges:
    def test_with_changes(self, tmp_path: Path) -> None:
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "a.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
        )

        # Make an uncommitted change
        (tmp_path / "b.txt").write_text("new file")

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        assert stub._repo_has_changes() is True

    def test_without_changes(self, tmp_path: Path) -> None:
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "a.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
        )

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        assert stub._repo_has_changes() is False

    def test_not_a_git_repo(self, tmp_path: Path) -> None:
        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        assert stub._repo_has_changes() is False

    def test_git_status_failure_logs_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """v123: git status failure emits debug log with return code."""
        import logging

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        with caplog.at_level(logging.DEBUG):
            result = stub._repo_has_changes()
        assert result is False
        assert any("git status check failed" in r.message for r in caplog.records)

    def test_timeout_returns_false(self, tmp_path: Path) -> None:
        """v149: git status timeout returns False instead of hanging."""
        import subprocess
        from unittest.mock import patch

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.base.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=30),
        ):
            assert stub._repo_has_changes() is False

    def test_timeout_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """v149: git status timeout emits warning log."""
        import logging
        import subprocess
        from unittest.mock import patch

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        with (
            patch(
                "helping_hands.lib.hands.v1.hand.cli.base.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=30),
            ),
            caplog.at_level(logging.WARNING),
        ):
            stub._repo_has_changes()
        assert any("git status timed out" in r.message for r in caplog.records)
