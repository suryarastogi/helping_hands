"""Claude Code CLI hand implementation."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
from typing import Any

from helping_hands.lib.hands.v1.hand.cli.base import (
    _format_cli_failure,
    _truncate_with_ellipsis,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.validation import has_cli_flag

logger = logging.getLogger(__name__)

__all__ = [
    "_OUTPUT_FORMAT_STREAM_JSON",
    "_SKIP_PERMISSIONS_FLAG",
    "_TOOL_SUMMARY_KEY_MAP",
    "_TOOL_SUMMARY_STATIC",
    "ClaudeCodeHand",
]

# --- Module-level constants ---------------------------------------------------

_TEXT_PREVIEW_MAX_LENGTH = 200
"""Maximum length for assistant text previews before truncation."""

_TOOL_RESULT_PREVIEW_MAX_LENGTH = 150
"""Maximum length for tool result previews before truncation."""

_COMMAND_PREVIEW_MAX_LENGTH = 80
"""Maximum length for Bash command / CronCreate prompt previews."""

# Stream-json event types emitted by ``claude --output-format stream-json``.

_EVENT_TYPE_ASSISTANT = "assistant"
"""Event type for assistant messages containing text and tool_use blocks."""

_EVENT_TYPE_USER = "user"
"""Event type for user messages containing tool_result blocks."""

_EVENT_TYPE_RESULT = "result"
"""Event type for the final result summary (cost, duration, usage)."""

# Content block types within assistant/user message payloads.

_BLOCK_TYPE_TOOL_USE = "tool_use"
"""Block type for a tool invocation inside an assistant message."""

_BLOCK_TYPE_TOOL_RESULT = "tool_result"
"""Block type for a tool result inside a user message."""

_BLOCK_TYPE_TEXT = "text"
"""Block type for assistant text output."""

# Dispatch table for _summarize_tool: maps tool name → input_data key.
# Tools listed here use the simple pattern ``"ToolName {input_data[key]}"``.
_TOOL_SUMMARY_KEY_MAP: dict[str, str] = {
    "Read": "file_path",
    "Edit": "file_path",
    "Write": "file_path",
    "Glob": "pattern",
    "NotebookEdit": "notebook_path",
}
"""Simple tool-name → input key mapping for ``_summarize_tool``."""

# Tools that need no input key — just return the tool name.
_TOOL_SUMMARY_STATIC: frozenset[str] = frozenset({"TodoWrite", "CronList"})
"""Tools whose summary is simply their name with no parameters."""

_OUTPUT_FORMAT_STREAM_JSON = "stream-json"
"""The ``--output-format`` value used for structured streaming output."""

_SKIP_PERMISSIONS_FLAG = "--dangerously-skip-permissions"
"""Claude CLI flag to bypass the interactive permission prompt."""

_DEFAULT_MAX_TURNS = 0
"""Default value for ``--max-turns`` (0 = unlimited / not injected)."""

_SYSTEM_PROMPT_MAX_LENGTH = 16_000
"""Cap on the length of an injected ``--append-system-prompt`` payload.

Truncates oversized agent docs (AGENT.md / CLAUDE.md) so that very large
files don't blow past Claude Code's CLI argument limits."""

_AGENT_DOC_CANDIDATES: tuple[str, ...] = ("AGENT.md", "CLAUDE.md")
"""Filenames searched at the repo root for the auto-injected system prompt."""


class _StreamJsonEmitter:
    """Parse Claude Code ``--output-format stream-json`` and emit progress."""

    def __init__(
        self,
        emit: _TwoPhaseCLIHand._Emitter,
        label: str,
    ) -> None:
        self._emit = emit
        self._label = label
        self._buffer = ""
        self._result = ""
        self._text_parts: list[str] = []
        self._session_id: str = ""
        self._total_cost_usd: float | None = None
        self._duration_ms: float | None = None
        self._usage: dict[str, int] = {}

    def _label_msg(self, msg: str) -> str:
        """Prefix *msg* with the backend label.

        Returns:
            A string of the form ``[<label>] <msg>``.
        """
        return f"[{self._label}] {msg}"

    async def __call__(self, chunk: str) -> None:
        """Buffer incoming text and process complete lines.

        Args:
            chunk: Raw text chunk from the Claude Code CLI subprocess.
        """
        self._buffer += chunk
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            stripped = line.strip()
            if not stripped:
                continue
            await self._process_line(stripped)

    async def flush(self) -> None:
        """Process any remaining data in the buffer."""
        if self._buffer.strip():
            await self._process_line(self._buffer.strip())
            self._buffer = ""

    @staticmethod
    def _normalize_preview(text: str) -> str:
        """Strip whitespace and collapse newlines to spaces.

        Args:
            text: Raw text to normalise for single-line preview display.

        Returns:
            The cleaned text with leading/trailing whitespace removed
            and internal newlines replaced by spaces.
        """
        return text.strip().replace("\n", " ")

    @staticmethod
    def _extract_message_blocks(event: dict) -> list:
        """Extract the ``message.content`` block list from a stream event.

        Returns an empty list when ``message`` is not a dict or has no
        ``content`` key, so callers can iterate unconditionally.

        Args:
            event: A parsed JSON event dict from the Claude Code stream.

        Returns:
            The ``content`` list, or ``[]`` if unavailable.
        """
        message = event.get("message")
        if not isinstance(message, dict):
            return []
        return message.get("content", [])

    async def _process_line(self, line: str) -> None:
        """Parse a single JSON event line and emit progress.

        Handles three event types: ``assistant`` (tool use and text blocks),
        ``user`` (tool result blocks), and ``result`` (cost/duration summary).
        Non-JSON lines are passed through verbatim.

        Args:
            line: A stripped, non-empty line from the Claude Code stream.
        """
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            # Not JSON (verbose logs, heartbeats) — pass through.
            await self._emit(line + "\n")
            return

        if not isinstance(event, dict):
            # JSON primitive (string, number, etc.) — pass through.
            await self._emit(line + "\n")
            return

        event_type = event.get("type", "")

        if event_type == _EVENT_TYPE_ASSISTANT:
            # Claude Code stream-json: message is a full Anthropic API message
            # with message.content[] array of {type: "text"} / {type: "tool_use"}.
            for block in self._extract_message_blocks(event):
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type", "")
                if block_type == _BLOCK_TYPE_TOOL_USE:
                    name = block.get("name", "unknown")
                    input_data = block.get("input", {})
                    summary = self._summarize_tool(name, input_data)
                    await self._emit(self._label_msg(summary) + "\n")
                elif block_type == _BLOCK_TYPE_TEXT:
                    text = block.get("text", "")
                    if text:
                        self._text_parts.append(text)
                        preview = self._normalize_preview(text)
                        preview = _truncate_with_ellipsis(
                            preview, _TEXT_PREVIEW_MAX_LENGTH
                        )
                        if preview:
                            await self._emit(self._label_msg(preview) + "\n")

        elif event_type == _EVENT_TYPE_USER:
            # Tool results: message.content[] array of {type: "tool_result"}.
            for block in self._extract_message_blocks(event):
                if not isinstance(block, dict):
                    continue
                if block.get("type") != _BLOCK_TYPE_TOOL_RESULT:
                    continue
                content = block.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict)
                    )
                if isinstance(content, str) and content.strip():
                    preview = self._normalize_preview(content)
                    preview = _truncate_with_ellipsis(
                        preview, _TOOL_RESULT_PREVIEW_MAX_LENGTH
                    )
                    await self._emit(self._label_msg(f"-> {preview}") + "\n")

        elif event_type == _EVENT_TYPE_RESULT:
            self._result = event.get("result", "")
            session_id = event.get("session_id", "")
            if isinstance(session_id, str) and session_id:
                self._session_id = session_id
            cost = event.get("total_cost_usd")
            duration = event.get("duration_ms")
            usage = event.get("usage")
            if cost is not None:
                try:
                    self._total_cost_usd = float(cost)
                except (TypeError, ValueError):
                    self._total_cost_usd = None
            if duration is not None:
                try:
                    self._duration_ms = float(duration)
                except (TypeError, ValueError):
                    self._duration_ms = None
            parts: list[str] = []
            if self._total_cost_usd is not None:
                parts.append(f"${self._total_cost_usd:.4f}")
            if self._duration_ms is not None:
                parts.append(f"{self._duration_ms / 1000:.1f}s")
            if isinstance(usage, dict):
                inp = usage.get("input_tokens")
                out = usage.get("output_tokens")
                if inp is not None or out is not None:
                    tok_parts: list[str] = []
                    if inp is not None:
                        tok_parts.append(f"in={inp}")
                        with contextlib.suppress(TypeError, ValueError):
                            self._usage["input_tokens"] = int(inp)
                    if out is not None:
                        tok_parts.append(f"out={out}")
                        with contextlib.suppress(TypeError, ValueError):
                            self._usage["output_tokens"] = int(out)
                    parts.append(" ".join(tok_parts))
            if parts:
                await self._emit(self._label_msg(f"api: {', '.join(parts)}") + "\n")

    @staticmethod
    def _summarize_tool(name: str, input_data: dict) -> str:
        """Return a one-line human-readable summary of a tool invocation.

        Uses ``_TOOL_SUMMARY_KEY_MAP`` for tools that follow the simple
        ``"ToolName {value}"`` pattern, ``_TOOL_SUMMARY_STATIC`` for
        tools with no parameters, and explicit branches for tools with
        custom formatting.

        Args:
            name: The tool name (e.g. ``"Read"``, ``"Bash"``).
            input_data: The tool's input parameters dict.

        Returns:
            A compact summary string for progress logging.
        """
        # Simple key-lookup tools: "ToolName {value}"
        key = _TOOL_SUMMARY_KEY_MAP.get(name)
        if key is not None:
            return f"{name} {input_data.get(key, '')}"

        # Static tools: just the tool name
        if name in _TOOL_SUMMARY_STATIC:
            return name

        # Custom-format tools
        if name == "Bash":
            cmd = input_data.get("command", "")
            return f"$ {_truncate_with_ellipsis(cmd, _COMMAND_PREVIEW_MAX_LENGTH)}"
        if name == "Grep":
            pattern = input_data.get("pattern", "")
            return f"Grep /{pattern}/"
        if name == "WebFetch":
            url = input_data.get("url", "")
            return f"WebFetch {url}"
        if name == "WebSearch":
            query = input_data.get("query", "")
            return f"WebSearch {query!r}" if query else "WebSearch"
        if name == "Agent":
            desc = input_data.get("description", "")
            return f"Agent: {desc}" if desc else "Agent"
        if name == "MultiTool":
            tool_uses = input_data.get("tool_uses", [])
            count = len(tool_uses) if isinstance(tool_uses, list) else 0
            return f"MultiTool ({count} tools)"
        if name == "Skill":
            skill = input_data.get("skill", "")
            return f"Skill: {skill}" if skill else "Skill"
        if name == "CronCreate":
            prompt = _truncate_with_ellipsis(
                input_data.get("prompt", ""), _COMMAND_PREVIEW_MAX_LENGTH
            )
            return f"CronCreate {prompt!r}" if prompt else "CronCreate"
        if name == "CronDelete":
            cron_id = input_data.get("id", "")
            return f"CronDelete {cron_id}" if cron_id else "CronDelete"
        if name == "EnterWorktree":
            wt_name = input_data.get("name", "")
            return f"EnterWorktree {wt_name}" if wt_name else "EnterWorktree"
        if name == "ExitWorktree":
            action = input_data.get("action", "")
            return f"ExitWorktree {action}" if action else "ExitWorktree"
        return f"tool: {name}"

    def result_text(self) -> str:
        """Return the final result text from the parsed stream.

        Prefers the explicit ``result`` event payload. Falls back to
        concatenated assistant text blocks if no result event was received.

        Returns:
            The result text, or an empty string if no output was captured.
        """
        if self._result:
            return self._result
        if self._text_parts:
            return "".join(self._text_parts)
        return ""

    @property
    def session_id(self) -> str:
        """Return the session ID captured from the result event.

        The session ID enables ``--continue`` in subsequent Claude Code CLI
        invocations to continue the same conversation.

        Returns:
            The session ID string, or empty if not available.
        """
        return self._session_id

    @property
    def cost_metadata(self) -> dict[str, Any]:
        """Return cost and usage metadata from the result event.

        Returns:
            Dict with ``total_cost_usd``, ``duration_ms``, and ``usage``
            keys (only present when values were received).
        """
        meta: dict[str, Any] = {}
        if self._total_cost_usd is not None:
            meta["total_cost_usd"] = self._total_cost_usd
        if self._duration_ms is not None:
            meta["duration_ms"] = self._duration_ms
        if self._usage:
            meta["usage"] = dict(self._usage)
        return meta


class ClaudeCodeHand(_TwoPhaseCLIHand):
    """Hand backed by Claude Code CLI subprocess execution."""

    _BACKEND_NAME = "claudecodecli"
    _CLI_LABEL = "claudecodecli"
    _CLI_DISPLAY_NAME = "Claude Code CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_CLAUDE_CLI_CMD"
    _DEFAULT_CLI_CMD = "claude -p"
    _DEFAULT_MODEL = "claude-opus-4-6"
    _DEFAULT_APPEND_ARGS = ("-p",)
    _CONTAINER_ENABLED_ENV_VAR = "HELPING_HANDS_CLAUDE_CONTAINER"
    _CONTAINER_IMAGE_ENV_VAR = "HELPING_HANDS_CLAUDE_CONTAINER_IMAGE"
    _NATIVE_CLI_AUTH_ENV_VAR = "HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH"
    _VERBOSE_CLI_FLAGS = ("--verbose",)
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._last_session_id: str = ""
        self._cumulative_cost_usd: float = 0.0

    @property
    def cost_metadata(self) -> dict[str, Any]:
        """Return cumulative cost/usage data from prior invocations.

        Populated as result events flow through ``_invoke_claude``.

        Returns:
            Dict with ``total_cost_usd`` and ``session_id`` keys when
            available.
        """
        meta: dict[str, Any] = {}
        if self._cumulative_cost_usd:
            meta["total_cost_usd"] = self._cumulative_cost_usd
        if self._last_session_id:
            meta["session_id"] = self._last_session_id
        return meta

    def _native_cli_auth_env_names(self) -> tuple[str, ...]:
        return ("ANTHROPIC_API_KEY",)

    def _describe_auth(self) -> str:
        """Describe the current Anthropic authentication state.

        Returns:
            Human-readable string indicating whether ``ANTHROPIC_API_KEY``
            is set.
        """
        present = self._env_var_status("ANTHROPIC_API_KEY")
        return f"auth=ANTHROPIC_API_KEY ({present})"

    def _pr_description_cmd(self) -> list[str] | None:
        if shutil.which("claude") is not None:
            return ["claude", "-p", "--output-format", "text"]
        return None

    _EXTRA_AUTH_TOKENS: tuple[str, ...] = ("anthropic_api_key",)
    """Backend-specific auth error tokens checked alongside shared ones."""

    @staticmethod
    def _build_claude_failure_message(*, return_code: int, output: str) -> str:
        """Build a human-readable failure message from Claude Code CLI output.

        Delegates to :func:`_format_cli_failure` with Claude-specific
        parameters for auth detection and remediation guidance.

        Args:
            return_code: Process exit code.
            output: Combined stdout/stderr from the Claude Code CLI process.

        Returns:
            Formatted error message with output tail and optional auth hint.
        """
        return _format_cli_failure(
            backend_name="Claude Code CLI",
            return_code=return_code,
            output=output,
            env_var_hint="ANTHROPIC_API_KEY",
            extra_tokens=ClaudeCodeHand._EXTRA_AUTH_TOKENS,
        )

    def _resolve_cli_model(self) -> str:
        """Resolve the CLI model, filtering out incompatible non-Anthropic models.

        Rejects GPT-family models (``gpt-*``) and explicitly OpenAI-prefixed
        models (``openai/*``) that survive the base-class provider strip.

        Returns:
            The resolved model name, or an empty string if the model is
            missing or incompatible with Claude Code.
        """
        model = super()._resolve_cli_model()
        if not model:
            return ""
        lowered = model.lower()
        if lowered.startswith(("gpt-", "openai/")):
            logger.warning(
                "Model %r is incompatible with Claude Code CLI — "
                "falling back to CLI default model",
                model,
            )
            return ""
        return model

    def _skip_permissions_enabled(self) -> bool:
        """Check whether ``--dangerously-skip-permissions`` should be added.

        Reads the ``HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS`` env var
        (default ``"1"``). Even when enabled, returns ``False`` if the process
        is running as root (UID 0), because Claude Code rejects the flag
        under root privileges.

        Returns:
            ``True`` if the flag should be injected into the command.
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
            except (ValueError, OSError):
                logger.debug("geteuid() check failed", exc_info=True)
        return True

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        if (
            cmd
            and cmd[0] == "claude"
            and self._skip_permissions_enabled()
            and _SKIP_PERMISSIONS_FLAG not in cmd
        ):
            return [cmd[0], _SKIP_PERMISSIONS_FLAG, *cmd[1:]]
        return cmd

    def _retry_command_after_failure(
        self,
        cmd: list[str],
        *,
        output: str,
        return_code: int,
    ) -> list[str] | None:
        if return_code == 0:
            return None
        if _SKIP_PERMISSIONS_FLAG not in cmd:
            return None
        lowered = output.lower()
        if self._ROOT_PERMISSION_ERROR.lower() not in lowered:
            return None
        return [token for token in cmd if token != _SKIP_PERMISSIONS_FLAG]

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        return self._build_claude_failure_message(
            return_code=return_code,
            output=output,
        )

    def _no_change_error_after_retries(
        self,
        *,
        prompt: str,
        combined_output: str,
    ) -> str | None:
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
        if not cmd or cmd[0] != "claude":
            return None
        if shutil.which("npx") is None:
            return None
        return ["npx", "-y", "@anthropic-ai/claude-code", *cmd[1:]]

    @staticmethod
    def _inject_output_format(cmd: list[str], fmt: str) -> list[str]:
        """Insert ``--output-format <fmt>`` before the ``-p`` flag."""
        if has_cli_flag(cmd, "output-format"):
            return cmd
        try:
            p_idx = cmd.index("-p")
        except ValueError:
            p_idx = len(cmd)
        return [*cmd[:p_idx], "--output-format", fmt, *cmd[p_idx:]]

    @staticmethod
    def _p_index(cmd: list[str]) -> int:
        """Return index of the ``-p`` flag, or ``len(cmd)`` if absent."""
        try:
            return cmd.index("-p")
        except ValueError:
            return len(cmd)

    # ------------------------------------------------------------------
    # --max-turns support
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_max_turns() -> int:
        """Resolve the ``--max-turns`` limit from the environment.

        Reads ``HELPING_HANDS_CLAUDE_MAX_TURNS`` (default ``0`` = unlimited).
        Non-numeric or non-positive values are treated as unlimited.

        Returns:
            The max turns integer, or ``0`` for unlimited.
        """
        raw = os.environ.get("HELPING_HANDS_CLAUDE_MAX_TURNS", "")
        if not raw.strip():
            return _DEFAULT_MAX_TURNS
        try:
            value = int(raw.strip())
        except ValueError:
            logger.warning(
                "HELPING_HANDS_CLAUDE_MAX_TURNS has non-integer value %r, "
                "using unlimited",
                raw,
            )
            return _DEFAULT_MAX_TURNS
        return value if value > 0 else _DEFAULT_MAX_TURNS

    @classmethod
    def _inject_max_turns(cls, cmd: list[str], max_turns: int) -> list[str]:
        """Insert ``--max-turns <n>`` before the ``-p`` flag if not present."""
        if max_turns <= 0:
            return cmd
        if has_cli_flag(cmd, "max-turns"):
            return cmd
        p_idx = cls._p_index(cmd)
        return [*cmd[:p_idx], "--max-turns", str(max_turns), *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --append-system-prompt support (AGENT.md / CLAUDE.md auto-read)
    # ------------------------------------------------------------------

    def _read_agent_doc(self) -> str:
        """Read the first available agent doc from the repo root.

        Checks ``_AGENT_DOC_CANDIDATES`` in order and returns the first
        file's content, truncated to ``_SYSTEM_PROMPT_MAX_LENGTH``.

        Returns:
            The file content, or empty if no candidate exists.
        """
        root = self.repo_index.root
        for candidate in _AGENT_DOC_CANDIDATES:
            path = root / candidate
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    logger.debug("Failed to read %s", path, exc_info=True)
                    continue
                if len(content) > _SYSTEM_PROMPT_MAX_LENGTH:
                    content = content[:_SYSTEM_PROMPT_MAX_LENGTH] + "\n...[truncated]"
                return content
        return ""

    def _resolve_system_prompt(self) -> str:
        """Resolve the ``--append-system-prompt`` content.

        Priority: ``HELPING_HANDS_CLAUDE_SYSTEM_PROMPT`` env var, then auto-read
        from AGENT.md/CLAUDE.md in the repo root.

        Returns:
            The system prompt string, or empty if nothing to inject.
        """
        explicit = os.environ.get("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", "").strip()
        if explicit:
            return explicit
        return self._read_agent_doc()

    @classmethod
    def _inject_system_prompt(cls, cmd: list[str], prompt: str) -> list[str]:
        """Insert ``--append-system-prompt <text>`` before ``-p`` if absent."""
        if not prompt:
            return cmd
        if has_cli_flag(cmd, "append-system-prompt") or has_cli_flag(
            cmd, "system-prompt"
        ):
            return cmd
        p_idx = cls._p_index(cmd)
        return [*cmd[:p_idx], "--append-system-prompt", prompt, *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --allowedTools / --disallowedTools support
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_tool_filters() -> tuple[list[str], list[str]]:
        """Resolve allowed and disallowed tool lists from the environment.

        Reads ``HELPING_HANDS_CLAUDE_ALLOWED_TOOLS`` and
        ``HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS`` as comma-separated lists.

        Returns:
            ``(allowed, disallowed)`` tuple of tool name lists.
        """
        allowed_raw = os.environ.get("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", "")
        disallowed_raw = os.environ.get("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", "")
        allowed = [t.strip() for t in allowed_raw.split(",") if t.strip()]
        disallowed = [t.strip() for t in disallowed_raw.split(",") if t.strip()]
        return allowed, disallowed

    @classmethod
    def _inject_tool_filters(
        cls,
        cmd: list[str],
        *,
        allowed: list[str],
        disallowed: list[str],
    ) -> list[str]:
        """Insert ``--allowedTools`` / ``--disallowedTools`` before ``-p``."""
        if not allowed and not disallowed:
            return cmd
        p_idx = cls._p_index(cmd)
        extra: list[str] = []
        if allowed and not has_cli_flag(cmd, "allowedTools"):
            extra.extend(["--allowedTools", ",".join(allowed)])
        if disallowed and not has_cli_flag(cmd, "disallowedTools"):
            extra.extend(["--disallowedTools", ",".join(disallowed)])
        if not extra:
            return cmd
        return [*cmd[:p_idx], *extra, *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --continue session resumption support
    # ------------------------------------------------------------------

    @staticmethod
    def _session_continue_enabled() -> bool:
        """Check whether session continuation is enabled.

        Reads ``HELPING_HANDS_CLAUDE_SESSION_CONTINUE`` (default ``"0"``;
        opt-in to avoid surprising apply-changes invocations with stale
        context). Returns ``True`` when the env var is truthy.
        """
        raw = os.environ.get("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", "0")
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _inject_continue(cls, cmd: list[str], session_id: str) -> list[str]:
        """Inject ``--continue --session-id <id>`` before ``-p``.

        Both flags compose with ``-p`` in current Claude Code (>= 2.x), so
        we keep ``-p`` intact and just prepend the new flags.

        Args:
            cmd: Command tokens.
            session_id: Session ID from a prior invocation (empty = no-op).

        Returns:
            Command tokens with continuation flags injected when applicable.
        """
        if not session_id:
            return cmd
        if has_cli_flag(cmd, "continue") or has_cli_flag(cmd, "resume"):
            return cmd
        p_idx = cls._p_index(cmd)
        extra: list[str] = ["--continue"]
        if not has_cli_flag(cmd, "session-id"):
            extra.extend(["--session-id", session_id])
        return [*cmd[:p_idx], *extra, *cmd[p_idx:]]

    def _build_cli_cmd(self, prompt: str) -> list[str]:
        """Render the CLI command and apply opt-in feature flag injections.

        The order is:

        1. Base render (``_render_command``) — model, prompt, defaults.
        2. ``--output-format stream-json`` for the streaming parser.
        3. ``--max-turns`` if configured.
        4. ``--append-system-prompt`` from env or AGENT.md/CLAUDE.md.
        5. ``--allowedTools`` / ``--disallowedTools`` from env.
        6. ``--continue --session-id`` if continuation is enabled and we
           captured a session ID from a prior invocation.

        Returns:
            Ready-to-execute command token list.
        """
        cmd = self._render_command(prompt)
        cmd = self._inject_output_format(cmd, _OUTPUT_FORMAT_STREAM_JSON)
        cmd = self._inject_max_turns(cmd, self._resolve_max_turns())
        cmd = self._inject_system_prompt(cmd, self._resolve_system_prompt())
        allowed, disallowed = self._resolve_tool_filters()
        cmd = self._inject_tool_filters(cmd, allowed=allowed, disallowed=disallowed)
        if self._session_continue_enabled() and self._last_session_id:
            cmd = self._inject_continue(cmd, self._last_session_id)
        return cmd

    async def _invoke_claude(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        model = self._resolve_cli_model() or "(default)"
        await emit(self._label_msg(f"model={model}") + "\n")
        cmd = self._build_cli_cmd(prompt)
        parser = _StreamJsonEmitter(emit, self._CLI_LABEL)
        try:
            raw = await self._invoke_cli_with_cmd(cmd, emit=parser)
        finally:
            await parser.flush()
        if parser.session_id:
            self._last_session_id = parser.session_id
        meta = parser.cost_metadata
        cost = meta.get("total_cost_usd")
        if isinstance(cost, int | float):
            self._cumulative_cost_usd += float(cost)
        return parser.result_text() or raw

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_claude(prompt, emit=emit)
