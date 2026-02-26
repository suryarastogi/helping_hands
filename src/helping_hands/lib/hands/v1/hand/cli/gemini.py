"""Gemini CLI hand implementation."""

from __future__ import annotations

import re

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
    # Gemini non-interactive calls can be quiet for several minutes before
    # first token/output, so use a safer backend-specific idle timeout.
    _DEFAULT_IDLE_TIMEOUT_SECONDS = 900.0
    _DEFAULT_APPROVAL_MODE = "auto_edit"

    @staticmethod
    def _looks_like_model_not_found(output: str) -> bool:
        lowered = output.lower()
        return (
            "modelnotfounderror" in lowered
            or "is no longer available to new users" in lowered
            or ("models/" in lowered and "not found" in lowered)
        )

    @staticmethod
    def _extract_unavailable_model(output: str) -> str:
        match = re.search(r"models/([A-Za-z0-9._-]+)", output)
        if not match:
            return ""
        return match.group(1)

    @staticmethod
    def _strip_model_args(cmd: list[str]) -> list[str] | None:
        cleaned: list[str] = []
        removed = False
        skip_next = False
        for index, token in enumerate(cmd):
            if skip_next:
                skip_next = False
                continue
            if token == "--model":
                removed = True
                if index + 1 < len(cmd):
                    skip_next = True
                continue
            if token.startswith("--model="):
                removed = True
                continue
            cleaned.append(token)
        if not removed:
            return None
        return cleaned

    @staticmethod
    def _has_approval_mode_flag(cmd: list[str]) -> bool:
        return any(
            token == "--approval-mode" or token.startswith("--approval-mode=")
            for token in cmd
        )

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        if not cmd or cmd[0] != "gemini":
            return cmd
        if self._has_approval_mode_flag(cmd):
            return cmd
        return [cmd[0], "--approval-mode", self._DEFAULT_APPROVAL_MODE, *cmd[1:]]

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
        if GeminiCLIHand._looks_like_model_not_found(tail):
            model = GeminiCLIHand._extract_unavailable_model(tail)
            model_hint = f"Requested model {model!r}. " if model else ""
            return (
                "Gemini CLI model is unavailable. "
                f"{model_hint}"
                "Use a currently available Gemini model, or omit --model to let "
                "Gemini CLI choose its default. "
                "If HELPING_HANDS_MODEL is set, update or unset it.\n"
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

    def _retry_command_after_failure(
        self,
        cmd: list[str],
        *,
        output: str,
        return_code: int,
    ) -> list[str] | None:
        if return_code == 0:
            return None
        if not self._looks_like_model_not_found(output):
            return None
        return self._strip_model_args(cmd)

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
