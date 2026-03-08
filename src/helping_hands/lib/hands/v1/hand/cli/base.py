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
from pathlib import Path
from typing import Any, Protocol

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse

logger = logging.getLogger(__name__)


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
    _VERBOSE_CLI_FLAGS: tuple[str, ...] = ()
    _SUMMARY_CHAR_LIMIT = 6000
    _DEFAULT_IO_POLL_SECONDS = 2.0
    _DEFAULT_HEARTBEAT_SECONDS = 20.0
    _DEFAULT_HEARTBEAT_SECONDS_VERBOSE = 5.0
    _DEFAULT_IDLE_TIMEOUT_SECONDS = 900.0

    class _Emitter(Protocol):
        async def __call__(self, chunk: str) -> None: ...

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)
        self._active_process: asyncio.subprocess.Process | None = None
        self._skill_catalog_dir: Path | None = None

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

    def _apply_verbose_flags(self, cmd: list[str]) -> list[str]:
        """Inject verbose CLI flags before the prompt argument.

        Flags are inserted right after the binary name (index 1) so they
        appear before ``-p``/``--prompt`` and the prompt text itself.
        Some CLIs ignore flags that appear after the prompt argument.
        """
        if not self.config.verbose or not self._VERBOSE_CLI_FLAGS:
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
        rendered = self._apply_verbose_flags(rendered)
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
            "Implement the task directly in the repository. "
            "Do not ask the user to paste files."
            f"{tool_section}"
            f"{skill_section}"
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
        cwd = str(self.repo_index.root.resolve())
        if self.config.verbose:
            await emit(f"[{self._CLI_LABEL}] cmd: {shlex.join(cmd)}\n")
            await emit(f"[{self._CLI_LABEL}] cwd: {cwd}\n")
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
                elapsed = time.monotonic() - start_time
                if self.config.verbose:
                    await emit(
                        f"[{self._CLI_LABEL}] finished in {elapsed:.1f}s "
                        f"(exit={return_code})\n"
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
        auth = self._describe_auth()
        auth_part = f" | {auth}" if auth else ""
        await emit(
            f"[{self._CLI_LABEL}] isolation={self._execution_mode()}{auth_part}\n"
        )
        if self.config.verbose:
            model = self._resolve_cli_model() or "(default)"
            await emit(
                f"[{self._CLI_LABEL}] verbose=on | model={model} "
                f"| heartbeat={self._heartbeat_seconds():.0f}s "
                f"| idle_timeout={self._idle_timeout_seconds():.0f}s\n"
            )
        run_start = time.monotonic()
        await emit(
            f"[{self._CLI_LABEL}] [phase 1/2] Initializing repository context...\n"
        )
        init_output = await self._invoke_backend(self._build_init_prompt(), emit=emit)
        if self._is_interrupted():
            await emit(f"[{self._CLI_LABEL}] Interrupted during initialization.\n")
            return init_output
        if self.config.verbose:
            phase1_elapsed = time.monotonic() - run_start
            await emit(
                f"[{self._CLI_LABEL}] phase 1 completed in {phase1_elapsed:.1f}s\n"
            )

        phase2_start = time.monotonic()
        await emit(f"[{self._CLI_LABEL}] [phase 2/2] Executing user task...\n")
        task_output = await self._invoke_backend(
            self._build_task_prompt(prompt=prompt, learned_summary=init_output),
            emit=emit,
        )
        if self.config.verbose:
            phase2_elapsed = time.monotonic() - phase2_start
            total_elapsed = time.monotonic() - run_start
            await emit(
                f"[{self._CLI_LABEL}] phase 2 completed in {phase2_elapsed:.1f}s "
                f"| total elapsed: {total_elapsed:.1f}s\n"
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
        if status == "updated":
            pr_url = metadata.get("pr_url", "")
            return f"[{self._CLI_LABEL}] PR updated: {pr_url}"
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
            f"\n[{self._CLI_LABEL}] Waiting {initial_wait:.0f}s "
            f"for CI checks on {ref[:8]}...\n"
        )
        await asyncio.sleep(initial_wait)

        poll_interval = 30.0
        deadline = time.monotonic() + max_poll_seconds
        while time.monotonic() < deadline:
            result = gh.get_check_runs(repo, ref)
            conclusion = result["conclusion"]
            if conclusion not in ("pending", "no_checks"):
                return result
            await emit(
                f"[{self._CLI_LABEL}] CI still {conclusion}, "
                f"polling again in {poll_interval:.0f}s...\n"
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
            if r.get("conclusion") in ("failure", "cancelled", "timed_out")
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

        pr_status = metadata.get("pr_status", "")
        if pr_status not in ("created", "updated"):
            return metadata

        pr_commit = metadata.get("pr_commit", "")
        pr_branch = metadata.get("pr_branch", "")
        if not pr_commit or not pr_branch:
            return metadata

        repo_dir = self.repo_index.root.resolve()
        repo = self._github_repo_from_origin(repo_dir)
        if not repo:
            return metadata

        from helping_hands.lib.github import GitHubClient

        initial_wait = self.ci_check_wait_minutes * 60
        max_poll = initial_wait * 2

        metadata["ci_fix_attempts"] = "0"
        metadata["ci_fix_status"] = "checking"

        try:
            with GitHubClient() as gh:
                current_ref = pr_commit
                for attempt in range(1, self.ci_max_retries + 1):
                    if self._is_interrupted():
                        metadata["ci_fix_status"] = "interrupted"
                        return metadata

                    check_result = await self._poll_ci_checks(
                        gh=gh,
                        repo=repo,
                        ref=current_ref,
                        emit=emit,
                        initial_wait=initial_wait,
                        max_poll_seconds=max_poll,
                    )

                    conclusion = check_result["conclusion"]
                    total = check_result["total_count"]

                    if conclusion == "success":
                        await emit(
                            f"[{self._CLI_LABEL}] CI passed "
                            f"({total} check{'s' if total != 1 else ''}). "
                            f"No fixes needed.\n"
                        )
                        metadata["ci_fix_status"] = "success"
                        return metadata

                    if conclusion == "no_checks":
                        await emit(
                            f"[{self._CLI_LABEL}] No CI checks found. "
                            "Skipping CI fix loop.\n"
                        )
                        metadata["ci_fix_status"] = "no_checks"
                        return metadata

                    if conclusion == "pending":
                        await emit(
                            f"[{self._CLI_LABEL}] CI checks still pending "
                            f"after waiting. Skipping fix attempt.\n"
                        )
                        metadata["ci_fix_status"] = "pending_timeout"
                        return metadata

                    # CI failed — attempt fix
                    await emit(
                        f"\n[{self._CLI_LABEL}] CI failed (attempt "
                        f"{attempt}/{self.ci_max_retries}). "
                        f"Invoking backend to fix...\n"
                    )

                    fix_prompt = self._build_ci_fix_prompt(
                        check_result=check_result,
                        original_prompt=prompt,
                        attempt=attempt,
                    )

                    await self._invoke_backend(fix_prompt, emit=emit)

                    if self._is_interrupted():
                        metadata["ci_fix_status"] = "interrupted"
                        return metadata

                    metadata["ci_fix_attempts"] = str(attempt)

                    if not self._repo_has_changes():
                        await emit(
                            f"[{self._CLI_LABEL}] No changes produced "
                            f"by fix attempt {attempt}.\n"
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
                        f"[{self._CLI_LABEL}] Fix pushed "
                        f"(commit {new_sha}). "
                        f"Waiting for CI...\n"
                    )

                    metadata["pr_commit"] = new_sha
                    current_ref = new_sha

                # Exhausted all retries
                metadata["ci_fix_status"] = "exhausted"
                await emit(
                    f"[{self._CLI_LABEL}] CI fix retries exhausted "
                    f"after {self.ci_max_retries} attempts.\n"
                )

        except Exception as exc:
            metadata["ci_fix_status"] = "error"
            metadata["ci_fix_error"] = str(exc)
            await emit(f"[{self._CLI_LABEL}] CI fix loop error: {exc}\n")

        return metadata

    def _format_ci_fix_message(self, metadata: dict[str, str]) -> str | None:
        ci_status = metadata.get("ci_fix_status", "")
        if not ci_status:
            return None
        attempts = metadata.get("ci_fix_attempts", "0")
        if ci_status == "success":
            return f"[{self._CLI_LABEL}] CI checks passed."
        if ci_status == "exhausted":
            return f"[{self._CLI_LABEL}] CI fix failed after {attempts} attempt(s)."
        if ci_status == "pending_timeout":
            return f"[{self._CLI_LABEL}] CI checks still pending after max wait time."
        if ci_status == "error":
            error = metadata.get("ci_fix_error", "")
            return f"[{self._CLI_LABEL}] CI fix error: {error}"
        return None

    # ------------------------------------------------------------------
    # Pre-commit hook fix
    # ------------------------------------------------------------------

    @staticmethod
    def _build_hook_fix_prompt(error_output: str) -> str:
        """Build a prompt asking the AI backend to fix git hook errors."""
        truncated = error_output.strip()
        if len(truncated) > 3000:
            truncated = f"{truncated[:3000]}\n...[truncated]"

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
                timeout=300,
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
                        timeout=300,
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
        super().interrupt()
        process = self._active_process
        if process is not None and process.returncode is None:
            process.terminate()

    def run(self, prompt: str) -> HandResponse:
        message = asyncio.run(self._collect_run_output(prompt))
        pr_metadata = self._finalize_after_run(prompt=prompt, message=message)

        if self.fix_ci and pr_metadata.get("pr_status") in ("created", "updated"):

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
