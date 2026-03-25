"""Shared two-phase subprocess base for CLI-backed hands."""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import AsyncIterator
from contextlib import suppress
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from github import GithubException

from helping_hands.lib.config import _TRUTHY_VALUES
from helping_hands.lib.github import (
    _CI_RUN_FAILURE_CONCLUSIONS,
    CI_CONCLUSIONS_IN_PROGRESS,
    CIConclusion,
)
from helping_hands.lib.hands.v1.hand.base import (
    _FILE_LIST_PREVIEW_LIMIT,
    _GIT_READ_TIMEOUT_S,
    _META_BACKEND,
    _META_CI_FIX_ATTEMPTS,
    _META_CI_FIX_ERROR,
    _META_CI_FIX_STATUS,
    _META_MODEL,
    _META_PR_BRANCH,
    _META_PR_COMMIT,
    _META_PR_ERROR,
    _META_PR_NUMBER,
    _META_PR_STATUS,
    _META_PR_URL,
    _PR_STATUS_CREATED,
    _PR_STATUS_DISABLED,
    _PR_STATUS_NO_CHANGES,
    _PR_STATUS_UPDATED,
    _PR_STATUSES_WITH_URL,
    Hand,
    HandResponse,
)
from helping_hands.lib.validation import has_cli_flag, require_non_empty_string

logger = logging.getLogger(__name__)

__all__ = [
    "_APPLY_CHANGES_TRUNCATION_LIMIT",
    "_AUTH_ERROR_TOKENS",
    "_CI_FIX_TEMPLATES",
    "_CI_POLL_INTERVAL_S",
    "_DOCKER_ENV_HINT_TEMPLATE",
    "_DOCKER_REBUILD_HINT_TEMPLATE",
    "_EMPTY_MODEL_MARKERS",
    "_FAILURE_OUTPUT_TAIL_LENGTH",
    "_GIT_REF_DISPLAY_LENGTH",
    "_HOOK_ERROR_TRUNCATION_LIMIT",
    "_PROCESS_TERMINATE_TIMEOUT_S",
    "_PR_DESCRIPTION_TIMEOUT_S",
    "_PR_STATUS_TEMPLATES",
    "_STREAM_READ_BUFFER_SIZE",
    "CIFixStatus",
    "_TwoPhaseCLIHand",
    "_detect_auth_failure",
    "_format_cli_failure",
    "_truncate_with_ellipsis",
]

# --- Module-level constants ---------------------------------------------------

_PROCESS_TERMINATE_TIMEOUT_S = 5
"""Seconds to wait for a subprocess to exit after SIGTERM before SIGKILL."""

_CI_POLL_INTERVAL_S = 30.0
"""Seconds between CI check polling attempts."""

_PR_DESCRIPTION_TIMEOUT_S = 300
"""Seconds timeout for the subprocess used to generate PR descriptions."""

_APPLY_CHANGES_TRUNCATION_LIMIT = 2000
"""Character limit for task output in the apply-changes enforcement prompt."""

_STREAM_READ_BUFFER_SIZE = 1024
"""Bytes to read at a time from subprocess stdout during streaming."""

_HOOK_ERROR_TRUNCATION_LIMIT = 3000
"""Character limit for hook error output in the hook-fix prompt."""

_GIT_REF_DISPLAY_LENGTH = 8
"""Number of characters to show when displaying a git commit ref."""

_FAILURE_OUTPUT_TAIL_LENGTH = 2000
"""Number of trailing characters kept from CLI output in failure messages."""

_EMPTY_MODEL_MARKERS: tuple[str, ...] = ("default", "None")
"""Model values treated as *empty* — resolved to ``_DEFAULT_MODEL`` instead.

Shared by :meth:`_TwoPhaseCLIHand._resolve_cli_model` and overrides in
``opencode.py``.
"""

_AUTH_ERROR_TOKENS: tuple[str, ...] = (
    "401 unauthorized",
    "authentication failed",
    "invalid api key",
    "api key not valid",
    "unauthorized",
)
"""Lowercase substrings in CLI output that indicate an authentication failure.

Shared across all CLI hand implementations. Individual backends may check
additional backend-specific tokens alongside these common ones.
"""

_DOCKER_ENV_HINT_TEMPLATE = (
    "If running app mode in Docker, set {} in .env "
    "and recreate server/worker containers."
)
"""Template for the Docker env-var remediation hint in auth failure messages.

Use with :meth:`str.format` passing the environment variable name, e.g.
``_DOCKER_ENV_HINT_TEMPLATE.format("ANTHROPIC_API_KEY")``.
"""

_DOCKER_REBUILD_HINT_TEMPLATE = (
    "If running app mode in Docker, rebuild worker images so "
    "the {} binary is installed."
)
"""Template for the Docker rebuild hint in command-not-found messages.

Use with :meth:`str.format` passing the binary name, e.g.
``_DOCKER_REBUILD_HINT_TEMPLATE.format("gemini")``.
"""


# --- CI fix status enum -------------------------------------------------------


class CIFixStatus(StrEnum):
    """State-machine values for the CI-fix loop in :meth:`_ci_fix_loop`.

    Being a :class:`StrEnum`, each member compares equal to its string value
    (e.g. ``CIFixStatus.SUCCESS == "success"``), so serialised metadata dicts
    remain human-readable and backward-compatible.
    """

    CHECKING = "checking"
    """CI checks are being polled (initial state)."""

    SUCCESS = "success"
    """All CI checks passed; no fix was needed."""

    NO_CHECKS = "no_checks"
    """No CI check runs were found for the ref."""

    PENDING_TIMEOUT = "pending_timeout"
    """CI checks were still pending after the maximum wait time."""

    INTERRUPTED = "interrupted"
    """The hand was interrupted (cancelled) during the CI fix loop."""

    EXHAUSTED = "exhausted"
    """All retry attempts were used without achieving CI success."""

    ERROR = "error"
    """An unexpected error occurred during the CI fix loop."""


# --- Status message dispatch tables -------------------------------------------

_PR_STATUS_TEMPLATES: dict[str, str] = {
    _PR_STATUS_CREATED: "PR created: {pr_url}",
    _PR_STATUS_UPDATED: "PR updated: {pr_url}",
    _PR_STATUS_DISABLED: "PR disabled (--no-pr).",
    _PR_STATUS_NO_CHANGES: "PR skipped: no file changes detected.",
    "interrupted": "Interrupted.",
}
"""Maps PR status values to message templates.

Templates may contain ``{pr_url}`` which is resolved from metadata at
format time.  Statuses not in this table fall through to a generic
``"PR status: {status}"`` message.
"""

_CI_FIX_TEMPLATES: dict[str, str] = {
    CIFixStatus.SUCCESS: "CI checks passed.",
    CIFixStatus.EXHAUSTED: "CI fix failed after {attempts} attempt(s).",
    CIFixStatus.PENDING_TIMEOUT: "CI checks still pending after max wait time.",
    CIFixStatus.ERROR: "CI fix error: {error}",
}
"""Maps CI fix status values to message templates.

Templates may contain ``{attempts}`` or ``{error}`` which are resolved
from metadata at format time.  Statuses not in this table return ``None``.
"""


def _truncate_with_ellipsis(text: str, limit: int) -> str:
    """Truncate *text* to *limit* characters, appending ``"..."`` if needed.

    Args:
        text: The string to truncate.
        limit: Maximum allowed length (must be > 3).

    Returns:
        The original string if within *limit*, otherwise the first
        ``limit - 3`` characters followed by ``"..."``.
    """
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _detect_auth_failure(
    output: str,
    extra_tokens: tuple[str, ...] = (),
) -> tuple[bool, str]:
    """Check CLI output tail for authentication error tokens.

    Extracts the trailing :data:`_FAILURE_OUTPUT_TAIL_LENGTH` characters,
    lowercases them, and checks for any of :data:`_AUTH_ERROR_TOKENS`
    plus *extra_tokens*.

    Args:
        output: Raw CLI stdout/stderr text.
        extra_tokens: Additional lowercase substrings to check alongside
            the shared :data:`_AUTH_ERROR_TOKENS`.

    Returns:
        ``(is_auth_failure, tail)`` where *tail* is the extracted trailing
        portion of *output* and *is_auth_failure* is ``True`` when any
        token matched.
    """
    tail = output.strip()[-_FAILURE_OUTPUT_TAIL_LENGTH:]
    lower_tail = tail.lower()
    is_auth = any(token in lower_tail for token in (*_AUTH_ERROR_TOKENS, *extra_tokens))
    return is_auth, tail


def _format_cli_failure(
    *,
    backend_name: str,
    return_code: int,
    output: str,
    env_var_hint: str,
    auth_guidance: str | None = None,
    extra_tokens: tuple[str, ...] = (),
) -> str:
    """Format a CLI failure message, detecting auth failures.

    Checks the output for authentication error tokens via
    :func:`_detect_auth_failure` and returns a targeted auth-failure message
    when detected, otherwise returns a generic failure message with the
    process exit code.

    Args:
        backend_name: Display name of the CLI backend (e.g. ``"Codex CLI"``).
        return_code: Process exit code.
        output: Combined stdout/stderr from the CLI process.
        env_var_hint: Environment variable name shown in the remediation hint
            and passed to :data:`_DOCKER_ENV_HINT_TEMPLATE`.
        auth_guidance: Custom auth remediation text.  Defaults to
            ``"Ensure {env_var_hint} is set in this runtime."``.
        extra_tokens: Additional auth error tokens passed to
            :func:`_detect_auth_failure`.

    Returns:
        Formatted error message string.
    """
    is_auth, tail = _detect_auth_failure(output, extra_tokens=extra_tokens)
    if is_auth:
        guidance = auth_guidance or f"Ensure {env_var_hint} is set in this runtime."
        return (
            f"{backend_name} authentication failed. "
            f"{guidance} "
            f"{_DOCKER_ENV_HINT_TEMPLATE.format(env_var_hint)}\n"
            f"Output:\n{tail}"
        )
    return f"{backend_name} failed (exit={return_code}). Output:\n{tail}"


class _TwoPhaseCLIHand(Hand):
    """Shared two-phase subprocess hand logic for CLI-driven backends."""

    _BACKEND_NAME = "external-cli"
    _CLI_LABEL = "external-cli"
    _CLI_DISPLAY_NAME = "External CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_CLI_CMD"
    _DEFAULT_CLI_CMD = ""
    _DEFAULT_MODEL = ""
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ()
    _CONTAINER_ENABLED_ENV_VAR = ""
    _CONTAINER_IMAGE_ENV_VAR = ""
    _NATIVE_CLI_AUTH_ENV_VAR = ""
    _RETRY_ON_NO_CHANGES = False
    _VERBOSE_CLI_FLAGS: tuple[str, ...] = ()
    _SUMMARY_CHAR_LIMIT = 6000
    _DEFAULT_IO_POLL_SECONDS = 2.0
    _DEFAULT_HEARTBEAT_SECONDS = 20.0
    _DEFAULT_HEARTBEAT_SECONDS_VERBOSE = 5.0
    _DEFAULT_IDLE_TIMEOUT_SECONDS = 900.0

    class _Emitter(Protocol):
        async def __call__(self, chunk: str) -> None: ...

    def __init__(self, config: Any, repo_index: Any) -> None:
        """Initialize the two-phase CLI hand.

        Args:
            config: Application configuration (model, verbose, tools, etc.).
            repo_index: Repository index providing the file tree and root path.
        """
        super().__init__(config, repo_index)
        self._active_process: asyncio.subprocess.Process | None = None
        self._skill_catalog_dir: Path | None = None
        self._baseline_head: str = ""

    def _label_msg(self, msg: str) -> str:
        """Prefix *msg* with the CLI backend label.

        Returns:
            A string of the form ``[<label>] <msg>``.
        """
        return f"[{self._CLI_LABEL}] {msg}"

    @staticmethod
    def _truncate_summary(text: str, *, limit: int) -> str:
        """Truncate text to *limit* characters with a ``[truncated]`` marker.

        Args:
            text: The text to truncate (leading/trailing whitespace stripped).
            limit: Maximum character count; must be a positive integer.

        Returns:
            The stripped text if within *limit*, otherwise the first *limit*
            characters followed by ``...[truncated]``.

        Raises:
            ValueError: If *limit* is less than 1.
        """
        if limit < 1:
            raise ValueError("limit must be a positive integer")
        clean = text.strip()
        if len(clean) <= limit:
            return clean
        return f"{clean[:limit]}\n...[truncated]"

    @staticmethod
    def _is_truthy(value: str | None) -> bool:
        """Check whether a string value is truthy for CLI env var parsing.

        Args:
            value: Raw string value, or None.

        Returns:
            True if the lowercased, stripped value is in ``_TRUTHY_VALUES``.
        """
        if value is None:
            return False
        return value.strip().lower() in _TRUTHY_VALUES

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        """Append default args when the command is a bare binary name.

        Args:
            tokens: Shell-split command tokens.

        Returns:
            The tokens list, with ``_DEFAULT_APPEND_ARGS`` appended when
            only a single token (the binary) was provided.
        """
        if len(tokens) == 1 and self._DEFAULT_APPEND_ARGS:
            return [*tokens, *self._DEFAULT_APPEND_ARGS]
        return tokens

    def _base_command(self) -> list[str]:
        """Resolve the CLI command from the environment variable or default.

        Reads ``self._COMMAND_ENV_VAR`` (falling back to
        ``self._DEFAULT_CLI_CMD``), shell-splits the value, and normalizes.

        Returns:
            A list of command tokens ready for subprocess execution.

        Raises:
            RuntimeError: If the value is an invalid shell expression or empty.
        """
        raw = os.environ.get(self._COMMAND_ENV_VAR, self._DEFAULT_CLI_CMD)
        try:
            tokens = shlex.split(raw)
        except ValueError as exc:
            msg = f"{self._COMMAND_ENV_VAR} contains an invalid shell expression: {exc}"
            raise RuntimeError(msg) from exc
        if not tokens:
            msg = f"{self._COMMAND_ENV_VAR} resolved to an empty command."
            raise RuntimeError(msg)
        return self._normalize_base_command(tokens)

    def _resolve_cli_model(self) -> str:
        """Resolve the model name for the CLI backend.

        Strips the provider prefix (e.g. ``anthropic/claude-sonnet-4-5``
        becomes ``claude-sonnet-4-5``) and falls back to ``_DEFAULT_MODEL``
        for blank, ``"default"``, or ``"None"`` values.

        Returns:
            The resolved model name string, or ``_DEFAULT_MODEL``.
        """
        model = str(self.config.model).strip()
        if not model or model in _EMPTY_MODEL_MARKERS:
            return self._DEFAULT_MODEL
        if "/" in model:
            _, _, provider_model = model.partition("/")
            if provider_model:
                return provider_model
        return model

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        """Apply backend-specific default flags to the command.

        Subclasses override this to inject default arguments (e.g. sandbox
        mode, output format).  The base implementation is a no-op.

        Args:
            cmd: The current command token list.

        Returns:
            The command list, possibly with additional flags.
        """
        return cmd

    def _apply_verbose_flags(self, cmd: list[str]) -> list[str]:
        """Inject verbose CLI flags before the prompt argument.

        Flags are inserted right after the binary name (index 1) so they
        appear before ``-p``/``--prompt`` and the prompt text itself.
        Some CLIs ignore flags that appear after the prompt argument.
        """
        if not self.config.verbose or not self._VERBOSE_CLI_FLAGS or not cmd:
            return cmd
        for flag in self._VERBOSE_CLI_FLAGS:
            if flag not in cmd:
                cmd = [cmd[0], flag, *cmd[1:]]
        return cmd

    @staticmethod
    def _inject_prompt_argument(cmd: list[str], prompt: str) -> bool:
        """Insert/replace prompt values for explicit prompt flags.

        Returns True when the prompt was wired into an explicit prompt flag.
        """
        for idx, token in enumerate(cmd):
            if token in {"-p", "--prompt"}:
                next_idx = idx + 1
                if next_idx < len(cmd) and not cmd[next_idx].startswith("-"):
                    cmd[next_idx] = prompt
                else:
                    cmd.insert(next_idx, prompt)
                return True
            if token.startswith("--prompt="):
                cmd[idx] = f"--prompt={prompt}"
                return True
            if token.startswith("-p="):
                cmd[idx] = f"-p={prompt}"
                return True
        return False

    def _render_command(self, prompt: str) -> list[str]:
        """Build the full CLI command with prompt, model, and container wrapping.

        Substitutes ``{prompt}``, ``{repo}``, and ``{model}`` placeholders in
        the base command, appends ``--model`` when needed, injects prompt
        arguments, applies backend defaults and verbose flags, and wraps in
        a Docker command when container execution is enabled.

        Args:
            prompt: The prompt text to inject into the command.

        Returns:
            A ready-to-execute command token list.
        """
        resolved_model = self._resolve_cli_model()
        placeholders = {
            "{prompt}": prompt,
            "{repo}": str(self.repo_index.root.resolve()),
            "{model}": resolved_model,
        }
        rendered: list[str] = []
        has_prompt_placeholder = False
        used_model_placeholder = False
        for token in self._base_command():
            updated = token
            for key, value in placeholders.items():
                if key in updated:
                    updated = updated.replace(key, value)
                    if key == "{prompt}":
                        has_prompt_placeholder = True
                    if key == "{model}":
                        used_model_placeholder = True
            rendered.append(updated)

        has_explicit_model_flag = has_cli_flag(rendered, "model")
        if (
            resolved_model
            and not used_model_placeholder
            and not has_explicit_model_flag
        ):
            rendered.extend(["--model", resolved_model])

        if not has_prompt_placeholder and not self._inject_prompt_argument(
            rendered, prompt
        ):
            rendered.append(prompt)
        rendered = self._apply_backend_defaults(rendered)
        rendered = self._apply_verbose_flags(rendered)
        return self._wrap_container_if_enabled(rendered)

    def _container_enabled(self) -> bool:
        """Check whether container-based execution is enabled.

        Returns:
            True if the backend's container env var is set to a truthy value.
        """
        if not self._CONTAINER_ENABLED_ENV_VAR:
            return False
        raw = os.environ.get(self._CONTAINER_ENABLED_ENV_VAR, "")
        if raw == "":
            return False
        return self._is_truthy(raw)

    def _container_image(self) -> str:
        """Return the Docker image name for container execution.

        Returns:
            The Docker image string from the environment.

        Raises:
            RuntimeError: If the backend has no container image env var
                configured, or if the env var is empty.
        """
        if not self._CONTAINER_IMAGE_ENV_VAR:
            msg = "Container execution is not configured for this backend."
            raise RuntimeError(msg)
        image = os.environ.get(self._CONTAINER_IMAGE_ENV_VAR, "").strip()
        if not image:
            msg = (
                f"{self._CONTAINER_IMAGE_ENV_VAR} must be set when "
                f"{self._CONTAINER_ENABLED_ENV_VAR} is enabled."
            )
            raise RuntimeError(msg)
        return image

    def _container_env_names(self) -> tuple[str, ...]:
        """Return env var names to forward into the Docker container.

        Returns:
            A tuple of environment variable names (API keys, model config).
        """
        return (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "HELPING_HANDS_MODEL",
        )

    def _use_native_cli_auth(self) -> bool:
        """Check whether the backend should use its native CLI auth session.

        Per-backend env var (e.g. ``HELPING_HANDS_CODEX_USE_NATIVE_CLI_AUTH``)
        takes precedence when set; otherwise falls back to the global
        ``config.use_native_cli_auth``.

        Returns:
            True if native CLI auth should be used for this backend.
        """
        env_var = self._NATIVE_CLI_AUTH_ENV_VAR
        if env_var:
            raw = os.environ.get(env_var, "").strip().lower()
            if raw:
                return raw in ("1", "true", "yes", "on")
        return self.config.use_native_cli_auth

    def _native_cli_auth_env_names(self) -> tuple[str, ...]:
        """Return env var names that carry API keys for this CLI backend.

        Subclasses override this to declare which env vars should be
        stripped when ``_use_native_cli_auth`` is True.

        Returns:
            A tuple of environment variable names (empty by default).
        """
        return ()

    @staticmethod
    def _env_var_status(name: str) -> str:
        """Return ``"set"`` or ``"not set"`` based on whether *name* is populated.

        Args:
            name: Environment variable name to check.

        Returns:
            ``"set"`` if the variable exists and contains non-whitespace
            characters, ``"not set"`` otherwise.
        """
        return "set" if os.environ.get(name, "").strip() else "not set"

    def _describe_auth(self) -> str:
        """Return a human-readable auth summary for the startup banner."""
        native_env_names = self._native_cli_auth_env_names()
        if not native_env_names:
            return ""
        env_label = ", ".join(native_env_names)
        if self._use_native_cli_auth():
            return f"auth=native-cli ({env_label} stripped)"
        set_vars = [n for n in native_env_names if self._env_var_status(n) == "set"]
        if set_vars:
            return f"auth={', '.join(set_vars)}"
        return f"auth=native-cli (no {env_label} set, using CLI session)"

    def _effective_container_env_names(self) -> tuple[str, ...]:
        """Return container env vars minus any blocked by native CLI auth.

        Returns:
            The filtered tuple of env var names to forward into Docker.
        """
        env_names = self._container_env_names()
        if not self._use_native_cli_auth():
            return env_names
        blocked = set(self._native_cli_auth_env_names())
        if not blocked:
            return env_names
        return tuple(name for name in env_names if name not in blocked)

    def _wrap_container_if_enabled(self, cmd: list[str]) -> list[str]:
        """Wrap a CLI command with Docker execution if container mode is enabled.

        When container mode is disabled, returns the command unchanged. When
        enabled, builds a ``docker run`` invocation that mounts the repo root
        at ``/workspace``, forwards relevant environment variables, and
        delegates to the specified container image.

        Args:
            cmd: The CLI command tokens to wrap.

        Returns:
            The original *cmd* if container mode is off, or a new list
            prefixed with ``docker run …`` otherwise.

        Raises:
            RuntimeError: If container mode is enabled but the ``docker``
                binary is not found on ``PATH``.
        """
        if not self._container_enabled():
            return cmd
        image = self._container_image()
        if shutil.which("docker") is None:
            msg = (
                f"{self._CONTAINER_ENABLED_ENV_VAR} is enabled but docker is not "
                "available on PATH."
            )
            raise RuntimeError(msg)
        repo_root = str(self.repo_index.root.resolve())
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-i",
            "-v",
            f"{repo_root}:/workspace",
            "-w",
            "/workspace",
        ]
        for env_name in self._effective_container_env_names():
            value = os.environ.get(env_name)
            if value:
                docker_cmd.extend(["-e", f"{env_name}={value}"])
        docker_cmd.append(image)
        docker_cmd.extend(cmd)
        return docker_cmd

    def _execution_mode(self) -> str:
        """Return a short label describing the current execution mode.

        Returns:
            ``"container+workspace-write"`` when Docker is enabled,
            otherwise ``"workspace-write"``.
        """
        if self._container_enabled():
            return "container+workspace-write"
        return "workspace-write"

    @staticmethod
    def _float_env(name: str, *, default: float) -> float:
        """Read a positive float from an environment variable.

        Logs a warning and returns *default* when the value is missing,
        non-numeric, or non-positive.

        Args:
            name: Environment variable name.
            default: Fallback value.

        Returns:
            The parsed float, or *default*.
        """
        raw = os.environ.get(name)
        if raw is None:
            return default
        try:
            value = float(raw.strip())
        except ValueError:
            logger.warning(
                "%s has non-numeric value %r, using default %s",
                name,
                raw,
                default,
            )
            return default
        if value <= 0:
            logger.warning(
                "%s has non-positive value %s, using default %s",
                name,
                value,
                default,
            )
            return default
        return value

    def _io_poll_seconds(self) -> float:
        """Return the IO poll interval for subprocess stdout reads.

        Returns:
            Seconds between read attempts (from env or class default).
        """
        return self._float_env(
            "HELPING_HANDS_CLI_IO_POLL_SECONDS",
            default=self._DEFAULT_IO_POLL_SECONDS,
        )

    def _heartbeat_seconds(self) -> float:
        """Return the heartbeat interval for idle-progress messages.

        Uses a shorter default when verbose mode is enabled.

        Returns:
            Seconds between heartbeat messages (from env or class default).
        """
        default = (
            self._DEFAULT_HEARTBEAT_SECONDS_VERBOSE
            if self.config.verbose
            else self._DEFAULT_HEARTBEAT_SECONDS
        )
        return self._float_env(
            "HELPING_HANDS_CLI_HEARTBEAT_SECONDS",
            default=default,
        )

    def _idle_timeout_seconds(self) -> float:
        """Return the idle timeout before the subprocess is terminated.

        Returns:
            Seconds of silence before termination (from env or class default).
        """
        return self._float_env(
            "HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS",
            default=self._DEFAULT_IDLE_TIMEOUT_SECONDS,
        )

    def _build_subprocess_env(self) -> dict[str, str]:
        """Build the environment dict for CLI subprocess execution.

        Copies the current process environment and strips native CLI auth
        keys when ``_use_native_cli_auth`` is True, so the subprocess relies
        on its own session auth instead of forwarded API keys.

        Returns:
            A dict of environment variables for the subprocess.
        """
        env = dict(os.environ)
        if not self._use_native_cli_auth():
            return env
        for env_name in self._native_cli_auth_env_names():
            env.pop(env_name, None)
        return env

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        """Build the error message for a non-zero CLI exit.

        Includes the exit code and the trailing portion of the output,
        truncated to ``_SUMMARY_CHAR_LIMIT`` characters.

        Args:
            return_code: The subprocess exit code.
            output: Combined stdout/stderr from the CLI run.

        Returns:
            A human-readable failure message string.
        """
        tail = output.strip()[-self._SUMMARY_CHAR_LIMIT :]
        return f"{self._CLI_DISPLAY_NAME} failed (exit={return_code}). Output:\n{tail}"

    def _command_not_found_message(self, command: str) -> str:
        """Build the error message shown when the CLI binary is not on PATH.

        Includes a Docker rebuild hint using ``_DOCKER_REBUILD_HINT_TEMPLATE``
        so that Docker app-mode users get actionable remediation advice.

        Args:
            command: The binary name that was not found.

        Returns:
            A human-readable error string suggesting how to fix the issue.
        """
        return (
            f"{self._CLI_DISPLAY_NAME} command not found: {command!r}. "
            f"Set {self._COMMAND_ENV_VAR} to a valid command. "
            f"{_DOCKER_REBUILD_HINT_TEMPLATE.format(command)}"
        )

    def _fallback_command_when_not_found(self, cmd: list[str]) -> list[str] | None:
        """Return an alternative command to try when the primary CLI is missing.

        Subclasses may override this to provide a fallback binary (e.g. npx).

        Args:
            cmd: The original command that was not found.

        Returns:
            A replacement command list, or ``None`` to raise immediately.
        """
        return None

    def _retry_command_after_failure(
        self,
        cmd: list[str],
        *,
        output: str,
        return_code: int,
    ) -> list[str] | None:
        """Return a modified command to retry after a non-zero exit.

        Subclasses may override this to attempt automatic recovery (e.g.
        adjusting flags) when the CLI process fails.

        Args:
            cmd: The command that failed.
            output: Combined stdout/stderr from the failed run.
            return_code: The process exit code.

        Returns:
            A replacement command list to retry, or ``None`` to skip retry.
        """
        return None

    def _build_init_prompt(self) -> str:
        """Build the phase-1 initialization prompt for repository learning.

        Includes the repo root path, a capped file tree, and instructions
        for the AI to read docs and produce an implementation summary.

        Returns:
            The initialization prompt string.
        """
        file_list = "\n".join(
            f"- {path}" for path in self.repo_index.files[:_FILE_LIST_PREVIEW_LIMIT]
        )
        if not file_list:
            file_list = "- (no indexed files)"
        ref_section = self._build_reference_repos_prompt_section()
        return (
            "Initialization phase: learn this repository before task execution.\n"
            "Execution context: this hand is running inside a non-interactive "
            "helping_hands script started by the user.\n"
            f"Repository root: {self.repo_index.root}\n"
            "Goals:\n"
            "1. Read README.md and AGENT.md if they exist.\n"
            "2. Learn conventions from the file tree snapshot.\n"
            "3. Output a concise implementation-oriented summary.\n"
            "Do not ask the user for file contents.\n"
            "Use only tools that are actually available in this runtime.\n"
            "If a tool/action is unavailable, do not loop on retries.\n"
            "Do not perform edits in this phase.\n\n"
            "Indexed files:\n"
            f"{file_list}\n"
            f"{ref_section}"
        )

    def _stage_skill_catalog(self) -> None:
        """Stage selected skill catalog files to a temp directory."""
        from helping_hands.lib.meta import skills as system_skills

        if not self._selected_skills:
            return
        self._skill_catalog_dir = Path(tempfile.mkdtemp(prefix="helping_hands_skills_"))
        system_skills.stage_skill_catalog(
            self._selected_skills, self._skill_catalog_dir
        )

    def _cleanup_skill_catalog(self) -> None:
        """Remove the staged skill catalog temp directory."""
        if self._skill_catalog_dir is not None:
            shutil.rmtree(self._skill_catalog_dir, ignore_errors=True)
            self._skill_catalog_dir = None

    def _build_task_prompt(self, *, prompt: str, learned_summary: str) -> str:
        """Build the phase-2 task execution prompt.

        Combines the truncated initialization summary, user prompt, tool
        and skill catalog sections, and reference repo context.

        Args:
            prompt: The original user task prompt.
            learned_summary: Output from the phase-1 initialization run.

        Returns:
            The task execution prompt string.
        """
        from helping_hands.lib.meta import skills as system_skills
        from helping_hands.lib.meta.tools import registry as tool_reg

        summary = self._truncate_summary(
            learned_summary,
            limit=self._SUMMARY_CHAR_LIMIT,
        )

        tool_section = ""
        if self._selected_tool_categories:
            tool_text = tool_reg.format_tool_instructions_for_cli(
                self._selected_tool_categories
            )
            if tool_text:
                tool_section = f"\n\nEnabled tools and capabilities:\n{tool_text}"

        skill_section = ""
        if self._selected_skills:
            skill_text = system_skills.format_skill_catalog_instructions(
                self._selected_skills, self._skill_catalog_dir
            )
            if skill_text:
                skill_section = f"\n\nSkill knowledge catalog:\n{skill_text}"

        return (
            "Task execution phase.\n\n"
            "Repository context learned from initialization:\n"
            f"{summary or '(no summary produced)'}\n\n"
            "User task request:\n"
            f"{prompt}\n\n"
            "Execution context: this hand is running inside a non-interactive "
            "helping_hands script started by the user.\n"
            "Do not ask the user for additional approvals or interactive input.\n"
            "Use only tools that are actually available in this runtime.\n"
            "If required write/edit tools are unavailable, report that briefly "
            "and stop instead of retrying unavailable tools.\n"
            "Implement the task directly in the repository by editing files. "
            "Do not run git add, git commit, or git push — "
            "the caller handles version control after you finish. "
            "Do not ask the user to paste files."
            f"{tool_section}"
            f"{skill_section}"
            f"{self._build_reference_repos_prompt_section()}"
        )

    def _current_head_sha(self) -> str:
        """Return the current HEAD commit SHA, or empty string on failure."""
        repo_root = self.repo_index.root.resolve()
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=_GIT_READ_TIMEOUT_S,
            )
        except (subprocess.TimeoutExpired, OSError):
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def _repo_has_changes(self) -> bool:
        """Check whether the working tree has uncommitted changes or new commits.

        Runs ``git status --porcelain`` to detect uncommitted changes.
        Also compares the current HEAD against the baseline captured before
        the backend ran, so that changes committed by the backend (e.g.
        Devin running ``git commit``) are not missed.

        Returns:
            True if the working tree has uncommitted changes or the HEAD
            has advanced since the baseline was captured.
        """
        repo_root = self.repo_index.root.resolve()
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=_GIT_READ_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "git status timed out after %ds; assuming no changes",
                _GIT_READ_TIMEOUT_S,
            )
            return False
        if result.returncode != 0:
            logger.debug(
                "git status check failed (code=%d); assuming no changes",
                result.returncode,
            )
            return False
        if result.stdout.strip():
            return True

        # Detect commits made by the backend itself.
        if self._baseline_head:
            current_head = self._current_head_sha()
            if current_head and current_head != self._baseline_head:
                logger.info(
                    "HEAD advanced from %s to %s — backend committed changes",
                    self._baseline_head[:8],
                    current_head[:8],
                )
                return True

        return False

    def _has_pending_changes(self, repo_dir: Path) -> bool:
        """Check for uncommitted changes or backend-made commits.

        Overrides the base implementation to also detect commits that
        the backend made directly (e.g. Devin running ``git commit``).
        """
        return self._repo_has_changes()

    @staticmethod
    def _looks_like_edit_request(prompt: str) -> bool:
        """Heuristic check for whether the prompt requests file edits.

        Looks for common action verbs (update, fix, add, etc.) in the
        lowercased prompt text.

        Args:
            prompt: The user prompt string.

        Returns:
            True if any action marker is found in the prompt.
        """
        lowered = prompt.lower()
        action_markers = (
            "update",
            "edit",
            "modify",
            "implement",
            "fix",
            "add",
            "remove",
            "rename",
            "refactor",
            "write",
            "create",
            "change",
            "improv",
            "clean",
            "delet",
            "migrat",
            "upgrad",
        )
        return any(marker in lowered for marker in action_markers)

    def _should_retry_without_changes(self, prompt: str) -> bool:
        """Decide whether to retry when the task produced no file changes.

        Returns True only when ``_RETRY_ON_NO_CHANGES`` is enabled, the
        hand is not interrupted, the prompt looks like an edit request,
        and the working tree has no changes.

        Args:
            prompt: The user prompt string.

        Returns:
            True if a retry (apply-changes enforcement) should be attempted.
        """
        if not self._RETRY_ON_NO_CHANGES:
            return False
        if self._is_interrupted():
            return False
        if not self._looks_like_edit_request(prompt):
            return False
        return not self._repo_has_changes()

    def _build_apply_changes_prompt(self, *, prompt: str, task_output: str) -> str:
        """Build the enforcement prompt asking the AI to apply file edits.

        Used when the task phase responded without modifying files.

        Args:
            prompt: The original user task prompt.
            task_output: The AI's prior response (truncated for context).

        Returns:
            The apply-changes enforcement prompt string.
        """
        summarized_output = self._truncate_summary(
            task_output, limit=_APPLY_CHANGES_TRUNCATION_LIMIT
        )
        return (
            "Follow-up enforcement phase.\n"
            "You previously responded without applying repository file changes.\n\n"
            "Original user request:\n"
            f"{prompt}\n\n"
            "Your prior response:\n"
            f"{summarized_output or '(none)'}\n\n"
            "Now apply the required edits directly in the repository working tree.\n"
            "Do not only describe changes.\n"
            "After editing, provide a short summary of changed files."
        )

    def _no_change_error_after_retries(
        self,
        *,
        prompt: str,
        combined_output: str,
    ) -> str | None:
        """Return an error message when the task phase produced no file changes.

        Called after all retry attempts if the working tree is still clean.
        Subclasses may override to provide a backend-specific diagnostic.

        Args:
            prompt: The original user prompt.
            combined_output: Accumulated CLI output across all attempts.

        Returns:
            An error message string, or ``None`` to silently accept no changes.
        """
        del prompt
        del combined_output
        return None

    async def _terminate_active_process(self) -> None:
        process = self._active_process
        if process is None or process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=_PROCESS_TERMINATE_TIMEOUT_S)
        except TimeoutError:
            process.kill()
            await process.wait()

    async def _invoke_cli(
        self,
        prompt: str,
        *,
        emit: _Emitter,
    ) -> str:
        return await self._invoke_cli_with_cmd(self._render_command(prompt), emit=emit)

    async def _invoke_cli_with_cmd(
        self,
        cmd: list[str],
        *,
        emit: _Emitter,
    ) -> str:
        """Execute a CLI subprocess and stream its output.

        Args:
            cmd: Command and arguments to execute.  Must contain at least
                one non-empty element.
            emit: Async callback that receives incremental output chunks.

        Returns:
            Concatenated stdout/stderr output from the subprocess.

        Raises:
            ValueError: If *cmd* is empty or its first element is empty.
            RuntimeError: If the subprocess cannot be started or times out.
        """
        if not cmd or not cmd[0]:
            raise ValueError(
                "cmd must be a non-empty list with a non-empty first element"
            )
        env = self._build_subprocess_env()
        cwd = str(self.repo_index.root.resolve())
        if self.config.verbose:
            await emit(self._label_msg(f"cmd: {shlex.join(cmd)}\n"))
            await emit(self._label_msg(f"cwd: {cwd}\n"))
        start_time = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
        except FileNotFoundError as exc:
            fallback = self._fallback_command_when_not_found(cmd)
            if fallback and fallback != cmd:
                await emit(
                    self._label_msg(
                        f"{cmd[0]!r} not found; retrying with {fallback[0]!r}.\n"
                    )
                )
                if fallback[0] == "npx":
                    await emit(
                        self._label_msg(
                            "npx fallback may take a while on "
                            "first run while the package is downloaded.\n"
                        )
                    )
                return await self._invoke_cli_with_cmd(fallback, emit=emit)
            raise RuntimeError(self._command_not_found_message(cmd[0])) from exc

        self._active_process = process
        chunks: list[str] = []
        stdout = process.stdout
        if stdout is None:
            await process.wait()
            self._active_process = None
            msg = f"{self._CLI_DISPLAY_NAME} did not expose stdout pipe."
            raise RuntimeError(msg)

        io_poll_seconds = self._io_poll_seconds()
        heartbeat_seconds = self._heartbeat_seconds()
        idle_timeout_seconds = self._idle_timeout_seconds()
        now = asyncio.get_running_loop().time()
        last_output_ts = now
        last_heartbeat_ts = now

        try:
            while True:
                if self._is_interrupted():
                    await self._terminate_active_process()
                    break

                try:
                    data = await asyncio.wait_for(
                        stdout.read(_STREAM_READ_BUFFER_SIZE),
                        timeout=io_poll_seconds,
                    )
                except TimeoutError as exc:
                    if process.returncode is not None:
                        break
                    now = asyncio.get_running_loop().time()
                    idle_seconds = now - last_output_ts
                    if now - last_heartbeat_ts >= heartbeat_seconds:
                        await emit(
                            self._label_msg(
                                f"still running "
                                f"({int(idle_seconds)}s since last output; "
                                f"timeout={int(idle_timeout_seconds)}s)...\n"
                            )
                        )
                        last_heartbeat_ts = now
                    if idle_seconds >= idle_timeout_seconds:
                        await self._terminate_active_process()
                        msg = (
                            f"{self._CLI_DISPLAY_NAME} produced no output for "
                            f"{int(idle_timeout_seconds)}s and was terminated. "
                            "Increase HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS "
                            "if this command is expected to run quietly."
                        )
                        raise RuntimeError(msg) from exc
                    continue
                if not data:
                    break

                last_output_ts = asyncio.get_running_loop().time()
                text = data.decode("utf-8", errors="replace")
                chunks.append(text)
                await emit(text)

            if not self._is_interrupted():
                return_code = await process.wait()
                elapsed = time.monotonic() - start_time
                if self.config.verbose:
                    await emit(
                        self._label_msg(
                            f"finished in {elapsed:.1f}s (exit={return_code})\n"
                        )
                    )
                if return_code != 0:
                    output = "".join(chunks)
                    retry_cmd = self._retry_command_after_failure(
                        cmd,
                        output=output,
                        return_code=return_code,
                    )
                    if retry_cmd and retry_cmd != cmd:
                        await emit(
                            self._label_msg(
                                "command failed; retrying with adjusted arguments.\n"
                            )
                        )
                        return await self._invoke_cli_with_cmd(retry_cmd, emit=emit)
                    msg = self._build_failure_message(
                        return_code=return_code,
                        output=output,
                    )
                    raise RuntimeError(msg)
            return "".join(chunks)
        finally:
            self._active_process = None

    async def _invoke_backend(self, prompt: str, *, emit: _Emitter) -> str:
        return await self._invoke_cli(prompt, emit=emit)

    async def _run_two_phase(
        self,
        prompt: str,
        *,
        emit: _Emitter,
    ) -> str:
        self.reset_interrupt()
        self._stage_skill_catalog()
        try:
            return await self._run_two_phase_inner(prompt, emit=emit)
        finally:
            self._cleanup_skill_catalog()

    async def _run_two_phase_inner(
        self,
        prompt: str,
        *,
        emit: _Emitter,
    ) -> str:
        self._baseline_head = self._current_head_sha()
        auth = self._describe_auth()
        auth_part = f" | {auth}" if auth else ""
        await emit(self._label_msg(f"isolation={self._execution_mode()}{auth_part}\n"))
        if self.config.verbose:
            model = self._resolve_cli_model() or "(default)"
            await emit(
                self._label_msg(
                    f"verbose=on | model={model} "
                    f"| heartbeat={self._heartbeat_seconds():.0f}s "
                    f"| idle_timeout={self._idle_timeout_seconds():.0f}s\n"
                )
            )
        run_start = time.monotonic()
        await emit(self._label_msg("[phase 1/2] Initializing repository context...\n"))
        init_output = await self._invoke_backend(self._build_init_prompt(), emit=emit)
        if self._is_interrupted():
            await emit(self._label_msg("Interrupted during initialization.\n"))
            return init_output
        if self.config.verbose:
            phase1_elapsed = time.monotonic() - run_start
            await emit(self._label_msg(f"phase 1 completed in {phase1_elapsed:.1f}s\n"))

        phase2_start = time.monotonic()
        await emit(self._label_msg("[phase 2/2] Executing user task...\n"))
        task_output = await self._invoke_backend(
            self._build_task_prompt(prompt=prompt, learned_summary=init_output),
            emit=emit,
        )
        if self.config.verbose:
            phase2_elapsed = time.monotonic() - phase2_start
            total_elapsed = time.monotonic() - run_start
            await emit(
                self._label_msg(
                    f"phase 2 completed in {phase2_elapsed:.1f}s "
                    f"| total elapsed: {total_elapsed:.1f}s\n"
                )
            )
        combined_output = f"{init_output}{task_output}"

        if self._should_retry_without_changes(prompt):
            await emit(
                self._label_msg(
                    "No file edits detected; requesting direct file application...\n"
                )
            )
            apply_output = await self._invoke_backend(
                self._build_apply_changes_prompt(
                    prompt=prompt,
                    task_output=task_output,
                ),
                emit=emit,
            )
            combined_output += apply_output

        if self._looks_like_edit_request(prompt) and not self._repo_has_changes():
            no_change_error = self._no_change_error_after_retries(
                prompt=prompt,
                combined_output=combined_output,
            )
            if no_change_error:
                raise RuntimeError(no_change_error)

        return combined_output

    async def _collect_run_output(self, prompt: str) -> str:
        chunks: list[str] = []

        async def _emit(chunk: str) -> None:
            chunks.append(chunk)

        await self._run_two_phase(prompt, emit=_emit)
        return "".join(chunks)

    def _interrupted_pr_metadata(self) -> dict[str, str]:
        """Return PR metadata indicating the run was interrupted.

        Returns:
            A dict with ``pr_status`` set to ``"interrupted"`` and
            empty PR fields.
        """
        return {
            "auto_pr": str(self.auto_pr).lower(),
            _META_PR_STATUS: "interrupted",
            _META_PR_URL: "",
            _META_PR_NUMBER: "",
            _META_PR_BRANCH: "",
            _META_PR_COMMIT: "",
        }

    def _finalize_after_run(self, *, prompt: str, message: str) -> dict[str, str]:
        """Finalize the run by committing, pushing, and creating the PR.

        Returns interrupted metadata without finalizing when the hand was
        interrupted.  Otherwise delegates to ``_finalize_repo_pr``.

        Args:
            prompt: The original user task prompt.
            message: Combined CLI output from the run.

        Returns:
            A dict of PR metadata (status, url, branch, commit, etc.).
        """
        if self._is_interrupted():
            return self._interrupted_pr_metadata()

        summary = self._truncate_summary(message, limit=self._SUMMARY_CHAR_LIMIT)
        return self._finalize_repo_pr(
            backend=self._BACKEND_NAME,
            prompt=prompt,
            summary=summary,
        )

    def _format_pr_status_message(self, metadata: dict[str, str]) -> str | None:
        """Format a human-readable PR status message for streaming output.

        Uses :data:`_PR_STATUS_TEMPLATES` for known statuses and falls
        back to a generic ``"PR status: {status}"`` message for unknown
        values.

        Args:
            metadata: PR metadata dict from ``_finalize_after_run``.

        Returns:
            A formatted status string, or ``None`` if no status to report.
        """
        status = metadata.get(_META_PR_STATUS, "")
        if not status:
            return None
        template = _PR_STATUS_TEMPLATES.get(status)
        if template is not None:
            pr_url = metadata.get(_META_PR_URL, "")
            return self._label_msg(template.format(pr_url=pr_url))
        error = metadata.get(_META_PR_ERROR, "").strip()
        if error:
            return self._label_msg(f"PR status: {status} ({error})")
        return self._label_msg(f"PR status: {status}")

    # ------------------------------------------------------------------
    # CI fix loop
    # ------------------------------------------------------------------

    async def _poll_ci_checks(
        self,
        *,
        gh: Any,
        repo: str,
        ref: str,
        emit: Any,
        initial_wait: float,
        max_poll_seconds: float,
    ) -> dict[str, Any]:
        """Wait for CI checks to complete and return the result."""
        await emit(
            "\n"
            + self._label_msg(
                f"Waiting {initial_wait:.0f}s "
                f"for CI checks on {ref[:_GIT_REF_DISPLAY_LENGTH]}...\n"
            )
        )
        await asyncio.sleep(initial_wait)

        poll_interval = _CI_POLL_INTERVAL_S
        deadline = time.monotonic() + max_poll_seconds
        while time.monotonic() < deadline:
            result = gh.get_check_runs(repo, ref)
            conclusion = result.get("conclusion", CIConclusion.PENDING)
            if conclusion not in CI_CONCLUSIONS_IN_PROGRESS:
                return result
            await emit(
                self._label_msg(
                    f"CI still {conclusion}, polling again in {poll_interval:.0f}s...\n"
                )
            )
            await asyncio.sleep(poll_interval)

        return gh.get_check_runs(repo, ref)

    @staticmethod
    def _build_ci_fix_prompt(
        *,
        check_result: dict[str, Any],
        original_prompt: str,
        attempt: int,
    ) -> str:
        """Build a prompt telling the AI to fix CI failures."""
        failed = [
            r
            for r in check_result.get("check_runs", [])
            if r.get("conclusion") in _CI_RUN_FAILURE_CONCLUSIONS
        ]
        failure_lines = []
        for r in failed:
            name = r.get("name", "unknown")
            conclusion = r.get("conclusion", "unknown")
            url = r.get("html_url", "")
            failure_lines.append(f"  - {name}: {conclusion} ({url})")

        failure_summary = "\n".join(failure_lines) or "  (no details available)"

        return (
            f"CI fix attempt {attempt}.\n\n"
            "The following CI checks failed after pushing changes:\n"
            f"{failure_summary}\n\n"
            "Original task was:\n"
            f"{original_prompt}\n\n"
            "Please investigate the CI failures by:\n"
            "1. Reading the relevant source files and test files\n"
            "2. Running the failing checks locally if possible "
            "(e.g. lint, test, typecheck commands)\n"
            "3. Fixing the issues in the repository\n\n"
            "Focus only on fixing the CI failures. "
            "Do not make unrelated changes."
        )

    async def _ci_fix_loop(
        self,
        *,
        prompt: str,
        metadata: dict[str, str],
        emit: Any,
    ) -> dict[str, str]:
        """Poll CI after PR push, attempt fixes if failures detected."""
        if not self.fix_ci:
            return metadata

        pr_status = metadata.get(_META_PR_STATUS, "")
        if pr_status not in _PR_STATUSES_WITH_URL:
            return metadata

        pr_commit = metadata.get(_META_PR_COMMIT, "")
        pr_branch = metadata.get(_META_PR_BRANCH, "")
        if not pr_commit or not pr_branch:
            return metadata

        repo_dir = self.repo_index.root.resolve()
        repo = self._github_repo_from_origin(repo_dir)
        if not repo:
            return metadata

        from helping_hands.lib.github import GitHubClient

        initial_wait = self.ci_check_wait_minutes * 60
        max_poll = initial_wait * 2

        metadata[_META_CI_FIX_ATTEMPTS] = "0"
        metadata[_META_CI_FIX_STATUS] = CIFixStatus.CHECKING

        try:
            with GitHubClient(token=self.config.github_token) as gh:
                current_ref = pr_commit
                for attempt in range(1, self.ci_max_retries + 1):
                    if self._is_interrupted():
                        metadata[_META_CI_FIX_STATUS] = CIFixStatus.INTERRUPTED
                        return metadata

                    check_result = await self._poll_ci_checks(
                        gh=gh,
                        repo=repo,
                        ref=current_ref,
                        emit=emit,
                        initial_wait=initial_wait,
                        max_poll_seconds=max_poll,
                    )

                    conclusion = check_result.get("conclusion", CIConclusion.PENDING)
                    total = check_result.get("total_count", 0)

                    if conclusion == CIConclusion.SUCCESS:
                        await emit(
                            self._label_msg(
                                f"CI passed "
                                f"({total} check{'s' if total != 1 else ''}). "
                                f"No fixes needed.\n"
                            )
                        )
                        metadata[_META_CI_FIX_STATUS] = CIFixStatus.SUCCESS
                        return metadata

                    if conclusion == CIConclusion.NO_CHECKS:
                        await emit(
                            self._label_msg(
                                "No CI checks found. Skipping CI fix loop.\n"
                            )
                        )
                        metadata[_META_CI_FIX_STATUS] = CIFixStatus.NO_CHECKS
                        return metadata

                    if conclusion == CIConclusion.PENDING:
                        await emit(
                            self._label_msg(
                                "CI checks still pending "
                                "after waiting. Skipping fix attempt.\n"
                            )
                        )
                        metadata[_META_CI_FIX_STATUS] = CIFixStatus.PENDING_TIMEOUT
                        return metadata

                    # CI failed — attempt fix
                    await emit(
                        "\n"
                        + self._label_msg(
                            f"CI failed (attempt "
                            f"{attempt}/{self.ci_max_retries}). "
                            f"Invoking backend to fix...\n"
                        )
                    )

                    fix_prompt = self._build_ci_fix_prompt(
                        check_result=check_result,
                        original_prompt=prompt,
                        attempt=attempt,
                    )

                    await self._invoke_backend(fix_prompt, emit=emit)

                    if self._is_interrupted():
                        metadata[_META_CI_FIX_STATUS] = CIFixStatus.INTERRUPTED
                        return metadata

                    metadata[_META_CI_FIX_ATTEMPTS] = str(attempt)

                    if not self._repo_has_changes():
                        await emit(
                            self._label_msg(
                                f"No changes produced by fix attempt {attempt}.\n"
                            )
                        )
                        continue

                    # Commit and push the fix
                    new_sha = self._add_and_commit_with_hook_retry(
                        gh,
                        repo_dir,
                        f"fix(ci): attempt {attempt} — "
                        f"fix CI failures ({self._BACKEND_NAME})",
                    )
                    self._push_noninteractive(gh, repo_dir, pr_branch)

                    await emit(
                        self._label_msg(
                            f"Fix pushed (commit {new_sha}). Waiting for CI...\n"
                        )
                    )

                    metadata[_META_PR_COMMIT] = new_sha
                    current_ref = new_sha

                # Exhausted all retries
                metadata[_META_CI_FIX_STATUS] = CIFixStatus.EXHAUSTED
                await emit(
                    self._label_msg(
                        f"CI fix retries exhausted "
                        f"after {self.ci_max_retries} attempts.\n"
                    )
                )

        except (
            GithubException,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            OSError,
        ) as exc:
            logger.debug("_ci_fix_loop unexpected error", exc_info=True)
            metadata[_META_CI_FIX_STATUS] = CIFixStatus.ERROR
            metadata[_META_CI_FIX_ERROR] = str(exc)
            await emit(self._label_msg(f"CI fix loop error: {exc}\n"))

        return metadata

    def _format_ci_fix_message(self, metadata: dict[str, str]) -> str | None:
        """Format a human-readable CI fix status message.

        Args:
            metadata: PR metadata dict containing ``ci_fix_status``.

        Returns:
            A status string, or ``None`` if no CI fix was attempted.
        """
        ci_status = metadata.get(_META_CI_FIX_STATUS, "")
        if not ci_status:
            return None
        template = _CI_FIX_TEMPLATES.get(ci_status)
        if template is None:
            return None
        attempts = metadata.get(_META_CI_FIX_ATTEMPTS, "0")
        error = metadata.get(_META_CI_FIX_ERROR, "")
        return self._label_msg(template.format(attempts=attempts, error=error))

    # ------------------------------------------------------------------
    # Pre-commit hook fix
    # ------------------------------------------------------------------

    @staticmethod
    def _build_hook_fix_prompt(error_output: str) -> str:
        """Build a prompt asking the AI backend to fix git hook errors."""
        truncated = error_output.strip()
        if len(truncated) > _HOOK_ERROR_TRUNCATION_LIMIT:
            truncated = f"{truncated[:_HOOK_ERROR_TRUNCATION_LIMIT]}\n...[truncated]"

        return (
            "Git pre-commit hook fix.\n\n"
            "A git commit was rejected because pre-commit hooks "
            "(husky/lint-staged/eslint/prettier) reported errors.\n\n"
            "Hook error output:\n"
            f"```\n{truncated}\n```\n\n"
            "Please fix the issues reported by the hooks:\n"
            "1. Read the error messages carefully\n"
            "2. Fix the linting, formatting, or type errors in the affected files\n"
            "3. Do not run git commit yourself\n\n"
            "Focus only on fixing the hook errors. "
            "Do not make unrelated changes."
        )

    def _try_fix_git_hook_errors(
        self,
        repo_dir: Path,
        error_output: str,
    ) -> bool:
        """Invoke the AI backend synchronously to fix hook errors."""
        prompt = self._build_hook_fix_prompt(error_output)
        cmd = self._render_command(prompt)
        env = self._build_subprocess_env()

        logger.info(
            "[%s] Invoking backend to fix git hook errors...",
            self._CLI_LABEL,
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=False,
                env=env,
                timeout=_PR_DESCRIPTION_TIMEOUT_S,
            )
        except FileNotFoundError:
            fallback = self._fallback_command_when_not_found(cmd)
            if fallback and fallback != cmd:
                try:
                    result = subprocess.run(
                        fallback,
                        cwd=str(repo_dir),
                        capture_output=True,
                        text=True,
                        check=False,
                        env=env,
                        timeout=_PR_DESCRIPTION_TIMEOUT_S,
                    )
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    logger.warning(
                        "[%s] Fallback command also failed for hook fix.",
                        self._CLI_LABEL,
                    )
                    return False
            else:
                logger.warning(
                    "[%s] Backend CLI not found for hook fix.",
                    self._CLI_LABEL,
                )
                return False
        except subprocess.TimeoutExpired:
            logger.warning(
                "[%s] Backend timed out while attempting hook fix.",
                self._CLI_LABEL,
            )
            return False

        if result.returncode != 0:
            logger.warning(
                "[%s] Backend returned non-zero (%d) during hook fix.",
                self._CLI_LABEL,
                result.returncode,
            )

        return self._repo_has_changes()

    def interrupt(self) -> None:
        """Signal the hand to stop execution.

        Extends the base ``Hand.interrupt()`` by also terminating the active
        subprocess (if one is running) via SIGTERM.
        """
        super().interrupt()
        process = self._active_process
        if process is not None and process.returncode is None:
            process.terminate()

    def run(self, prompt: str) -> HandResponse:
        """Execute the two-phase CLI workflow synchronously.

        Runs init → task phases via ``asyncio.run``, finalises the repo
        (commit/push/PR), and optionally enters the CI-fix loop.

        Args:
            prompt: The user task description to execute.

        Returns:
            A ``HandResponse`` with the combined output and PR metadata.

        Raises:
            ValueError: If *prompt* is empty or whitespace-only.
        """
        require_non_empty_string(prompt, "prompt")
        message = asyncio.run(self._collect_run_output(prompt))
        pr_metadata = self._finalize_after_run(prompt=prompt, message=message)

        if self.fix_ci and pr_metadata.get(_META_PR_STATUS) in _PR_STATUSES_WITH_URL:

            async def _run_ci_fix() -> dict[str, str]:
                async def _noop_emit(chunk: str) -> None:
                    pass

                return await self._ci_fix_loop(
                    prompt=prompt,
                    metadata=pr_metadata,
                    emit=_noop_emit,
                )

            pr_metadata = asyncio.run(_run_ci_fix())

        return HandResponse(
            message=message,
            metadata={
                _META_BACKEND: self._BACKEND_NAME,
                _META_MODEL: self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Execute the two-phase CLI workflow with streaming output.

        Yields chunks as they arrive from the subprocess, then finalises the
        repo and optionally enters the CI-fix loop.

        Args:
            prompt: The user task description to execute.

        Yields:
            Output chunks from the subprocess and PR status messages.

        Raises:
            ValueError: If *prompt* is empty or whitespace-only.
        """
        require_non_empty_string(prompt, "prompt")
        output_queue: asyncio.Queue[str | None] = asyncio.Queue()
        collected: list[str] = []

        async def _emit(chunk: str) -> None:
            collected.append(chunk)
            await output_queue.put(chunk)

        async def _produce() -> None:
            error: Exception | None = None
            try:
                await self._run_two_phase(prompt, emit=_emit)
            except Exception as exc:  # pragma: no cover - propagated below
                error = exc
            finally:
                if error is None:
                    message = "".join(collected)
                    metadata = self._finalize_after_run(prompt=prompt, message=message)
                    pr_status_message = self._format_pr_status_message(metadata)
                    if pr_status_message:
                        await output_queue.put(f"\n{pr_status_message}\n")
                    # CI fix loop (only runs if fix_ci=True and PR was created/updated)
                    metadata = await self._ci_fix_loop(
                        prompt=prompt,
                        metadata=metadata,
                        emit=_emit,
                    )
                    ci_msg = self._format_ci_fix_message(metadata)
                    if ci_msg:
                        await output_queue.put(f"\n{ci_msg}\n")
                await output_queue.put(None)
            if error is not None:
                raise error

        producer_task = asyncio.create_task(_produce())
        try:
            while True:
                chunk = await output_queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            if not producer_task.done():
                producer_task.cancel()
                with suppress(asyncio.CancelledError):
                    await producer_task
            else:
                exc = producer_task.exception()
                if exc is not None:
                    raise exc  # pragma: no cover
