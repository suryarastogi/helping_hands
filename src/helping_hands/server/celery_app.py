"""Celery application and task definitions."""

from __future__ import annotations

import os
from pathlib import Path

from celery import Celery

celery_app = Celery(
    "helping_hands",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="helping_hands.build_feature")
def build_feature(repo_path: str, prompt: str) -> dict[str, str]:
    """Async task: run a hand against a repo with a user prompt.

    This is the primary unit of work in app mode. The server enqueues this
    task; a worker picks it up, runs the hand, and stores the result.
    """
    from helping_hands.lib.config import Config
    from helping_hands.lib.repo import RepoIndex

    config = Config.from_env(overrides={"repo": repo_path})
    repo_index = RepoIndex.from_path(Path(config.repo))
    n = len(repo_index.files)
    s = "s" if n != 1 else ""
    greeting = f"Ready. Indexed {n} file{s} in {repo_index.root}."
    return {"status": "ok", "greeting": greeting, "prompt": prompt}
