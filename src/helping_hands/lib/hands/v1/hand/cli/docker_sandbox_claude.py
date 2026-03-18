"""Claude Code hand running inside a Docker sandbox (microVM).

Uses ``docker sandbox create`` / ``docker sandbox exec`` to run Claude Code
inside an isolated Docker Desktop microVM sandbox.  The workspace directory is
automatically synced between host and sandbox at the same absolute path.

Requires Docker Desktop with the ``docker sandbox`` CLI plugin installed.

See https://docs.docker.com/ai/sandboxes/ for details.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import uuid
from typing import Any

from helping_hands.lib.hands.v1.hand.base import (
    _UUID_HEX_LENGTH,
)
from helping_hands.lib.hands.v1.hand.cli.base import (
    _STREAM_READ_BUFFER_SIZE,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.hands.v1.hand.cli.claude import (
    _OUTPUT_FORMAT_STREAM_JSON,
    ClaudeCodeHand,
    _StreamJsonEmitter,
)

__all__ = ["DockerSandboxClaudeCodeHand"]

_SANDBOX_NAME_MAX_LENGTH = 30
"""Maximum character length for the sanitised repo-name portion of a sandbox name."""

_SANDBOX_UUID_HEX_LENGTH = _UUID_HEX_LENGTH
"""Number of hex characters from a UUID4 appended to sandbox names.

Delegates to :data:`helping_hands.lib.hands.v1.hand.base._UUID_HEX_LENGTH`
so the branch-name and sandbox-name UUID truncation stays consistent.
"""

_AUTH_FAILURE_SUBSTRINGS = ("not logged in", "authentication_failed")
"""Lowercase substrings in CLI output that indicate an authentication failure."""


class DockerSandboxClaudeCodeHand(ClaudeCodeHand):
    """Claude Code running inside a Docker Desktop sandbox (microVM).

    Instead of running ``claude -p`` directly as a subprocess, this hand
    creates a Docker sandbox and executes Claude Code commands within it
    using ``docker sandbox exec``.

    The sandbox provides full microVM isolation while keeping the workspace
    directory synced between host and sandbox at the same absolute path.

    Environment variables:
      - ``HELPING_HANDS_DOCKER_SANDBOX_CLEANUP``:  set to ``0`` to keep the
        sandbox after the run completes (default: ``1`` — auto-remove).
      - ``HELPING_HANDS_DOCKER_SANDBOX_NAME``:  override the auto-generated
        sandbox name.
      - ``HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE``: custom base image template
        to pass to ``docker sandbox create --template``.
    """

    _BACKEND_NAME = "docker-sandbox-claude"
    _CLI_LABEL = "docker-sandbox"
    _CLI_DISPLAY_NAME = "Docker Sandbox Claude Code"

    # Disable the legacy container wrapping — we handle isolation ourselves.
    _CONTAINER_ENABLED_ENV_VAR = ""
    _CONTAINER_IMAGE_ENV_VAR = ""

    def __init__(self, config: Any, repo_index: Any) -> None:
        """Initialise the Docker sandbox Claude Code hand.

        Args:
            config: Hand configuration object.
            repo_index: Repository index with file metadata and root path.
        """
        super().__init__(config, repo_index)
        self._sandbox_name: str | None = None
        self._sandbox_created: bool = False

    # ------------------------------------------------------------------
    # Sandbox name
    # ------------------------------------------------------------------

    def _resolve_sandbox_name(self) -> str:
        """Return a deterministic-ish sandbox name for this hand run."""
        if self._sandbox_name is not None:
            return self._sandbox_name
        override = os.environ.get("HELPING_HANDS_DOCKER_SANDBOX_NAME", "").strip()
        if override:
            self._sandbox_name = override
            return override
        repo_name = self.repo_index.root.name
        safe = re.sub(r"[^a-zA-Z0-9-]", "-", repo_name).strip("-")[
            :_SANDBOX_NAME_MAX_LENGTH
        ]
        self._sandbox_name = f"hh-{safe}-{uuid.uuid4().hex[:_SANDBOX_UUID_HEX_LENGTH]}"
        return self._sandbox_name

    # ------------------------------------------------------------------
    # Sandbox lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    async def _docker_sandbox_available() -> bool:
        """Return True if ``docker sandbox`` subcommand is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "sandbox",
                "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError:
            return False

    async def _ensure_sandbox(self, emit: _TwoPhaseCLIHand._Emitter) -> None:
        """Create the Docker sandbox if it doesn't already exist."""
        if self._sandbox_created:
            return

        if shutil.which("docker") is None:
            raise RuntimeError(
                "Docker CLI not found on PATH.  Docker Desktop with the "
                "sandbox plugin is required for DockerSandboxClaudeCodeHand."
            )

        if not await self._docker_sandbox_available():
            raise RuntimeError(
                "'docker sandbox' command not available.  "
                "Docker Desktop 4.49+ is required for sandbox support.  "
                "Update Docker Desktop or run: docker desktop update\n"
                "See https://docs.docker.com/ai/sandboxes/ for details."
            )

        name = self._resolve_sandbox_name()
        workspace = str(self.repo_index.root.resolve())
        cmd = ["docker", "sandbox", "create", "--name", name]

        template = os.environ.get("HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE", "").strip()
        if template:
            cmd.extend(["--template", template])

        cmd.extend(["claude", workspace])

        await emit(self._label_msg(f"Creating sandbox '{name}'...") + "\n")
        if self.config.verbose:
            await emit(self._label_msg(f"cmd: {' '.join(cmd)}") + "\n")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        # Stream output in real-time so the user can see progress
        # (template pulls, microVM setup, etc.).
        chunks: list[str] = []
        stdout = process.stdout
        if stdout is None:
            raise RuntimeError("subprocess stdout stream is unexpectedly None")
        while True:
            data = await stdout.read(_STREAM_READ_BUFFER_SIZE)
            if not data:
                break
            text = data.decode("utf-8", errors="replace")
            chunks.append(text)
            await emit(self._label_msg(text))
        await process.wait()
        output_text = "".join(chunks)

        if process.returncode != 0:
            raise RuntimeError(
                f"Failed to create Docker sandbox '{name}' "
                f"(exit={process.returncode}):\n{output_text}"
            )

        self._sandbox_created = True
        await emit(self._label_msg(f"Sandbox '{name}' ready.") + "\n")

    async def _remove_sandbox(self, emit: _TwoPhaseCLIHand._Emitter) -> None:
        """Remove the Docker sandbox."""
        if not self._sandbox_created:
            return

        name = self._resolve_sandbox_name()
        await emit(self._label_msg(f"Removing sandbox '{name}'...") + "\n")

        process = await asyncio.create_subprocess_exec(
            "docker",
            "sandbox",
            "stop",
            name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await process.communicate()

        process = await asyncio.create_subprocess_exec(
            "docker",
            "sandbox",
            "rm",
            name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await process.communicate()
        self._sandbox_created = False

    def _should_cleanup(self) -> bool:
        """Return whether the sandbox should be removed after the run.

        Reads ``HELPING_HANDS_DOCKER_SANDBOX_CLEANUP`` from the environment
        (default ``"1"``).  Any truthy value means cleanup is enabled.

        Returns:
            ``True`` if the sandbox should be auto-removed, ``False`` otherwise.
        """
        raw = os.environ.get("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "1")
        return self._is_truthy(raw)

    # ------------------------------------------------------------------
    # Command wrapping
    # ------------------------------------------------------------------

    def _wrap_sandbox_exec(self, cmd: list[str]) -> list[str]:
        """Wrap a command with ``docker sandbox exec``."""
        name = self._resolve_sandbox_name()
        workspace = str(self.repo_index.root.resolve())
        sandbox_cmd = [
            "docker",
            "sandbox",
            "exec",
            "--workdir",
            workspace,
        ]
        # Forward relevant env vars into the sandbox.
        for env_name in self._effective_container_env_names():
            value = os.environ.get(env_name)
            if value:
                sandbox_cmd.extend(["--env", f"{env_name}={value}"])
        sandbox_cmd.append(name)
        sandbox_cmd.extend(cmd)
        return sandbox_cmd

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def _execution_mode(self) -> str:
        """Return the execution mode identifier for this hand.

        Returns:
            The string ``"docker-sandbox"``.
        """
        return "docker-sandbox"

    async def _invoke_claude(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Invoke Claude Code inside the Docker sandbox.

        Builds the raw claude command, wraps it with ``docker sandbox exec``,
        and streams the output through :class:`_StreamJsonEmitter`.

        Args:
            prompt: The task prompt to pass to Claude Code.
            emit: Callback for streaming progress messages.

        Returns:
            The parsed result text from the stream-json output, or the raw
            CLI output if no result event was emitted.
        """
        # Build the raw claude command (no container wrapping since
        # _CONTAINER_ENABLED_ENV_VAR is empty).
        cmd = self._render_command(prompt)
        cmd = self._inject_output_format(cmd, _OUTPUT_FORMAT_STREAM_JSON)
        # Wrap with docker sandbox exec.
        cmd = self._wrap_sandbox_exec(cmd)
        parser = _StreamJsonEmitter(emit, self._CLI_LABEL)
        raw = await self._invoke_cli_with_cmd(cmd, emit=parser)
        await parser.flush()
        return parser.result_text() or raw

    async def _run_two_phase(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Run the two-phase flow inside a Docker sandbox.

        Creates the sandbox before the run and removes it afterwards (unless
        cleanup is disabled via ``HELPING_HANDS_DOCKER_SANDBOX_CLEANUP=0``).

        Args:
            prompt: The task prompt to execute.
            emit: Callback for streaming progress messages.

        Returns:
            The raw output from the two-phase execution.
        """
        await self._ensure_sandbox(emit)
        try:
            return await super()._run_two_phase(prompt, emit=emit)
        finally:
            if self._should_cleanup():
                await self._remove_sandbox(emit)

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        """Build a human-readable error message for sandbox failures.

        Detects authentication failures (OAuth tokens unavailable inside the
        sandbox) and suggests ``ANTHROPIC_API_KEY`` as a workaround.  For
        other failures, delegates to the base Claude failure message and
        appends a sandbox context note if not already mentioned.

        Args:
            return_code: The CLI process exit code.
            output: The raw CLI stderr/stdout output.

        Returns:
            A descriptive error message string.
        """
        lowered = output.lower()
        if any(s in lowered for s in _AUTH_FAILURE_SUBSTRINGS):
            return (
                "Claude Code inside the Docker sandbox is not authenticated.\n"
                "The sandbox cannot access the host macOS Keychain, so OAuth "
                "login tokens are not available.\n"
                "Set ANTHROPIC_API_KEY in your environment:\n"
                "  ANTHROPIC_API_KEY=sk-ant-... uv run helping-hands ... "
                "--backend docker-sandbox-claude"
            )
        base = self._build_claude_failure_message(
            return_code=return_code,
            output=output,
        )
        if "sandbox" not in base.lower():
            base += (
                "\nNote: this command ran inside Docker sandbox "
                f"'{self._resolve_sandbox_name()}'."
            )
        return base

    def _command_not_found_message(self, command: str) -> str:
        """Return the error message when a command is not found inside the sandbox.

        Args:
            command: The command name that was not found.

        Returns:
            A user-facing error message suggesting the sandbox template image
            needs Claude Code installed.
        """
        return (
            f"Command not found inside Docker sandbox: {command!r}. "
            "Ensure Claude Code is installed in the sandbox template image."
        )

    def _fallback_command_when_not_found(self, cmd: list[str]) -> list[str] | None:
        """Return a fallback command when the primary is not found.

        Inside the sandbox the ``npx`` fallback does not apply — the sandbox
        template image is expected to have Claude Code installed.

        Args:
            cmd: The original command argv that was not found.

        Returns:
            Always ``None`` (no fallback).
        """
        return None
