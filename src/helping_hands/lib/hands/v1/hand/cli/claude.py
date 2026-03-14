"""Claude Code CLI hand implementation."""

from __future__ import annotations

import json
import logging
import os
import shutil

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

logger = logging.getLogger(__name__)

__all__ = ["ClaudeCodeHand"]

# --- Module-level constants ---------------------------------------------------

_TEXT_PREVIEW_MAX_LENGTH = 200
"""Maximum length for assistant text previews before truncation."""

_TOOL_RESULT_PREVIEW_MAX_LENGTH = 150
"""Maximum length for tool result previews before truncation."""

_COMMAND_PREVIEW_MAX_LENGTH = 80
"""Maximum length for Bash command / CronCreate prompt previews."""

_FAILURE_OUTPUT_TAIL_LENGTH = 2000
"""Number of trailing characters kept from CLI output in failure messages."""

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

    async def __call__(self, chunk: str) -> None:
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

    async def _process_line(self, line: str) -> None:
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            # Not JSON (verbose logs, heartbeats) — pass through.
            await self._emit(line + "\n")
            return

        event_type = event.get("type", "")

        if event_type == _EVENT_TYPE_ASSISTANT:
            # Claude Code stream-json: message is a full Anthropic API message
            # with message.content[] array of {type: "text"} / {type: "tool_use"}.
            message = event.get("message")
            if not isinstance(message, dict):
                return
            for block in message.get("content", []):
                block_type = block.get("type", "")
                if block_type == _BLOCK_TYPE_TOOL_USE:
                    name = block.get("name", "unknown")
                    input_data = block.get("input", {})
                    summary = self._summarize_tool(name, input_data)
                    await self._emit(f"[{self._label}] {summary}\n")
                elif block_type == _BLOCK_TYPE_TEXT:
                    text = block.get("text", "")
                    if text:
                        self._text_parts.append(text)
                        preview = text.strip().replace("\n", " ")
                        if len(preview) > _TEXT_PREVIEW_MAX_LENGTH:
                            preview = preview[: _TEXT_PREVIEW_MAX_LENGTH - 3] + "..."
                        if preview:
                            await self._emit(f"[{self._label}] {preview}\n")

        elif event_type == _EVENT_TYPE_USER:
            # Tool results: message.content[] array of {type: "tool_result"}.
            message = event.get("message")
            if not isinstance(message, dict):
                return
            for block in message.get("content", []):
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
                    preview = content.strip().replace("\n", " ")
                    if len(preview) > _TOOL_RESULT_PREVIEW_MAX_LENGTH:
                        preview = preview[: _TOOL_RESULT_PREVIEW_MAX_LENGTH - 3] + "..."
                    await self._emit(f"[{self._label}] -> {preview}\n")

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
                await self._emit(f"[{self._label}] api: {', '.join(parts)}\n")

    @staticmethod
    def _summarize_tool(name: str, input_data: dict) -> str:
        if name == "Read":
            path = input_data.get("file_path", "")
            return f"Read {path}"
        if name == "Edit":
            path = input_data.get("file_path", "")
            return f"Edit {path}"
        if name == "Write":
            path = input_data.get("file_path", "")
            return f"Write {path}"
        if name == "Bash":
            cmd = input_data.get("command", "")
            if len(cmd) > _COMMAND_PREVIEW_MAX_LENGTH:
                cmd = cmd[: _COMMAND_PREVIEW_MAX_LENGTH - 3] + "..."
            return f"$ {cmd}"
        if name == "Glob":
            pattern = input_data.get("pattern", "")
            return f"Glob {pattern}"
        if name == "Grep":
            pattern = input_data.get("pattern", "")
            return f"Grep /{pattern}/"
        if name == "Agent":
            desc = input_data.get("description", "")
            return f"Agent: {desc}" if desc else "Agent"
        if name == "WebFetch":
            url = input_data.get("url", "")
            return f"WebFetch {url}"
        if name == "WebSearch":
            query = input_data.get("query", "")
            return f"WebSearch {query!r}" if query else "WebSearch"
        if name == "NotebookEdit":
            path = input_data.get("notebook_path", "")
            return f"NotebookEdit {path}"
        if name == "TodoWrite":
            return "TodoWrite"
        if name == "MultiTool":
            tool_uses = input_data.get("tool_uses", [])
            count = len(tool_uses) if isinstance(tool_uses, list) else 0
            return f"MultiTool ({count} tools)"
        if name == "Skill":
            skill = input_data.get("skill", "")
            return f"Skill: {skill}" if skill else "Skill"
        if name == "CronCreate":
            prompt = input_data.get("prompt", "")
            if len(prompt) > _COMMAND_PREVIEW_MAX_LENGTH:
                prompt = prompt[: _COMMAND_PREVIEW_MAX_LENGTH - 3] + "..."
            return f"CronCreate {prompt!r}" if prompt else "CronCreate"
        if name == "CronDelete":
            cron_id = input_data.get("id", "")
            return f"CronDelete {cron_id}" if cron_id else "CronDelete"
        if name == "CronList":
            return "CronList"
        if name == "EnterWorktree":
            wt_name = input_data.get("name", "")
            return f"EnterWorktree {wt_name}" if wt_name else "EnterWorktree"
        if name == "ExitWorktree":
            action = input_data.get("action", "")
            return f"ExitWorktree {action}" if action else "ExitWorktree"
        return f"tool: {name}"

    def result_text(self) -> str:
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

    def _pr_description_cmd(self) -> list[str] | None:
        if shutil.which("claude") is not None:
            return ["claude", "-p", "--output-format", "text"]
        return None

    @staticmethod
    def _build_claude_failure_message(*, return_code: int, output: str) -> str:
        tail = output.strip()[-_FAILURE_OUTPUT_TAIL_LENGTH:]
        if _TwoPhaseCLIHand._is_auth_error(tail, extra_tokens=("anthropic_api_key",)):
            return (
                "Claude Code CLI authentication failed. "
                "Ensure ANTHROPIC_API_KEY is set in this runtime. "
                "If running app mode in Docker, set ANTHROPIC_API_KEY in .env "
                "and recreate server/worker containers.\n"
                f"Output:\n{tail}"
            )
        return f"Claude Code CLI failed (exit={return_code}). Output:\n{tail}"

    def _resolve_cli_model(self) -> str:
        model = super()._resolve_cli_model()
        if not model:
            return ""
        lowered = model.lower()
        if lowered.startswith("gpt-"):
            return ""
        return model

    def _skip_permissions_enabled(self) -> bool:
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
            except Exception:
                logger.debug("geteuid() check failed", exc_info=True)
        return True

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        if (
            cmd
            and cmd[0] == "claude"
            and self._skip_permissions_enabled()
            and "--dangerously-skip-permissions" not in cmd
        ):
            return [cmd[0], "--dangerously-skip-permissions", *cmd[1:]]
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
        if "--dangerously-skip-permissions" not in cmd:
            return None
        lowered = output.lower()
        if self._ROOT_PERMISSION_ERROR.lower() not in lowered:
            return None
        return [token for token in cmd if token != "--dangerously-skip-permissions"]

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        return self._build_claude_failure_message(
            return_code=return_code,
            output=output,
        )

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"Claude Code CLI command not found: {command!r}. "
            "Set HELPING_HANDS_CLAUDE_CLI_CMD to a valid command."
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
        if any(t == "--output-format" or t.startswith("--output-format=") for t in cmd):
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
        await emit(f"[{self._CLI_LABEL}] model={model}\n")
        cmd = self._render_command(prompt)
        cmd = self._inject_output_format(cmd, "stream-json")
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
