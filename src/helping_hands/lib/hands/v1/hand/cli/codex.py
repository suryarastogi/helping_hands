"""Codex CLI hand implementation."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from helping_hands.lib.hands.v1.hand.cli.base import (
    _format_cli_failure,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.validation import has_cli_flag

__all__ = ["CodexCLIHand"]


class CodexCLIHand(_TwoPhaseCLIHand):
    """Hand backed by Codex CLI subprocess execution."""

    _BACKEND_NAME = "codexcli"
    _CLI_LABEL = "codexcli"
    _CLI_DISPLAY_NAME = "Codex CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_CODEX_CLI_CMD"
    _DEFAULT_CLI_CMD = "codex exec"
    _DEFAULT_MODEL = "gpt-5.2"
    _DEFAULT_SANDBOX_MODE = "workspace-write"
    _DEFAULT_SANDBOX_MODE_IN_CONTAINER = "danger-full-access"
    _DEFAULT_SKIP_GIT_REPO_CHECK = "1"
    _CONTAINER_ENABLED_ENV_VAR = "HELPING_HANDS_CODEX_CONTAINER"
    _CONTAINER_IMAGE_ENV_VAR = "HELPING_HANDS_CODEX_CONTAINER_IMAGE"
    _NATIVE_CLI_AUTH_ENV_VAR = "HELPING_HANDS_CODEX_USE_NATIVE_CLI_AUTH"

    def _pr_description_cmd(self) -> list[str] | None:
        """Use Codex CLI to generate PR descriptions and commit messages.

        Returns:
            Command token list when ``codex`` is on ``$PATH``, else ``None``.
        """
        if shutil.which("codex") is not None:
            return ["codex", "exec"]
        return None

    def _native_cli_auth_env_names(self) -> tuple[str, ...]:
        """Return env var names used for native Codex CLI authentication.

        Returns:
            Tuple containing ``"OPENAI_API_KEY"``.
        """
        return ("OPENAI_API_KEY",)

    @staticmethod
    def _build_codex_failure_message(*, return_code: int, output: str) -> str:
        """Build a human-readable failure message from Codex CLI output.

        Delegates to :func:`_format_cli_failure` with Codex-specific
        parameters for auth detection and remediation guidance.

        Args:
            return_code: Process exit code.
            output: Combined stdout/stderr from the Codex CLI process.

        Returns:
            Formatted error message with output tail and optional auth hint.
        """
        return _format_cli_failure(
            backend_name="Codex CLI",
            return_code=return_code,
            output=output,
            env_var_hint="OPENAI_API_KEY",
            extra_tokens=("missing bearer or basic authentication",),
        )

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        """Expand bare ``codex`` to ``codex exec``.

        Args:
            tokens: Parsed command tokens from the env var.

        Returns:
            Command tokens with ``exec`` subcommand appended if missing.
        """
        if tokens[0] == "codex" and len(tokens) == 1:
            return ["codex", "exec"]
        return super()._normalize_base_command(tokens)

    def _apply_codex_exec_sandbox_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--sandbox`` flag into ``codex exec`` if not already present.

        Uses ``HELPING_HANDS_CODEX_SANDBOX_MODE`` env var or auto-detects
        based on whether the process runs inside a Docker container.

        Args:
            cmd: Full command tokens.

        Returns:
            Command tokens with ``--sandbox <mode>`` inserted after ``exec``.
        """
        if len(cmd) < 2 or cmd[0] != "codex" or cmd[1] != "exec":
            return cmd
        if has_cli_flag(cmd, "sandbox"):
            return cmd
        sandbox_mode = os.environ.get("HELPING_HANDS_CODEX_SANDBOX_MODE")
        if sandbox_mode is None:
            sandbox_mode = self._auto_sandbox_mode()
        else:
            sandbox_mode = sandbox_mode.strip() or self._auto_sandbox_mode()
        return [*cmd[:2], "--sandbox", sandbox_mode, *cmd[2:]]

    def _auto_sandbox_mode(self) -> str:
        """Select sandbox mode based on runtime environment.

        Returns:
            ``"danger-full-access"`` inside Docker, ``"workspace-write"`` otherwise.
        """
        if Path("/.dockerenv").exists():
            return self._DEFAULT_SANDBOX_MODE_IN_CONTAINER
        return self._DEFAULT_SANDBOX_MODE

    def _skip_git_repo_check_enabled(self) -> bool:
        """Check whether the ``--skip-git-repo-check`` flag should be added.

        Reads ``HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK`` (default ``"1"``).

        Returns:
            True if the env var holds a truthy value.
        """
        raw = os.environ.get(
            "HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK",
            self._DEFAULT_SKIP_GIT_REPO_CHECK,
        )
        return self._is_truthy(raw)

    def _apply_codex_exec_git_repo_check_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--skip-git-repo-check`` into ``codex exec`` when enabled.

        Args:
            cmd: Full command tokens.

        Returns:
            Command tokens with the flag inserted after ``exec`` if applicable.
        """
        if len(cmd) < 2 or cmd[0] != "codex" or cmd[1] != "exec":
            return cmd
        if any(
            token == "--skip-git-repo-check"
            or token.startswith("--skip-git-repo-check")
            for token in cmd
        ):
            return cmd
        if not self._skip_git_repo_check_enabled():
            return cmd
        return [*cmd[:2], "--skip-git-repo-check", *cmd[2:]]

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        """Apply Codex-specific sandbox and git-repo-check defaults.

        Args:
            cmd: Full command tokens.

        Returns:
            Command tokens with sandbox and git-repo-check flags applied.
        """
        cmd = self._apply_codex_exec_sandbox_defaults(cmd)
        return self._apply_codex_exec_git_repo_check_defaults(cmd)

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        """Delegate to ``_build_codex_failure_message``.

        Args:
            return_code: Process exit code.
            output: Combined stdout/stderr.

        Returns:
            Formatted error message.
        """
        return self._build_codex_failure_message(
            return_code=return_code,
            output=output,
        )

    async def _invoke_codex(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Invoke the Codex CLI with the given prompt.

        Args:
            prompt: Task prompt to send to the CLI.
            emit: Async callback for streaming output chunks.

        Returns:
            Combined CLI output text.
        """
        return await self._invoke_cli(prompt, emit=emit)

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Entry point for the two-phase CLI loop; delegates to ``_invoke_codex``.

        Args:
            prompt: Task prompt to send to the CLI.
            emit: Async callback for streaming output chunks.

        Returns:
            Combined CLI output text.
        """
        return await self._invoke_codex(prompt, emit=emit)
