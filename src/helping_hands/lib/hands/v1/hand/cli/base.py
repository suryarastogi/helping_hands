"""Shared two-phase subprocess base for CLI-backed hands.

Defines ``_TwoPhaseCLIHand``, the abstract base that all external-CLI
hand backends inherit.  Provides the two-phase execution model
(initialization + task), async subprocess streaming with heartbeat and
idle-timeout, optional Docker container wrapping, and native-CLI-auth
support.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any, Protocol

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse


class _TwoPhaseCLIHand(Hand):
    """Shared two-phase subprocess base for CLI-driven backends.

    All CLI hands (``codexcli``, ``claudecodecli``, ``goose``,
    ``geminicli``) extend this class and run in two phases:

    1. **Initialization pass** — feeds repo context (README, AGENT.md,
       file tree snapshot) to the external CLI so it understands the
       codebase before making changes.
    2. **Task pass** — sends the user prompt to the CLI to apply the
       requested changes directly.

    Shared infrastructure:

    * Async subprocess streaming with configurable I/O poll interval,
      heartbeat logging during quiet periods, and idle-timeout
      termination.
    * Optional containerized execution (Docker bind-mount of target
      repo).
    * Native CLI auth toggle (``--use-native-cli-auth``) to strip
      provider API key env vars from the subprocess environment.
    * Final PR finalization inherited from ``Hand``.

    Subclasses override ``_base_command()``,
    ``_apply_backend_defaults()``, and ``_build_*_prompt()`` methods to
    specialize behavior for each CLI tool.
    """

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
    _DEFAULT_IO_POLL_SECONDS = 2.0
    _DEFAULT_HEARTBEAT_SECONDS = 20.0
    _DEFAULT_IDLE_TIMEOUT_SECONDS = 900.0

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

        if not has_prompt_placeholder and not self._inject_prompt_argument(
            rendered, prompt
        ):
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

    def _use_native_cli_auth(self) -> bool:
        return bool(getattr(self.config, "use_native_cli_auth", False))

    def _native_cli_auth_env_names(self) -> tuple[str, ...]:
        return ()

    def _describe_auth(self) -> str:
        """Return a human-readable auth summary for the startup banner."""
        native_env_names = self._native_cli_auth_env_names()
        if not native_env_names:
            return ""
        env_label = ", ".join(native_env_names)
        if self._use_native_cli_auth():
            return f"auth=native-cli ({env_label} stripped)"
        set_vars = [n for n in native_env_names if os.environ.get(n, "").strip()]
        if set_vars:
            return f"auth={', '.join(set_vars)}"
        return f"auth=native-cli (no {env_label} set, using CLI session)"

    def _effective_container_env_names(self) -> tuple[str, ...]:
        env_names = self._container_env_names()
        if not self._use_native_cli_auth():
            return env_names
        blocked = set(self._native_cli_auth_env_names())
        if not blocked:
            return env_names
        return tuple(name for name in env_names if name not in blocked)

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
        for env_name in self._effective_container_env_names():
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

    @staticmethod
    def _float_env(name: str, *, default: float) -> float:
        raw = os.environ.get(name)
        if raw is None:
            return default
        try:
            value = float(raw.strip())
        except ValueError:
            return default
        if value <= 0:
            return default
        return value

    def _io_poll_seconds(self) -> float:
        return self._float_env(
            "HELPING_HANDS_CLI_IO_POLL_SECONDS",
            default=self._DEFAULT_IO_POLL_SECONDS,
        )

    def _heartbeat_seconds(self) -> float:
        return self._float_env(
            "HELPING_HANDS_CLI_HEARTBEAT_SECONDS",
            default=self._DEFAULT_HEARTBEAT_SECONDS,
        )

    def _idle_timeout_seconds(self) -> float:
        return self._float_env(
            "HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS",
            default=self._DEFAULT_IDLE_TIMEOUT_SECONDS,
        )

    def _build_subprocess_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if not self._use_native_cli_auth():
            return env
        for env_name in self._native_cli_auth_env_names():
            env.pop(env_name, None)
        return env

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
            "Execution context: this hand is running inside a non-interactive "
            "helping_hands script started by the user.\n"
            "Do not ask the user for additional approvals or interactive input.\n"
            "Use only tools that are actually available in this runtime.\n"
            "If required write/edit tools are unavailable, report that briefly "
            "and stop instead of retrying unavailable tools.\n"
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

    def _no_change_error_after_retries(
        self,
        *,
        prompt: str,
        combined_output: str,
    ) -> str | None:
        del prompt
        del combined_output
        return None

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
        env = self._build_subprocess_env()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo_index.root.resolve()),
                stdin=asyncio.subprocess.DEVNULL,
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
                if fallback[0] == "npx":
                    await emit(
                        f"[{self._CLI_LABEL}] npx fallback may take a while on "
                        "first run while the package is downloaded.\n"
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
                        stdout.read(1024),
                        timeout=io_poll_seconds,
                    )
                except TimeoutError as exc:
                    if process.returncode is not None:
                        break
                    now = asyncio.get_running_loop().time()
                    idle_seconds = now - last_output_ts
                    if now - last_heartbeat_ts >= heartbeat_seconds:
                        await emit(
                            f"[{self._CLI_LABEL}] still running "
                            f"({int(idle_seconds)}s since last output; "
                            f"timeout={int(idle_timeout_seconds)}s)...\n"
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
                            "adjusted arguments.\n"
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
        auth = self._describe_auth()
        auth_part = f" | {auth}" if auth else ""
        await emit(
            f"[{self._CLI_LABEL}] isolation={self._execution_mode()}{auth_part}\n"
        )
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
