"""Celery application and task definitions."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from celery import Celery


def _resolve_celery_urls() -> tuple[str, str]:
    """Resolve broker/result backend URLs with sensible env fallbacks.

    Priority order:
    1. `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`
    2. shared `REDIS_URL`
    3. local default (`redis://localhost:6379/0`)
    """
    redis_url = os.environ.get("REDIS_URL")
    broker_url = (
        os.environ.get("CELERY_BROKER_URL") or redis_url or "redis://localhost:6379/0"
    )
    # Fall back to broker URL so polling still works when only broker is set.
    backend_url = os.environ.get("CELERY_RESULT_BACKEND") or redis_url or broker_url
    return broker_url, backend_url


_BROKER_URL, _RESULT_BACKEND_URL = _resolve_celery_urls()

celery_app = Celery(
    "helping_hands",
    broker=_BROKER_URL,
    backend=_RESULT_BACKEND_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # RedBeat scheduler configuration for cron-scheduled tasks
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=_BROKER_URL,
    redbeat_key_prefix="redbeat:",
)


_SUPPORTED_BACKENDS = {
    "e2e",
    "basic-langgraph",
    "basic-atomic",
    "basic-agent",
    "codexcli",
    "claudecodecli",
    "goose",
    "geminicli",
}
_VERBOSE = os.environ.get("HELPING_HANDS_VERBOSE", "").lower() in ("1", "true", "yes")
_MAX_STORED_UPDATES = 2000 if _VERBOSE else 200
_MAX_UPDATE_LINE_CHARS = 4000 if _VERBOSE else 800
_BUFFER_FLUSH_CHARS = 40 if _VERBOSE else 180


def _github_clone_url(repo: str) -> str:
    token = os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN", "")).strip()
    if token:
        return f"https://x-access-token:{token}@github.com/{repo}.git"
    return f"https://github.com/{repo}.git"


def _git_noninteractive_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return env


def _redact_sensitive(text: str) -> str:
    return re.sub(
        r"(https://x-access-token:)[^@]+(@github\.com/)",
        r"\1***\2",
        text,
    )


def _repo_tmp_dir() -> Path | None:
    """Return the directory to use for temporary repo clones.

    Reads HELPING_HANDS_REPO_TMP; falls back to the OS default temp dir.
    """
    d = os.environ.get("HELPING_HANDS_REPO_TMP", "").strip()
    if d:
        p = Path(d).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return None


def _resolve_repo_path(repo: str) -> tuple[Path, str | None, Path | None]:
    """Resolve local repo path or clone an owner/repo reference.

    Returns (repo_path, cloned_from, temp_root) where temp_root is the
    directory to clean up after use (None for local paths).
    """
    path = Path(repo).expanduser().resolve()
    if path.is_dir():
        return path, None, None

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        dest_root = Path(mkdtemp(prefix="helping_hands_repo_", dir=_repo_tmp_dir()))
        dest = dest_root / "repo"
        url = _github_clone_url(repo)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True,
            text=True,
            check=False,
            env=_git_noninteractive_env(),
        )
        if result.returncode != 0:
            shutil.rmtree(dest_root, ignore_errors=True)
            stderr = result.stderr.strip() or "unknown git clone error"
            stderr = _redact_sensitive(stderr)
            msg = f"failed to clone {repo}: {stderr}"
            raise ValueError(msg)
        return dest.resolve(), repo, dest_root

    raise ValueError(f"{repo} is not a directory or owner/repo reference")


def _normalize_backend(backend: str | None) -> tuple[str, str]:
    """Resolve requested backend and runtime backend implementation."""
    requested = (backend or "codexcli").strip().lower()
    if requested not in _SUPPORTED_BACKENDS:
        choices = ", ".join(sorted(_SUPPORTED_BACKENDS))
        msg = f"unsupported backend {requested!r}; expected one of: {choices}"
        raise ValueError(msg)

    runtime = "basic-atomic" if requested == "basic-agent" else requested
    return requested, runtime


def _has_codex_auth() -> bool:
    """Return whether runtime has credentials for Codex CLI calls."""
    if os.environ.get("OPENAI_API_KEY"):
        return True
    auth_file = Path.home() / ".codex" / "auth.json"
    return auth_file.is_file()


def _has_gemini_auth() -> bool:
    """Return whether runtime has credentials for Gemini CLI calls."""
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _trim_updates(updates: list[str]) -> None:
    if len(updates) > _MAX_STORED_UPDATES:
        del updates[: len(updates) - _MAX_STORED_UPDATES]


def _append_update(updates: list[str], text: str) -> None:
    clean = text.strip()
    if not clean:
        return
    if len(clean) > _MAX_UPDATE_LINE_CHARS:
        clean = clean[:_MAX_UPDATE_LINE_CHARS] + " ...[truncated]"
    updates.append(clean)
    _trim_updates(updates)


class _UpdateCollector:
    """Collect and compact stream chunks into line-like update entries."""

    def __init__(self, updates: list[str]) -> None:
        self._updates = updates
        self._buffer = ""

    def feed(self, chunk: str) -> None:
        if not chunk:
            return
        self._buffer += chunk
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            _append_update(self._updates, line)
        if len(self._buffer) >= _BUFFER_FLUSH_CHARS:
            _append_update(self._updates, self._buffer)
            self._buffer = ""

    def flush(self) -> None:
        if self._buffer:
            _append_update(self._updates, self._buffer)
            self._buffer = ""


def _update_progress(
    task: object,
    *,
    task_id: str | None,
    stage: str,
    updates: list[str],
    prompt: str,
    pr_number: int | None,
    backend: str,
    runtime_backend: str,
    repo_path: str,
    model: str | None,
    max_iterations: int,
    no_pr: bool,
    enable_execution: bool,
    enable_web: bool,
    use_native_cli_auth: bool,
    tools: tuple[str, ...],
    skills: tuple[str, ...],
    workspace: str | None = None,
) -> None:
    update_state = getattr(task, "update_state", None)
    if not callable(update_state):
        return
    meta: dict[str, Any] = {
        "task_id": task_id,
        "stage": stage,
        "prompt": prompt,
        "pr_number": pr_number,
        "backend": backend,
        "runtime_backend": runtime_backend,
        "repo_path": repo_path,
        "model": model,
        "max_iterations": max_iterations,
        "no_pr": no_pr,
        "enable_execution": enable_execution,
        "enable_web": enable_web,
        "use_native_cli_auth": use_native_cli_auth,
        "tools": list(tools),
        "skills": list(skills),
        "updates": list(updates),
    }
    if workspace:
        meta["workspace"] = workspace
    update_state(state="PROGRESS", meta=meta)


async def _collect_stream(
    hand: Any,
    prompt: str,
    *,
    task: object,
    task_id: str | None,
    pr_number: int | None,
    updates: list[str],
    backend: str,
    runtime_backend: str,
    repo_path: str,
    model: str | None,
    max_iterations: int,
    no_pr: bool,
    enable_execution: bool,
    enable_web: bool,
    use_native_cli_auth: bool,
    tools: tuple[str, ...],
    skills: tuple[str, ...],
    workspace: str | None,
) -> str:
    parts: list[str] = []
    collector = _UpdateCollector(updates)
    chunk_count = 0

    async for chunk in hand.stream(prompt):
        text = str(chunk)
        parts.append(text)
        collector.feed(text)
        chunk_count += 1
        if chunk_count % (2 if _VERBOSE else 8) == 0:
            _update_progress(
                task,
                task_id=task_id,
                stage="running",
                updates=updates,
                prompt=prompt,
                pr_number=pr_number,
                backend=backend,
                runtime_backend=runtime_backend,
                repo_path=repo_path,
                model=model,
                max_iterations=max_iterations,
                no_pr=no_pr,
                enable_execution=enable_execution,
                enable_web=enable_web,
                use_native_cli_auth=use_native_cli_auth,
                tools=tools,
                skills=skills,
                workspace=workspace,
            )

    collector.flush()
    _update_progress(
        task,
        task_id=task_id,
        stage="running",
        updates=updates,
        prompt=prompt,
        pr_number=pr_number,
        backend=backend,
        runtime_backend=runtime_backend,
        repo_path=repo_path,
        model=model,
        max_iterations=max_iterations,
        no_pr=no_pr,
        enable_execution=enable_execution,
        enable_web=enable_web,
        use_native_cli_auth=use_native_cli_auth,
        tools=tools,
        skills=skills,
        workspace=workspace,
    )
    return "".join(parts)


@celery_app.task(bind=True, name="helping_hands.build_feature")
def build_feature(
    self: object,
    repo_path: str,
    prompt: str,
    pr_number: int | None = None,
    backend: str = "codexcli",
    model: str | None = None,
    max_iterations: int = 6,
    no_pr: bool = False,
    enable_execution: bool = False,
    enable_web: bool = False,
    use_native_cli_auth: bool = False,
    tools: list[str] | None = None,
    skills: list[str] | None = None,
) -> dict[str, Any]:  # pragma: no cover - exercised in integration
    """Async task: run a hand against a GitHub repo with a user prompt.

    This is the primary unit of work in app mode. The server enqueues this
    task; a worker picks it up, runs the hand, and stores the result.
    The Celery task ID is used as the hand UUID.
    """
    from helping_hands.lib.config import Config
    from helping_hands.lib.hands.v1.hand import (
        BasicAtomicHand,
        BasicLangGraphHand,
        ClaudeCodeHand,
        CodexCLIHand,
        E2EHand,
        GeminiCLIHand,
        GooseCLIHand,
    )
    from helping_hands.lib.meta import skills as meta_skills
    from helping_hands.lib.meta.tools import registry as meta_tools
    from helping_hands.lib.repo import RepoIndex

    task_id = getattr(getattr(self, "request", None), "id", None)
    requested_backend, runtime_backend = _normalize_backend(backend)
    resolved_iterations = max(1, int(max_iterations))
    selected_tools = meta_tools.normalize_tool_selection(tools)
    meta_tools.validate_tool_category_names(selected_tools)
    selected_skills = meta_skills.normalize_skill_selection(skills)
    meta_skills.validate_skill_names(selected_skills)
    updates: list[str] = []
    _append_update(
        updates,
        (
            f"Task received. backend={requested_backend}, model={model or 'default'}, "
            f"repo={repo_path}, max_iterations={resolved_iterations}, "
            f"no_pr={no_pr}, enable_execution={enable_execution}, "
            f"enable_web={enable_web}, use_native_cli_auth={use_native_cli_auth}, "
            f"tools={','.join(selected_tools) or 'none'}, "
            f"skills={','.join(selected_skills) or 'none'}"
        ),
    )
    _update_progress(
        self,
        task_id=task_id,
        stage="starting",
        updates=updates,
        prompt=prompt,
        pr_number=pr_number,
        backend=requested_backend,
        runtime_backend=runtime_backend,
        repo_path=repo_path,
        model=model,
        max_iterations=resolved_iterations,
        no_pr=no_pr,
        enable_execution=enable_execution,
        enable_web=enable_web,
        use_native_cli_auth=use_native_cli_auth,
        tools=selected_tools,
        skills=selected_skills,
    )

    if runtime_backend == "e2e":
        config = Config.from_env(
            overrides={
                "repo": repo_path,
                "model": model,
                "enable_execution": enable_execution,
                "enable_web": enable_web,
                "use_native_cli_auth": use_native_cli_auth,
                "enabled_tools": selected_tools,
                "enabled_skills": selected_skills,
            }
        )
        repo_index = RepoIndex(root=Path(config.repo or "."), files=[])
        hand = E2EHand(config, repo_index)
        _append_update(updates, "Running E2E hand.")
        _update_progress(
            self,
            task_id=task_id,
            stage="running",
            updates=updates,
            prompt=prompt,
            pr_number=pr_number,
            backend=requested_backend,
            runtime_backend=runtime_backend,
            repo_path=repo_path,
            model=config.model,
            max_iterations=resolved_iterations,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            tools=selected_tools,
            skills=selected_skills,
        )
        response = hand.run(
            prompt,
            hand_uuid=task_id,
            pr_number=pr_number,
            dry_run=no_pr,
        )
        _append_update(updates, response.message)
        return {
            "status": "ok",
            "prompt": prompt,
            "pr_number": pr_number,
            "repo_path": repo_path,
            "backend": requested_backend,
            "runtime_backend": runtime_backend,
            "message": response.message,
            "updates": updates,
            **response.metadata,
        }

    try:
        resolved_repo_path, cloned_from, _tmp_root = _resolve_repo_path(repo_path)
    except ValueError as exc:
        _append_update(updates, f"Repo resolution failed: {exc}")
        raise

    try:
        overrides = {"repo": str(resolved_repo_path), "model": model}
        overrides["enable_execution"] = enable_execution
        overrides["enable_web"] = enable_web
        overrides["use_native_cli_auth"] = use_native_cli_auth
        overrides["enabled_tools"] = selected_tools
        overrides["enabled_skills"] = selected_skills
        config = Config.from_env(overrides=overrides)
        repo_index = RepoIndex.from_path(Path(config.repo))

        if cloned_from:
            _append_update(updates, f"Cloned {cloned_from} to {resolved_repo_path}")
        if pr_number is not None and cloned_from:
            _append_update(updates, f"Checking out PR #{pr_number} branch...")
            from helping_hands.lib.github import GitHubClient as _GHClient

            with _GHClient() as _gh:
                _pr_info = _gh.get_pr(cloned_from, pr_number)
                _pr_branch = str(_pr_info["head"])
                _gh.fetch_branch(resolved_repo_path, _pr_branch)
                _gh.switch_branch(resolved_repo_path, _pr_branch)
                _gh.pull(resolved_repo_path, branch=_pr_branch)
            _append_update(
                updates,
                f"Checked out branch {_pr_branch} for PR #{pr_number} (up to date)",
            )
            repo_index = RepoIndex.from_path(Path(config.repo))
        if runtime_backend == "codexcli" and not _has_codex_auth():
            msg = (
                "Codex authentication is missing in worker runtime. "
                "Set OPENAI_API_KEY in .env and recreate containers, "
                "or run `codex login` in the worker environment."
            )
            _append_update(updates, msg)
            raise RuntimeError(msg)
        if runtime_backend == "geminicli" and not _has_gemini_auth():
            msg = (
                "Gemini authentication is missing in worker runtime. "
                "Set GEMINI_API_KEY in .env and recreate containers."
            )
            _append_update(updates, msg)
            raise RuntimeError(msg)
        _append_update(
            updates,
            (
                f"Running hand. backend={requested_backend} "
                f"(runtime={runtime_backend}), model={config.model}"
            ),
        )
        _update_progress(
            self,
            task_id=task_id,
            stage="running",
            updates=updates,
            prompt=prompt,
            pr_number=pr_number,
            backend=requested_backend,
            runtime_backend=runtime_backend,
            repo_path=repo_path,
            model=config.model,
            max_iterations=resolved_iterations,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            tools=selected_tools,
            skills=selected_skills,
            workspace=str(resolved_repo_path),
        )

        try:
            if runtime_backend == "basic-langgraph":
                hand = BasicLangGraphHand(
                    config,
                    repo_index,
                    max_iterations=resolved_iterations,
                )
            elif runtime_backend == "codexcli":
                hand = CodexCLIHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "claudecodecli":
                hand = ClaudeCodeHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "goose":
                hand = GooseCLIHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "geminicli":
                hand = GeminiCLIHand(
                    config,
                    repo_index,
                )
            else:
                hand = BasicAtomicHand(
                    config,
                    repo_index,
                    max_iterations=resolved_iterations,
                )
        except ModuleNotFoundError as exc:
            if runtime_backend == "basic-langgraph":
                extra = "langchain"
            elif runtime_backend in {"basic-atomic", "basic-agent"}:
                extra = "atomic"
            else:
                extra = None
            if extra:
                install_hint = f"Install with: uv sync --extra {extra}"
            else:
                install_hint = "Check runtime setup."
            msg = (
                f"Missing dependency for backend {requested_backend}:"
                f" {exc}. {install_hint}"
            )
            _append_update(updates, msg)
            raise RuntimeError(msg) from exc

        hand.auto_pr = not no_pr
        hand.pr_number = pr_number
        message = asyncio.run(
            _collect_stream(
                hand,
                prompt,
                task=self,
                task_id=task_id,
                pr_number=pr_number,
                updates=updates,
                backend=requested_backend,
                runtime_backend=runtime_backend,
                repo_path=repo_path,
                model=config.model,
                max_iterations=resolved_iterations,
                no_pr=no_pr,
                enable_execution=enable_execution,
                enable_web=enable_web,
                use_native_cli_auth=use_native_cli_auth,
                tools=selected_tools,
                skills=selected_skills,
                workspace=str(resolved_repo_path),
            )
        )
        _append_update(updates, "Task complete.")
        return {
            "status": "ok",
            "prompt": prompt,
            "pr_number": pr_number,
            "backend": requested_backend,
            "runtime_backend": runtime_backend,
            "repo": repo_path,
            "workspace": str(resolved_repo_path),
            "model": config.model,
            "max_iterations": str(resolved_iterations),
            "no_pr": str(no_pr).lower(),
            "enable_execution": str(enable_execution).lower(),
            "enable_web": str(enable_web).lower(),
            "use_native_cli_auth": str(use_native_cli_auth).lower(),
            "tools": list(selected_tools),
            "skills": list(selected_skills),
            "message": message,
            "updates": updates,
        }
    finally:
        if _tmp_root is not None:
            shutil.rmtree(_tmp_root, ignore_errors=True)


@celery_app.task(bind=True, name="helping_hands.scheduled_build")
def scheduled_build(
    self: object,
    schedule_id: str,
) -> dict[str, Any]:  # pragma: no cover - exercised in integration
    """Execute a scheduled build task.

    This task is triggered by RedBeat scheduler and looks up the schedule
    configuration to run the appropriate build_feature task.
    """
    from helping_hands.server.schedules import get_schedule_manager

    manager = get_schedule_manager(celery_app)
    schedule = manager.get_schedule(schedule_id)

    if schedule is None:
        return {
            "status": "error",
            "message": f"Schedule {schedule_id} not found",
            "schedule_id": schedule_id,
        }

    if not schedule.enabled:
        return {
            "status": "skipped",
            "message": f"Schedule {schedule_id} is disabled",
            "schedule_id": schedule_id,
        }

    # Trigger the actual build task
    result = build_feature.delay(
        repo_path=schedule.repo_path,
        prompt=schedule.prompt,
        backend=schedule.backend,
        model=schedule.model,
        max_iterations=schedule.max_iterations,
        no_pr=schedule.no_pr,
        enable_execution=schedule.enable_execution,
        enable_web=schedule.enable_web,
        use_native_cli_auth=schedule.use_native_cli_auth,
        tools=getattr(schedule, "tools", []),
        skills=schedule.skills,
    )

    # Record the run
    manager.record_run(schedule_id, result.id)

    return {
        "status": "triggered",
        "schedule_id": schedule_id,
        "schedule_name": schedule.name,
        "build_task_id": result.id,
        "prompt": schedule.prompt,
        "repo_path": schedule.repo_path,
    }
