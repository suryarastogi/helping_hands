"""Celery application and task definitions."""

from __future__ import annotations

import os

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
    """Async task: run the agent against a repo with a user prompt.

    This is the primary unit of work in app mode. The server enqueues this
    task; a worker picks it up, runs the agent, and stores the result.
    """
    from hhpy.helping_hands.lib.agent import Agent
    from hhpy.helping_hands.lib.config import Config
    from hhpy.helping_hands.lib.repo import RepoIndex

    config = Config.from_env(overrides={"repo": repo_path})
    repo_index = RepoIndex.from_path(config.repo)  # type: ignore[arg-type]
    agent = Agent(config=config, repo_index=repo_index)
    return {"status": "ok", "greeting": agent.greet(), "prompt": prompt}
