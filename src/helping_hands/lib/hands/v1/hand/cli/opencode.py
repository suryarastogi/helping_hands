"""OpenCode CLI hand implementation."""

from __future__ import annotations

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

_FAILURE_OUTPUT_TAIL_LENGTH = 2000
"""Number of trailing characters kept from CLI output in failure messages."""


class OpenCodeCLIHand(_TwoPhaseCLIHand):
    """Hand backed by OpenCode CLI subprocess execution."""

    _BACKEND_NAME = "opencodecli"
    _CLI_LABEL = "opencodecli"
    _CLI_DISPLAY_NAME = "OpenCode CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_OPENCODE_CLI_CMD"
    _DEFAULT_CLI_CMD = "opencode run"
    _DEFAULT_MODEL = ""

    def _resolve_cli_model(self) -> str:
        """Preserve provider/model format (e.g. anthropic/claude-sonnet-4-6)."""
        model = str(self.config.model).strip()
        if not model or model in ("default", "None"):
            return self._DEFAULT_MODEL
        return model

    @staticmethod
    def _build_opencode_failure_message(*, return_code: int, output: str) -> str:
        tail = output.strip()[-_FAILURE_OUTPUT_TAIL_LENGTH:]
        lower_tail = tail.lower()
        if any(
            token in lower_tail
            for token in (
                "401 unauthorized",
                "authentication failed",
                "invalid api key",
                "api key not valid",
                "unauthorized",
            )
        ):
            return (
                "OpenCode CLI authentication failed. "
                "Ensure your provider API key is set or run 'opencode auth login'. "
                "If running app mode in Docker, set the appropriate API key in .env "
                "and recreate server/worker containers.\n"
                f"Output:\n{tail}"
            )
        return f"OpenCode CLI failed (exit={return_code}). Output:\n{tail}"

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        return self._build_opencode_failure_message(
            return_code=return_code,
            output=output,
        )

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"OpenCode CLI command not found: {command!r}. "
            "Set HELPING_HANDS_OPENCODE_CLI_CMD to a valid command. "
            "If running app mode in Docker, rebuild worker images so "
            "the opencode binary is installed."
        )

    async def _invoke_opencode(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_cli(prompt, emit=emit)

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_opencode(prompt, emit=emit)
