"""Tests for DockerSandboxClaudeCodeHand static/pure helper methods."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
    DockerSandboxClaudeCodeHand,
)
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_hand(tmp_path: Path, model: str = "claude-sonnet-4-5"):
    (tmp_path / "main.py").write_text("")
    config = Config(repo=str(tmp_path), model=model)
    repo_index = RepoIndex.from_path(tmp_path)
    return DockerSandboxClaudeCodeHand(config=config, repo_index=repo_index)


@pytest.fixture()
def hand(tmp_path):
    return _make_hand(tmp_path)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_sandbox_state_initialized(self, hand) -> None:
        assert hand._sandbox_name is None
        assert hand._sandbox_created is False

    def test_backend_name(self, hand) -> None:
        assert hand._BACKEND_NAME == "docker-sandbox-claude"

    def test_container_env_vars_disabled(self, hand) -> None:
        assert hand._CONTAINER_ENABLED_ENV_VAR == ""
        assert hand._CONTAINER_IMAGE_ENV_VAR == ""


# ---------------------------------------------------------------------------
# _resolve_sandbox_name
# ---------------------------------------------------------------------------


class TestResolveSandboxName:
    def test_env_var_override(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "my-sandbox")
        name = hand._resolve_sandbox_name()
        assert name == "my-sandbox"
        assert hand._sandbox_name == "my-sandbox"

    def test_env_var_override_strips_whitespace(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "  trimmed  ")
        assert hand._resolve_sandbox_name() == "trimmed"

    def test_auto_generated_from_repo_name(self, hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", raising=False)
        name = hand._resolve_sandbox_name()
        assert name.startswith("hh-")
        assert len(name) > 4  # hh- + safe name + uuid hex

    def test_caching_returns_same(self, hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", raising=False)
        first = hand._resolve_sandbox_name()
        second = hand._resolve_sandbox_name()
        assert first == second
        assert first is second  # exact same object from cache

    def test_special_chars_sanitized(self, tmp_path, monkeypatch) -> None:
        # Create a repo dir with special chars
        repo_dir = tmp_path / "my repo!@#"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", raising=False)
        config = Config(repo=str(repo_dir), model="claude-sonnet-4-5")
        repo_index = RepoIndex.from_path(repo_dir)
        h = DockerSandboxClaudeCodeHand(config=config, repo_index=repo_index)
        name = h._resolve_sandbox_name()
        # Should only contain alphanumeric and hyphens
        assert name.startswith("hh-")
        # The repo name portion should have special chars replaced
        assert "!" not in name
        assert "@" not in name
        assert "#" not in name


# ---------------------------------------------------------------------------
# _should_cleanup
# ---------------------------------------------------------------------------


class TestShouldCleanup:
    def test_default_truthy(self, hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", raising=False)
        assert hand._should_cleanup() is True

    def test_env_var_zero_is_falsy(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "0")
        assert hand._should_cleanup() is False

    def test_env_var_false_is_falsy(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "false")
        assert hand._should_cleanup() is False

    def test_env_var_one_is_truthy(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "1")
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
    def test_builds_correct_docker_command(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        # Clear env vars that might be forwarded
        for env in hand._effective_container_env_names():
            monkeypatch.delenv(env, raising=False)
        cmd = hand._wrap_sandbox_exec(["claude", "-p", "hello"])
        assert cmd[0] == "docker"
        assert cmd[1] == "sandbox"
        assert cmd[2] == "exec"
        assert "--workdir" in cmd
        assert "test-sb" in cmd
        assert cmd[-3:] == ["claude", "-p", "hello"]

    def test_forwards_env_vars(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        cmd = hand._wrap_sandbox_exec(["claude", "-p", "hello"])
        # Should have --env ANTHROPIC_API_KEY=sk-test-key somewhere
        env_args = []
        for i, arg in enumerate(cmd):
            if arg == "--env" and i + 1 < len(cmd):
                env_args.append(cmd[i + 1])
        anthropic_env = [a for a in env_args if a.startswith("ANTHROPIC_API_KEY=")]
        assert len(anthropic_env) >= 1
        assert anthropic_env[0] == "ANTHROPIC_API_KEY=sk-test-key"

    def test_skips_unset_env_vars(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "test-sb")
        # Ensure ANTHROPIC_API_KEY is not set
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cmd = hand._wrap_sandbox_exec(["claude"])
        env_args = []
        for i, arg in enumerate(cmd):
            if arg == "--env" and i + 1 < len(cmd):
                env_args.append(cmd[i + 1])
        anthropic_env = [a for a in env_args if a.startswith("ANTHROPIC_API_KEY=")]
        assert len(anthropic_env) == 0


# ---------------------------------------------------------------------------
# _build_failure_message
# ---------------------------------------------------------------------------


class TestBuildFailureMessage:
    def test_auth_failure_not_logged_in(self, hand) -> None:
        msg = hand._build_failure_message(return_code=1, output="Error: not logged in")
        assert "not authenticated" in msg.lower() or "ANTHROPIC_API_KEY" in msg

    def test_auth_failure_authentication_failed(self, hand) -> None:
        msg = hand._build_failure_message(return_code=1, output="authentication_failed")
        assert "ANTHROPIC_API_KEY" in msg
        assert "sandbox" in msg.lower() or "Keychain" in msg

    def test_non_auth_delegates_to_claude_base(self, hand) -> None:
        msg = hand._build_failure_message(return_code=1, output="some random error")
        assert "Claude Code CLI failed" in msg or "exit=1" in msg

    def test_appends_sandbox_note_when_missing(self, hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "my-sb")
        msg = hand._build_failure_message(return_code=1, output="some random error")
        assert "Docker sandbox" in msg
        assert "my-sb" in msg

    def test_no_duplicate_sandbox_note(self, hand) -> None:
        # If the base message already mentions sandbox, don't append note
        with patch.object(
            DockerSandboxClaudeCodeHand,
            "_build_claude_failure_message",
            return_value="Error in sandbox environment",
        ):
            msg = hand._build_failure_message(return_code=1, output="some error")
            # Should not have a second "sandbox" mention appended
            count = msg.lower().count("sandbox")
            assert count == 1


# ---------------------------------------------------------------------------
# _command_not_found_message
# ---------------------------------------------------------------------------


class TestCommandNotFoundMessage:
    def test_returns_sandbox_specific_message(self, hand) -> None:
        msg = hand._command_not_found_message("claude")
        assert "Docker sandbox" in msg
        assert "'claude'" in msg
        assert "template" in msg.lower()


# ---------------------------------------------------------------------------
# _fallback_command_when_not_found
# ---------------------------------------------------------------------------


class TestFallbackCommandWhenNotFound:
    def test_returns_none(self, hand) -> None:
        assert hand._fallback_command_when_not_found(["claude", "-p"]) is None


# ---------------------------------------------------------------------------
# _docker_sandbox_available (async)
# ---------------------------------------------------------------------------


class TestDockerSandboxAvailable:
    def test_success_returncode_zero(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = asyncio.run(
                DockerSandboxClaudeCodeHand._docker_sandbox_available()
            )
            assert result is True

    def test_failure_returncode_nonzero(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = asyncio.run(
                DockerSandboxClaudeCodeHand._docker_sandbox_available()
            )
            assert result is False

    def test_file_not_found(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError,
        ):
            result = asyncio.run(
                DockerSandboxClaudeCodeHand._docker_sandbox_available()
            )
            assert result is False


# ---------------------------------------------------------------------------
# _ensure_sandbox
# ---------------------------------------------------------------------------


class TestEnsureSandbox:
    def test_skips_when_already_created(self, hand) -> None:
        hand._sandbox_created = True
        emit = AsyncMock()
        asyncio.run(hand._ensure_sandbox(emit))
        emit.assert_not_awaited()

    def test_docker_not_on_path_raises(self, hand, monkeypatch) -> None:
        hand._sandbox_created = False
        emit = AsyncMock()
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: None,
        )
        with pytest.raises(RuntimeError, match="Docker CLI not found"):
            asyncio.run(hand._ensure_sandbox(emit))

    def test_sandbox_not_available_raises(self, hand, monkeypatch) -> None:
        hand._sandbox_created = False
        emit = AsyncMock()
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/local/bin/docker",
        )

        async def _mock_available() -> bool:
            return False

        with (
            patch.object(
                DockerSandboxClaudeCodeHand,
                "_docker_sandbox_available",
                side_effect=_mock_available,
            ),
            pytest.raises(RuntimeError, match=r"docker sandbox.*not available"),
        ):
            asyncio.run(hand._ensure_sandbox(emit))

    def test_ensure_sandbox_success(self, hand, monkeypatch) -> None:
        hand._sandbox_created = False
        emit = AsyncMock()
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "ok-sb")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", raising=False)
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/local/bin/docker",
        )

        async def _mock_available() -> bool:
            return True

        # Mock the subprocess for sandbox create
        mock_stdout = AsyncMock()
        mock_stdout.read = AsyncMock(side_effect=[b"Creating sandbox...\n", b""])
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_stdout
        mock_proc.wait = AsyncMock()

        with (
            patch.object(
                DockerSandboxClaudeCodeHand,
                "_docker_sandbox_available",
                side_effect=_mock_available,
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
        ):
            asyncio.run(hand._ensure_sandbox(emit))

        assert hand._sandbox_created is True
        assert emit.await_count >= 2  # "Creating sandbox..." + "Sandbox ready."

    def test_ensure_sandbox_create_failure(self, hand, monkeypatch) -> None:
        hand._sandbox_created = False
        emit = AsyncMock()
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "fail-sb")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", raising=False)
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/local/bin/docker",
        )

        async def _mock_available() -> bool:
            return True

        mock_stdout = AsyncMock()
        mock_stdout.read = AsyncMock(side_effect=[b"Error creating\n", b""])
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.stdout = mock_stdout
        mock_proc.wait = AsyncMock()

        with (
            patch.object(
                DockerSandboxClaudeCodeHand,
                "_docker_sandbox_available",
                side_effect=_mock_available,
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            pytest.raises(RuntimeError, match="Failed to create Docker sandbox"),
        ):
            asyncio.run(hand._ensure_sandbox(emit))

        assert hand._sandbox_created is False

    def test_ensure_sandbox_with_template(self, hand, monkeypatch) -> None:
        hand._sandbox_created = False
        emit = AsyncMock()
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "tmpl-sb")
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", "my-image:latest")
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/local/bin/docker",
        )

        async def _mock_available() -> bool:
            return True

        mock_stdout = AsyncMock()
        mock_stdout.read = AsyncMock(side_effect=[b"", b""])
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_stdout
        mock_proc.wait = AsyncMock()

        captured_cmds: list[list[str]] = []

        async def _capture_exec(*args, **kwargs):
            captured_cmds.append(list(args))
            return mock_proc

        with (
            patch.object(
                DockerSandboxClaudeCodeHand,
                "_docker_sandbox_available",
                side_effect=_mock_available,
            ),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_capture_exec,
            ),
        ):
            asyncio.run(hand._ensure_sandbox(emit))

        # Verify --template was included in command
        assert len(captured_cmds) == 1
        cmd_args = captured_cmds[0]
        assert "--template" in cmd_args
        template_idx = cmd_args.index("--template")
        assert cmd_args[template_idx + 1] == "my-image:latest"

    def test_ensure_sandbox_verbose(self, tmp_path, monkeypatch) -> None:
        (tmp_path / "main.py").write_text("")
        config = Config(repo=str(tmp_path), model="claude-sonnet-4-5", verbose=True)
        repo_index = RepoIndex.from_path(tmp_path)
        hand = DockerSandboxClaudeCodeHand(config=config, repo_index=repo_index)
        hand._sandbox_created = False
        emit = AsyncMock()
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "verbose-sb")
        monkeypatch.delenv("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", raising=False)
        monkeypatch.setattr(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.shutil.which",
            lambda cmd: "/usr/local/bin/docker",
        )

        async def _mock_available() -> bool:
            return True

        mock_stdout = AsyncMock()
        mock_stdout.read = AsyncMock(side_effect=[b"", b""])
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_stdout
        mock_proc.wait = AsyncMock()

        with (
            patch.object(
                DockerSandboxClaudeCodeHand,
                "_docker_sandbox_available",
                side_effect=_mock_available,
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
        ):
            asyncio.run(hand._ensure_sandbox(emit))

        # Verbose mode should emit the command
        emitted = [str(call.args[0]) for call in emit.call_args_list]
        cmd_lines = [e for e in emitted if "cmd:" in e]
        assert len(cmd_lines) >= 1


# ---------------------------------------------------------------------------
# _remove_sandbox
# ---------------------------------------------------------------------------


class TestRemoveSandbox:
    def test_skips_when_not_created(self, hand) -> None:
        hand._sandbox_created = False
        emit = AsyncMock()
        asyncio.run(hand._remove_sandbox(emit))
        emit.assert_not_awaited()

    def test_removes_when_created(self, hand, monkeypatch) -> None:
        hand._sandbox_created = True
        monkeypatch.setenv("HELPING_HANDS_DOCKER_SANDBOX_NAME", "rm-sb")
        emit = AsyncMock()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            asyncio.run(hand._remove_sandbox(emit))

        assert hand._sandbox_created is False
        # Should have emitted "Removing sandbox..."
        emitted = [str(call.args[0]) for call in emit.call_args_list]
        removing = [e for e in emitted if "Removing" in e]
        assert len(removing) >= 1
