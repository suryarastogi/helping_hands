"""Claude Code CLI hand implementation."""

from __future__ import annotations

import json
import os
import shutil

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand


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

        if event_type == "assistant":
            # Claude Code stream-json: message is a full Anthropic API message
            # with message.content[] array of {type: "text"} / {type: "tool_use"}.
            message = event.get("message", {})
            for block in message.get("content", []):
                block_type = block.get("type", "")
                if block_type == "tool_use":
                    name = block.get("name", "unknown")
                    input_data = block.get("input", {})
                    summary = self._summarize_tool(name, input_data)
                    await self._emit(f"[{self._label}] {summary}\n")
                elif block_type == "text":
                    text = block.get("text", "")
                    if text:
                        self._text_parts.append(text)
                        preview = text.strip().replace("\n", " ")
                        if len(preview) > 200:
                            preview = preview[:197] + "..."
                        if preview:
                            await self._emit(f"[{self._label}] {preview}\n")

        elif event_type == "user":
            # Tool results: message.content[] array of {type: "tool_result"}.
            message = event.get("message", {})
            for block in message.get("content", []):
                if block.get("type") != "tool_result":
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
                    if len(preview) > 150:
                        preview = preview[:147] + "..."
                    await self._emit(f"[{self._label}] -> {preview}\n")

        elif event_type == "result":
            self._result = event.get("result", "")
            cost = event.get("total_cost_usd")
            duration = event.get("duration_ms")
            parts: list[str] = []
            if cost is not None:
                parts.append(f"${cost:.4f}")
            if duration is not None:
                parts.append(f"{duration / 1000:.1f}s")
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
            if len(cmd) > 80:
                cmd = cmd[:77] + "..."
            return f"$ {cmd}"
        if name == "Glob":
            pattern = input_data.get("pattern", "")
            return f"Glob {pattern}"
        if name == "Grep":
            pattern = input_data.get("pattern", "")
            return f"Grep /{pattern}/"
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
    _DEFAULT_MODEL = ""
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
        tail = output.strip()[-2000:]
        lower_tail = tail.lower()
        if any(
            token in lower_tail
            for token in (
                "401 unauthorized",
                "unauthorized",
                "authentication failed",
                "invalid api key",
                "anthropic_api_key",
            )
        ):
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
                pass
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
        cmd = self._render_command(prompt)
        cmd = self._inject_output_format(cmd, "stream-json")
        parser = _StreamJsonEmitter(emit, self._CLI_LABEL)
        raw = await self._invoke_cli_with_cmd(cmd, emit=parser)
        await parser.flush()
        return parser.result_text() or raw

    async def _invoke_backend(
        self,
        prompt: str,
        *,
        emit: _TwoPhaseCLIHand._Emitter,
    ) -> str:
        return await self._invoke_claude(prompt, emit=emit)
