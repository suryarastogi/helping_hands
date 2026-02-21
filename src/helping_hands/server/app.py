"""FastAPI application for app mode.

Exposes an HTTP API that enqueues repo-building jobs via Celery.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from helping_hands.server.celery_app import build_feature

app = FastAPI(
    title="helping_hands",
    description="AI-powered repo builder — app mode.",
    version="0.1.0",
)


class BuildRequest(BaseModel):
    """Request body for the /build endpoint."""

    repo_path: str
    prompt: str


class BuildResponse(BaseModel):
    """Response for an enqueued build job."""

    task_id: str
    status: str


class TaskStatus(BaseModel):
    """Response for checking task status."""

    task_id: str
    status: str
    result: dict | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


@app.post("/build", response_model=BuildResponse)
def enqueue_build(req: BuildRequest) -> BuildResponse:
    """Enqueue a repo-building task and return the task ID."""
    task = build_feature.delay(req.repo_path, req.prompt)
    return BuildResponse(task_id=task.id, status="queued")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    """Check the status of an enqueued task."""
    result = build_feature.AsyncResult(task_id)
    return TaskStatus(
        task_id=task_id,
        status=result.status,
        result=result.result if result.ready() else None,
    )
