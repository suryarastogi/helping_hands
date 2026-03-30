"""Devin CLI hand implementation."""

from __future__ import annotations

import os
import shutil

from helping_hands.lib.hands.v1.hand.cli.base import (
    _EMPTY_MODEL_MARKERS,
    _format_cli_failure,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.validation import has_cli_flag

__all__ = ["DevinCLIHand"]


class DevinCLIHand(_TwoPhaseCLIHand):
    """Hand backed by Devin CLI subprocess execution."""

    _BACKEND_NAME = "devincli"
    _CLI_LABEL = "devincli"
    _CLI_DISPLAY_NAME = "Devin CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_DEVIN_CLI_CMD"
    _DEFAULT_CLI_CMD = "devin -p"
    _DEFAULT_MODEL = "claude-opus-4-6"
    _MODEL_ENV_VAR = "HELPING_HANDS_DEVIN_MODEL"
    _NATIVE_CLI_AUTH_ENV_VAR = "HELPING_HANDS_DEVIN_USE_NATIVE_CLI_AUTH"
    _DEFAULT_PERMISSION_MODE = "dangerous"
    _RETRY_ON_NO_CHANGES = True

    def _pr_description_cmd(self) -> list[str] | None:
        """Use Devin CLI to generate PR descriptions and commit messages.

        Returns:
            Command token list when ``devin`` is on ``$PATH``, else ``None``.
        """
        if shutil.which("devin") is not None:
            return ["devin", "-p"]
        return None

    def _inject_prompt_argument(self, cmd: list[str], prompt: str) -> bool:
        """Append ``-- <prompt>`` to the command.

        Devin's ``-p`` is ``--print`` (a boolean flag), not a prompt
        argument.  Prompts are passed as positional args after ``--``.

        Args:
            cmd: Mutable command token list.
            prompt: Prompt text to inject.

        Returns:
            Always ``True`` — prompt is always injected.
        """
        cmd.extend(["--", prompt])
        return True

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        """Ensure bare ``devin`` is expanded to ``devin -p``.

        Args:
            tokens: Parsed command tokens from the env var.

        Returns:
            Command tokens with ``-p`` appended if missing.
        """
        if tokens == ["devin"]:
            return ["devin", "-p"]
        return super()._normalize_base_command(tokens)

    def _native_cli_auth_env_names(self) -> tuple[str, ...]:
        """Return env var names used for native Devin CLI authentication.

        Returns:
            Tuple containing ``"DEVIN_API_KEY"``.
        """
        return ("DEVIN_API_KEY",)

    def _resolve_cli_model(self) -> str:
        """Resolve model with per-backend env var override.

        Checks ``HELPING_HANDS_DEVIN_MODEL`` first, then falls back to the
        config model, preserving provider/model format
        (e.g. ``anthropic/claude-sonnet-4-6``).  Falls back to
        :attr:`_DEFAULT_MODEL` (``claude-opus-4-6``) when unset.

        Returns:
            Resolved model name string.
        """
        env_model = os.environ.get(self._MODEL_ENV_VAR, "").strip()
        if env_model and env_model not in _EMPTY_MODEL_MARKERS:
            return env_model
        model = str(self.config.model).strip()
        if not model or model in _EMPTY_MODEL_MARKERS:
            return self._DEFAULT_MODEL
        return model

    def _describe_auth(self) -> str:
        """Describe the current authentication state for Devin.

        When native CLI auth is enabled, reports that ``DEVIN_API_KEY``
        will be stripped from the subprocess environment.  Otherwise
        reports whether the key is set.

        Returns:
            Human-readable auth summary string.
        """
        if self._use_native_cli_auth():
            return "auth=native-cli (DEVIN_API_KEY stripped)"
        present = self._env_var_status("DEVIN_API_KEY")
        return f"auth=DEVIN_API_KEY ({present})"

    def _permission_mode(self) -> str:
        """Return the Devin ``--permission-mode`` value.

        Reads ``HELPING_HANDS_DEVIN_PERMISSION_MODE`` env var, falling
        back to :attr:`_DEFAULT_PERMISSION_MODE` (``"dangerous"``).

        Returns:
            Permission mode string (``"auto"`` or ``"dangerous"``).
        """
        raw = os.environ.get("HELPING_HANDS_DEVIN_PERMISSION_MODE", "").strip()
        return raw or self._DEFAULT_PERMISSION_MODE

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--permission-mode`` into the Devin command if not present.

        Args:
            cmd: Full command tokens.

        Returns:
            Command tokens with ``--permission-mode`` applied.
        """
        if not cmd or cmd[0] != "devin":
            return cmd
        if has_cli_flag(cmd, "permission-mode"):
            return cmd
        mode = self._permission_mode()
        return [cmd[0], "--permission-mode", mode, *cmd[1:]]

    @staticmethod
    def _build_devin_failure_message(*, return_code: int, output: str) -> str:
        """Build a user-facing error message from Devin CLI failure output.

        Delegates to :func:`_format_cli_failure` with Devin-specific
        parameters for auth detection and remediation guidance.

        Args:
            return_code: Process exit code.
            output: Raw stdout/stderr from the CLI process.

        Returns:
            Descriptive error message string.
        """
        return _format_cli_failure(
            backend_name="Devin CLI",
            return_code=return_code,
            output=output,
            env_var_hint="DEVIN_API_KEY",
            auth_guidance=("Ensure DEVIN_API_KEY is set or run 'devin auth login'."),
        )

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        """Delegate to :meth:`_build_devin_failure_message`.

        Args:
            return_code: Process exit code.
            output: Raw stdout/stderr from the CLI process.

        Returns:
            Descriptive error message string.
        """
        return self._build_devin_failure_message(
            return_code=return_code,
            output=output,
        )

    async def _invoke_devin(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Invoke the Devin CLI with the given prompt.

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
        """Run the backend invocation by delegating to :meth:`_invoke_devin`.

        Args:
            prompt: User prompt to pass to the CLI.
            emit: Streaming emitter callback.

        Returns:
            Raw CLI output string.
        """
        return await self._invoke_devin(prompt, emit=emit)
