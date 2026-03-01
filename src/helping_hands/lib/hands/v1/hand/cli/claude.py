"""Claude Code CLI hand implementation."""

from __future__ import annotations

import logging
import os
import shutil

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

logger = logging.getLogger(__name__)


class ClaudeCodeHand(_TwoPhaseCLIHand):
    """Hand backed by Claude Code CLI subprocess execution."""

    _BACKEND_NAME = "claudecodecli"
    _CLI_LABEL = "claudecodecli"
    _CLI_DISPLAY_NAME = "Claude Code CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_CLAUDE_CLI_CMD"
    _DEFAULT_CLI_CMD = "claude -p"
    _DEFAULT_MODEL = ""
    _DEFAULT_APPEND_ARGS = ("-p",)
    _CONTAINER_ENABLED_ENV_VAR = "HELPING_HANDS_CLAUDE_CONTAINER"
    _CONTAINER_IMAGE_ENV_VAR = "HELPING_HANDS_CLAUDE_CONTAINER_IMAGE"
    _DEFAULT_SKIP_PERMISSIONS = "1"
    _RETRY_ON_NO_CHANGES = True
    _ROOT_PERMISSION_ERROR = (
        "--dangerously-skip-permissions cannot be used with root/sudo privileges"
    )
    _PERMISSION_PROMPT_MARKERS = (
        "write permissions to this file haven't been granted",
        "approve the write operation",
        "blocked pending your approval",
        "approve this operation",
    )

    def _native_cli_auth_env_names(self) -> tuple[str, ...]:
        """Return Anthropic API key env var for native CLI auth stripping."""
        return ("ANTHROPIC_API_KEY",)

    def _pr_description_cmd(self) -> list[str] | None:
        if shutil.which("claude") is not None:
            return ["claude", "-p", "--output-format", "text"]
        return None

    @staticmethod
    def _build_claude_failure_message(*, return_code: int, output: str) -> str:
        """Build a user-facing error message, detecting auth failures in the output tail."""
        tail = output.strip()[-2000:]
        lower_tail = tail.lower()
        if any(
            token in lower_tail
            for token in (
                "401 unauthorized",
                "unauthorized",
                "authentication failed",
                "invalid api key",
                "anthropic_api_key",
            )
        ):
            return (
                "Claude Code CLI authentication failed. "
                "Ensure ANTHROPIC_API_KEY is set in this runtime. "
                "If running app mode in Docker, set ANTHROPIC_API_KEY in .env "
                "and recreate server/worker containers.\n"
                f"Output:\n{tail}"
            )
        return f"Claude Code CLI failed (exit={return_code}). Output:\n{tail}"

    def _resolve_cli_model(self) -> str:
        """Return the model string for Claude CLI, filtering out non-Anthropic models.

        GPT-family models are silently dropped so Claude uses its own default.
        """
        model = super()._resolve_cli_model()
        if not model:
            return ""
        lowered = model.lower()
        if lowered.startswith("gpt-"):
            return ""
        return model

    def _skip_permissions_enabled(self) -> bool:
        """Check whether ``--dangerously-skip-permissions`` should be injected.

        Returns False when running as root (euid 0) since Claude rejects the
        flag under elevated privileges, or when explicitly disabled via
        ``HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS=0``.
        """
        raw = os.environ.get(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS",
            self._DEFAULT_SKIP_PERMISSIONS,
        )
        if not self._is_truthy(raw):
            return False
        geteuid = getattr(os, "geteuid", None)
        if callable(geteuid):
            try:
                if int(geteuid()) == 0:
                    return False
            except (ValueError, TypeError, OSError):
                logger.debug("geteuid() check failed", exc_info=True)
        return True

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--dangerously-skip-permissions`` for non-root ``claude`` commands."""
        if (
            cmd
            and cmd[0] == "claude"
            and self._skip_permissions_enabled()
            and "--dangerously-skip-permissions" not in cmd
        ):
            return [cmd[0], "--dangerously-skip-permissions", *cmd[1:]]
        return cmd

    def _retry_command_after_failure(
        self,
        cmd: list[str],
        *,
        output: str,
        return_code: int,
    ) -> list[str] | None:
        """Retry without ``--dangerously-skip-permissions`` if Claude rejected it under root."""
        if return_code == 0:
            return None
        if "--dangerously-skip-permissions" not in cmd:
            return None
        lowered = output.lower()
        if self._ROOT_PERMISSION_ERROR.lower() not in lowered:
            return None
        return [token for token in cmd if token != "--dangerously-skip-permissions"]

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        return self._build_claude_failure_message(
            return_code=return_code,
            output=output,
        )

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"Claude Code CLI command not found: {command!r}. "
            "Set HELPING_HANDS_CLAUDE_CLI_CMD to a valid command."
        )

    def _no_change_error_after_retries(
        self,
        *,
        prompt: str,
        combined_output: str,
    ) -> str | None:
        """Return an error message if Claude requested interactive write approval.

        When the combined output contains permission-prompt markers, it means
        Claude could not apply edits in non-interactive mode.
        """
        del prompt
        lowered = combined_output.lower()
        if any(marker in lowered for marker in self._PERMISSION_PROMPT_MARKERS):
            return (
                "Claude Code CLI could not apply edits because write permission "
                "approval was required in non-interactive mode. Ensure the "
                "runtime can run with --dangerously-skip-permissions (non-root), "
                "or use HELPING_HANDS_CLAUDE_CLI_CMD with a fully "
                "non-interactive write-capable setup."
            )
        return None

    def _fallback_command_when_not_found(self, cmd: list[str]) -> list[str] | None:
        """Fall back to ``npx -y @anthropic-ai/claude-code`` when ``claude`` is missing."""
        if not cmd or cmd[0] != "claude":
            return None
        if shutil.which("npx") is None:
            return None
        return ["npx", "-y", "@anthropic-ai/claude-code", *cmd[1:]]

    async def _invoke_claude(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Invoke the Claude Code CLI with *prompt* and return its output."""
        return await self._invoke_cli(prompt, emit=emit)

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_claude(prompt, emit=emit)
