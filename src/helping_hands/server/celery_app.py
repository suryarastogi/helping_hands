"""Celery application and task definitions."""

from __future__ import annotations

import asyncio
import os
import re
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
)


_SUPPORTED_BACKENDS = {
    "e2e",
    "basic-langgraph",
    "basic-atomic",
    "basic-agent",
    "codexcli",
}
_MAX_STORED_UPDATES = 200
_MAX_UPDATE_LINE_CHARS = 800
_BUFFER_FLUSH_CHARS = 180


def _resolve_repo_path(repo: str) -> tuple[Path, str | None]:
    """Resolve local repo path or clone an owner/repo reference."""
    path = Path(repo).expanduser().resolve()
    if path.is_dir():
        return path, None

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        dest_root = Path(mkdtemp(prefix="helping_hands_repo_"))
        dest = dest_root / "repo"
        url = f"https://github.com/{repo}.git"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown git clone error"
            msg = f"failed to clone {repo}: {stderr}"
            raise ValueError(msg)
        return dest.resolve(), repo

    raise ValueError(f"{repo} is not a directory or owner/repo reference")


def _normalize_backend(backend: str | None) -> tuple[str, str]:
    """Resolve requested backend and runtime backend implementation."""
    requested = (backend or "e2e").strip().lower()
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
    backend: str,
    runtime_backend: str,
    repo_path: str,
    model: str | None,
    max_iterations: int,
    no_pr: bool,
    workspace: str | None = None,
) -> None:
    update_state = getattr(task, "update_state", None)
    if not callable(update_state):
        return
    meta: dict[str, Any] = {
        "task_id": task_id,
        "stage": stage,
        "backend": backend,
        "runtime_backend": runtime_backend,
        "repo_path": repo_path,
        "model": model,
        "max_iterations": max_iterations,
        "no_pr": no_pr,
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
    updates: list[str],
    backend: str,
    runtime_backend: str,
    repo_path: str,
    model: str | None,
    max_iterations: int,
    no_pr: bool,
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
        if chunk_count % 8 == 0:
            _update_progress(
                task,
                task_id=task_id,
                stage="running",
                updates=updates,
                backend=backend,
                runtime_backend=runtime_backend,
                repo_path=repo_path,
                model=model,
                max_iterations=max_iterations,
                no_pr=no_pr,
                workspace=workspace,
            )

    collector.flush()
    return "".join(parts)


@celery_app.task(bind=True, name="helping_hands.build_feature")
def build_feature(
    self: object,
    repo_path: str,
    prompt: str,
    pr_number: int | None = None,
    backend: str = "e2e",
    model: str | None = None,
    max_iterations: int = 6,
    no_pr: bool = False,
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
        CodexCLIHand,
        E2EHand,
    )
    from helping_hands.lib.repo import RepoIndex

    task_id = getattr(getattr(self, "request", None), "id", None)
    requested_backend, runtime_backend = _normalize_backend(backend)
    resolved_iterations = max(1, int(max_iterations))
    updates: list[str] = []
    _append_update(
        updates,
        (
            f"Task received. backend={requested_backend}, model={model or 'default'}, "
            f"repo={repo_path}, max_iterations={resolved_iterations}, no_pr={no_pr}"
        ),
    )
    _update_progress(
        self,
        task_id=task_id,
        stage="starting",
        updates=updates,
        backend=requested_backend,
        runtime_backend=runtime_backend,
        repo_path=repo_path,
        model=model,
        max_iterations=resolved_iterations,
        no_pr=no_pr,
    )

    if runtime_backend == "e2e":
        config = Config.from_env(overrides={"repo": repo_path, "model": model})
        repo_index = RepoIndex(root=Path(config.repo or "."), files=[])
        hand = E2EHand(config, repo_index)
        _append_update(updates, "Running E2E hand.")
        _update_progress(
            self,
            task_id=task_id,
            stage="running",
            updates=updates,
            backend=requested_backend,
            runtime_backend=runtime_backend,
            repo_path=repo_path,
            model=config.model,
            max_iterations=resolved_iterations,
            no_pr=no_pr,
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
            "backend": requested_backend,
            "runtime_backend": runtime_backend,
            "message": response.message,
            "updates": updates,
            **response.metadata,
        }

    try:
        resolved_repo_path, cloned_from = _resolve_repo_path(repo_path)
    except ValueError as exc:
        _append_update(updates, f"Repo resolution failed: {exc}")
        raise

    overrides = {"repo": str(resolved_repo_path), "model": model}
    config = Config.from_env(overrides=overrides)
    repo_index = RepoIndex.from_path(Path(config.repo))

    if cloned_from:
        _append_update(updates, f"Cloned {cloned_from} to {resolved_repo_path}")
    if runtime_backend == "codexcli" and not _has_codex_auth():
        msg = (
            "Codex authentication is missing in worker runtime. "
            "Set OPENAI_API_KEY in .env and recreate containers, "
            "or run `codex login` in the worker environment."
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
        backend=requested_backend,
        runtime_backend=runtime_backend,
        repo_path=repo_path,
        model=config.model,
        max_iterations=resolved_iterations,
        no_pr=no_pr,
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
            f"Missing dependency for backend {requested_backend}: {exc}. {install_hint}"
        )
        _append_update(updates, msg)
        raise RuntimeError(msg) from exc

    hand.auto_pr = not no_pr
    message = asyncio.run(
        _collect_stream(
            hand,
            prompt,
            task=self,
            task_id=task_id,
            updates=updates,
            backend=requested_backend,
            runtime_backend=runtime_backend,
            repo_path=repo_path,
            model=config.model,
            max_iterations=resolved_iterations,
            no_pr=no_pr,
            workspace=str(resolved_repo_path),
        )
    )
    _append_update(updates, "Task complete.")
    return {
        "status": "ok",
        "backend": requested_backend,
        "runtime_backend": runtime_backend,
        "repo": repo_path,
        "workspace": str(resolved_repo_path),
        "model": config.model,
        "max_iterations": str(resolved_iterations),
        "no_pr": str(no_pr).lower(),
        "message": message,
        "updates": updates,
    }
