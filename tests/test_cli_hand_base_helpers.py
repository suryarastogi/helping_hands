"""Tests for _TwoPhaseCLIHand lower-level helper methods.

Covers model resolution, prompt argument injection, subprocess env building,
auth description, container env filtering, and timing overrides.

Model resolution (_resolve_cli_model) is the single place where the
user-supplied "provider/model" string is normalised into the bare model ID
that each CLI backend expects; a bug there silently passes a wrong model string
to the subprocess. Auth env stripping (_build_subprocess_env, native-CLI-auth
path) is a security boundary: when a CLI uses its own credential store the API
key must be removed from the child environment or it may override the intended
identity. The _repo_has_changes check drives the no-change retry loop — a false
positive wastes a retry; a false negative skips retry on a real edit task.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import (
    _EMPTY_MODEL_MARKERS,
    _TwoPhaseCLIHand,
)

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
        self._baseline_head = ""
        self._ci_fix_mode = False


# ---------------------------------------------------------------------------
# _resolve_cli_model
# ---------------------------------------------------------------------------


class TestEmptyModelMarkers:
    """Tests for the _EMPTY_MODEL_MARKERS constant."""

    def test_contains_default(self) -> None:
        assert "default" in _EMPTY_MODEL_MARKERS

    def test_contains_none_string(self) -> None:
        assert "None" in _EMPTY_MODEL_MARKERS

    def test_is_tuple(self) -> None:
        assert isinstance(_EMPTY_MODEL_MARKERS, tuple)

    def test_all_markers_fall_back_to_default_model(self) -> None:
        """Every marker in _EMPTY_MODEL_MARKERS should trigger fallback."""
        for marker in _EMPTY_MODEL_MARKERS:
            stub = _Stub(model=marker)
            assert stub._resolve_cli_model() == "stub-model-1", (
                f"marker {marker!r} did not trigger fallback"
            )


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


# ---------------------------------------------------------------------------
# _label_msg
# ---------------------------------------------------------------------------


class TestLabelMsg:
    """v267: _label_msg prefixes messages with the CLI backend label."""

    def test_default_label(self) -> None:
        stub = _Stub()
        assert stub._label_msg("hello") == "[stub] hello"

    def test_empty_message(self) -> None:
        stub = _Stub()
        assert stub._label_msg("") == "[stub] "

    def test_custom_label(self) -> None:
        stub = _Stub()
        stub._CLI_LABEL = "custom-backend"
        assert stub._label_msg("test") == "[custom-backend] test"

    def test_message_with_newline(self) -> None:
        stub = _Stub()
        result = stub._label_msg("phase 1 done\n")
        assert result == "[stub] phase 1 done\n"

    def test_message_with_interpolation(self) -> None:
        stub = _Stub()
        elapsed = 3.5
        result = stub._label_msg(f"finished in {elapsed:.1f}s (exit=0)\n")
        assert result == "[stub] finished in 3.5s (exit=0)\n"

    def test_format_pr_status_uses_label_msg(self) -> None:
        """Ensure _format_pr_status_message uses the label prefix."""
        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=Path("/tmp"))
        metadata = {"pr_status": "no_changes"}
        result = stub._format_pr_status_message(metadata)
        assert result is not None
        assert result.startswith("[stub] ")

    def test_format_ci_fix_message_uses_label_msg(self) -> None:
        """Ensure _format_ci_fix_message uses the label prefix."""
        stub = _Stub()
        metadata = {"ci_fix_status": "success", "ci_fix_attempts": "0"}
        result = stub._format_ci_fix_message(metadata)
        assert result is not None
        assert result.startswith("[stub] ")


# ---------------------------------------------------------------------------
# _repo_has_changes — HEAD advance detection (lines 1040-1047)
# ---------------------------------------------------------------------------


class TestRepoHasChangesHeadAdvance:
    """Tests for HEAD advance detection when _baseline_head is set."""

    def test_head_advanced_returns_true(self, tmp_path: Path) -> None:
        """When HEAD advanced since baseline, _repo_has_changes returns True."""
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

        # Capture baseline HEAD
        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Make a new commit
        (tmp_path / "b.txt").write_text("new")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "second"], cwd=tmp_path, capture_output=True
        )

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        stub._baseline_head = baseline
        assert stub._repo_has_changes() is True

    def test_head_same_as_baseline_returns_false(self, tmp_path: Path) -> None:
        """When HEAD matches baseline and no uncommitted changes, returns False."""
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

        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        ).stdout.strip()

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        stub._baseline_head = baseline
        assert stub._repo_has_changes() is False


# ---------------------------------------------------------------------------
# _has_pending_changes override (line 1057)
# ---------------------------------------------------------------------------


class TestHasPendingChangesOverride:
    """Tests for _has_pending_changes which delegates to _repo_has_changes."""

    def test_delegates_to_repo_has_changes(self, tmp_path: Path) -> None:
        """_has_pending_changes calls _repo_has_changes internally."""
        from unittest.mock import patch as mock_patch

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        with mock_patch.object(stub, "_repo_has_changes", return_value=True) as m:
            result = stub._has_pending_changes(tmp_path)
        assert result is True
        m.assert_called_once()

    def test_returns_false_when_no_changes(self, tmp_path: Path) -> None:
        """_has_pending_changes returns False when _repo_has_changes is False."""
        from unittest.mock import patch as mock_patch

        stub = _Stub()
        stub.repo_index = SimpleNamespace(root=tmp_path)
        with mock_patch.object(stub, "_repo_has_changes", return_value=False):
            result = stub._has_pending_changes(tmp_path)
        assert result is False
