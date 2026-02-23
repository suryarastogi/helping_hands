"""CLI-oriented hand backends for external assistant CLIs.

This module provides subprocess-backed two-phase backends that:
1. run an initialization/learning pass over repository context, then
2. execute the user task prompt with that learned summary.

Implemented:
- ``CodexCLIHand``
- ``ClaudeCodeHand``

Scaffold:
- ``GeminiCLIHand``
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
from collections.abc import AsyncIterator
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse


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
    _RETRY_ON_NO_CHANGES = False
    _SUMMARY_CHAR_LIMIT = 6000

    class _Emitter(Protocol):
        async def __call__(self, chunk: str) -> None: ...

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)
        self._active_process: asyncio.subprocess.Process | None = None

    @staticmethod
    def _truncate_summary(text: str, *, limit: int) -> str:
        clean = text.strip()
        if len(clean) <= limit:
            return clean
        return f"{clean[:limit]}\n...[truncated]"

    @staticmethod
    def _is_truthy(value: str | None) -> bool:
        if value is None:
            return False
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        if len(tokens) == 1 and self._DEFAULT_APPEND_ARGS:
            return [*tokens, *self._DEFAULT_APPEND_ARGS]
        return tokens

    def _base_command(self) -> list[str]:
        raw = os.environ.get(self._COMMAND_ENV_VAR, self._DEFAULT_CLI_CMD)
        tokens = shlex.split(raw)
        if not tokens:
            msg = f"{self._COMMAND_ENV_VAR} resolved to an empty command."
            raise RuntimeError(msg)
        return self._normalize_base_command(tokens)

    def _resolve_cli_model(self) -> str:
        model = str(self.config.model).strip()
        if not model or model == "default":
            return self._DEFAULT_MODEL
        if "/" in model:
            _, _, provider_model = model.partition("/")
            if provider_model:
                return provider_model
        return model

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        return cmd

    def _render_command(self, prompt: str) -> list[str]:
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

        has_explicit_model_flag = any(
            token == "--model" or token.startswith("--model=") for token in rendered
        )
        if (
            resolved_model
            and not used_model_placeholder
            and not has_explicit_model_flag
        ):
            rendered.extend(["--model", resolved_model])

        if not has_prompt_placeholder:
            rendered.append(prompt)
        rendered = self._apply_backend_defaults(rendered)
        return self._wrap_container_if_enabled(rendered)

    def _container_enabled(self) -> bool:
        if not self._CONTAINER_ENABLED_ENV_VAR:
            return False
        raw = os.environ.get(self._CONTAINER_ENABLED_ENV_VAR, "")
        if raw == "":
            return False
        return self._is_truthy(raw)

    def _container_image(self) -> str:
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
        return (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "HELPING_HANDS_MODEL",
        )

    def _wrap_container_if_enabled(self, cmd: list[str]) -> list[str]:
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
        for env_name in self._container_env_names():
            value = os.environ.get(env_name)
            if value:
                docker_cmd.extend(["-e", f"{env_name}={value}"])
        docker_cmd.append(image)
        docker_cmd.extend(cmd)
        return docker_cmd

    def _execution_mode(self) -> str:
        if self._container_enabled():
            return "container+workspace-write"
        return "workspace-write"

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        tail = output.strip()[-2000:]
        return f"{self._CLI_DISPLAY_NAME} failed (exit={return_code}). Output:\n{tail}"

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"{self._CLI_DISPLAY_NAME} command not found: {command!r}. "
            f"Set {self._COMMAND_ENV_VAR} to a valid command."
        )

    def _fallback_command_when_not_found(self, cmd: list[str]) -> list[str] | None:
        return None

    def _retry_command_after_failure(
        self,
        cmd: list[str],
        *,
        output: str,
        return_code: int,
    ) -> list[str] | None:
        return None

    def _build_init_prompt(self) -> str:
        file_list = "\n".join(f"- {path}" for path in self.repo_index.files[:200])
        if not file_list:
            file_list = "- (no indexed files)"
        return (
            "Initialization phase: learn this repository before task execution.\n"
            f"Repository root: {self.repo_index.root}\n"
            "Goals:\n"
            "1. Read README.md and AGENT.md if they exist.\n"
            "2. Learn conventions from the file tree snapshot.\n"
            "3. Output a concise implementation-oriented summary.\n"
            "Do not ask the user for file contents.\n"
            "Do not perform edits in this phase.\n\n"
            "Indexed files:\n"
            f"{file_list}\n"
        )

    def _build_task_prompt(self, *, prompt: str, learned_summary: str) -> str:
        summary = self._truncate_summary(
            learned_summary,
            limit=self._SUMMARY_CHAR_LIMIT,
        )
        return (
            "Task execution phase.\n\n"
            "Repository context learned from initialization:\n"
            f"{summary or '(no summary produced)'}\n\n"
            "User task request:\n"
            f"{prompt}\n\n"
            "Implement the task directly in the repository. "
            "Do not ask the user to paste files."
        )

    def _repo_has_changes(self) -> bool:
        repo_root = self.repo_index.root.resolve()
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())

    @staticmethod
    def _looks_like_edit_request(prompt: str) -> bool:
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
        )
        return any(marker in lowered for marker in action_markers)

    def _should_retry_without_changes(self, prompt: str) -> bool:
        if not self._RETRY_ON_NO_CHANGES:
            return False
        if self._is_interrupted():
            return False
        if not self._looks_like_edit_request(prompt):
            return False
        return not self._repo_has_changes()

    def _build_apply_changes_prompt(self, *, prompt: str, task_output: str) -> str:
        summarized_output = self._truncate_summary(task_output, limit=2000)
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

    async def _terminate_active_process(self) -> None:
        process = self._active_process
        if process is None or process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
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
        env = dict(os.environ)
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo_index.root.resolve()),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
        except FileNotFoundError as exc:
            fallback = self._fallback_command_when_not_found(cmd)
            if fallback and fallback != cmd:
                await emit(
                    f"[{self._CLI_LABEL}] {cmd[0]!r} not found; "
                    f"retrying with {fallback[0]!r}.\n"
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

        try:
            while True:
                if self._is_interrupted():
                    await self._terminate_active_process()
                    break

                data = await stdout.read(1024)
                if not data:
                    break

                text = data.decode("utf-8", errors="replace")
                chunks.append(text)
                await emit(text)

            if not self._is_interrupted():
                return_code = await process.wait()
                if return_code != 0:
                    output = "".join(chunks)
                    retry_cmd = self._retry_command_after_failure(
                        cmd,
                        output=output,
                        return_code=return_code,
                    )
                    if retry_cmd and retry_cmd != cmd:
                        await emit(
                            f"[{self._CLI_LABEL}] command failed; retrying with "
                            "adjusted permissions flags.\n"
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
        await emit(f"[{self._CLI_LABEL}] isolation={self._execution_mode()}\n")
        await emit(
            f"[{self._CLI_LABEL}] [phase 1/2] Initializing repository context...\n"
        )
        init_output = await self._invoke_backend(self._build_init_prompt(), emit=emit)
        if self._is_interrupted():
            await emit(f"[{self._CLI_LABEL}] Interrupted during initialization.\n")
            return init_output

        await emit(f"[{self._CLI_LABEL}] [phase 2/2] Executing user task...\n")
        task_output = await self._invoke_backend(
            self._build_task_prompt(prompt=prompt, learned_summary=init_output),
            emit=emit,
        )
        combined_output = f"{init_output}{task_output}"

        if self._should_retry_without_changes(prompt):
            await emit(
                f"[{self._CLI_LABEL}] No file edits detected; "
                "requesting direct file application...\n"
            )
            apply_output = await self._invoke_backend(
                self._build_apply_changes_prompt(
                    prompt=prompt,
                    task_output=task_output,
                ),
                emit=emit,
            )
            combined_output += apply_output

        return combined_output

    async def _collect_run_output(self, prompt: str) -> str:
        chunks: list[str] = []

        async def _emit(chunk: str) -> None:
            chunks.append(chunk)

        await self._run_two_phase(prompt, emit=_emit)
        return "".join(chunks)

    def _interrupted_pr_metadata(self) -> dict[str, str]:
        return {
            "auto_pr": str(self.auto_pr).lower(),
            "pr_status": "interrupted",
            "pr_url": "",
            "pr_number": "",
            "pr_branch": "",
            "pr_commit": "",
        }

    def _finalize_after_run(self, *, prompt: str, message: str) -> dict[str, str]:
        if self._is_interrupted():
            return self._interrupted_pr_metadata()

        summary = self._truncate_summary(message, limit=self._SUMMARY_CHAR_LIMIT)
        return self._finalize_repo_pr(
            backend=self._BACKEND_NAME,
            prompt=prompt,
            summary=summary,
        )

    def _format_pr_status_message(self, metadata: dict[str, str]) -> str | None:
        status = metadata.get("pr_status", "")
        if not status:
            return None
        if status == "created":
            pr_url = metadata.get("pr_url", "")
            return f"[{self._CLI_LABEL}] PR created: {pr_url}"
        if status == "disabled":
            return f"[{self._CLI_LABEL}] PR disabled (--no-pr)."
        if status == "no_changes":
            return f"[{self._CLI_LABEL}] PR skipped: no file changes detected."
        if status == "interrupted":
            return f"[{self._CLI_LABEL}] Interrupted."
        error = metadata.get("pr_error", "").strip()
        if error:
            return f"[{self._CLI_LABEL}] PR status: {status} ({error})"
        return f"[{self._CLI_LABEL}] PR status: {status}"

    def interrupt(self) -> None:
        super().interrupt()
        process = self._active_process
        if process is not None and process.returncode is None:
            process.terminate()

    def run(self, prompt: str) -> HandResponse:
        message = asyncio.run(self._collect_run_output(prompt))
        pr_metadata = self._finalize_after_run(prompt=prompt, message=message)
        return HandResponse(
            message=message,
            metadata={
                "backend": self._BACKEND_NAME,
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
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


class CodexCLIHand(_TwoPhaseCLIHand):
    """Hand backed by Codex CLI subprocess execution."""

    _BACKEND_NAME = "codexcli"
    _CLI_LABEL = "codexcli"
    _CLI_DISPLAY_NAME = "Codex CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_CODEX_CLI_CMD"
    _DEFAULT_CLI_CMD = "codex exec"
    _DEFAULT_MODEL = "gpt-5.2"
    _DEFAULT_SANDBOX_MODE = "workspace-write"
    _DEFAULT_SANDBOX_MODE_IN_CONTAINER = "danger-full-access"
    _DEFAULT_SKIP_GIT_REPO_CHECK = "1"
    _CONTAINER_ENABLED_ENV_VAR = "HELPING_HANDS_CODEX_CONTAINER"
    _CONTAINER_IMAGE_ENV_VAR = "HELPING_HANDS_CODEX_CONTAINER_IMAGE"

    @staticmethod
    def _build_codex_failure_message(*, return_code: int, output: str) -> str:
        tail = output.strip()[-2000:]
        lower_tail = tail.lower()
        if (
            "401 unauthorized" in lower_tail
            or "missing bearer or basic authentication" in lower_tail
        ):
            return (
                "Codex CLI authentication failed (401 Unauthorized). "
                "Ensure OPENAI_API_KEY is set in this runtime. "
                "If running app mode in Docker, set OPENAI_API_KEY in .env "
                "and recreate server/worker containers.\n"
                f"Output:\n{tail}"
            )
        return f"Codex CLI failed (exit={return_code}). Output:\n{tail}"

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        if tokens[0] == "codex" and len(tokens) == 1:
            return ["codex", "exec"]
        return super()._normalize_base_command(tokens)

    def _apply_codex_exec_sandbox_defaults(self, cmd: list[str]) -> list[str]:
        if len(cmd) < 2 or cmd[0] != "codex" or cmd[1] != "exec":
            return cmd
        if any(token == "--sandbox" or token.startswith("--sandbox=") for token in cmd):
            return cmd
        sandbox_mode = os.environ.get("HELPING_HANDS_CODEX_SANDBOX_MODE")
        if sandbox_mode is None:
            sandbox_mode = self._auto_sandbox_mode()
        else:
            sandbox_mode = sandbox_mode.strip() or self._auto_sandbox_mode()
        if not sandbox_mode:
            sandbox_mode = self._auto_sandbox_mode()
        return [*cmd[:2], "--sandbox", sandbox_mode, *cmd[2:]]

    def _auto_sandbox_mode(self) -> str:
        if Path("/.dockerenv").exists():
            return self._DEFAULT_SANDBOX_MODE_IN_CONTAINER
        return self._DEFAULT_SANDBOX_MODE

    def _skip_git_repo_check_enabled(self) -> bool:
        raw = os.environ.get(
            "HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK",
            self._DEFAULT_SKIP_GIT_REPO_CHECK,
        )
        return self._is_truthy(raw)

    def _apply_codex_exec_git_repo_check_defaults(self, cmd: list[str]) -> list[str]:
        if len(cmd) < 2 or cmd[0] != "codex" or cmd[1] != "exec":
            return cmd
        if any(
            token == "--skip-git-repo-check"
            or token.startswith("--skip-git-repo-check")
            for token in cmd
        ):
            return cmd
        if not self._skip_git_repo_check_enabled():
            return cmd
        return [*cmd[:2], "--skip-git-repo-check", *cmd[2:]]

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        cmd = self._apply_codex_exec_sandbox_defaults(cmd)
        return self._apply_codex_exec_git_repo_check_defaults(cmd)

    def _build_failure_message(self, *, return_code: int, output: str) -> str:
        return self._build_codex_failure_message(
            return_code=return_code,
            output=output,
        )

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"Codex CLI command not found: {command!r}. "
            "Set HELPING_HANDS_CODEX_CLI_CMD to a valid command. "
            "If running app mode in Docker, rebuild worker images so "
            "the codex binary is installed."
        )

    async def _invoke_codex(
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
        return await self._invoke_codex(prompt, emit=emit)


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
    _DEFAULT_SKIP_PERMISSIONS = "1"
    _RETRY_ON_NO_CHANGES = True
    _ROOT_PERMISSION_ERROR = (
        "--dangerously-skip-permissions cannot be used with root/sudo privileges"
    )

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

    def _fallback_command_when_not_found(self, cmd: list[str]) -> list[str] | None:
        if not cmd or cmd[0] != "claude":
            return None
        if shutil.which("npx") is None:
            return None
        return ["npx", "-y", "@anthropic-ai/claude-code", *cmd[1:]]

    async def _invoke_claude(
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
        return await self._invoke_claude(prompt, emit=emit)


class GeminiCLIHand(Hand):
    """Hand backed by Gemini CLI via a terminal/bash invocation.

    This backend would run the Gemini CLI as a subprocess with repo context
    and the user prompt, then capture stdout/stderr. Not yet implemented;
    this class is scaffolding for future integration.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="geminicli",
            prompt=prompt,
            summary="GeminiCLI hand not yet implemented.",
        )
        return HandResponse(
            message="GeminiCLI hand not yet implemented.",
            metadata={
                "backend": "geminicli",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "GeminiCLI hand not yet implemented."
