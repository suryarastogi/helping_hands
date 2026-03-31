"""Claude Code CLI hand implementation."""

from __future__ import annotations

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

_EVENT_TYPE_SYSTEM = "system"
"""Event type for system messages (configuration, model info, etc.)."""

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
"""Default max turns (0 = unlimited). Set via HELPING_HANDS_CLAUDE_MAX_TURNS."""

_SYSTEM_PROMPT_MAX_LENGTH = 12000
"""Maximum character length for ``--append-system-prompt`` content."""

_AGENT_DOC_CANDIDATES = ("AGENT.md", "agent.md", "CLAUDE.md")
"""Filenames to read from repo root for ``--append-system-prompt`` injection."""

_DEFAULT_THINKING_BUDGET = 0
"""Default thinking-budget-tokens (0 = omit flag). Set via env var."""

_MCP_CONFIG_MAX_SIZE = 64 * 1024
"""Maximum size (bytes) for MCP config files to prevent accidental huge reads."""


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
        self._active_subagents: int = 0
        self._total_subagents: int = 0
        self._model: str = ""
        self._is_error: bool = False

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
                    if name == "Agent":
                        self._total_subagents += 1
                        self._active_subagents += 1
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

        elif event_type == _EVENT_TYPE_SYSTEM:
            # System events carry model info and configuration.
            model = event.get("model", "")
            if isinstance(model, str) and model:
                self._model = model

        elif event_type == _EVENT_TYPE_RESULT:
            self._result = event.get("result", "")
            self._is_error = bool(event.get("is_error", False))
            # Capture session ID for --continue / --resume support.
            session_id = event.get("session_id", "")
            if isinstance(session_id, str) and session_id:
                self._session_id = session_id
            cost = event.get("total_cost_usd")
            duration = event.get("duration_ms")
            usage = event.get("usage")
            if cost is not None:
                self._total_cost_usd = float(cost)
            if duration is not None:
                self._duration_ms = float(duration)
            parts: list[str] = []
            if cost is not None:
                parts.append(f"${cost:.4f}")
            if duration is not None:
                parts.append(f"{duration / 1000:.1f}s")
            if isinstance(usage, dict):
                inp = usage.get("input_tokens")
                out = usage.get("output_tokens")
                if inp is not None or out is not None:
                    tok_parts: list[str] = []
                    if inp is not None:
                        tok_parts.append(f"in={inp}")
                        self._usage["input_tokens"] = int(inp)
                    if out is not None:
                        tok_parts.append(f"out={out}")
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
        if name == "ToolSearch":
            query = input_data.get("query", "")
            return f"ToolSearch {query!r}" if query else "ToolSearch"
        if name == "SendMessage":
            to = input_data.get("to", "")
            return f"SendMessage -> {to}" if to else "SendMessage"
        if name == "TaskOutput":
            task_id = input_data.get("id", "")
            return f"TaskOutput {task_id}" if task_id else "TaskOutput"
        if name == "TaskStop":
            task_id = input_data.get("id", "")
            return f"TaskStop {task_id}" if task_id else "TaskStop"
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

        The session ID enables ``--continue`` / ``--resume`` in subsequent
        Claude Code CLI invocations to continue the same conversation.

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

    @property
    def model(self) -> str:
        """Return the model name captured from a system event.

        Returns:
            The model string, or empty if no system event was received.
        """
        return self._model

    @property
    def is_error(self) -> bool:
        """Return whether the result event indicated an error.

        Returns:
            ``True`` if the result was flagged as an error.
        """
        return self._is_error

    @property
    def total_subagents(self) -> int:
        """Return the total number of Agent tool invocations observed.

        Returns:
            Count of Agent tool_use blocks seen in the stream.
        """
        return self._total_subagents


class ClaudeCodeHand(_TwoPhaseCLIHand):
    """Hand backed by Claude Code CLI subprocess execution.

    Supports advanced Claude Code CLI features via environment variables:

    - ``HELPING_HANDS_CLAUDE_MAX_TURNS``: Limit the number of agentic turns
      per invocation (maps to ``--max-turns``). Default: unlimited.
    - ``HELPING_HANDS_CLAUDE_SYSTEM_PROMPT``: Custom system prompt injected
      via ``--append-system-prompt``. When not set, the hand auto-reads
      ``AGENT.md`` or ``CLAUDE.md`` from the repo root.
    - ``HELPING_HANDS_CLAUDE_ALLOWED_TOOLS``: Comma-separated list of Claude
      Code tool names to allow (maps to ``--allowedTools``).
    - ``HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS``: Comma-separated list of
      Claude Code tool names to disallow (maps to ``--disallowedTools``).
    - ``HELPING_HANDS_CLAUDE_SESSION_CONTINUE``: Set to ``1`` to enable
      session continuation (``--continue``) for the apply-changes enforcement
      phase, reusing the session from the task phase.
    - ``HELPING_HANDS_CLAUDE_MCP_CONFIG``: Path to a JSON MCP config file
      passed via ``--mcp-config`` to give Claude access to external MCP tools.
    - ``HELPING_HANDS_CLAUDE_THINKING_BUDGET``: Token budget for extended
      thinking (maps to ``--thinking-budget-tokens``). Default: omitted.
    - ``HELPING_HANDS_CLAUDE_PERMISSION_MODE``: Permission mode string
      (e.g. ``plan``, ``default``) for ``--permission-mode``.
    """

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

    def __init__(self, config: Any, repo_index: Any) -> None:
        """Initialize the Claude Code CLI hand.

        Args:
            config: Application configuration (model, verbose, tools, etc.).
            repo_index: Repository index providing the file tree and root path.
        """
        super().__init__(config, repo_index)
        self._last_session_id: str = ""
        self._cumulative_cost_usd: float = 0.0
        self._cumulative_input_tokens: int = 0
        self._cumulative_output_tokens: int = 0
        self._next_invoke_continue: bool = False

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

    @staticmethod
    def _inject_max_turns(cmd: list[str], max_turns: int) -> list[str]:
        """Insert ``--max-turns <n>`` before the ``-p`` flag if not present.

        Args:
            cmd: Command tokens.
            max_turns: Maximum turn count (0 = skip injection).

        Returns:
            Command tokens with ``--max-turns`` injected when applicable.
        """
        if max_turns <= 0:
            return cmd
        if has_cli_flag(cmd, "max-turns"):
            return cmd
        try:
            p_idx = cmd.index("-p")
        except ValueError:
            p_idx = len(cmd)
        return [*cmd[:p_idx], "--max-turns", str(max_turns), *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --append-system-prompt support (AGENT.md / CLAUDE.md injection)
    # ------------------------------------------------------------------

    def _read_agent_doc(self) -> str:
        """Read the first available agent doc from the repo root.

        Checks ``_AGENT_DOC_CANDIDATES`` in order and returns the first
        file's content, truncated to ``_SYSTEM_PROMPT_MAX_LENGTH``.

        Returns:
            The file content string, or empty if no candidate exists.
        """
        root = self.repo_index.root
        for candidate in _AGENT_DOC_CANDIDATES:
            path = root / candidate
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                    if len(content) > _SYSTEM_PROMPT_MAX_LENGTH:
                        content = (
                            content[:_SYSTEM_PROMPT_MAX_LENGTH] + "\n...[truncated]"
                        )
                    return content
                except OSError:
                    logger.debug("Failed to read %s", path, exc_info=True)
        return ""

    def _resolve_system_prompt(self) -> str:
        """Resolve the ``--append-system-prompt`` content.

        Priority: ``HELPING_HANDS_CLAUDE_SYSTEM_PROMPT`` env var → auto-read
        from AGENT.md/CLAUDE.md in the repo root.

        Returns:
            The system prompt string, or empty if nothing to inject.
        """
        explicit = os.environ.get("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", "").strip()
        if explicit:
            return explicit
        return self._read_agent_doc()

    @staticmethod
    def _inject_system_prompt(cmd: list[str], prompt: str) -> list[str]:
        """Insert ``--append-system-prompt <text>`` before ``-p`` if not present.

        Args:
            cmd: Command tokens.
            prompt: System prompt text (empty = skip injection).

        Returns:
            Command tokens with the flag injected when applicable.
        """
        if not prompt:
            return cmd
        if has_cli_flag(cmd, "append-system-prompt"):
            return cmd
        if has_cli_flag(cmd, "system-prompt"):
            return cmd
        try:
            p_idx = cmd.index("-p")
        except ValueError:
            p_idx = len(cmd)
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

    @staticmethod
    def _inject_tool_filters(
        cmd: list[str],
        *,
        allowed: list[str],
        disallowed: list[str],
    ) -> list[str]:
        """Insert ``--allowedTools`` and/or ``--disallowedTools`` flags.

        Args:
            cmd: Command tokens.
            allowed: Tool names to allow (empty = skip).
            disallowed: Tool names to disallow (empty = skip).

        Returns:
            Command tokens with tool filter flags injected.
        """
        if not allowed and not disallowed:
            return cmd
        try:
            p_idx = cmd.index("-p")
        except ValueError:
            p_idx = len(cmd)
        extra: list[str] = []
        if allowed and not has_cli_flag(cmd, "allowedTools"):
            extra.extend(["--allowedTools", ",".join(allowed)])
        if disallowed and not has_cli_flag(cmd, "disallowedTools"):
            extra.extend(["--disallowedTools", ",".join(disallowed)])
        return [*cmd[:p_idx], *extra, *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --continue session resumption support
    # ------------------------------------------------------------------

    def _session_continue_enabled(self) -> bool:
        """Check whether session continuation is enabled.

        Reads ``HELPING_HANDS_CLAUDE_SESSION_CONTINUE`` (default ``"1"``).

        Returns:
            ``True`` if the apply-changes phase should reuse the session.
        """
        raw = os.environ.get("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", "1")
        return self._is_truthy(raw)

    @staticmethod
    def _inject_continue_session(cmd: list[str], session_id: str) -> list[str]:
        """Replace ``-p`` with ``--continue`` and inject the session ID.

        When a session ID is available from a prior invocation, this replaces
        the ``-p`` (print) flag with ``--continue`` so Claude Code continues
        the existing conversation instead of starting a new one.

        Args:
            cmd: Command tokens containing ``-p``.
            session_id: Session ID from a prior result event.

        Returns:
            Command tokens with ``--continue`` and ``--session-id`` injected.
        """
        if not session_id:
            return cmd
        if has_cli_flag(cmd, "continue") or has_cli_flag(cmd, "resume"):
            return cmd
        result = list(cmd)
        # Replace -p with --continue (both accept a prompt argument).
        try:
            p_idx = result.index("-p")
            result[p_idx] = "--continue"
        except ValueError:
            return cmd
        # Inject --session-id before the prompt.
        if not has_cli_flag(result, "session-id"):
            result.insert(p_idx, session_id)
            result.insert(p_idx, "--session-id")
        return result

    # ------------------------------------------------------------------
    # --mcp-config support
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_mcp_config() -> str:
        """Resolve the ``--mcp-config`` file path from the environment.

        Reads ``HELPING_HANDS_CLAUDE_MCP_CONFIG``. The file must exist and
        be a valid JSON file within the size limit.

        Returns:
            The validated file path string, or empty if not configured.
        """
        raw = os.environ.get("HELPING_HANDS_CLAUDE_MCP_CONFIG", "").strip()
        if not raw:
            return ""
        import pathlib

        path = pathlib.Path(raw).expanduser().resolve()
        if not path.is_file():
            logger.warning(
                "HELPING_HANDS_CLAUDE_MCP_CONFIG path %r does not exist, skipping",
                raw,
            )
            return ""
        try:
            size = path.stat().st_size
        except OSError:
            logger.warning("Cannot stat MCP config %r, skipping", raw, exc_info=True)
            return ""
        if size > _MCP_CONFIG_MAX_SIZE:
            logger.warning(
                "MCP config %r is %d bytes (max %d), skipping",
                raw,
                size,
                _MCP_CONFIG_MAX_SIZE,
            )
            return ""
        return str(path)

    @staticmethod
    def _inject_mcp_config(cmd: list[str], config_path: str) -> list[str]:
        """Insert ``--mcp-config <path>`` before the ``-p`` flag if not present.

        Args:
            cmd: Command tokens.
            config_path: Path to the MCP config JSON file (empty = skip).

        Returns:
            Command tokens with ``--mcp-config`` injected when applicable.
        """
        if not config_path:
            return cmd
        if has_cli_flag(cmd, "mcp-config"):
            return cmd
        try:
            p_idx = cmd.index("-p")
        except ValueError:
            p_idx = len(cmd)
        return [*cmd[:p_idx], "--mcp-config", config_path, *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --thinking-budget-tokens support
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_thinking_budget() -> int:
        """Resolve the ``--thinking-budget-tokens`` value from the environment.

        Reads ``HELPING_HANDS_CLAUDE_THINKING_BUDGET`` (default ``0`` = omit).
        Non-numeric or non-positive values are treated as omit.

        Returns:
            The thinking budget integer, or ``0`` to omit the flag.
        """
        raw = os.environ.get("HELPING_HANDS_CLAUDE_THINKING_BUDGET", "")
        if not raw.strip():
            return _DEFAULT_THINKING_BUDGET
        try:
            value = int(raw.strip())
        except ValueError:
            logger.warning(
                "HELPING_HANDS_CLAUDE_THINKING_BUDGET has non-integer value %r, "
                "omitting flag",
                raw,
            )
            return _DEFAULT_THINKING_BUDGET
        return value if value > 0 else _DEFAULT_THINKING_BUDGET

    @staticmethod
    def _inject_thinking_budget(cmd: list[str], budget: int) -> list[str]:
        """Insert ``--thinking-budget-tokens <n>`` before ``-p`` if not present.

        Args:
            cmd: Command tokens.
            budget: Token budget for extended thinking (0 = skip injection).

        Returns:
            Command tokens with ``--thinking-budget-tokens`` injected.
        """
        if budget <= 0:
            return cmd
        if has_cli_flag(cmd, "thinking-budget-tokens"):
            return cmd
        try:
            p_idx = cmd.index("-p")
        except ValueError:
            p_idx = len(cmd)
        return [*cmd[:p_idx], "--thinking-budget-tokens", str(budget), *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --permission-mode support
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_permission_mode() -> str:
        """Resolve the ``--permission-mode`` value from the environment.

        Reads ``HELPING_HANDS_CLAUDE_PERMISSION_MODE``. When set, this is
        passed directly to the Claude CLI. Common values include
        ``plan``, ``default``, and ``bypassPermissions``.

        Returns:
            The permission mode string, or empty if not configured.
        """
        return os.environ.get("HELPING_HANDS_CLAUDE_PERMISSION_MODE", "").strip()

    @staticmethod
    def _inject_permission_mode(cmd: list[str], mode: str) -> list[str]:
        """Insert ``--permission-mode <mode>`` before ``-p`` if not present.

        Args:
            cmd: Command tokens.
            mode: Permission mode string (empty = skip injection).

        Returns:
            Command tokens with ``--permission-mode`` injected when applicable.
        """
        if not mode:
            return cmd
        if has_cli_flag(cmd, "permission-mode"):
            return cmd
        try:
            p_idx = cmd.index("-p")
        except ValueError:
            p_idx = len(cmd)
        return [*cmd[:p_idx], "--permission-mode", mode, *cmd[p_idx:]]

    # ------------------------------------------------------------------
    # --resume support (continue without a new prompt)
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_resume_session(cmd: list[str], session_id: str) -> list[str]:
        """Replace ``-p`` with ``--resume`` and inject the session ID.

        Unlike ``--continue`` which takes a new prompt, ``--resume`` resumes
        the session without additional user input. Useful for retrying after
        max-turns or interruptions.

        Args:
            cmd: Command tokens containing ``-p``.
            session_id: Session ID from a prior result event.

        Returns:
            Command tokens with ``--resume`` and ``--session-id`` injected,
            with the prompt argument removed.
        """
        if not session_id:
            return cmd
        if has_cli_flag(cmd, "resume") or has_cli_flag(cmd, "continue"):
            return cmd
        result = list(cmd)
        try:
            p_idx = result.index("-p")
        except ValueError:
            return cmd
        # Remove -p and the prompt argument that follows it.
        if p_idx + 1 < len(result):
            result.pop(p_idx + 1)
        result[p_idx] = "--resume"
        # Inject --session-id before --resume.
        if not has_cli_flag(result, "session-id"):
            result.insert(p_idx, session_id)
            result.insert(p_idx, "--session-id")
        return result

    # ------------------------------------------------------------------
    # Cost tracking
    # ------------------------------------------------------------------

    def _accumulate_cost(self, parser: _StreamJsonEmitter) -> None:
        """Accumulate cost and usage metadata from a completed invocation.

        Args:
            parser: The stream parser that processed the CLI output.
        """
        meta = parser.cost_metadata
        if "total_cost_usd" in meta:
            self._cumulative_cost_usd += meta["total_cost_usd"]
        usage = meta.get("usage", {})
        self._cumulative_input_tokens += usage.get("input_tokens", 0)
        self._cumulative_output_tokens += usage.get("output_tokens", 0)

    # ------------------------------------------------------------------
    # Core invocation (overrides)
    # ------------------------------------------------------------------

    async def _invoke_claude(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Invoke the Claude Code CLI with all configured enhancements.

        When ``_next_invoke_continue`` is True and a session ID is available
        from a prior invocation, the command uses ``--continue`` instead of
        ``-p`` to resume the existing conversation. The flag is automatically
        reset after each invocation.

        Args:
            prompt: Task prompt to send to Claude Code.
            emit: Async callback for streaming output chunks.

        Returns:
            The parsed result text from the stream-json output.
        """
        # Consume the continue flag (reset after use).
        continue_session = self._next_invoke_continue
        self._next_invoke_continue = False

        model = self._resolve_cli_model() or "(default)"
        await emit(self._label_msg(f"model={model}") + "\n")
        cmd = self._render_command(prompt)
        cmd = self._inject_output_format(cmd, _OUTPUT_FORMAT_STREAM_JSON)

        # --max-turns
        max_turns = self._resolve_max_turns()
        cmd = self._inject_max_turns(cmd, max_turns)
        if max_turns > 0 and self.config.verbose:
            await emit(self._label_msg(f"max-turns={max_turns}") + "\n")

        # --append-system-prompt (AGENT.md / CLAUDE.md injection)
        system_prompt = self._resolve_system_prompt()
        if system_prompt:
            cmd = self._inject_system_prompt(cmd, system_prompt)
            if self.config.verbose:
                preview = system_prompt[:80].replace("\n", " ")
                await emit(
                    self._label_msg(
                        f"system-prompt injected ({len(system_prompt)} chars): {preview}..."
                    )
                    + "\n"
                )

        # --allowedTools / --disallowedTools
        allowed, disallowed = self._resolve_tool_filters()
        cmd = self._inject_tool_filters(cmd, allowed=allowed, disallowed=disallowed)
        if allowed and self.config.verbose:
            await emit(self._label_msg(f"allowedTools={','.join(allowed)}") + "\n")
        if disallowed and self.config.verbose:
            await emit(
                self._label_msg(f"disallowedTools={','.join(disallowed)}") + "\n"
            )

        # --mcp-config
        mcp_config = self._resolve_mcp_config()
        if mcp_config:
            cmd = self._inject_mcp_config(cmd, mcp_config)
            if self.config.verbose:
                await emit(self._label_msg(f"mcp-config={mcp_config}") + "\n")

        # --thinking-budget-tokens
        thinking_budget = self._resolve_thinking_budget()
        cmd = self._inject_thinking_budget(cmd, thinking_budget)
        if thinking_budget > 0 and self.config.verbose:
            await emit(self._label_msg(f"thinking-budget={thinking_budget}") + "\n")

        # --permission-mode
        permission_mode = self._resolve_permission_mode()
        if permission_mode:
            cmd = self._inject_permission_mode(cmd, permission_mode)
            if self.config.verbose:
                await emit(self._label_msg(f"permission-mode={permission_mode}") + "\n")

        # --continue session resumption
        if continue_session and self._last_session_id:
            cmd = self._inject_continue_session(cmd, self._last_session_id)
            await emit(
                self._label_msg(f"continuing session {self._last_session_id[:12]}...")
                + "\n"
            )

        parser = _StreamJsonEmitter(emit, self._CLI_LABEL)
        try:
            raw = await self._invoke_cli_with_cmd(cmd, emit=parser)
        finally:
            await parser.flush()

        # Capture session ID for potential --continue reuse.
        if parser.session_id:
            self._last_session_id = parser.session_id

        # Accumulate cost tracking.
        self._accumulate_cost(parser)

        return parser.result_text() or raw

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_claude(prompt, emit=emit)

    async def _run_two_phase_inner(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        """Run the two-phase flow with Claude-specific enhancements.

        Overrides the base to use ``--continue`` for the apply-changes
        enforcement phase when session continuation is enabled, and to
        emit cumulative cost summary at the end.
        """
        import time

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
        init_output = await self._invoke_claude(self._build_init_prompt(), emit=emit)
        if self._is_interrupted():
            await emit(self._label_msg("Interrupted during initialization.\n"))
            return init_output
        if self.config.verbose:
            phase1_elapsed = time.monotonic() - run_start
            await emit(self._label_msg(f"phase 1 completed in {phase1_elapsed:.1f}s\n"))

        phase2_start = time.monotonic()
        await emit(self._label_msg("[phase 2/2] Executing user task...\n"))
        task_output = await self._invoke_claude(
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
            # Set flag so next _invoke_claude uses --continue.
            self._next_invoke_continue = self._session_continue_enabled() and bool(
                self._last_session_id
            )
            apply_output = await self._invoke_claude(
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

        # Emit cumulative cost summary.
        if self._cumulative_cost_usd > 0:
            await emit(
                self._label_msg(
                    f"total cost: ${self._cumulative_cost_usd:.4f} "
                    f"(in={self._cumulative_input_tokens}, "
                    f"out={self._cumulative_output_tokens})\n"
                )
            )

        return combined_output
