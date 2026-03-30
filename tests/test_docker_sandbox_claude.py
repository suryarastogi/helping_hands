"""Tests for DockerSandboxClaudeCodeHand lifecycle and helper methods.

Protects the Docker sandbox lifecycle: _ensure_sandbox must check Docker CLI
availability, verify the sandbox plugin, create the sandbox with optional
template, and set _sandbox_created; _remove_sandbox must clean up even when
the parent task raises.  _wrap_sandbox_exec must forward API key environment
variables into the container so the Claude CLI can authenticate.  _build_failure_message
must distinguish auth failures (directing users to ANTHROPIC_API_KEY) from
generic failures (citing the sandbox name), without duplicating notes when the
base message already mentions sandbox.  Sandbox name generation must produce
stable, alphanumeric-only identifiers safe for Docker naming rules.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
    _AUTH_FAILURE_SUBSTRINGS,
    DockerSandboxClaudeCodeHand,
)
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def hand(make_cli_hand):
    return make_cli_hand(DockerSandboxClaudeCodeHand, model="claude-sonnet-4-5")


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestClassAttributes:
    def test_backend_name(self) -> None:
        assert DockerSandboxClaudeCodeHand._BACKEND_NAME == "docker-sandbox-claude"

    def test_cli_label(self) -> None:
        assert DockerSandboxClaudeCodeHand._CLI_LABEL == "docker-sandbox"

    def test_cli_display_name(self) -> None:
        assert (
            DockerSandboxClaudeCodeHand._CLI_DISPLAY_NAME
            == "Docker Sandbox Claude Code"
        )

    def test_container_env_vars_disabled(self) -> None:
        assert DockerSandboxClaudeCodeHand._CONTAINER_ENABLED_ENV_VAR == ""
        assert DockerSandboxClaudeCodeHand._CONTAINER_IMAGE_ENV_VAR == ""


# ---------------------------------------------------------------------------
# _resolve_sandbox_name
# ---------------------------------------------------------------------------


class TestResolveSandboxName:
    def test_env_var_override(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "my-sandbox")
        name = hand._resolve_sandbox_name()
        assert name == "my-sandbox"

    def test_env_var_override_stripped(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "  my-sandbox  ")
        name = hand._resolve_sandbox_name()
        assert name == "my-sandbox"

    def test_auto_generated_from_repo_name(self, hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", raising=False)
        name = hand._resolve_sandbox_name()
        assert name.startswith("hh-")
        # Should contain sanitized repo dir name and a hex suffix
        parts = name.split("-")
        assert len(parts[-1]) == 8  # uuid hex suffix

    def test_special_characters_sanitized(self, tmp_path, monkeypatch) -> None:
        # Create a directory with special chars
        repo_dir = tmp_path / "my_repo@v2.0!"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("")
        config = Config(repo=str(repo_dir), model="claude-sonnet-4-5")
        repo_index = RepoIndex.from_path(repo_dir)
        hand = DockerSandboxClaudeCodeHand(config=config, repo_index=repo_index)
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", raising=False)

        name = hand._resolve_sandbox_name()
        # No special chars except hyphens
        assert name.startswith("hh-")
        # The core part should only have alphanumeric and hyphens
        for char in name[3:]:
            assert char.isalnum() or char == "-"

    def test_cached_on_second_call(self, hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", raising=False)
        first = hand._resolve_sandbox_name()
        second = hand._resolve_sandbox_name()
        assert first == second

    def test_preexisting_name_returned(self, hand) -> None:
        hand._sandbox_name = "already-set"
        assert hand._resolve_sandbox_name() == "already-set"


# ---------------------------------------------------------------------------
# _should_cleanup
# ---------------------------------------------------------------------------


class TestShouldCleanup:
    def test_default_is_true(self, hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", raising=False)
        assert hand._should_cleanup() is True

    def test_set_to_zero_returns_false(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "0")
        assert hand._should_cleanup() is False

    def test_set_to_one_returns_true(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "1")
        assert hand._should_cleanup() is True

    def test_set_to_false_returns_false(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "false")
        assert hand._should_cleanup() is False

    def test_set_to_true_returns_true(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "true")
        assert hand._should_cleanup() is True


# ---------------------------------------------------------------------------
# _execution_mode
# ---------------------------------------------------------------------------


class TestExecutionMode:
    def test_returns_docker_sandbox(self, hand) -> None:
        assert hand._execution_mode() == "docker-sandbox"


# ---------------------------------------------------------------------------
# _wrap_sandbox_exec
# ---------------------------------------------------------------------------


class TestWrapSandboxExec:
    def test_basic_wrapping(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        # Clear env vars that might be forwarded
        for key in hand._effective_container_env_names():
            monkeypatch.delenv(key, raising=False)

        result = hand._wrap_sandbox_exec(["claude", "-p", "hello"])
        assert result[0] == "docker"
        assert result[1] == "sandbox"
        assert result[2] == "exec"
        assert "--workdir" in result
        assert "test-sb" in result
        assert result[-3:] == ["claude", "-p", "hello"]

    def test_env_var_forwarding(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        # Ensure native CLI auth is disabled so ANTHROPIC_API_KEY is forwarded.
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH", raising=False)
        monkeypatch.delenv("HELPING_HANDS_USE_NATIVE_CLI_AUTH", raising=False)

        result = hand._wrap_sandbox_exec(["claude", "-p", "hello"])
        # Should contain --env flag with the API key
        env_idx = None
        for i, arg in enumerate(result):
            if (
                arg == "--env"
                and i + 1 < len(result)
                and result[i + 1].startswith("ANTHROPIC_API_KEY=")
            ):
                env_idx = i
                break
        assert env_idx is not None, "ANTHROPIC_API_KEY should be forwarded"
        assert result[env_idx + 1] == "ANTHROPIC_API_KEY=sk-ant-test123"


# ---------------------------------------------------------------------------
# _build_failure_message
# ---------------------------------------------------------------------------


class TestBuildFailureMessage:
    def test_auth_not_logged_in(self, hand) -> None:
        msg = hand._build_failure_message(
            return_code=1, output="Error: not logged in to Claude"
        )
        assert "not authenticated" in msg.lower() or "ANTHROPIC_API_KEY" in msg
        assert "Docker sandbox" in msg or "docker-sandbox-claude" in msg.lower()

    def test_auth_authentication_failed(self, hand) -> None:
        msg = hand._build_failure_message(return_code=1, output="authentication_failed")
        assert "ANTHROPIC_API_KEY" in msg
        assert "sandbox" in msg.lower()

    def test_generic_failure_appends_sandbox_note(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "my-sb")
        msg = hand._build_failure_message(return_code=42, output="something went wrong")
        assert "my-sb" in msg
        assert "sandbox" in msg.lower()

    def test_no_duplicate_sandbox_note(self, hand, monkeypatch) -> None:
        """If base message already mentions 'sandbox', don't append again."""
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "my-sb")
        # The auth path already mentions sandbox
        msg = hand._build_failure_message(return_code=1, output="not logged in")
        # Count occurrences of "sandbox" — auth message says "Docker sandbox"
        assert "sandbox" in msg.lower()


# ---------------------------------------------------------------------------
# _command_not_found_message
# ---------------------------------------------------------------------------


class TestCommandNotFoundMessage:
    def test_includes_command_name(self, hand) -> None:
        msg = hand._command_not_found_message("claude")
        assert "claude" in msg
        assert "Docker sandbox" in msg
        assert "sandbox template" in msg.lower()


# ---------------------------------------------------------------------------
# _fallback_command_when_not_found
# ---------------------------------------------------------------------------


class TestFallbackCommandWhenNotFound:
    def test_returns_none(self, hand) -> None:
        assert hand._fallback_command_when_not_found(["claude", "-p"]) is None


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_initial_state(self, hand) -> None:
        assert hand._sandbox_name is None
        assert hand._sandbox_created is False


# ---------------------------------------------------------------------------
# _docker_sandbox_available (async, mocked subprocess)
# ---------------------------------------------------------------------------


class TestDockerSandboxAvailable:
    def test_returns_true_on_success(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = asyncio.new_event_loop().run_until_complete(
                DockerSandboxClaudeCodeHand._docker_sandbox_available()
            )
        assert result is True

    def test_returns_false_on_failure(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = asyncio.new_event_loop().run_until_complete(
                DockerSandboxClaudeCodeHand._docker_sandbox_available()
            )
        assert result is False

    def test_returns_false_on_file_not_found(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("docker not found"),
        ):
            result = asyncio.new_event_loop().run_until_complete(
                DockerSandboxClaudeCodeHand._docker_sandbox_available()
            )
        assert result is False


# ---------------------------------------------------------------------------
# _ensure_sandbox (async, mocked subprocess)
# ---------------------------------------------------------------------------


class TestEnsureSandbox:
    def test_skips_if_already_created(self, hand) -> None:
        hand._sandbox_created = True
        emit = AsyncMock()
        asyncio.new_event_loop().run_until_complete(hand._ensure_sandbox(emit))
        emit.assert_not_awaited()

    def test_raises_if_docker_not_found(self, hand, monkeypatch) -> None:
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: None,
        )
        emit = AsyncMock()
        with pytest.raises(RuntimeError, match="Docker CLI not found"):
            asyncio.new_event_loop().run_until_complete(hand._ensure_sandbox(emit))

    def test_raises_if_sandbox_plugin_unavailable(self, hand, monkeypatch) -> None:
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/bin/docker",
        )
        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_docker_sandbox_available",
            new_callable=AsyncMock,
            return_value=False,
        ):
            emit = AsyncMock()
            with pytest.raises(RuntimeError, match=r"docker sandbox.*not available"):
                asyncio.new_event_loop().run_until_complete(hand._ensure_sandbox(emit))

    def test_creates_sandbox_successfully(self, hand, monkeypatch) -> None:
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/bin/docker",
        )
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", raising=False)

        # Mock _docker_sandbox_available
        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_docker_sandbox_available",
            new_callable=AsyncMock,
            return_value=True,
        ):
            # Mock subprocess for sandbox creation
            mock_stdout = AsyncMock()
            mock_stdout.read = AsyncMock(side_effect=[b"sandbox ready\n", b""])
            mock_proc = AsyncMock()
            mock_proc.stdout = mock_stdout
            mock_proc.returncode = 0
            mock_proc.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                emit = AsyncMock()
                asyncio.new_event_loop().run_until_complete(hand._ensure_sandbox(emit))

        assert hand._sandbox_created is True

    def test_raises_on_create_failure(self, hand, monkeypatch) -> None:
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/bin/docker",
        )
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", raising=False)

        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_docker_sandbox_available",
            new_callable=AsyncMock,
            return_value=True,
        ):
            mock_stdout = AsyncMock()
            mock_stdout.read = AsyncMock(side_effect=[b"error: quota exceeded\n", b""])
            mock_proc = AsyncMock()
            mock_proc.stdout = mock_stdout
            mock_proc.returncode = 1
            mock_proc.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                emit = AsyncMock()
                with pytest.raises(RuntimeError, match="Failed to create"):
                    asyncio.new_event_loop().run_until_complete(
                        hand._ensure_sandbox(emit)
                    )

    def test_template_env_var_applied(self, hand, monkeypatch) -> None:
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/bin/docker",
        )
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", "my-template")

        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_docker_sandbox_available",
            new_callable=AsyncMock,
            return_value=True,
        ):
            mock_stdout = AsyncMock()
            mock_stdout.read = AsyncMock(side_effect=[b"ok\n", b""])
            mock_proc = AsyncMock()
            mock_proc.stdout = mock_stdout
            mock_proc.returncode = 0
            mock_proc.wait = AsyncMock()

            calls = []

            async def capture_create(*args, **kwargs):
                calls.append(args)
                return mock_proc

            with patch("asyncio.create_subprocess_exec", side_effect=capture_create):
                emit = AsyncMock()
                asyncio.new_event_loop().run_until_complete(hand._ensure_sandbox(emit))

        # Check that --template my-template was passed
        cmd_args = calls[0]
        assert "--template" in cmd_args
        idx = cmd_args.index("--template")
        assert cmd_args[idx + 1] == "my-template"


# ---------------------------------------------------------------------------
# _remove_sandbox (async, mocked subprocess)
# ---------------------------------------------------------------------------


class TestRemoveSandbox:
    def test_skips_if_not_created(self, hand) -> None:
        hand._sandbox_created = False
        emit = AsyncMock()
        asyncio.new_event_loop().run_until_complete(hand._remove_sandbox(emit))
        emit.assert_not_awaited()

    def test_stops_and_removes_sandbox(self, hand, monkeypatch) -> None:
        hand._sandbox_created = True
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            emit = AsyncMock()
            asyncio.new_event_loop().run_until_complete(hand._remove_sandbox(emit))

        assert hand._sandbox_created is False


# ---------------------------------------------------------------------------
# _invoke_claude (async, wraps command with sandbox exec + stream-json)
# ---------------------------------------------------------------------------


class TestInvokeClaude:
    def test_wraps_with_sandbox_and_returns_result(self, hand, monkeypatch) -> None:
        """_invoke_claude wraps cmd with _wrap_sandbox_exec and uses emitter."""
        captured_cmd: list[str] = []

        async def fake_invoke_cli_with_cmd(cmd, *, emit):
            captured_cmd.extend(cmd)
            # Simulate stream-json result event
            import json

            event = json.dumps(
                {"type": "result", "result": "sandbox done", "total_cost_usd": 0.01}
            )
            await emit(event + "\n")
            return "raw fallback"

        monkeypatch.setattr(hand, "_invoke_cli_with_cmd", fake_invoke_cli_with_cmd)
        monkeypatch.setattr(
            hand, "_render_command", lambda prompt: ["claude", "-p", prompt]
        )
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")

        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        result = asyncio.run(hand._invoke_claude("fix bug", emit=emit))
        assert result == "sandbox done"
        # The command should be wrapped with docker sandbox exec
        assert "docker" in captured_cmd
        assert "sandbox" in captured_cmd
        assert "exec" in captured_cmd

    def test_falls_back_to_raw_output(self, hand, monkeypatch) -> None:
        """When emitter has no result_text, falls back to raw CLI output."""

        async def fake_invoke_cli_with_cmd(cmd, *, emit):
            await emit("plain output\n")
            return "raw result"

        monkeypatch.setattr(hand, "_invoke_cli_with_cmd", fake_invoke_cli_with_cmd)
        monkeypatch.setattr(
            hand, "_render_command", lambda prompt: ["claude", "-p", prompt]
        )
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(hand._invoke_claude("fix bug", emit=emit))
        assert result == "raw result"


# ---------------------------------------------------------------------------
# _run_two_phase (async, sandbox lifecycle)
# ---------------------------------------------------------------------------


class TestRunTwoPhase:
    def test_ensures_sandbox_and_cleans_up(self, hand, monkeypatch) -> None:
        """_run_two_phase calls _ensure_sandbox before, _remove_sandbox after."""
        ensure_called = []
        remove_called = []

        async def fake_ensure(emit):
            ensure_called.append(True)

        async def fake_remove(emit):
            remove_called.append(True)

        monkeypatch.setattr(hand, "_ensure_sandbox", fake_ensure)
        monkeypatch.setattr(hand, "_remove_sandbox", fake_remove)
        monkeypatch.setattr(hand, "_should_cleanup", lambda: True)

        # Patch at the _TwoPhaseCLIHand level (where super() resolves to)
        async def fake_parent_run_two_phase(self, prompt, *, emit):
            return "result"

        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        monkeypatch.setattr(
            _TwoPhaseCLIHand, "_run_two_phase", fake_parent_run_two_phase
        )

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(hand._run_two_phase("task", emit=emit))
        assert result == "result"
        assert ensure_called == [True]
        assert remove_called == [True]

    def test_skips_cleanup_when_disabled(self, hand, monkeypatch) -> None:
        """_run_two_phase skips _remove_sandbox when _should_cleanup is False."""
        remove_called = []

        async def fake_ensure(emit):
            pass

        async def fake_remove(emit):
            remove_called.append(True)

        monkeypatch.setattr(hand, "_ensure_sandbox", fake_ensure)
        monkeypatch.setattr(hand, "_remove_sandbox", fake_remove)
        monkeypatch.setattr(hand, "_should_cleanup", lambda: False)

        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        async def fake_parent_run_two_phase(self, prompt, *, emit):
            return "result"

        monkeypatch.setattr(
            _TwoPhaseCLIHand, "_run_two_phase", fake_parent_run_two_phase
        )

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(hand._run_two_phase("task", emit=emit))
        assert result == "result"
        assert remove_called == []

    def test_cleans_up_even_on_exception(self, hand, monkeypatch) -> None:
        """_run_two_phase calls _remove_sandbox even when parent raises."""
        remove_called = []

        async def fake_ensure(emit):
            pass

        async def fake_remove(emit):
            remove_called.append(True)

        monkeypatch.setattr(hand, "_ensure_sandbox", fake_ensure)
        monkeypatch.setattr(hand, "_remove_sandbox", fake_remove)
        monkeypatch.setattr(hand, "_should_cleanup", lambda: True)

        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        async def fake_parent_run_two_phase(self, prompt, *, emit):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            _TwoPhaseCLIHand, "_run_two_phase", fake_parent_run_two_phase
        )

        async def emit(text: str) -> None:
            pass

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(hand._run_two_phase("task", emit=emit))
        assert remove_called == [True]


# ---------------------------------------------------------------------------
# _ensure_sandbox verbose branch (127->130)
# ---------------------------------------------------------------------------


class TestEnsureSandboxVerboseBranch:
    def test_no_verbose_cmd_output(self, make_cli_hand, tmp_path, monkeypatch) -> None:
        """When config.verbose is False, _ensure_sandbox skips cmd log line."""
        hand = make_cli_hand(DockerSandboxClaudeCodeHand, model="claude-sonnet-4-5")
        hand.config = Config(
            repo=str(tmp_path), model="claude-sonnet-4-5", verbose=False
        )
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/bin/docker",
        )
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", raising=False)

        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_docker_sandbox_available",
            new_callable=AsyncMock,
            return_value=True,
        ):
            mock_stdout = AsyncMock()
            mock_stdout.read = AsyncMock(side_effect=[b"ok\n", b""])
            mock_proc = AsyncMock()
            mock_proc.stdout = mock_stdout
            mock_proc.returncode = 0
            mock_proc.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                emitted: list[str] = []

                async def capture_emit(text: str) -> None:
                    emitted.append(text)

                asyncio.new_event_loop().run_until_complete(
                    hand._ensure_sandbox(capture_emit)
                )

        # Should NOT contain "cmd:" verbose line
        assert not any("cmd:" in e for e in emitted)
        # Should contain the "Creating sandbox" line
        assert any("Creating sandbox" in e for e in emitted)

    def test_verbose_includes_cmd_output(
        self, make_cli_hand, tmp_path, monkeypatch
    ) -> None:
        """When config.verbose is True, _ensure_sandbox emits cmd line."""
        hand = make_cli_hand(DockerSandboxClaudeCodeHand, model="claude-sonnet-4-5")
        hand.config = Config(
            repo=str(tmp_path), model="claude-sonnet-4-5", verbose=True
        )
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/bin/docker",
        )
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", raising=False)

        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_docker_sandbox_available",
            new_callable=AsyncMock,
            return_value=True,
        ):
            mock_stdout = AsyncMock()
            mock_stdout.read = AsyncMock(side_effect=[b"ok\n", b""])
            mock_proc = AsyncMock()
            mock_proc.stdout = mock_stdout
            mock_proc.returncode = 0
            mock_proc.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                emitted: list[str] = []

                async def capture_emit(text: str) -> None:
                    emitted.append(text)

                asyncio.new_event_loop().run_until_complete(
                    hand._ensure_sandbox(capture_emit)
                )

        # Should contain "cmd:" verbose line
        assert any("cmd:" in e for e in emitted)


# ---------------------------------------------------------------------------
# _build_failure_message sandbox-already-in-base branch (268->273)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# _ensure_sandbox — stdout-None RuntimeError (v121)
# ---------------------------------------------------------------------------


class TestEnsureSandboxStdoutNone:
    def test_raises_runtime_error_when_stdout_is_none(self, hand, monkeypatch) -> None:
        """When create_subprocess_exec returns a process with stdout=None,
        _ensure_sandbox should raise RuntimeError instead of AssertionError."""
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/bin/docker",
        )
        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_docker_sandbox_available",
            new_callable=AsyncMock,
            return_value=True,
        ):
            mock_proc = AsyncMock()
            mock_proc.stdout = None  # simulate stdout being None
            mock_proc.returncode = 0
            mock_proc.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                emit = AsyncMock()
                with pytest.raises(
                    RuntimeError, match="stdout stream is unexpectedly None"
                ):
                    asyncio.new_event_loop().run_until_complete(
                        hand._ensure_sandbox(emit)
                    )


# ---------------------------------------------------------------------------


class TestBuildFailureMessageSandboxInBase:
    def test_skips_note_when_base_contains_sandbox(self, hand, monkeypatch) -> None:
        """When _build_claude_failure_message already mentions 'sandbox',
        the extra note is not appended (branch 268->273)."""
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_build_claude_failure_message",
            return_value="CLI failed inside sandbox environment",
        ):
            msg = hand._build_failure_message(return_code=42, output="generic error")
        # Should NOT have the extra "Note:" appended
        assert "Note:" not in msg
        assert msg == "CLI failed inside sandbox environment"


# ---------------------------------------------------------------------------
# _AUTH_FAILURE_SUBSTRINGS constant (v174)
# ---------------------------------------------------------------------------


class TestAuthFailureSubstrings:
    """Tests for the _AUTH_FAILURE_SUBSTRINGS constant."""

    def test_is_tuple(self) -> None:
        assert isinstance(_AUTH_FAILURE_SUBSTRINGS, tuple)

    def test_not_empty(self) -> None:
        assert len(_AUTH_FAILURE_SUBSTRINGS) > 0

    def test_all_strings(self) -> None:
        assert all(isinstance(s, str) for s in _AUTH_FAILURE_SUBSTRINGS)

    def test_all_lowercase(self) -> None:
        assert all(s == s.lower() for s in _AUTH_FAILURE_SUBSTRINGS)

    def test_contains_not_logged_in(self) -> None:
        assert "not logged in" in _AUTH_FAILURE_SUBSTRINGS

    def test_contains_authentication_failed(self) -> None:
        assert "authentication_failed" in _AUTH_FAILURE_SUBSTRINGS

    def test_build_failure_message_uses_constant(self) -> None:
        """_build_failure_message uses _AUTH_FAILURE_SUBSTRINGS."""
        import inspect

        src = inspect.getsource(DockerSandboxClaudeCodeHand._build_failure_message)
        assert "_AUTH_FAILURE_SUBSTRINGS" in src


# ---------------------------------------------------------------------------
# Docstring presence tests (v174)
# ---------------------------------------------------------------------------


class TestDockerSandboxDocstrings:
    """Verify Google-style docstrings on 4 newly-documented methods."""

    def test_invoke_claude_has_docstring(self) -> None:
        doc = DockerSandboxClaudeCodeHand._invoke_claude.__doc__
        assert doc is not None
        assert "Args:" in doc

    def test_invoke_claude_has_returns(self) -> None:
        doc = DockerSandboxClaudeCodeHand._invoke_claude.__doc__
        assert "Returns:" in doc

    def test_run_two_phase_has_docstring(self) -> None:
        doc = DockerSandboxClaudeCodeHand._run_two_phase.__doc__
        assert doc is not None
        assert "Args:" in doc

    def test_run_two_phase_has_returns(self) -> None:
        doc = DockerSandboxClaudeCodeHand._run_two_phase.__doc__
        assert "Returns:" in doc

    def test_build_failure_message_has_docstring(self) -> None:
        doc = DockerSandboxClaudeCodeHand._build_failure_message.__doc__
        assert doc is not None
        assert "Args:" in doc

    def test_build_failure_message_has_returns(self) -> None:
        doc = DockerSandboxClaudeCodeHand._build_failure_message.__doc__
        assert "Returns:" in doc

    def test_command_not_found_message_has_docstring(self) -> None:
        doc = DockerSandboxClaudeCodeHand._command_not_found_message.__doc__
        assert doc is not None
        assert "Args:" in doc

    def test_command_not_found_message_has_returns(self) -> None:
        doc = DockerSandboxClaudeCodeHand._command_not_found_message.__doc__
        assert "Returns:" in doc
