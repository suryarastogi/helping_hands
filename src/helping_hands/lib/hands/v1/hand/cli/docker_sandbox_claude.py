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

from helping_hands.lib.hands.v1.hand.cli.base import (
    _STREAM_READ_BUFFER_SIZE,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.hands.v1.hand.cli.claude import (
    ClaudeCodeHand,
    _StreamJsonEmitter,
)

__all__ = ["DockerSandboxClaudeCodeHand"]

_SANDBOX_NAME_MAX_LENGTH = 30
"""Maximum character length for the sanitised repo-name portion of a sandbox name."""

_SANDBOX_UUID_HEX_LENGTH = 8
"""Number of hex characters from a UUID4 appended to sandbox names."""


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
            config: Application configuration (``Config`` instance).
            repo_index: Repository index describing the target workspace.
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

        await emit(f"[{self._CLI_LABEL}] Creating sandbox '{name}'...\n")
        if self.config.verbose:
            await emit(f"[{self._CLI_LABEL}] cmd: {' '.join(cmd)}\n")

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
            await emit(f"[{self._CLI_LABEL}] {text}")
        await process.wait()
        output_text = "".join(chunks)

        if process.returncode != 0:
            raise RuntimeError(
                f"Failed to create Docker sandbox '{name}' "
                f"(exit={process.returncode}):\n{output_text}"
            )

        self._sandbox_created = True
        await emit(f"[{self._CLI_LABEL}] Sandbox '{name}' ready.\n")

    async def _remove_sandbox(self, emit: _TwoPhaseCLIHand._Emitter) -> None:
        """Remove the Docker sandbox."""
        if not self._sandbox_created:
            return

        name = self._resolve_sandbox_name()
        await emit(f"[{self._CLI_LABEL}] Removing sandbox '{name}'...\n")

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
        """Whether the sandbox should be removed after the run completes.

        Reads ``HELPING_HANDS_DOCKER_SANDBOX_CLEANUP`` (default ``"1"``).

        Returns:
            ``True`` if the sandbox should be auto-removed.
        """
        raw = os.environ.get("HELPING_HANDS_DOCKER_SANDBOX_CLEANUP", "1")
        return self._is_truthy(raw)

    # ------------------------------------------------------------------
    # Command wrapping
    # ------------------------------------------------------------------

    def _wrap_sandbox_exec(self, cmd: list[str]) -> list[str]:
        """Wrap a command with ``docker sandbox exec``.

        Prepends ``docker sandbox exec --workdir <workspace> <name>`` and
        forwards relevant environment variables into the sandbox.

        Args:
            cmd: The command and arguments to execute inside the sandbox.

        Returns:
            A new command list prefixed with the sandbox exec invocation.
        """
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
        # Build the raw claude command (no container wrapping since
        # _CONTAINER_ENABLED_ENV_VAR is empty).
        cmd = self._render_command(prompt)
        cmd = self._inject_output_format(cmd, "stream-json")
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
        await self._ensure_sandbox(emit)
        try:
            return await super()._run_two_phase(prompt, emit=emit)
        finally:
            if self._should_cleanup():
                await self._remove_sandbox(emit)

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        """Build a user-facing error message for a failed sandbox run.

        Detects authentication failures and suggests ``ANTHROPIC_API_KEY``.
        Appends a sandbox-context note when the base message does not
        already mention the sandbox.

        Args:
            return_code: Process exit code from the sandbox command.
            output: Combined stdout/stderr captured from the process.

        Returns:
            A descriptive error message string.
        """
        lowered = output.lower()
        if "not logged in" in lowered or "authentication_failed" in lowered:
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
        """Return an error message when a command is missing inside the sandbox.

        Args:
            command: The command that was not found.

        Returns:
            A message advising the user to install the command in the
            sandbox template image.
        """
        return (
            f"Command not found inside Docker sandbox: {command!r}. "
            "Ensure Claude Code is installed in the sandbox template image."
        )

    def _fallback_command_when_not_found(self, cmd: list[str]) -> list[str] | None:
        """Return a fallback command when the primary is not found.

        Inside a Docker sandbox, the ``npx`` fallback does not apply —
        the sandbox template should have Claude Code pre-installed.

        Args:
            cmd: The original command that was not found.

        Returns:
            Always ``None`` (no fallback available in sandbox mode).
        """
        return None
