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


@celery_app.task(bind=True, name="helping_hands.build_feature")
def build_feature(
    self: object, repo_path: str, prompt: str, pr_number: int | None = None
) -> dict[str, str]:  # pragma: no cover - exercised in integration
    """Async task: run a hand against a GitHub repo with a user prompt.

    This is the primary unit of work in app mode. The server enqueues this
    task; a worker picks it up, runs the hand, and stores the result.
    The Celery task ID is used as the hand UUID.
    """
    from helping_hands.lib.config import Config
    from helping_hands.lib.hands.v1.hand import E2EHand
    from helping_hands.lib.repo import RepoIndex

    config = Config.from_env(overrides={"repo": repo_path})
    repo_index = RepoIndex(root=Path(config.repo or "."), files=[])
    task_id = getattr(getattr(self, "request", None), "id", None)
    response = E2EHand(config, repo_index).run(
        prompt,
        hand_uuid=task_id,
        pr_number=pr_number,
    )
    return {"status": "ok", "message": response.message, **response.metadata}
