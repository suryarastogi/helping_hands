"""Gemini CLI hand implementation."""

from __future__ import annotations

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand


class GeminiCLIHand(_TwoPhaseCLIHand):
    """Hand backed by Gemini CLI subprocess execution."""

    _BACKEND_NAME = "geminicli"
    _CLI_LABEL = "geminicli"
    _CLI_DISPLAY_NAME = "Gemini CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_GEMINI_CLI_CMD"
    _DEFAULT_CLI_CMD = "gemini -p"
    _DEFAULT_MODEL = ""
    _DEFAULT_APPEND_ARGS = ("-p",)

    @staticmethod
    def _build_gemini_failure_message(*, return_code: int, output: str) -> str:
        tail = output.strip()[-2000:]
        lower_tail = tail.lower()
        if any(
            token in lower_tail
            for token in (
                "401 unauthorized",
                "gemini_api_key",
                "invalid api key",
                "api key not valid",
                "authentication failed",
            )
        ):
            return (
                "Gemini CLI authentication failed. "
                "Ensure GEMINI_API_KEY is set in this runtime. "
                "If running app mode in Docker, set GEMINI_API_KEY in .env "
                "and recreate server/worker containers.\n"
                f"Output:\n{tail}"
            )
        return f"Gemini CLI failed (exit={return_code}). Output:\n{tail}"

    def _build_subprocess_env(self) -> dict[str, str]:
        env = super()._build_subprocess_env()
        if env.get("GEMINI_API_KEY", "").strip():
            return env
        msg = (
            "Gemini CLI authentication is missing. Set GEMINI_API_KEY in this runtime."
        )
        raise RuntimeError(msg)

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        return self._build_gemini_failure_message(
            return_code=return_code,
            output=output,
        )

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"Gemini CLI command not found: {command!r}. "
            "Set HELPING_HANDS_GEMINI_CLI_CMD to a valid command. "
            "If running app mode in Docker, rebuild worker images so "
            "the gemini binary is installed."
        )

    async def _invoke_gemini(
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
        return await self._invoke_gemini(prompt, emit=emit)
