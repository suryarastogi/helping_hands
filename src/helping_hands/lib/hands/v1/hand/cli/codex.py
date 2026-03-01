"""Codex CLI hand implementation."""

from __future__ import annotations

import os
from pathlib import Path

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand


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

    def _native_cli_auth_env_names(self) -> tuple[str, ...]:
        return ("OPENAI_API_KEY",)

    @staticmethod
    def _build_codex_failure_message(*, return_code: int, output: str) -> str:
        """Build a user-facing error message, detecting 401 auth failures in the output."""
        tail = output.strip()[-2000:]
        lower_tail = tail.lower()
        if (
            "401 unauthorized" in lower_tail
            or "missing bearer or basic authentication" in lower_tail
        ):
            return (
                "Codex CLI authentication failed (401 Unauthorized). "
                "Ensure OPENAI_API_KEY is set in this runtime. "
                "If running app mode in Docker, set OPENAI_API_KEY in .env "
                "and recreate server/worker containers.\n"
                f"Output:\n{tail}"
            )
        return f"Codex CLI failed (exit={return_code}). Output:\n{tail}"

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        if tokens[0] == "codex" and len(tokens) == 1:
            return ["codex", "exec"]
        return super()._normalize_base_command(tokens)

    def _apply_codex_exec_sandbox_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--sandbox`` with runtime-aware mode for ``codex exec`` commands.

        Uses ``workspace-write`` on host and ``danger-full-access`` in containers
        (to avoid landlock failures). Respects ``HELPING_HANDS_CODEX_SANDBOX_MODE``
        override.
        """
        if len(cmd) < 2 or cmd[0] != "codex" or cmd[1] != "exec":
            return cmd
        if any(token == "--sandbox" or token.startswith("--sandbox=") for token in cmd):
            return cmd
        sandbox_mode = os.environ.get("HELPING_HANDS_CODEX_SANDBOX_MODE")
        if sandbox_mode is None:
            sandbox_mode = self._auto_sandbox_mode()
        else:
            sandbox_mode = sandbox_mode.strip() or self._auto_sandbox_mode()
        if not sandbox_mode:
            sandbox_mode = self._auto_sandbox_mode()
        return [*cmd[:2], "--sandbox", sandbox_mode, *cmd[2:]]

    def _auto_sandbox_mode(self) -> str:
        """Return ``danger-full-access`` in Docker, ``workspace-write`` on host."""
        if Path("/.dockerenv").exists():
            return self._DEFAULT_SANDBOX_MODE_IN_CONTAINER
        return self._DEFAULT_SANDBOX_MODE

    def _skip_git_repo_check_enabled(self) -> bool:
        raw = os.environ.get(
            "HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK",
            self._DEFAULT_SKIP_GIT_REPO_CHECK,
        )
        return self._is_truthy(raw)

    def _apply_codex_exec_git_repo_check_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--skip-git-repo-check`` for non-interactive ``codex exec`` runs."""
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
        """Apply Codex-specific defaults: sandbox mode and git-repo-check skip."""
        cmd = self._apply_codex_exec_sandbox_defaults(cmd)
        return self._apply_codex_exec_git_repo_check_defaults(cmd)

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        return self._build_codex_failure_message(
            return_code=return_code,
            output=output,
        )

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"Codex CLI command not found: {command!r}. "
            "Set HELPING_HANDS_CODEX_CLI_CMD to a valid command. "
            "If running app mode in Docker, rebuild worker images so "
            "the codex binary is installed."
        )

    async def _invoke_codex(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Invoke the Codex CLI with *prompt* and return its output."""
        return await self._invoke_cli(prompt, emit=emit)

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_codex(prompt, emit=emit)
