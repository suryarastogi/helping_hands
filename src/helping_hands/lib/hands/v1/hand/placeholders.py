"""CLI-oriented hand backends for external assistant CLIs.

The Claude and Gemini hands remain scaffolds. ``CodexCLIHand`` is implemented
as a subprocess-backed backend that:
1. runs an initialization/learning pass over the repository context, then
2. runs the user task prompt,
while streaming output and supporting cooperative interruption.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
from collections.abc import AsyncIterator
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse


class ClaudeCodeHand(Hand):
    """Hand backed by Claude Code via a terminal/bash invocation.

    This backend would run the Claude Code CLI (or equivalent) as a
    subprocess: e.g. a terminal/bash call that passes the repo path and
    user prompt, then captures stdout/stderr. Not yet implemented; this
    class is scaffolding for future integration.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="claudecode",
            prompt=prompt,
            summary="ClaudeCode hand not yet implemented.",
        )
        return HandResponse(
            message="ClaudeCode hand not yet implemented.",
            metadata={
                "backend": "claudecode",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "ClaudeCode hand not yet implemented."


class CodexCLIHand(Hand):
    """Hand backed by Codex CLI subprocess execution.

    The hand runs two phases:
    1. initialize/learn repository context (README/AGENT/tree conventions),
    2. execute the user task with that learned summary.
    """

    _DEFAULT_CLI_CMD = "codex exec"
    _DEFAULT_CODEX_MODEL = "gpt-5.2"
    _DEFAULT_SANDBOX_MODE = "workspace-write"
    _DEFAULT_SANDBOX_MODE_IN_CONTAINER = "danger-full-access"
    _DEFAULT_SKIP_GIT_REPO_CHECK = "1"
    _SUMMARY_CHAR_LIMIT = 6000

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)
        self._active_process: asyncio.subprocess.Process | None = None

    class _Emitter(Protocol):
        async def __call__(self, chunk: str) -> None: ...

    @staticmethod
    def _truncate_summary(text: str, *, limit: int) -> str:
        clean = text.strip()
        if len(clean) <= limit:
            return clean
        return f"{clean[:limit]}\n...[truncated]"

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

    def _base_command(self) -> list[str]:
        raw = os.environ.get("HELPING_HANDS_CODEX_CLI_CMD", self._DEFAULT_CLI_CMD)
        tokens = shlex.split(raw)
        if not tokens:
            msg = "HELPING_HANDS_CODEX_CLI_CMD resolved to an empty command."
            raise RuntimeError(msg)

        # ``codex`` with no subcommand opens interactive mode; ensure non-interactive.
        if tokens[0] == "codex" and len(tokens) == 1:
            tokens.append("exec")
        return tokens

    def _resolve_codex_model(self) -> str:
        model = str(self.config.model).strip()
        if not model or model == "default":
            return self._DEFAULT_CODEX_MODEL
        if "/" in model:
            _, _, provider_model = model.partition("/")
            if provider_model:
                return provider_model
        return model

    def _render_command(self, prompt: str) -> list[str]:
        resolved_model = self._resolve_codex_model()
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
        if not used_model_placeholder and not has_explicit_model_flag:
            rendered.extend(["--model", resolved_model])

        if not has_prompt_placeholder:
            rendered.append(prompt)
        rendered = self._apply_codex_exec_sandbox_defaults(rendered)
        rendered = self._apply_codex_exec_git_repo_check_defaults(rendered)
        return self._wrap_container_if_enabled(rendered)

    @staticmethod
    def _is_truthy(value: str | None) -> bool:
        if value is None:
            return False
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _container_enabled(self) -> bool:
        raw = os.environ.get("HELPING_HANDS_CODEX_CONTAINER", "")
        if raw == "":
            return False
        return self._is_truthy(raw)

    def _container_image(self) -> str:
        image = os.environ.get("HELPING_HANDS_CODEX_CONTAINER_IMAGE", "").strip()
        if not image:
            msg = (
                "HELPING_HANDS_CODEX_CONTAINER_IMAGE must be set when "
                "HELPING_HANDS_CODEX_CONTAINER is enabled."
            )
            raise RuntimeError(msg)
        return image

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

    def _wrap_container_if_enabled(self, cmd: list[str]) -> list[str]:
        if not self._container_enabled():
            return cmd
        image = self._container_image()
        if shutil.which("docker") is None:
            msg = (
                "HELPING_HANDS_CODEX_CONTAINER is enabled but docker is not "
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
        for env_name in (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "HELPING_HANDS_MODEL",
        ):
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

    async def _invoke_codex(
        self,
        prompt: str,
        *,
        emit: _Emitter,
    ) -> str:
        cmd = self._render_command(prompt)
        # Pass env explicitly so Codex CLI sees OPENAI_API_KEY etc. (Celery worker
        # may not pass env to child on some setups).
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
            msg = (
                f"Codex CLI command not found: {cmd[0]!r}. "
                "Set HELPING_HANDS_CODEX_CLI_CMD to a valid command. "
                "If running app mode in Docker, rebuild worker images so "
                "the codex binary is installed."
            )
            raise RuntimeError(msg) from exc

        self._active_process = process
        chunks: list[str] = []
        stdout = process.stdout
        if stdout is None:
            await process.wait()
            self._active_process = None
            msg = "Codex CLI did not expose stdout pipe."
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
                    msg = self._build_codex_failure_message(
                        return_code=return_code,
                        output="".join(chunks),
                    )
                    raise RuntimeError(msg)
            return "".join(chunks)
        finally:
            self._active_process = None

    async def _run_two_phase(
        self,
        prompt: str,
        *,
        emit: _Emitter,
    ) -> str:
        self.reset_interrupt()
        await emit(f"[codexcli] isolation={self._execution_mode()}\n")
        await emit("[codexcli] [phase 1/2] Initializing repository context...\n")
        init_output = await self._invoke_codex(self._build_init_prompt(), emit=emit)
        if self._is_interrupted():
            await emit("[codexcli] Interrupted during initialization.\n")
            return init_output

        await emit("[codexcli] [phase 2/2] Executing user task...\n")
        task_output = await self._invoke_codex(
            self._build_task_prompt(prompt=prompt, learned_summary=init_output),
            emit=emit,
        )
        return f"{init_output}{task_output}"

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
            backend="codexcli",
            prompt=prompt,
            summary=summary,
        )

    @staticmethod
    def _format_pr_status_message(metadata: dict[str, str]) -> str | None:
        status = metadata.get("pr_status", "")
        if not status:
            return None
        if status == "created":
            pr_url = metadata.get("pr_url", "")
            return f"[codexcli] PR created: {pr_url}"
        if status == "disabled":
            return "[codexcli] PR disabled (--no-pr)."
        if status == "no_changes":
            return "[codexcli] PR skipped: no file changes detected."
        if status == "interrupted":
            return "[codexcli] Interrupted."
        error = metadata.get("pr_error", "").strip()
        if error:
            return f"[codexcli] PR status: {status} ({error})"
        return f"[codexcli] PR status: {status}"

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
                "backend": "codexcli",
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
