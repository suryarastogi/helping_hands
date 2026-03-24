"""Claude Code CLI hand implementation."""

from __future__ import annotations

import json
import logging
import os
import shutil

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
            cost = event.get("total_cost_usd")
            duration = event.get("duration_ms")
            usage = event.get("usage")
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
                    if out is not None:
                        tok_parts.append(f"out={out}")
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

    async def _invoke_claude(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        model = self._resolve_cli_model() or "(default)"
        await emit(self._label_msg(f"model={model}") + "\n")
        cmd = self._render_command(prompt)
        cmd = self._inject_output_format(cmd, _OUTPUT_FORMAT_STREAM_JSON)
        parser = _StreamJsonEmitter(emit, self._CLI_LABEL)
        try:
            raw = await self._invoke_cli_with_cmd(cmd, emit=parser)
        finally:
            await parser.flush()
        return parser.result_text() or raw

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_claude(prompt, emit=emit)
