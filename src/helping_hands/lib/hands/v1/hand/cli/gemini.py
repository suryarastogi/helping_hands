"""Gemini CLI hand implementation."""

from __future__ import annotations

import re
import shutil

from helping_hands.lib.hands.v1.hand.cli.base import (
    _DOCKER_ENV_HINT_TEMPLATE,
    _detect_auth_failure,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.validation import has_cli_flag

__all__ = ["GeminiCLIHand"]


class GeminiCLIHand(_TwoPhaseCLIHand):
    """Hand backed by Gemini CLI subprocess execution."""

    _BACKEND_NAME = "geminicli"
    _CLI_LABEL = "geminicli"
    _CLI_DISPLAY_NAME = "Gemini CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_GEMINI_CLI_CMD"
    _DEFAULT_CLI_CMD = "gemini -p"
    _DEFAULT_MODEL = ""
    _DEFAULT_APPEND_ARGS = ("-p",)
    _VERBOSE_CLI_FLAGS = ("--verbose",)
    _DEFAULT_APPROVAL_MODE = "auto_edit"

    def _pr_description_cmd(self) -> list[str] | None:
        """Return the command for generating PR descriptions via Gemini CLI.

        Returns:
            ``["gemini", "-p"]`` if the ``gemini`` binary is on PATH, else None.
        """
        if shutil.which("gemini") is not None:
            return ["gemini", "-p"]
        return None

    def _describe_auth(self) -> str:
        """Describe the current Gemini authentication state.

        Returns:
            Human-readable string indicating whether ``GEMINI_API_KEY`` is set.
        """
        present = self._env_var_status("GEMINI_API_KEY")
        return f"auth=GEMINI_API_KEY ({present})"

    @staticmethod
    def _looks_like_model_not_found(output: str) -> bool:
        """Detect model-not-found errors in Gemini CLI output.

        Args:
            output: Raw CLI output text.

        Returns:
            True if the output contains model-not-found error patterns.
        """
        lowered = output.lower()
        return (
            "modelnotfounderror" in lowered
            or "is no longer available to new users" in lowered
            or ("models/" in lowered and "not found" in lowered)
        )

    @staticmethod
    def _extract_unavailable_model(output: str) -> str:
        """Extract the model name from a model-not-found error message.

        Args:
            output: Raw CLI output text containing a ``models/`` reference.

        Returns:
            The model identifier (e.g. ``"gemini-1.5-pro"``), or empty string.
        """
        match = re.search(r"models/([A-Za-z0-9._-]+)", output)
        if not match:
            return ""
        return match.group(1)

    @staticmethod
    def _strip_model_args(cmd: list[str]) -> list[str] | None:
        """Remove ``--model`` / ``--model=`` flags from the command.

        Used for retry after a model-not-found error so Gemini CLI
        falls back to its default model.

        Args:
            cmd: Full command tokens.

        Returns:
            Command tokens without model flags, or None if no flags were removed.
        """
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
        """Check whether the command already contains ``--approval-mode``.

        Args:
            cmd: Full command tokens.

        Returns:
            True if ``--approval-mode`` or ``--approval-mode=`` is present.
        """
        return has_cli_flag(cmd, "approval-mode")

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--approval-mode auto_edit`` if not already present.

        Args:
            cmd: Full command tokens.

        Returns:
            Command tokens with approval mode inserted after the binary name.
        """
        if not cmd or cmd[0] != "gemini":
            return cmd
        if self._has_approval_mode_flag(cmd):
            return cmd
        return [cmd[0], "--approval-mode", self._DEFAULT_APPROVAL_MODE, *cmd[1:]]

    @staticmethod
    def _build_gemini_failure_message(*, return_code: int, output: str) -> str:
        """Build a human-readable failure message from Gemini CLI output.

        Detects authentication errors, model-not-found errors, and provides
        targeted remediation guidance for each case.

        Args:
            return_code: Process exit code.
            output: Combined stdout/stderr from the Gemini CLI process.

        Returns:
            Formatted error message with output tail and contextual hints.
        """
        is_auth, tail = _detect_auth_failure(output, extra_tokens=("gemini_api_key",))
        if is_auth:
            return (
                "Gemini CLI authentication failed. "
                "Ensure GEMINI_API_KEY is set in this runtime. "
                f"{_DOCKER_ENV_HINT_TEMPLATE.format('GEMINI_API_KEY')}\n"
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
        """Build the subprocess environment, requiring ``GEMINI_API_KEY``.

        Returns:
            Environment dict with ``GEMINI_API_KEY`` present.

        Raises:
            RuntimeError: If ``GEMINI_API_KEY`` is not set or empty.
        """
        env = super()._build_subprocess_env()
        if env.get("GEMINI_API_KEY", "").strip():
            return env
        msg = (
            "Gemini CLI authentication is missing. Set GEMINI_API_KEY in this runtime."
        )
        raise RuntimeError(msg)

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        """Delegate to ``_build_gemini_failure_message``.

        Args:
            return_code: Process exit code.
            output: Combined stdout/stderr.

        Returns:
            Formatted error message.
        """
        return self._build_gemini_failure_message(
            return_code=return_code,
            output=output,
        )

    def _retry_command_after_failure(
        self,
        cmd: list[str],
        *,
        output: str,
        return_code: int,
    ) -> list[str] | None:
        """Retry without ``--model`` if the model was not found.

        Args:
            cmd: Original command tokens.
            output: CLI output from the failed invocation.
            return_code: Process exit code.

        Returns:
            Modified command without model flags, or None if no retry needed.
        """
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
        """Invoke the Gemini CLI with the given prompt.

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
        """Entry point for the two-phase CLI loop; delegates to ``_invoke_gemini``.

        Args:
            prompt: Task prompt to send to the CLI.
            emit: Async callback for streaming output chunks.

        Returns:
            Combined CLI output text.
        """
        return await self._invoke_gemini(prompt, emit=emit)
