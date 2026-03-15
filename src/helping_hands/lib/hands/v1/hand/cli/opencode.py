"""OpenCode CLI hand implementation."""

from __future__ import annotations

from helping_hands.lib.hands.v1.hand.cli.base import (
    _DOCKER_ENV_HINT_TEMPLATE,
    _detect_auth_failure,
    _TwoPhaseCLIHand,
)

__all__ = ["OpenCodeCLIHand"]


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
        """Build a user-facing error message from OpenCode CLI failure output.

        Checks the tail of the output for authentication error tokens
        and returns a specialised auth-failure message when detected.

        Args:
            return_code: Process exit code.
            output: Raw stdout/stderr from the CLI process.

        Returns:
            Descriptive error message string.
        """
        is_auth, tail = _detect_auth_failure(output)
        if is_auth:
            return (
                "OpenCode CLI authentication failed. "
                "Ensure your provider API key is set or run 'opencode auth login'. "
                f"{_DOCKER_ENV_HINT_TEMPLATE.format('the appropriate API key')}\n"
                f"Output:\n{tail}"
            )
        return f"OpenCode CLI failed (exit={return_code}). Output:\n{tail}"

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        """Delegate to :meth:`_build_opencode_failure_message`.

        Args:
            return_code: Process exit code.
            output: Raw stdout/stderr from the CLI process.

        Returns:
            Descriptive error message string.
        """
        return self._build_opencode_failure_message(
            return_code=return_code,
            output=output,
        )

    async def _invoke_opencode(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Invoke the OpenCode CLI with the given prompt.

        Args:
            prompt: User prompt to pass to the CLI.
            emit: Streaming emitter callback.

        Returns:
            Raw CLI output string.
        """
        return await self._invoke_cli(prompt, emit=emit)

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Run the backend invocation by delegating to :meth:`_invoke_opencode`.

        Args:
            prompt: User prompt to pass to the CLI.
            emit: Streaming emitter callback.

        Returns:
            Raw CLI output string.
        """
        return await self._invoke_opencode(prompt, emit=emit)
