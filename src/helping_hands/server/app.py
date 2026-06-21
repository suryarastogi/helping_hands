"""FastAPI application for app mode.

Exposes an HTTP API that enqueues repo-building jobs via Celery.
"""

from __future__ import annotations

import ast
import html
import json
import logging
import os
import subprocess
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib import error as urllib_error, request as urllib_request
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, ValidationError, field_validator

from helping_hands.lib import (
    version as _version,  # noqa: F401  -- eagerly cache at startup
)
from helping_hands.lib.config import _is_truthy_env
from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.lib.hands.v1.hand.factory import (
    BACKEND_BASIC_AGENT,
    BACKEND_BASIC_ATOMIC,
    BACKEND_BASIC_LANGGRAPH,
    BACKEND_CLAUDECODECLI,
    BACKEND_CODEXCLI,
    BACKEND_DEVINCLI,
    BACKEND_DOCKER_SANDBOX_CLAUDE,
    BACKEND_E2E,
    BACKEND_GEMINICLI,
    BACKEND_GOOSE,
    BACKEND_OPENCODECLI,
)
from helping_hands.lib.meta.tools import registry as meta_tools
from helping_hands.lib.validation import (
    install_hint,
    parse_comma_list,
    require_non_empty_string,
)
from helping_hands.server import multiplayer_yjs as _multiplayer_yjs
from helping_hands.server.celery_app import build_feature, celery_app
from helping_hands.server.constants import (
    ANTHROPIC_BETA_HEADER as _ANTHROPIC_BETA_HEADER,
    ANTHROPIC_USAGE_URL as _ANTHROPIC_USAGE_URL,
    DEFAULT_BACKEND as _DEFAULT_BACKEND,
    DEFAULT_CI_WAIT_MINUTES as _DEFAULT_CI_WAIT_MINUTES,
    DEFAULT_MAX_ITERATIONS as _DEFAULT_MAX_ITERATIONS,
    DEFAULT_REDIS_URL as _DEFAULT_REDIS_URL,
    GRILL_ME_ENABLED_ENV_VAR as _GRILL_ME_ENABLED_ENV_VAR,
    INTERVAL_PRESETS as _INTERVAL_PRESETS,
    MAX_CI_WAIT_MINUTES as _MAX_CI_WAIT_MINUTES,
    MAX_GITHUB_TOKEN_LENGTH as _MAX_GITHUB_TOKEN_LENGTH,
    MAX_INTERVAL_SECONDS as _MAX_INTERVAL_SECONDS,
    MAX_ITERATIONS_UPPER_BOUND as _MAX_ITERATIONS_UPPER_BOUND,
    MAX_MODEL_LENGTH as _MAX_MODEL_LENGTH,
    MAX_PROMPT_LENGTH as _MAX_PROMPT_LENGTH,
    MAX_REFERENCE_REPOS as _MAX_REFERENCE_REPOS,
    MAX_REPO_PATH_LENGTH as _MAX_REPO_PATH_LENGTH,
    MIN_CI_WAIT_MINUTES as _MIN_CI_WAIT_MINUTES,
    MIN_INTERVAL_SECONDS as _MIN_INTERVAL_SECONDS,
    RESPONSE_STATUS_ERROR as _RESPONSE_STATUS_ERROR,
    RESPONSE_STATUS_NA as _RESPONSE_STATUS_NA,
    RESPONSE_STATUS_OK as _RESPONSE_STATUS_OK,
    SCHEDULE_TYPE_CRON as _SCHEDULE_TYPE_CRON,
    SCHEDULE_TYPE_INTERVAL as _SCHEDULE_TYPE_INTERVAL,
    USAGE_API_TIMEOUT_S as _USAGE_API_TIMEOUT_S,
    USAGE_CACHE_TTL_S as _USAGE_CACHE_TTL_S,
    USAGE_USER_AGENT as _USAGE_USER_AGENT,
)
from helping_hands.server.mgrill_bridge import (
    mgrill_room_name as _mgrill_room_name,
    start_mgrill_bridge,
    stop_mgrill_bridge,
)
from helping_hands.server.multiplayer_yjs import (
    create_yjs_app,
    get_connected_players,
    get_decoration_state,
    get_multiplayer_stats,
    get_player_activity_summary,
    start_yjs_server,
    stop_yjs_server,
)
from helping_hands.server.task_result import normalize_task_result
from helping_hands.server.task_runs import (
    init_task_runs_schema,
    read_task_run,
)
from helping_hands.server.token_helpers import (
    get_claude_oauth_token as _get_claude_oauth_token,
    redact_token as _redact_token,
)

if TYPE_CHECKING:
    from helping_hands.server.schedules import ScheduleManager
    from helping_hands.server.templates import TemplateManager

logger = logging.getLogger(__name__)

__all__ = [
    "BackendName",
    "BuildRequest",
    "BuildResponse",
    "ClaudeUsageLevel",
    "ClaudeUsageResponse",
    "CronPresetsResponse",
    "CurrentTask",
    "CurrentTasksResponse",
    "ScheduleListResponse",
    "ScheduleRequest",
    "ScheduleResponse",
    "ScheduleTriggerResponse",
    "ServerConfig",
    "ServiceHealthResponse",
    "TaskCancelResponse",
    "TaskStatus",
    "TemplateListResponse",
    "TemplateRequest",
    "TemplateResponse",
    "WorkerCapacityResponse",
    "app",
]

# Lazy import for optional schedule dependencies
_schedule_manager: ScheduleManager | None = None

# Maximum number of tool entries in a single request.
_MAX_TOOL_ITEMS = 50

# --- Health-check timeout constants (seconds) ---
_REDIS_HEALTH_TIMEOUT_S = 2
_DB_HEALTH_TIMEOUT_S = 3
_CELERY_HEALTH_TIMEOUT_S = 2.0
_CELERY_INSPECT_TIMEOUT_S = 1.0

# --- Preview truncation limits for error/debug messages ---
_HTTP_ERROR_BODY_PREVIEW_LENGTH = 200
_USAGE_DATA_PREVIEW_LENGTH = 300


# --- Schedule endpoint constants ---
_SCHEDULE_NOT_FOUND_DETAIL = "Schedule not found"
"""HTTP 404 detail message for missing schedule resources."""

_TEMPLATE_NOT_FOUND_DETAIL = "Template not found"
"""HTTP 404 detail message for missing template resources."""


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage server lifecycle — start/stop Yjs server + multiplayer-grill bridge."""
    init_task_runs_schema()
    await start_yjs_server()
    await start_mgrill_bridge(_multiplayer_yjs.yjs_websocket_server)
    try:
        yield
    finally:
        await stop_mgrill_bridge()
        await stop_yjs_server()


app = FastAPI(
    title="helping_hands",
    description="AI-powered repo builder — app mode.",
    version="0.1.0",
    lifespan=_lifespan,
)

# --- Yjs-based multiplayer WebSocket (awareness protocol) ---
_yjs_app = create_yjs_app()
if _yjs_app is not None:
    app.mount("/ws/yjs", _yjs_app)


class _ToolValidatorMixin(BaseModel):
    """Shared coercion and validation for tools list fields."""

    tools: list[str] = Field(default_factory=list, max_length=_MAX_TOOL_ITEMS)

    @field_validator("tools", mode="before")
    @classmethod
    def _coerce_tools(
        cls, value: str | list[str] | tuple[str, ...] | None
    ) -> list[str]:
        """Normalize raw tool input into a list of tool category names.

        Accepts comma-separated strings, sequences, or ``None`` and
        delegates to ``normalize_tool_selection``.

        Args:
            value: Raw tool selection from the request body.

        Returns:
            A normalized list of tool category name strings.
        """
        normalized = meta_tools.normalize_tool_selection(value)
        return list(normalized)

    @field_validator("tools")
    @classmethod
    def _validate_tools(cls, value: list[str]) -> list[str]:
        """Validate that all tool names are recognized category names.

        Args:
            value: List of tool category names to validate.

        Returns:
            The unchanged list if all names are valid.

        Raises:
            ValueError: If any name is not a known tool category.
        """
        meta_tools.validate_tool_category_names(tuple(value))
        return value


BackendName = Literal[
    "e2e",
    "basic-langgraph",
    "basic-atomic",
    "basic-agent",
    "codexcli",
    "claudecodecli",
    "devincli",
    "docker-sandbox-claude",
    "goose",
    "geminicli",
    "opencodecli",
]


class BuildRequest(_ToolValidatorMixin):
    """Request body for the /build endpoint."""

    repo_path: str = Field(min_length=1, max_length=_MAX_REPO_PATH_LENGTH)
    prompt: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH)
    backend: BackendName = _DEFAULT_BACKEND
    model: str | None = Field(default=None, max_length=_MAX_MODEL_LENGTH)
    max_iterations: int = Field(
        default=_DEFAULT_MAX_ITERATIONS,
        ge=1,
        le=_MAX_ITERATIONS_UPPER_BOUND,
    )
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    pr_number: int | None = None
    issue_number: int | None = None
    create_issue: bool = False
    project_url: str | None = None
    fix_ci: bool = False
    fix_conflicts: bool = False
    master_rebase: bool = False
    ci_check_wait_minutes: float = Field(
        default=_DEFAULT_CI_WAIT_MINUTES,
        ge=_MIN_CI_WAIT_MINUTES,
        le=_MAX_CI_WAIT_MINUTES,
    )
    github_token: str | None = Field(default=None, max_length=_MAX_GITHUB_TOKEN_LENGTH)
    reference_repos: list[str] = Field(
        default_factory=list, max_length=_MAX_REFERENCE_REPOS
    )


class BuildResponse(BaseModel):
    """Response for an enqueued build job."""

    task_id: str
    status: str
    backend: str


class TaskStatus(BaseModel):
    """Response for checking task status."""

    task_id: str
    status: str
    result: dict[str, Any] | None = None
    from_snapshot: bool = False


class TaskCancelResponse(BaseModel):
    """Response for cancelling a running task."""

    task_id: str
    cancelled: bool
    detail: str


class CurrentTask(BaseModel):
    """Summary of a currently active/queued task."""

    task_id: str
    status: str
    backend: str | None = None
    repo_path: str | None = None
    worker: str | None = None
    source: str


class CurrentTasksResponse(BaseModel):
    """Response for listing currently active/queued task UUIDs."""

    tasks: list[CurrentTask]
    source: str


class WorkerCapacityResponse(BaseModel):
    """Response for worker capacity introspection."""

    max_workers: int = Field(ge=1)
    source: str
    workers: dict[str, int] = Field(default_factory=dict)


class QueueDepthResponse(BaseModel):
    """Aggregate task counts across workers and the broker queue."""

    active: int = Field(ge=0, default=0)
    reserved: int = Field(ge=0, default=0)
    scheduled: int = Field(ge=0, default=0)
    broker_depth: int = Field(ge=0, default=0)
    source: str


class ServerConfig(BaseModel):
    """Runtime configuration exposed to the frontend."""

    in_docker: bool
    native_auth_default: bool
    enabled_backends: list[str]
    claude_native_cli_auth: bool
    has_github_token: bool
    default_repo: str | None = None
    grill_enabled: bool = False


# --- Scheduled Task Models ---


class ScheduleRequest(_ToolValidatorMixin):
    """Request body for creating/updating a scheduled task."""

    name: str = Field(min_length=1, max_length=100)
    schedule_type: str = Field(
        default=_SCHEDULE_TYPE_CRON,
        description="'cron' for fixed-time or 'interval' for delay-after-completion",
    )
    cron_expression: str = Field(
        default="",
        max_length=100,
        description="Cron expression (e.g., '0 0 * * *') or preset name. Required for cron schedules.",
    )
    interval_seconds: int | None = Field(
        default=None,
        ge=_MIN_INTERVAL_SECONDS,
        le=_MAX_INTERVAL_SECONDS,
        description="Seconds between completion and next start. Required for interval schedules.",
    )
    repo_path: str = Field(min_length=1, max_length=_MAX_REPO_PATH_LENGTH)
    prompt: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH)
    backend: BackendName = _DEFAULT_BACKEND
    model: str | None = Field(default=None, max_length=_MAX_MODEL_LENGTH)
    max_iterations: int = Field(
        default=_DEFAULT_MAX_ITERATIONS,
        ge=1,
        le=_MAX_ITERATIONS_UPPER_BOUND,
    )
    pr_number: int | None = None
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    fix_ci: bool = False
    fix_conflicts: bool = False
    master_rebase: bool = False
    ci_check_wait_minutes: float = Field(
        default=_DEFAULT_CI_WAIT_MINUTES,
        ge=_MIN_CI_WAIT_MINUTES,
        le=_MAX_CI_WAIT_MINUTES,
    )
    github_token: str | None = Field(default=None, max_length=_MAX_GITHUB_TOKEN_LENGTH)
    reference_repos: list[str] = Field(
        default_factory=list, max_length=_MAX_REFERENCE_REPOS
    )
    watch_labels: list[str] = Field(
        default_factory=list,
        description="Issue label filter for watch_issues schedules.",
    )
    enabled: bool = True


class ScheduleResponse(BaseModel):
    """Response for a scheduled task."""

    schedule_id: str
    name: str
    schedule_type: str = _SCHEDULE_TYPE_CRON
    cron_expression: str = ""
    interval_seconds: int | None = None
    repo_path: str
    prompt: str
    backend: str
    model: str | None = None
    max_iterations: int = _DEFAULT_MAX_ITERATIONS
    pr_number: int | None = None
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    fix_ci: bool = False
    fix_conflicts: bool = False
    master_rebase: bool = False
    ci_check_wait_minutes: float = _DEFAULT_CI_WAIT_MINUTES
    github_token: str | None = None
    reference_repos: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    watch_labels: list[str] = Field(default_factory=list)
    enabled: bool = True
    created_at: str
    last_run_at: str | None = None
    last_run_task_id: str | None = None
    run_count: int = 0
    next_run_at: str | None = None


class ScheduleListResponse(BaseModel):
    """Response for listing scheduled tasks."""

    schedules: list[ScheduleResponse]
    total: int


class ScheduleTriggerResponse(BaseModel):
    """Response for manually triggering a scheduled task."""

    schedule_id: str
    task_id: str
    message: str


class TemplateRequest(_ToolValidatorMixin):
    """Request body for creating/updating a task template."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    repo_path: str | None = Field(default=None, max_length=_MAX_REPO_PATH_LENGTH)
    prompt: str | None = Field(default=None, max_length=_MAX_PROMPT_LENGTH)
    backend: str | None = Field(default=None, max_length=_MAX_MODEL_LENGTH)
    model: str | None = Field(default=None, max_length=_MAX_MODEL_LENGTH)
    max_iterations: int | None = Field(
        default=None, ge=1, le=_MAX_ITERATIONS_UPPER_BOUND
    )
    pr_number: int | None = None
    issue_number: int | None = None
    create_issue: bool | None = None
    project_url: str | None = None
    no_pr: bool | None = None
    enable_execution: bool | None = None
    enable_web: bool | None = None
    use_native_cli_auth: bool | None = None
    fix_ci: bool | None = None
    fix_conflicts: bool | None = None
    master_rebase: bool | None = None
    ci_check_wait_minutes: float | None = Field(
        default=None, ge=_MIN_CI_WAIT_MINUTES, le=_MAX_CI_WAIT_MINUTES
    )
    reference_repos: list[str] | None = Field(
        default=None, max_length=_MAX_REFERENCE_REPOS
    )


class TemplateResponse(BaseModel):
    """Response for a task template."""

    template_id: str
    name: str
    description: str = ""
    owner_token_hash: str | None = None
    created_at: str
    updated_at: str
    repo_path: str | None = None
    prompt: str | None = None
    backend: str | None = None
    model: str | None = None
    max_iterations: int | None = None
    pr_number: int | None = None
    issue_number: int | None = None
    create_issue: bool | None = None
    project_url: str | None = None
    no_pr: bool | None = None
    enable_execution: bool | None = None
    enable_web: bool | None = None
    use_native_cli_auth: bool | None = None
    fix_ci: bool | None = None
    fix_conflicts: bool | None = None
    master_rebase: bool | None = None
    ci_check_wait_minutes: float | None = None
    reference_repos: list[str] | None = None
    tools: list[str] | None = None


class TemplateListResponse(BaseModel):
    """Response for listing task templates."""

    templates: list[TemplateResponse]
    total: int


class CronPresetsResponse(BaseModel):
    """Response for listing available cron and interval presets."""

    presets: dict[str, str]
    interval_presets: dict[str, int] = Field(default_factory=dict)


class ClaudeUsageLevel(BaseModel):
    """A single usage tier (e.g. session or weekly)."""

    name: str
    percent_used: float
    detail: str


class ClaudeUsageResponse(BaseModel):
    """Claude Code CLI usage information."""

    levels: list[ClaudeUsageLevel] = Field(default_factory=list)
    error: str | None = None
    fetched_at: str


def _extract_usage_level(
    data: dict[str, Any],
    key: str,
    name: str,
) -> ClaudeUsageLevel | None:
    """Extract a single usage level from the API response.

    Args:
        data: Top-level usage API response dict.
        key: Key for the usage window (e.g. ``"five_hour"``).
        name: Human-readable label (e.g. ``"Session"``).

    Returns:
        A ``ClaudeUsageLevel`` if the window contains a numeric utilization
        value, otherwise ``None``.
    """
    window = data.get(key, {})
    utilization = window.get("utilization")
    if not isinstance(utilization, int | float):
        return None
    pct = round(utilization, 1)
    resets = window.get("resets_at", "")
    return ClaudeUsageLevel(
        name=name,
        percent_used=pct,
        detail=f"Resets {resets}" if resets else "",
    )


_usage_cache: ClaudeUsageResponse | None = None
_usage_cache_ts: float = 0.0


def _fetch_claude_usage(*, force: bool = False) -> ClaudeUsageResponse:
    """Fetch Claude Code usage via the Anthropic OAuth usage API.

    Results are cached for 5 minutes to avoid rate-limiting (429).
    Pass ``force=True`` to bypass the cache.
    """
    global _usage_cache, _usage_cache_ts

    if (
        not force
        and _usage_cache is not None
        and (time.monotonic() - _usage_cache_ts) < _USAGE_CACHE_TTL_S
    ):
        return _usage_cache

    now = datetime.now(UTC).isoformat()

    token = _get_claude_oauth_token()
    if not token:
        return ClaudeUsageResponse(
            error="Could not read Claude Code credentials",
            fetched_at=now,
        )

    try:
        req = urllib_request.Request(
            _ANTHROPIC_USAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": _ANTHROPIC_BETA_HEADER,
                "User-Agent": _USAGE_USER_AGENT,
            },
        )
        with urllib_request.urlopen(req, timeout=_USAGE_API_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode(errors="replace"))
    except urllib_error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode(errors="replace")[:_HTTP_ERROR_BODY_PREVIEW_LENGTH]
        except (OSError, UnicodeDecodeError):
            logger.debug("Failed to read HTTP error body", exc_info=True)
        return ClaudeUsageResponse(
            error=f"Usage API returned {exc.code}: {body}",
            fetched_at=now,
        )
    except (urllib_error.URLError, OSError, json.JSONDecodeError) as exc:
        return ClaudeUsageResponse(
            error=f"Usage API request failed: {exc}",
            fetched_at=now,
        )

    levels: list[ClaudeUsageLevel] = []
    for key, name in (("five_hour", "Session"), ("seven_day", "Weekly")):
        level = _extract_usage_level(data, key, name)
        if level is not None:
            levels.append(level)

    if not levels:
        return ClaudeUsageResponse(
            error=f"No usage data in response: {json.dumps(data)[:_USAGE_DATA_PREVIEW_LENGTH]}",
            fetched_at=now,
        )

    result = ClaudeUsageResponse(levels=levels, fetched_at=now)
    _usage_cache = result
    _usage_cache_ts = time.monotonic()
    return result


_TERMINAL_TASK_STATES = {"SUCCESS", "FAILURE", "REVOKED"}
_CURRENT_TASK_STATES = {
    "PENDING",
    "QUEUED",
    "RECEIVED",
    "STARTED",
    "RUNNING",
    "PROGRESS",
    "RETRY",
    "RESERVED",
    "SCHEDULED",
    "SENT",
}
_TASK_STATE_PRIORITY = {
    "STARTED": 6,
    "RUNNING": 6,
    "PROGRESS": 6,
    "RETRY": 5,
    "RECEIVED": 4,
    "PENDING": 3,
    "QUEUED": 3,
    "SENT": 3,
    "RESERVED": 2,
    "SCHEDULED": 1,
}
_BACKEND_LOOKUP: dict[str, BackendName] = {
    BACKEND_E2E: "e2e",
    BACKEND_BASIC_LANGGRAPH: "basic-langgraph",
    BACKEND_BASIC_ATOMIC: "basic-atomic",
    BACKEND_BASIC_AGENT: "basic-agent",
    BACKEND_CODEXCLI: "codexcli",
    BACKEND_CLAUDECODECLI: "claudecodecli",
    BACKEND_DOCKER_SANDBOX_CLAUDE: "docker-sandbox-claude",
    BACKEND_GOOSE: "goose",
    BACKEND_GEMINICLI: "geminicli",
    BACKEND_OPENCODECLI: "opencodecli",
    BACKEND_DEVINCLI: "devincli",
}
assert _TERMINAL_TASK_STATES.isdisjoint(_CURRENT_TASK_STATES), (
    "_TERMINAL_TASK_STATES and _CURRENT_TASK_STATES must be disjoint"
)

assert set(_TASK_STATE_PRIORITY.keys()) <= _CURRENT_TASK_STATES, (
    "_TASK_STATE_PRIORITY keys must be a subset of _CURRENT_TASK_STATES"
)

_RECENT_TERMINAL_WINDOW_S = 60  # seconds; include terminal tasks this recent

_FLOWER_API_URL_ENV = "HELPING_HANDS_FLOWER_API_URL"
_FLOWER_API_TIMEOUT_SECONDS_ENV = "HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS"
_DEFAULT_FLOWER_API_TIMEOUT_SECONDS = 0.75
_HELPING_HANDS_TASK_NAME = "helping_hands.build_feature"
_WORKER_CAPACITY_ENV_VARS = (
    "HELPING_HANDS_MAX_WORKERS",
    "HELPING_HANDS_WORKER_CONCURRENCY",
    "CELERY_WORKER_CONCURRENCY",
    "CELERYD_CONCURRENCY",
)
_DEFAULT_WORKER_CAPACITY = os.cpu_count() or 4


_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>helping_hands · server ui</title>
    <style>
      :root {
        --background: #020817;
        --background-soft: #0b1220;
        --panel: #0f172a;
        --panel-elevated: #111b31;
        --foreground: #e2e8f0;
        --muted: #94a3b8;
        --border: #1f2937;
        --ring: #334155;
        --primary: #2563eb;
        --primary-hover: #1d4ed8;
        --secondary: #1e293b;
        --secondary-hover: #334155;
        --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
      }
      * {
        box-sizing: border-box;
      }
      html,
      body {
        min-height: 100%;
      }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Space Grotesk", "Segoe UI", sans-serif;
        color: var(--foreground);
        background:
          radial-gradient(circle at 10% -10%, #172554 0%, transparent 40%),
          radial-gradient(circle at 110% 0%, #1e1b4b 0%, transparent 42%),
          linear-gradient(180deg, var(--background-soft) 0%, var(--background) 100%);
      }
      .page {
        max-width: 1280px;
        min-height: 100vh;
        margin: 0 auto;
        padding: 28px 20px 36px;
        display: grid;
        gap: 14px;
        grid-template-columns: 300px minmax(0, 1fr);
        align-items: start;
      }
      .main-column {
        display: grid;
        gap: 14px;
      }
      .card {
        background: linear-gradient(
          180deg,
          var(--panel-elevated) 0%,
          var(--panel) 100%
        );
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 20px 40px rgba(2, 8, 23, 0.45);
      }
      .task-list-card {
        position: sticky;
        top: 14px;
      }
      .new-submission-button {
        width: 100%;
        margin-bottom: 10px;
      }
      .new-submission-button.active {
        background: var(--primary-hover);
      }
      .task-list-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 8px;
      }
      .task-list-header h2 {
        margin: 0;
        font-size: 1rem;
      }
      .text-button {
        background: transparent;
        border: 0;
        color: var(--muted);
        font-weight: 600;
        padding: 0;
        cursor: pointer;
      }
      .text-button:hover {
        color: var(--foreground);
      }
      .text-button:disabled {
        opacity: 0.45;
        cursor: not-allowed;
      }
      .empty-list {
        margin: 8px 0 0;
        color: var(--muted);
        font-size: 0.92rem;
      }
      .task-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 8px;
        max-height: calc(100vh - 140px);
        overflow: auto;
      }
      .task-row {
        width: 100%;
        text-align: left;
        display: grid;
        gap: 6px;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 9px;
        background: #0b1326;
        color: var(--foreground);
        cursor: pointer;
      }
      .task-row:hover {
        border-color: var(--ring);
        background: #101a31;
      }
      .task-row.active {
        border-color: #3b82f6;
        background: #10203d;
      }
      .task-row-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }
      .task-row code {
        font-family: var(--mono);
        font-size: 0.76rem;
        color: #93c5fd;
      }
      .task-row-meta {
        font-size: 0.74rem;
        color: var(--muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .status-pill {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        border-radius: 999px;
        padding: 3px 7px;
        border: 1px solid transparent;
      }
      .status-pill.ok {
        color: #86efac;
        background: #052e16;
        border-color: rgba(34, 197, 94, 0.45);
      }
      .status-pill.fail {
        color: #fca5a5;
        background: #450a0a;
        border-color: rgba(239, 68, 68, 0.5);
      }
      .status-pill.run {
        color: #67e8f9;
        background: #083344;
        border-color: rgba(6, 182, 212, 0.5);
      }
      .status-pill.idle {
        color: #cbd5e1;
        background: #0f172a;
        border-color: #334155;
      }
      .header h1 {
        margin: 0;
        font-size: 1.4rem;
        letter-spacing: -0.015em;
      }
      .header p {
        margin: 6px 0 0;
        color: var(--muted);
      }
      .form-grid {
        display: grid;
        gap: 10px;
        margin-top: 12px;
      }
      .advanced-settings {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: #0b1326;
        overflow: hidden;
      }
      .advanced-settings > summary {
        cursor: pointer;
        padding: 10px 12px;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--foreground);
      }
      .advanced-settings[open] > summary {
        background: #101a31;
        border-bottom: 1px solid var(--border);
      }
      .advanced-settings-body {
        display: grid;
        gap: 10px;
        padding: 12px;
      }
      label {
        display: grid;
        gap: 6px;
        font-size: 0.93rem;
        color: var(--muted);
      }
      input,
      textarea,
      select,
      button {
        font: inherit;
      }
      input,
      textarea,
      select {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        color: var(--foreground);
        background: #0a1324;
      }
      input:focus,
      textarea:focus,
      select:focus {
        outline: 2px solid rgba(59, 130, 246, 0.45);
        outline-offset: 0;
        border-color: #3b82f6;
      }
      input[type="checkbox"] {
        width: auto;
        accent-color: var(--primary);
      }
      textarea {
        resize: vertical;
      }
      .row {
        display: grid;
        gap: 10px;
      }
      .two-col {
        grid-template-columns: 1fr 1fr;
      }
      .check-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .check-row {
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 9px 10px;
        background: #0b1326;
        color: var(--foreground);
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 9px;
      }
      button {
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 10px 14px;
        background: var(--primary);
        color: #eff6ff;
        cursor: pointer;
        font-weight: 600;
      }
      button:hover {
        background: var(--primary-hover);
      }
      button.secondary {
        background: var(--secondary);
        border-color: var(--border);
        color: var(--foreground);
      }
      button.secondary:hover {
        background: var(--secondary-hover);
      }
      .meta-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin-top: 10px;
      }
      .meta-item {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        background: #0b1326;
      }
      .meta-label {
        display: block;
        font-size: 0.82rem;
        color: var(--muted);
        margin-bottom: 4px;
      }
      .meta-item strong {
        display: block;
        font-family: var(--mono);
        font-size: 0.84rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
      }
      .usage-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .usage-label {
        min-width: 56px;
        font-size: 0.78rem;
        color: var(--muted);
        font-family: var(--mono);
      }
      .usage-track {
        flex: 1;
        height: 10px;
        background: #1e293b;
        border-radius: 5px;
        border: 1px solid var(--border);
        overflow: hidden;
      }
      .usage-fill {
        height: 100%;
        border-radius: 4px;
        background: #22d3ee;
        transition: width 0.4s ease;
      }
      .usage-fill.warn { background: #facc15; }
      .usage-fill.crit { background: #f87171; }
      .usage-pct {
        min-width: 32px;
        text-align: right;
        font-size: 0.78rem;
        font-family: var(--mono);
        color: var(--muted);
      }
      .output-pane {
        margin-top: 12px;
      }
      .pane-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 8px;
      }
      .pane-header h2 {
        margin: 0;
        font-size: 1rem;
      }
      .pane-tabs {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: #0a1324;
        padding: 2px;
      }
      .tab-btn {
        border: 0;
        border-radius: 6px;
        padding: 5px 10px;
        background: transparent;
        color: var(--muted);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.01em;
        cursor: pointer;
      }
      .tab-btn:hover {
        background: #16233f;
        color: var(--foreground);
      }
      .tab-btn.active {
        background: var(--secondary);
        color: var(--foreground);
      }
      .output-pane pre {
        margin: 0;
        min-height: 280px;
        max-height: min(68vh, 860px);
        overflow: auto;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #020817;
        color: #cbd5e1;
        font-family: var(--mono);
        font-size: 0.8rem;
        line-height: 1.45;
        white-space: pre;
      }
      .task-error-banner {
        margin: 0 0 8px;
        padding: 10px 12px;
        border-radius: 8px;
        border: 1px solid rgba(239, 68, 68, 0.5);
        background: var(--danger-soft);
        color: #fca5a5;
        font-size: 0.82rem;
        line-height: 1.45;
      }
      .task-error-banner strong {
        display: block;
        margin-bottom: 4px;
        color: #fecaca;
      }
      .task-error-banner code {
        font-family: var(--mono);
        font-size: 0.78rem;
        color: #fca5a5;
      }
      .prefix-filters {
        display: flex;
        align-items: center;
        gap: 5px;
        flex-wrap: wrap;
        padding: 4px 0;
        margin-bottom: 4px;
      }
      .prefix-filters-label {
        font-size: 0.7rem;
        color: var(--muted);
        font-weight: 600;
        margin-right: 2px;
      }
      .usage-total {
        margin-left: auto;
        font-size: 0.7rem;
        font-family: var(--mono);
        color: var(--accent);
        font-weight: 600;
        white-space: nowrap;
      }
      .prefix-chip {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1px 8px;
        background: transparent;
        color: var(--muted);
        font-family: var(--mono);
        font-size: 0.68rem;
        cursor: pointer;
        transition: all 0.15s;
        white-space: nowrap;
      }
      .prefix-chip:hover {
        border-color: var(--accent);
        color: var(--foreground);
      }
      .prefix-chip.show { color: var(--foreground); }
      .prefix-chip.hide {
        color: #6b7280;
        border-color: #7f1d1d;
        background: rgba(127,29,29,0.15);
        text-decoration: line-through;
      }
      .prefix-chip.only {
        color: #22c55e;
        border-color: #166534;
        background: rgba(22,101,52,0.15);
      }
      .prefix-chip.reset {
        font-family: inherit;
        color: var(--muted);
        border-style: dashed;
      }
      .prefix-chip.reset:hover { color: var(--foreground); }
      .prefix-chip-icon { font-size: 0.55rem; line-height: 1; }
      code {
        font-family: var(--mono);
        font-size: 0.84rem;
      }
      .is-hidden {
        display: none;
      }
      @media (max-width: 1020px) {
        .page {
          grid-template-columns: 1fr;
        }
        .task-list-card {
          position: static;
        }
        .task-list {
          max-height: 280px;
        }
      }
      @media (max-width: 920px) {
        .two-col,
        .check-grid,
        .meta-grid {
          grid-template-columns: 1fr;
        }
        .pane-header {
          align-items: flex-start;
          flex-direction: column;
        }
      }
      .server-ui-badge {
        font-size: 0.6em;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #93c5fd;
        background: rgba(37, 99, 235, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 6px;
        padding: 2px 7px;
        vertical-align: middle;
      }
      .status-blinker {
        width: 10px;
        height: 10px;
        border-radius: 999px;
        flex-shrink: 0;
        display: inline-block;
        cursor: help;
      }
      .status-blinker.pulse {
        animation: blinker-pulse 1.4s ease-in-out infinite;
      }
      @keyframes blinker-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
      }
      .status-with-blinker {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .toast-container {
        position: fixed;
        bottom: 16px;
        right: 16px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        z-index: 200;
        pointer-events: none;
      }
      .toast {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #111b31;
        border: 1px solid #1f2937;
        border-left: 3px solid #94a3b8;
        border-radius: 8px;
        padding: 10px 14px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: #e2e8f0;
        backdrop-filter: blur(8px);
        pointer-events: auto;
        animation: toast-slide-in 0.3s ease-out;
        min-width: 240px;
        max-width: 380px;
      }
      .toast--ok { border-left-color: #22c55e; }
      .toast--fail { border-left-color: #ef4444; }
      .toast-text {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .toast-close {
        background: none;
        border: none;
        color: #94a3b8;
        cursor: pointer;
        font-size: 1.1rem;
        padding: 0 2px;
        line-height: 1;
      }
      .toast-close:hover { color: #e2e8f0; }
      @keyframes toast-slide-in {
        from { opacity: 0; transform: translateX(100%); }
        to { opacity: 1; transform: translateX(0); }
      }
      /* --- Repo suggest / chip input --- */
      .repo-suggest-wrapper { position: relative; }
      .repo-chip-wrapper { position: relative; }
      .repo-chip-container {
        display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
        padding: 4px 8px; min-height: 34px;
        border: 1px solid #2a3553; border-radius: 8px;
        background: #0d1527; cursor: text;
      }
      .repo-chip {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 2px 8px; border-radius: 6px;
        background: rgba(99,102,241,0.18); border: 1px solid #6366f1;
        font-size: 0.82rem; white-space: nowrap;
      }
      .repo-chip-remove {
        all: unset; cursor: pointer; font-size: 0.85rem;
        line-height: 1; opacity: 0.6; padding: 0 1px;
      }
      .repo-chip-remove:hover { opacity: 1; }
      .repo-chip-input-el {
        flex: 1; min-width: 80px; border: none; outline: none;
        background: transparent; color: #e2e8f0; font-size: 0.82rem; padding: 2px 0;
      }
      .repo-dropdown {
        position: absolute; top: 100%; left: 0; right: 0; z-index: 50;
        margin: 2px 0 0; padding: 4px 0; list-style: none;
        background: #0f1729; border: 1px solid #2a3553; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4); max-height: 200px; overflow-y: auto;
      }
      .repo-dropdown-up {
        top: auto; bottom: 100%; margin: 0 0 2px;
      }
      .repo-dropdown li {
        padding: 6px 10px; font-size: 0.82rem; cursor: pointer;
      }
      .repo-dropdown li.highlighted {
        background: rgba(99,102,241,0.18);
      }
    </style>
  </head>
  <body>
    <main class="page">
      <aside class="card task-list-card">
        <button
          type="button"
          id="new-submission-btn"
          class="new-submission-button active"
        >
          New Task
        </button>
        <button
          type="button"
          id="schedules-btn"
          class="new-submission-button"
          style="margin-top: 8px;"
        >
          Scheduled tasks
        </button>
        <div class="task-list-header">
          <h2>Submitted tasks</h2>
          <button type="button" id="clear-history-btn" class="text-button">
            Clear
          </button>
        </div>
        <p id="empty-list" class="empty-list">No tasks submitted yet.</p>
        <ul id="task-list" class="task-list"></ul>
      </aside>

      <div class="main-column">
        <section id="submission-view" class="card">
          <header class="header">
            <h1>helping_hands <span class="server-ui-badge">server&nbsp;ui</span></h1>
            <p>
              Submit runs to <code>/build</code> and track progress from
              <code>/tasks/{task_id}</code>.
            </p>
          </header>

          <form id="run-form" method="post" action="/build/form" class="form-grid">
            <label for="repo_path">
              Repo path (owner/repo)
              <div class="repo-suggest-wrapper">
                <input
                  id="repo_path"
                  name="repo_path"
                  value="suryarastogi/helping_hands"
                  required
                  autocomplete="off"
                />
                <ul id="repo_path_dropdown" class="repo-dropdown" style="display:none"></ul>
              </div>
            </label>

            <label for="prompt">
              Prompt
              <textarea id="prompt" name="prompt" required rows="6">
__DEFAULT_SMOKE_TEST_PROMPT__</textarea>
            </label>

            <details class="advanced-settings">
              <summary>Advanced settings</summary>
              <div class="advanced-settings-body">
                <div class="row two-col">
                  <label for="backend">
                    Backend
                    <select id="backend" name="backend">
                      <option value="e2e">Smoke Test (internal)</option>
                      <option value="basic-langgraph">basic-langgraph</option>
                      <option value="basic-atomic">basic-atomic</option>
                      <option value="basic-agent">basic-agent</option>
                      <option value="codexcli" selected>codexcli</option>
                      <option value="claudecodecli">claudecodecli</option>
                      <option value="goose">goose</option>
                      <option value="geminicli">geminicli</option>
                      <option value="opencodecli">opencodecli</option>
                      <option value="devincli">devincli</option>
                    </select>
                  </label>

                  <label for="model">
                    Model (optional)
                    <input id="model" name="model" placeholder="claude-opus-4-6" />
                  </label>
                </div>

                <div class="row two-col">
                  <label for="max_iterations">
                    Max iterations
                    <input
                      id="max_iterations"
                      name="max_iterations"
                      type="number"
                      min="1"
                      value="6"
                    />
                  </label>

                  <label for="pr_number">
                    PR number (optional)
                    <input id="pr_number" name="pr_number" type="number" min="1" />
                  </label>
                </div>

                <label for="tools">
                  Tools (comma-separated, optional)
                  <input
                    id="tools"
                    name="tools"
                    placeholder="execution,web"
                  />
                </label>

                <div class="row check-grid">
                  <label class="check-row" for="no_pr">
                    <input id="no_pr" name="no_pr" type="checkbox" />
                    Disable final PR push/create
                  </label>

                  <label class="check-row" for="enable_execution">
                    <input
                      id="enable_execution"
                      name="enable_execution"
                      type="checkbox"
                    />
                    Enable execution tools
                  </label>

                  <label class="check-row" for="enable_web">
                    <input id="enable_web" name="enable_web" type="checkbox" />
                    Enable web tools
                  </label>

                  <label class="check-row" for="use_native_cli_auth">
                    <input
                      id="use_native_cli_auth"
                      name="use_native_cli_auth"
                      type="checkbox"
                    />
                    Use native CLI auth (Codex/Claude)
                  </label>

                  <label class="check-row" for="fix_ci">
                    <input id="fix_ci" name="fix_ci" type="checkbox" />
                    Fix CI failures (auto-retry)
                  </label>
                  <label class="check-row" for="fix_conflicts">
                    <input id="fix_conflicts" name="fix_conflicts" type="checkbox" />
                    AI Fix Conflicts
                  </label>
                  <label class="check-row" for="master_rebase">
                    <input id="master_rebase" name="master_rebase" type="checkbox" />
                    AI Master Rebase
                  </label>
                </div>
                <div class="row">
                  <label for="github_token">GitHub Token
                    <input id="github_token" name="github_token" type="password" placeholder="ghp_... (optional)" />
                  </label>
                </div>
                <div class="row">
                  <label>Reference Repos
                    <div class="repo-chip-wrapper" id="ref_repos_wrapper">
                      <div class="repo-chip-container" id="ref_repos_chips">
                        <input class="repo-chip-input-el" id="ref_repos_input" placeholder="owner/repo (optional, read-only)" autocomplete="off" />
                      </div>
                      <ul id="ref_repos_dropdown" class="repo-dropdown repo-dropdown-up" style="display:none"></ul>
                    </div>
                    <input id="reference_repos" name="reference_repos" type="hidden" />
                  </label>
                </div>
              </div>
            </details>

            <div class="actions">
              <button type="submit">Submit run</button>
            </div>
          </form>
        </section>

        <section id="monitor-view" class="card is-hidden">
          <div class="actions">
            <button id="stop-btn" type="button" class="secondary">
              Stop polling
            </button>
          </div>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">Status</span>
              <strong class="status-with-blinker">
                <span id="status-blinker" class="status-blinker"
                  style="background-color:#6b7280" title="idle"></span>
                <span id="status">idle</span>
              </strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">Task</span>
              <strong id="task_label">-</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">Polling</span>
              <strong id="polling_label">off</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">Runtime</span>
              <strong id="runtime_label">-</strong>
            </div>
          </div>

          <article class="output-pane">
            <div class="pane-header">
              <h2>Output</h2>
              <div class="pane-tabs" role="tablist" aria-label="Output mode">
                <button
                  type="button"
                  class="tab-btn active"
                  data-output-tab="updates"
                >
                  Updates
                </button>
                <button type="button" class="tab-btn" data-output-tab="raw">
                  Raw
                </button>
                <button type="button" class="tab-btn" data-output-tab="payload">
                  Payload
                </button>
              </div>
              <button type="button" id="copy_output_btn" class="secondary"
                style="font-size:0.7rem;padding:2px 8px;" title="Copy output to clipboard">Copy</button>
            </div>
            <div id="prefix_filters" class="prefix-filters" style="display:none;"></div>
            <div id="task_error_banner" class="task-error-banner" style="display:none;">
              <strong id="task_error_type"></strong>
              <code id="task_error_msg"></code>
            </div>
            <pre id="output_text">No updates yet.</pre>
          </article>
        </section>

        <section id="claude-usage-view" class="card" style="margin-bottom: 16px;">
          <header class="header" style="margin-bottom: 8px;">
            <h1 style="display:flex;align-items:center;gap:8px;">
              Claude Usage
              <button type="button" id="usage-refresh-btn" class="secondary"
                style="font-size:0.7rem;padding:3px 8px;">Refresh</button>
            </h1>
          </header>
          <div id="usage-meters" style="display:grid;gap:8px;">
            <span style="color:#94a3b8;font-size:0.8rem;">Loading...</span>
          </div>
          <div id="usage-error" style="color:#fca5a5;font-size:0.78rem;display:none;margin-top:4px;"></div>
          <div id="usage-timestamp" style="color:#64748b;font-size:0.7rem;margin-top:6px;"></div>
        </section>

        <section id="schedules-view" class="card is-hidden">
          <header class="header">
            <h1>Scheduled tasks <span class="server-ui-badge">cron</span></h1>
            <p>Create and monitor recurring builds with cron expressions.</p>
          </header>

          <div class="actions" style="margin-bottom: 16px;">
            <button type="button" id="new-schedule-btn">New schedule</button>
            <button type="button" id="refresh-schedules-btn" class="secondary">
              Refresh
            </button>
          </div>

          <div id="schedules-list">
            <p class="empty-list">No scheduled tasks yet.</p>
          </div>

          <div id="schedule-form-container" class="is-hidden" style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border);">
            <h2 id="schedule-form-title" style="margin-bottom: 12px;">New schedule</h2>
            <form id="schedule-form" class="form-grid">
              <input type="hidden" id="schedule_id" name="schedule_id" />
              <label for="schedule_name">
                Name
                <input id="schedule_name" name="name" required placeholder="e.g. Daily docs update" />
              </label>

              <div class="row two-col">
                <label for="schedule_cron">
                  Cron expression
                  <input id="schedule_cron" name="cron_expression" required placeholder="0 0 * * * (midnight)" />
                </label>
                <label for="schedule_preset">
                  Or preset
                  <select id="schedule_preset">
                    <option value="">Custom</option>
                    <option value="every_minute">Every minute</option>
                    <option value="every_5_minutes">Every 5 minutes</option>
                    <option value="every_15_minutes">Every 15 minutes</option>
                    <option value="hourly">Hourly</option>
                    <option value="daily">Daily (midnight)</option>
                    <option value="weekly">Weekly (Sunday midnight)</option>
                    <option value="monthly">Monthly (1st midnight)</option>
                    <option value="weekdays">Weekdays (9am)</option>
                  </select>
                </label>
              </div>

              <label for="schedule_repo">
                Repo path (owner/repo)
                <div class="repo-suggest-wrapper">
                  <input id="schedule_repo" name="repo_path" required placeholder="owner/repo" autocomplete="off" />
                  <ul id="schedule_repo_dropdown" class="repo-dropdown" style="display:none"></ul>
                </div>
              </label>

              <label for="schedule_prompt">
                Prompt
                <textarea id="schedule_prompt" name="prompt" required rows="4" placeholder="Update documentation..."></textarea>
              </label>

              <details class="advanced-settings">
                <summary>Advanced settings</summary>
                <div class="advanced-settings-body">
                  <div class="row two-col">
                    <label for="schedule_backend">
                      Backend
                      <select id="schedule_backend" name="backend">
                        <option value="claudecodecli" selected>claudecodecli</option>
                        <option value="codexcli">codexcli</option>
                        <option value="basic-langgraph">basic-langgraph</option>
                        <option value="basic-atomic">basic-atomic</option>
                        <option value="goose">goose</option>
                        <option value="geminicli">geminicli</option>
                        <option value="opencodecli">opencodecli</option>
                        <option value="devincli">devincli</option>
                      </select>
                    </label>
                    <label for="schedule_model">
                      Model (optional)
                      <input id="schedule_model" name="model" placeholder="claude-opus-4-6" />
                    </label>
                  </div>
                  <label for="schedule_pr_number">
                    PR number (optional)
                    <input id="schedule_pr_number" name="pr_number" type="number" min="1" />
                  </label>
                  <div class="row check-grid">
                    <label class="check-row" for="schedule_no_pr">
                      <input id="schedule_no_pr" name="no_pr" type="checkbox" />
                      Disable final PR
                    </label>
                    <label class="check-row" for="schedule_enabled">
                      <input id="schedule_enabled" name="enabled" type="checkbox" checked />
                      Enabled
                    </label>
                    <label class="check-row" for="schedule_fix_ci">
                      <input id="schedule_fix_ci" name="fix_ci" type="checkbox" />
                      Fix CI
                    </label>
                    <label class="check-row" for="schedule_fix_conflicts">
                      <input id="schedule_fix_conflicts" name="fix_conflicts" type="checkbox" />
                      AI Fix Conflicts
                    </label>
                    <label class="check-row" for="schedule_master_rebase">
                      <input id="schedule_master_rebase" name="master_rebase" type="checkbox" />
                      AI Master Rebase
                    </label>
                  </div>
                  <div class="row">
                    <label for="schedule_github_token">GitHub Token
                      <input id="schedule_github_token" name="github_token" type="password" placeholder="ghp_... (optional)" />
                    </label>
                  </div>
                  <div class="row">
                    <label>Reference Repos
                      <div class="repo-chip-wrapper" id="sched_ref_repos_wrapper">
                        <div class="repo-chip-container" id="sched_ref_repos_chips">
                          <input class="repo-chip-input-el" id="sched_ref_repos_input" placeholder="owner/repo (optional, read-only)" autocomplete="off" />
                        </div>
                        <ul id="sched_ref_repos_dropdown" class="repo-dropdown repo-dropdown-up" style="display:none"></ul>
                      </div>
                      <input id="schedule_reference_repos" name="reference_repos" type="hidden" />
                    </label>
                  </div>
                </div>
              </details>

              <div class="actions">
                <button type="submit" id="schedule-submit-btn">Create schedule</button>
                <button type="button" id="schedule-cancel-btn" class="secondary">Cancel</button>
              </div>
            </form>
          </div>
        </section>
      </div>
    </main>

    <script>
      // --- Recent repos (localStorage) ---
      const RECENT_REPOS_KEY = "hh_recent_repos";
      const MAX_RECENT = 20;
      function loadRecentRepos() {
        try { const r = JSON.parse(localStorage.getItem(RECENT_REPOS_KEY) || "[]"); return Array.isArray(r) ? r.filter(s => typeof s === "string") : []; }
        catch { return []; }
      }
      function saveRecentRepos(repos) {
        try { localStorage.setItem(RECENT_REPOS_KEY, JSON.stringify(repos)); } catch {}
      }
      function addRecentRepo(repo) {
        const t = repo.trim();
        if (!t) return;
        const prev = loadRecentRepos();
        const next = [t, ...prev.filter(r => r !== t)].slice(0, MAX_RECENT);
        saveRecentRepos(next);
      }

      // --- Suggest dropdown for single-value repo inputs ---
      function setupRepoSuggest(inputEl, dropdownEl) {
        let hlIdx = -1;
        function getFiltered() {
          const val = inputEl.value.trim().toLowerCase();
          const all = loadRecentRepos();
          return val ? all.filter(s => s.toLowerCase().includes(val)) : all;
        }
        function render() {
          const items = getFiltered().slice(0, 8);
          if (items.length === 0) { dropdownEl.style.display = "none"; return; }
          dropdownEl.innerHTML = items.map((r, i) =>
            `<li class="${i === hlIdx ? "highlighted" : ""}">${escapeHtml(r)}</li>`
          ).join("");
          dropdownEl.style.display = "";
          dropdownEl.querySelectorAll("li").forEach((li, i) => {
            li.addEventListener("mousedown", e => { e.preventDefault(); inputEl.value = items[i]; dropdownEl.style.display = "none"; hlIdx = -1; });
            li.addEventListener("mouseenter", () => { hlIdx = i; render(); });
          });
        }
        inputEl.addEventListener("input", () => { hlIdx = -1; render(); });
        inputEl.addEventListener("focus", () => render());
        inputEl.addEventListener("keydown", e => {
          const items = getFiltered().slice(0, 8);
          if (e.key === "ArrowDown") { e.preventDefault(); hlIdx = Math.min(hlIdx + 1, items.length - 1); render(); }
          else if (e.key === "ArrowUp") { e.preventDefault(); hlIdx = Math.max(hlIdx - 1, -1); render(); }
          else if (e.key === "Enter" && hlIdx >= 0 && hlIdx < items.length) { e.preventDefault(); inputEl.value = items[hlIdx]; dropdownEl.style.display = "none"; hlIdx = -1; }
          else if (e.key === "Escape") { dropdownEl.style.display = "none"; hlIdx = -1; }
        });
        document.addEventListener("mousedown", e => { if (!inputEl.parentElement.contains(e.target)) { dropdownEl.style.display = "none"; hlIdx = -1; } });
      }

      // --- Chip input for reference repos ---
      function setupChipInput(containerEl, inputEl, dropdownEl, hiddenEl) {
        let chips = [];
        let hlIdx = -1;

        function syncHidden() {
          hiddenEl.value = chips.join(", ");
        }
        function getFiltered() {
          const val = inputEl.value.trim().toLowerCase();
          const all = loadRecentRepos().filter(r => !chips.includes(r));
          return val ? all.filter(s => s.toLowerCase().includes(val)) : all;
        }
        function renderChips() {
          // Remove existing chip elements
          containerEl.querySelectorAll(".repo-chip").forEach(el => el.remove());
          chips.forEach(repo => {
            const span = document.createElement("span");
            span.className = "repo-chip";
            span.textContent = repo;
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "repo-chip-remove";
            btn.textContent = "\u00d7";
            btn.addEventListener("click", e => { e.stopPropagation(); chips = chips.filter(r => r !== repo); renderChips(); syncHidden(); });
            span.appendChild(btn);
            containerEl.insertBefore(span, inputEl);
          });
          inputEl.placeholder = chips.length === 0 ? "owner/repo (optional, read-only)" : "";
          syncHidden();
        }
        function renderDropdown() {
          const items = getFiltered().slice(0, 8);
          if (items.length === 0) { dropdownEl.style.display = "none"; return; }
          dropdownEl.innerHTML = items.map((r, i) =>
            `<li class="${i === hlIdx ? "highlighted" : ""}">${escapeHtml(r)}</li>`
          ).join("");
          dropdownEl.style.display = "";
          dropdownEl.querySelectorAll("li").forEach((li, i) => {
            li.addEventListener("mousedown", e => { e.preventDefault(); addChip(items[i]); });
            li.addEventListener("mouseenter", () => { hlIdx = i; renderDropdown(); });
          });
        }
        function addChip(repo) {
          const t = repo.trim();
          if (!t || chips.includes(t)) return;
          chips.push(t);
          inputEl.value = "";
          hlIdx = -1;
          renderChips();
          renderDropdown();
        }

        containerEl.addEventListener("click", () => inputEl.focus());
        inputEl.addEventListener("input", () => { hlIdx = -1; renderDropdown(); });
        inputEl.addEventListener("focus", () => renderDropdown());
        inputEl.addEventListener("keydown", e => {
          const items = getFiltered().slice(0, 8);
          if (e.key === "Enter" || e.key === "Tab" || e.key === ",") {
            if (hlIdx >= 0 && hlIdx < items.length) { e.preventDefault(); addChip(items[hlIdx]); return; }
            if (inputEl.value.trim()) { e.preventDefault(); addChip(inputEl.value); return; }
            if (e.key === "Tab") return;
          }
          if (e.key === "Backspace" && !inputEl.value && chips.length > 0) { chips.pop(); renderChips(); renderDropdown(); }
          if (e.key === "ArrowDown") { e.preventDefault(); hlIdx = Math.min(hlIdx + 1, items.length - 1); renderDropdown(); }
          if (e.key === "ArrowUp") { e.preventDefault(); hlIdx = Math.max(hlIdx - 1, -1); renderDropdown(); }
          if (e.key === "Escape") { dropdownEl.style.display = "none"; hlIdx = -1; }
        });
        document.addEventListener("mousedown", e => {
          if (!containerEl.parentElement.contains(e.target)) { dropdownEl.style.display = "none"; hlIdx = -1; }
        });

        // Public API to set chips programmatically (e.g. from query params or schedule edit)
        return {
          setChips(arr) { chips = [...arr]; renderChips(); },
          getChips() { return [...chips]; },
        };
      }

      const form = document.getElementById("run-form");
      const submissionView = document.getElementById("submission-view");
      const monitorView = document.getElementById("monitor-view");
      const newSubmissionBtn = document.getElementById("new-submission-btn");
      const clearHistoryBtn = document.getElementById("clear-history-btn");
      const taskListEl = document.getElementById("task-list");
      const emptyListEl = document.getElementById("empty-list");
      const stopBtn = document.getElementById("stop-btn");
      const statusEl = document.getElementById("status");
      const taskLabelEl = document.getElementById("task_label");
      const pollingLabelEl = document.getElementById("polling_label");
      const outputTextEl = document.getElementById("output_text");
      const statusBlinkerEl = document.getElementById("status-blinker");
      const runtimeLabelEl = document.getElementById("runtime_label");
      const tabButtons = Array.from(document.querySelectorAll("[data-output-tab]"));
      const historyStorageKey = "helping_hands_task_history_v1";
      const terminalStatuses = new Set(["SUCCESS", "FAILURE", "REVOKED"]);

      let taskId = null;
      let status = "idle";
      let payloadData = null;
      let updates = [];
      let outputTab = "updates";
      let isPolling = false;
      let accUsage = null;
      let accUsageCursor = 0;
      let pollHandle = null;
      let discoveryHandle = null;
      const prefixFilters = {};
      const prefixFiltersEl = document.getElementById("prefix_filters");
      const errorBannerEl = document.getElementById("task_error_banner");
      const errorTypeEl = document.getElementById("task_error_type");
      const errorMsgEl = document.getElementById("task_error_msg");
      const PREFIX_RE = new RegExp("^\\\\[([^\\\\]]+)\\\\]");
      let runtimeHandle = null;
      let startedAtMs = null;
      let taskHistory = loadTaskHistory();

      // Schedule elements
      const schedulesBtn = document.getElementById("schedules-btn");
      const schedulesView = document.getElementById("schedules-view");
      const schedulesList = document.getElementById("schedules-list");
      const newScheduleBtn = document.getElementById("new-schedule-btn");
      const refreshSchedulesBtn = document.getElementById("refresh-schedules-btn");
      const scheduleFormContainer = document.getElementById("schedule-form-container");
      const scheduleForm = document.getElementById("schedule-form");
      const scheduleFormTitle = document.getElementById("schedule-form-title");
      const scheduleSubmitBtn = document.getElementById("schedule-submit-btn");
      const scheduleCancelBtn = document.getElementById("schedule-cancel-btn");
      const schedulePreset = document.getElementById("schedule_preset");
      const scheduleCron = document.getElementById("schedule_cron");

      const cronPresets = {
        "every_minute": "* * * * *",
        "every_5_minutes": "*/5 * * * *",
        "every_15_minutes": "*/15 * * * *",
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "weekly": "0 0 * * 0",
        "monthly": "0 0 1 * *",
        "weekdays": "0 9 * * 1-5"
      };

      function setView(nextView) {
        const isSubmission = nextView === "submission";
        const isSchedules = nextView === "schedules";
        submissionView.classList.toggle("is-hidden", !isSubmission);
        monitorView.classList.toggle("is-hidden", isSubmission || isSchedules);
        schedulesView.classList.toggle("is-hidden", !isSchedules);
        newSubmissionBtn.classList.toggle("active", isSubmission);
        schedulesBtn.classList.toggle("active", isSchedules);
      }

      function setStatus(value) {
        status = value;
        statusEl.textContent = value;
        const tone = statusTone(value);
        statusBlinkerEl.style.backgroundColor = statusBlinkerColor(tone);
        statusBlinkerEl.title = value;
        statusBlinkerEl.classList.toggle("pulse", tone === "run");
      }

      function setTaskId(value) {
        taskId = value || null;
        taskLabelEl.textContent = taskId || "-";
      }

      function formatElapsed(ms) {
        const totalSec = Math.max(0, Math.floor(ms / 1000));
        const m = Math.floor(totalSec / 60);
        const s = totalSec % 60;
        return m > 0 ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`;
      }

      function startRuntimeTimer(isoStr) {
        stopRuntimeTimer();
        const ms = Date.parse(isoStr);
        if (!Number.isFinite(ms)) return;
        startedAtMs = ms;
        const tick = () => { runtimeLabelEl.textContent = formatElapsed(Date.now() - startedAtMs); };
        tick();
        runtimeHandle = setInterval(tick, 1000);
      }

      function stopRuntimeTimer() {
        if (runtimeHandle) { clearInterval(runtimeHandle); runtimeHandle = null; }
        startedAtMs = null;
      }

      function setPolling(value) {
        isPolling = value;
        pollingLabelEl.textContent = value ? "active" : "off";
      }

      function setOutput(value) {
        payloadData = value;
        // Show error banner for failed tasks
        const result = value && value.result;
        const isFail = statusTone(status) === "fail";
        const errorStr = result && typeof result.error === "string" ? result.error : null;
        const errorType = result && typeof result.error_type === "string" ? result.error_type : null;
        if (isFail && errorStr) {
          errorTypeEl.textContent = errorType || "Error";
          errorMsgEl.textContent = errorStr;
          errorBannerEl.style.display = "";
        } else {
          errorBannerEl.style.display = "none";
        }
        // incremental usage accumulation from payload
        const payloadUpdates = (value && value.result && Array.isArray(value.result.updates))
          ? value.result.updates.map((item) => String(item)) : [];
        if (payloadUpdates.length < accUsageCursor) {
          // reset (task switch)
          accUsageCursor = 0;
          accUsage = null;
          if (payloadUpdates.length > 0) {
            accUsage = accumulateUsage(payloadUpdates);
            accUsageCursor = payloadUpdates.length;
          }
        } else if (payloadUpdates.length > accUsageCursor) {
          const delta = accumulateUsage(payloadUpdates.slice(accUsageCursor));
          accUsageCursor = payloadUpdates.length;
          if (delta) {
            if (!accUsage) { accUsage = delta; }
            else {
              accUsage = {
                totalCost: accUsage.totalCost + delta.totalCost,
                totalSeconds: accUsage.totalSeconds + delta.totalSeconds,
                totalIn: accUsage.totalIn + delta.totalIn,
                totalOut: accUsage.totalOut + delta.totalOut,
                count: accUsage.count + delta.count,
              };
            }
          }
        }
        renderOutput();
      }

      function setUpdates(value) {
        updates = Array.isArray(value) ? value.map((item) => String(item)) : [];
        renderOutput();
      }

      function shortTaskId(value) {
        if (!value || value.length <= 26) {
          return value || "-";
        }
        return `${value.slice(0, 10)}...${value.slice(-8)}`;
      }

      let toastCounter = 0;
      const toastContainerEl = document.getElementById("toast-container");

      function showToast(tid, tStatus) {
        const tone = statusTone(tStatus);
        const el = document.createElement("div");
        el.className = "toast toast--" + tone;
        el.innerHTML =
          '<span class="toast-text">Task ' + shortTaskId(tid) + " \u2014 " + tStatus + "</span>" +
          '<button class="toast-close" aria-label="Dismiss">\u00d7</button>';
        el.querySelector(".toast-close").onclick = function () { el.remove(); };
        toastContainerEl.appendChild(el);
        setTimeout(function () { el.remove(); }, 5000);
      }

      var _swReg = null;
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/notif-sw.js").then(function(reg) {
          _swReg = reg;
        }).catch(function() {});
      }

      function sendBrowserNotification(tid, tStatus) {
        if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
        var tone = tStatus.toUpperCase() === "SUCCESS" ? "completed successfully" : "failed";
        var body = "Task " + shortTaskId(tid) + " " + tone;
        if (_swReg) {
          _swReg.showNotification("Helping Hands", { body: body, tag: tid });
        } else {
          try { new Notification("Helping Hands", { body: body }); } catch(e) {}
        }
      }

      if (typeof Notification !== "undefined" && Notification.permission === "default") {
        Notification.requestPermission();
      }

      function statusTone(value) {
        const normalized = String(value || "").trim().toUpperCase();
        if (normalized === "SUCCESS") {
          return "ok";
        }
        if (
          normalized === "FAILURE" ||
          normalized === "REVOKED" ||
          normalized === "POLL_ERROR"
        ) {
          return "fail";
        }
        if (
          [
            "QUEUED",
            "PENDING",
            "STARTED",
            "RUNNING",
            "RECEIVED",
            "RETRY",
            "PROGRESS",
            "SCHEDULED",
            "RESERVED",
            "SENT",
            "MONITORING",
            "SUBMITTING",
          ].includes(normalized)
        ) {
          return "run";
        }
        return "idle";
      }

      function statusBlinkerColor(tone) {
        if (tone === "ok") return "#22c55e";
        if (tone === "fail") return "#ef4444";
        if (tone === "run") return "#eab308";
        return "#6b7280";
      }

      function parseOptimisticUpdates(rawUpdates) {
        const lines = [];
        const source = Array.isArray(rawUpdates) ? rawUpdates : [];
        for (const entry of source) {
          const chunks = String(entry).split(/\r?\n/);
          for (const chunk of chunks) {
            const trimmed = chunk.trim();
            if (!trimmed) {
              continue;
            }
            if (trimmed.includes(".zshenv:.:1: no such file or directory")) {
              continue;
            }
            lines.push(trimmed);
          }
        }
        return lines;
      }

      function extractPrefixes(rawUpdates) {
        const seen = new Set();
        for (const entry of rawUpdates) {
          for (const line of String(entry).split(/\r?\n/)) {
            const m = line.trim().match(PREFIX_RE);
            if (m) seen.add(m[1]);
          }
        }
        return Array.from(seen).sort();
      }

      function filterLinesByPrefix(text, filters) {
        const entries = Object.entries(filters);
        if (entries.length === 0) return text;
        const hasOnly = entries.some(([, mode]) => mode === "only");
        const result = [];
        for (const line of text.split("\n")) {
          const m = line.match(PREFIX_RE);
          const prefix = m ? m[1] : null;
          if (hasOnly) {
            if (!prefix || filters[prefix] !== "only") continue;
            result.push(line.replace(PREFIX_RE, "").trimStart());
          } else {
            if (prefix && filters[prefix] === "hide") continue;
            result.push(line);
          }
        }
        return result.join("\n");
      }

      function accumulateUsage(rawUpdates) {
        const apiCostRe = /api:\\s*\\$([0-9]+(?:\\.[0-9]+)?)/;
        let totalCost = 0, totalSeconds = 0, totalIn = 0, totalOut = 0, count = 0;
        for (const entry of rawUpdates) {
          for (const line of String(entry).split(/\r?\n/)) {
            const costMatch = line.match(apiCostRe);
            if (!costMatch) continue;
            count++;
            totalCost += parseFloat(costMatch[1]);
            const secMatch = line.match(/([0-9]+(?:\\.[0-9]+)?)s/);
            if (secMatch) totalSeconds += parseFloat(secMatch[1]);
            const inMatch = line.match(/in=([0-9]+)/);
            if (inMatch) totalIn += parseInt(inMatch[1], 10);
            const outMatch = line.match(/out=([0-9]+)/);
            if (outMatch) totalOut += parseInt(outMatch[1], 10);
          }
        }
        if (count === 0) return null;
        return { totalCost, totalSeconds, totalIn, totalOut, count };
      }

      function renderPrefixFilters() {
        const prefixes = extractPrefixes(updates);
        const usage = accUsage;
        if (prefixes.length === 0 && !usage) {
          prefixFiltersEl.style.display = "none";
          return;
        }
        if ((prefixes.length === 0 || outputTab === "payload") && !usage) {
          prefixFiltersEl.style.display = "none";
          return;
        }
        prefixFiltersEl.style.display = "flex";
        let html = '';
        if (prefixes.length > 0 && outputTab !== "payload") {
          html += '<span class="prefix-filters-label">Filter:</span>';
          for (const prefix of prefixes) {
            const mode = prefixFilters[prefix] || "show";
            const icons = { show: "\u25cf", hide: "\u25cb", only: "\u25c9" };
            const titles = {
              show: "Showing (click to hide)",
              hide: "Hidden (click for only)",
              only: "Only (click to reset)",
            };
            html += `<button type="button" class="prefix-chip ${mode}" data-prefix="${prefix}" title="[${prefix}] \u2014 ${titles[mode]}"><span class="prefix-chip-icon">${icons[mode]}</span>[${prefix}]</button>`;
          }
          if (Object.keys(prefixFilters).length > 0) {
            html += '<button type="button" class="prefix-chip reset" data-prefix="__reset__" title="Reset all filters">Reset</button>';
          }
        }
        if (usage) {
          html += `<span class="usage-total" title="${usage.count} API call${usage.count !== 1 ? 's' : ''}, ${Math.round(usage.totalSeconds)}s, in=${usage.totalIn.toLocaleString()} out=${usage.totalOut.toLocaleString()}">api: $${usage.totalCost.toFixed(4)}, ${Math.round(usage.totalSeconds)}s, in=${usage.totalIn.toLocaleString()} out=${usage.totalOut.toLocaleString()}</span>`;
        }
        prefixFiltersEl.innerHTML = html;
      }

      prefixFiltersEl.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-prefix]");
        if (!btn) return;
        const prefix = btn.getAttribute("data-prefix");
        if (prefix === "__reset__") {
          for (const key of Object.keys(prefixFilters)) delete prefixFilters[key];
        } else {
          const current = prefixFilters[prefix] || "show";
          const next = current === "show" ? "hide" : current === "hide" ? "only" : "show";
          if (next === "show") {
            delete prefixFilters[prefix];
          } else {
            prefixFilters[prefix] = next;
          }
        }
        renderPrefixFilters();
        renderOutput();
      });

      function renderOutput() {
        let text = "No updates yet.";
        if (outputTab === "payload") {
          text = payloadData ? JSON.stringify(payloadData, null, 2) : "{}";
        } else if (outputTab === "raw") {
          text = updates.length > 0 ? updates.join("\n") : "No raw output yet.";
        } else {
          const parsed = parseOptimisticUpdates(updates);
          text = parsed.length > 0 ? parsed.join("\n") : "No updates yet.";
        }
        if (outputTab !== "payload") {
          text = filterLinesByPrefix(text, prefixFilters);
        }
        outputTextEl.textContent = text;
        renderPrefixFilters();
      }

      function setOutputTab(nextTab) {
        outputTab = nextTab;
        for (const button of tabButtons) {
          const active = button.getAttribute("data-output-tab") === nextTab;
          button.classList.toggle("active", active);
        }
        renderOutput();
      }

      function loadTaskHistory() {
        try {
          const raw = window.localStorage.getItem(historyStorageKey);
          if (!raw) {
            return [];
          }
          const parsed = JSON.parse(raw);
          if (!Array.isArray(parsed)) {
            return [];
          }
          return parsed
            .filter(
              (item) =>
                item &&
                typeof item === "object" &&
                String(item.taskId || "").trim()
            )
            .slice(0, 60);
        } catch (_ignored) {
          return [];
        }
      }

      function persistTaskHistory() {
        try {
          window.localStorage.setItem(historyStorageKey, JSON.stringify(taskHistory));
        } catch (_ignored) {
          // Best effort only.
        }
      }

      function upsertTaskHistory(patch) {
        const normalizedId = String(patch.taskId || "").trim();
        if (!normalizedId) {
          return;
        }
        const now = Date.now();
        const idx = taskHistory.findIndex((item) => item.taskId === normalizedId);
        if (idx >= 0) {
          const existing = taskHistory[idx];
          const updated = {
            ...existing,
            status: patch.status || existing.status,
            backend: patch.backend || existing.backend,
            repoPath: patch.repoPath || existing.repoPath,
            lastUpdatedAt: now,
          };
          taskHistory = [updated].concat(
            taskHistory.filter((_, index) => index !== idx)
          );
        } else {
          taskHistory = [
            {
              taskId: normalizedId,
              status: patch.status || "queued",
              backend: patch.backend || "unknown",
              repoPath: patch.repoPath || "",
              createdAt: now,
              lastUpdatedAt: now,
            },
          ].concat(taskHistory);
        }
        taskHistory = taskHistory.slice(0, 60);
        persistTaskHistory();
        renderTaskHistory();
      }

      function renderTaskHistory() {
        taskListEl.innerHTML = "";
        if (taskHistory.length === 0) {
          emptyListEl.style.display = "block";
          clearHistoryBtn.disabled = true;
          return;
        }
        emptyListEl.style.display = "none";
        clearHistoryBtn.disabled = false;

        for (const item of taskHistory) {
          const row = document.createElement("button");
          row.type = "button";
          row.className = "task-row";
          if (!monitorView.classList.contains("is-hidden") && taskId === item.taskId) {
            row.classList.add("active");
          }

          const top = document.createElement("span");
          top.className = "task-row-top";
          const idCode = document.createElement("code");
          idCode.textContent = shortTaskId(item.taskId);
          const tone = statusTone(item.status);
          const rowBlinker = document.createElement("span");
          rowBlinker.className = `status-blinker${tone === "run" ? " pulse" : ""}`;
          rowBlinker.style.backgroundColor = statusBlinkerColor(tone);
          rowBlinker.title = item.status;
          const statusPill = document.createElement("span");
          statusPill.className = `status-pill ${tone}`;
          statusPill.textContent = item.status;
          top.appendChild(idCode);
          top.appendChild(rowBlinker);
          top.appendChild(statusPill);

          const meta = document.createElement("span");
          meta.className = "task-row-meta";
          const backend = item.backend || "unknown";
          const repoPath = item.repoPath || "manual";
          const timestamp = new Date(
            item.lastUpdatedAt || Date.now()
          ).toLocaleTimeString();
          meta.textContent = `${backend} | ${repoPath} | ${timestamp}`;

          row.appendChild(top);
          row.appendChild(meta);
          row.title = item.taskId;
          row.addEventListener("click", () => {
            selectTask(item.taskId);
          });

          const listItem = document.createElement("li");
          listItem.appendChild(row);
          taskListEl.appendChild(listItem);
        }
      }

      async function pollTaskOnce(taskId) {
        const pollUrl = `/tasks/${encodeURIComponent(taskId)}?_=${Date.now()}`;
        const response = await fetch(pollUrl, { cache: "no-store" });
        if (!response.ok) {
          let details = "";
          try {
            const errData = await response.json();
            if (errData && typeof errData === "object") {
              details = errData.detail || JSON.stringify(errData);
            }
          } catch (_ignored) {
            details = await response.text();
          }
          const suffix = details ? `: ${details}` : "";
          throw new Error(`Task lookup failed: ${response.status}${suffix}`);
        }
        const data = await response.json();
        setStatus(data.status);
        if (Array.isArray(data && data.result && data.result.updates)) {
          setUpdates(data.result.updates);
        } else {
          setUpdates([]);
        }
        setOutput(data);
        const sa = data.result && data.result.started_at;
        if (sa && !terminalStatuses.has(data.status) && !runtimeHandle) {
          startRuntimeTimer(sa);
        }
        upsertTaskHistory({
          taskId: data.task_id,
          status: data.status,
        });
        if (terminalStatuses.has(data.status)) {
          stopRuntimeTimer();
          const rt = data.result && data.result.runtime;
          if (rt) { runtimeLabelEl.textContent = rt; }
          showToast(data.task_id, data.status);
          sendBrowserNotification(data.task_id, data.status);
          stopPolling();
        }
      }

      function stopPolling() {
        if (pollHandle) {
          clearInterval(pollHandle);
          pollHandle = null;
        }
        setPolling(false);
      }

      function startPolling(taskId) {
        stopPolling();
        setTaskId(taskId);
        setPolling(true);
        setView("monitor");
        pollTaskOnce(taskId).catch((err) => {
          setStatus("error");
          setOutput({ error: String(err) });
        });
        pollHandle = setInterval(() => {
          pollTaskOnce(taskId).catch((err) => {
            // Keep retrying; transient backend errors should not stop monitoring.
            setStatus("poll_error");
            setOutput({ error: String(err) });
          });
        }, 2000);
      }

      function selectTask(selectedTaskId) {
        stopRuntimeTimer();
        runtimeLabelEl.textContent = "-";
        setStatus("monitoring");
        setOutput(null);
        setUpdates([]);
        setOutputTab("updates");
        startPolling(selectedTaskId);
        upsertTaskHistory({
          taskId: selectedTaskId,
          status: "monitoring",
        });
      }

      function clearForNewSubmission() {
        stopPolling();
        stopRuntimeTimer();
        runtimeLabelEl.textContent = "-";
        setStatus("idle");
        setTaskId(null);
        setOutput(null);
        setUpdates([]);
        setOutputTab("updates");
        setView("submission");
        renderTaskHistory();
      }

      function applyQueryDefaults() {
        const params = new URLSearchParams(window.location.search);
        const repoPath = params.get("repo_path");
        const prompt = params.get("prompt");
        const backend = params.get("backend");
        const model = params.get("model");
        const maxIterations = params.get("max_iterations");
        const prNumber = params.get("pr_number");
        const noPr = params.get("no_pr");
        const enableExecution = params.get("enable_execution");
        const enableWeb = params.get("enable_web");
        const useNativeCliAuth = params.get("use_native_cli_auth");
        const fixCi = params.get("fix_ci");
        const fixConflicts = params.get("fix_conflicts");
        const masterRebase = params.get("master_rebase");
        const tools = params.get("tools");
        const taskId = params.get("task_id");
        const status = params.get("status");
        const error = params.get("error");

        if (repoPath) {
          document.getElementById("repo_path").value = repoPath;
        }
        if (prompt) {
          document.getElementById("prompt").value = prompt;
        }
        if (backend) {
          document.getElementById("backend").value = backend;
        }
        if (model) {
          document.getElementById("model").value = model;
        }
        if (maxIterations) {
          document.getElementById("max_iterations").value = maxIterations;
        }
        if (prNumber) {
          document.getElementById("pr_number").value = prNumber;
        }
        if (tools) {
          document.getElementById("tools").value = tools;
        }
        if (noPr === "1" || noPr === "true") {
          document.getElementById("no_pr").checked = true;
        }
        if (enableExecution === "1" || enableExecution === "true") {
          document.getElementById("enable_execution").checked = true;
        }
        if (enableWeb === "1" || enableWeb === "true") {
          document.getElementById("enable_web").checked = true;
        }
        if (useNativeCliAuth === "1" || useNativeCliAuth === "true") {
          document.getElementById("use_native_cli_auth").checked = true;
        }
        if (fixCi === "1" || fixCi === "true") {
          document.getElementById("fix_ci").checked = true;
        }
        if (fixConflicts === "1" || fixConflicts === "true") {
          document.getElementById("fix_conflicts").checked = true;
        }
        if (masterRebase === "1" || masterRebase === "true") {
          document.getElementById("master_rebase").checked = true;
        }
        const githubTokenParam = params.get("github_token");
        if (githubTokenParam) {
          document.getElementById("github_token").value = githubTokenParam;
        }
        const referenceReposParam = params.get("reference_repos");
        if (referenceReposParam) {
          refReposChip.setChips(referenceReposParam.split(",").map(s => s.trim()).filter(s => s.length > 0));
        }
        if (error) {
          setStatus("error");
          setOutput({ error });
        }
        if (taskId) {
          upsertTaskHistory({
            taskId,
            status: status || "queued",
            backend: backend || undefined,
            repoPath: repoPath || undefined,
          });
          setStatus(status || "queued");
          selectTask(taskId);
        }
      }

      async function refreshCurrentTasks() {
        try {
          const response = await fetch(`/tasks/current?_=${Date.now()}`, {
            cache: "no-store",
          });
          if (!response.ok) {
            return;
          }
          const data = await response.json();
          if (!Array.isArray(data.tasks)) {
            return;
          }
          for (const item of data.tasks) {
            const discoveredTaskId = String(
              item && item.task_id ? item.task_id : ""
            ).trim();
            if (!discoveredTaskId) {
              continue;
            }
            upsertTaskHistory({
              taskId: discoveredTaskId,
              status: String(item.status || "unknown"),
              backend: typeof item.backend === "string" ? item.backend : undefined,
              repoPath: typeof item.repo_path === "string" ? item.repo_path : undefined,
            });
          }
        } catch (_ignored) {
          // Best effort only.
        }
      }

      // Initialize suggest dropdowns and chip inputs
      setupRepoSuggest(document.getElementById("repo_path"), document.getElementById("repo_path_dropdown"));
      setupRepoSuggest(document.getElementById("schedule_repo"), document.getElementById("schedule_repo_dropdown"));
      const refReposChip = setupChipInput(
        document.getElementById("ref_repos_chips"),
        document.getElementById("ref_repos_input"),
        document.getElementById("ref_repos_dropdown"),
        document.getElementById("reference_repos"),
      );
      const schedRefReposChip = setupChipInput(
        document.getElementById("sched_ref_repos_chips"),
        document.getElementById("sched_ref_repos_input"),
        document.getElementById("sched_ref_repos_dropdown"),
        document.getElementById("schedule_reference_repos"),
      );

      applyQueryDefaults();
      renderTaskHistory();
      renderOutput();

      refreshCurrentTasks();
      discoveryHandle = setInterval(() => {
        refreshCurrentTasks();
      }, 5000);

      /* ── Claude Usage Meter ── */
      const usageMeters = document.getElementById("usage-meters");
      const usageError = document.getElementById("usage-error");
      const usageTimestamp = document.getElementById("usage-timestamp");
      const usageRefreshBtn = document.getElementById("usage-refresh-btn");

      async function refreshClaudeUsage() {
        try {
          usageRefreshBtn.disabled = true;
          const res = await fetch("/health/claude-usage?force=true&_=" + Date.now(), { cache: "no-store" });
          if (!res.ok) {
            usageMeters.innerHTML = '<span style="color:#94a3b8;font-size:0.8rem;">Unavailable</span>';
            return;
          }
          const data = await res.json();
          if (data.error) {
            usageMeters.innerHTML = "";
            usageError.textContent = data.error;
            usageError.style.display = "block";
          } else {
            usageError.style.display = "none";
            let html = "";
            for (const level of data.levels || []) {
              const pct = Math.min(level.percent_used, 100);
              const cls = pct >= 90 ? " crit" : pct >= 70 ? " warn" : "";
              html += '<div class="usage-row">'
                + '<span class="usage-label">' + level.name + '</span>'
                + '<div class="usage-track"><div class="usage-fill' + cls + '" style="width:' + pct + '%"></div></div>'
                + '<span class="usage-pct">' + Math.round(pct) + '%</span>'
                + '</div>';
            }
            usageMeters.innerHTML = html || '<span style="color:#94a3b8;font-size:0.8rem;">No data</span>';
          }
          if (data.fetched_at) {
            const d = new Date(data.fetched_at);
            usageTimestamp.textContent = "Updated " + d.toLocaleTimeString();
          }
        } catch (_) {
          usageMeters.innerHTML = '<span style="color:#94a3b8;font-size:0.8rem;">Failed to load</span>';
        } finally {
          usageRefreshBtn.disabled = false;
        }
      }

      refreshClaudeUsage();
      setInterval(refreshClaudeUsage, 3600000);
      usageRefreshBtn.addEventListener("click", refreshClaudeUsage);

      newSubmissionBtn.addEventListener("click", () => {
        clearForNewSubmission();
      });

      clearHistoryBtn.addEventListener("click", () => {
        taskHistory = [];
        persistTaskHistory();
        renderTaskHistory();
      });

      for (const button of tabButtons) {
        button.addEventListener("click", () => {
          const nextTab = button.getAttribute("data-output-tab");
          if (!nextTab) {
            return;
          }
          setOutputTab(nextTab);
        });
      }

      document.getElementById("copy_output_btn").addEventListener("click", () => {
        const text = outputTextEl.textContent || "";
        navigator.clipboard.writeText(text).catch(() => {});
      });

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setStatus("submitting");
        setView("monitor");
        setPolling(false);
        setTaskId(null);
        setUpdates([]);
        setOutputTab("updates");
        const repoPath = document.getElementById("repo_path").value.trim();
        const prompt = document.getElementById("prompt").value.trim();
        const backend = document.getElementById("backend").value;
        const model = document.getElementById("model").value.trim();
        const maxIterationsRaw = document.getElementById("max_iterations").value.trim();
        const prRaw = document.getElementById("pr_number").value.trim();
        const toolsRaw = document.getElementById("tools").value.trim();
        const noPr = document.getElementById("no_pr").checked;
        const enableExecution = document.getElementById("enable_execution").checked;
        const enableWeb = document.getElementById("enable_web").checked;
        const useNativeCliAuth = document.getElementById("use_native_cli_auth").checked;
        const fixCi = document.getElementById("fix_ci").checked;
        const fixConflicts = document.getElementById("fix_conflicts").checked;
        const masterRebase = document.getElementById("master_rebase").checked;
        const githubToken = document.getElementById("github_token").value.trim();
        const referenceRepos = document.getElementById("reference_repos").value.trim();
        const payload = {
          repo_path: repoPath,
          prompt,
          backend,
          max_iterations: maxIterationsRaw ? Number(maxIterationsRaw) : 6,
          no_pr: noPr,
          enable_execution: enableExecution,
          enable_web: enableWeb,
          use_native_cli_auth: useNativeCliAuth,
          fix_ci: fixCi,
          fix_conflicts: fixConflicts,
          master_rebase: masterRebase,
        };
        if (model) {
          payload.model = model;
        }
        if (prRaw) {
          payload.pr_number = Number(prRaw);
        }
        if (toolsRaw) {
          payload.tools = toolsRaw
            .split(",")
            .map((item) => item.trim())
            .filter((item) => item.length > 0);
        }
        if (githubToken) {
          payload.github_token = githubToken;
        }
        if (referenceRepos) {
          payload.reference_repos = referenceRepos.split(",").map(s => s.trim()).filter(s => s.length > 0);
        }

        try {
          const response = await fetch("/build", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data?.detail || `Build enqueue failed: ${response.status}`);
          }
          setTaskId(data.task_id);
          setStatus(data.status);
          setOutput(data);
          setUpdates([]);
          upsertTaskHistory({
            taskId: data.task_id,
            status: data.status,
            backend: data.backend,
            repoPath,
          });
          // Remember repos for autocomplete
          addRecentRepo(repoPath);
          for (const r of refReposChip.getChips()) { addRecentRepo(r); }
          startPolling(data.task_id);
        } catch (err) {
          setStatus("error");
          setOutput({ error: String(err) });
          setPolling(false);
        }
      });

      stopBtn.addEventListener("click", () => {
        stopPolling();
        setStatus("stopped");
      });

      window.addEventListener("beforeunload", () => {
        stopPolling();
        if (discoveryHandle) {
          clearInterval(discoveryHandle);
          discoveryHandle = null;
        }
      });

      // Schedule management functions
      schedulesBtn.addEventListener("click", () => {
        if (schedulesView.classList.contains("is-hidden")) {
          setView("schedules");
          loadSchedules();
        } else {
          setView("submission");
        }
      });

      schedulePreset.addEventListener("change", (e) => {
        const preset = e.target.value;
        if (preset && cronPresets[preset]) {
          scheduleCron.value = cronPresets[preset];
        }
      });

      newScheduleBtn.addEventListener("click", () => {
        scheduleFormTitle.textContent = "New schedule";
        scheduleSubmitBtn.textContent = "Create schedule";
        scheduleForm.reset();
        document.getElementById("schedule_id").value = "";
        document.getElementById("schedule_enabled").checked = true;
        schedRefReposChip.setChips([]);
        scheduleFormContainer.classList.remove("is-hidden");
      });

      scheduleCancelBtn.addEventListener("click", () => {
        scheduleFormContainer.classList.add("is-hidden");
        scheduleForm.reset();
        schedRefReposChip.setChips([]);
      });

      refreshSchedulesBtn.addEventListener("click", loadSchedules);

      async function loadSchedules() {
        try {
          const response = await fetch("/schedules");
          if (!response.ok) throw new Error("Failed to load schedules");
          const data = await response.json();
          renderSchedules(data.schedules);
        } catch (err) {
          schedulesList.innerHTML = `<p class="empty-list" style="color:#ef4444;">Error: ${err.message}</p>`;
        }
      }

      function renderSchedules(schedules) {
        if (!schedules || schedules.length === 0) {
          schedulesList.innerHTML = '<p class="empty-list">No scheduled tasks yet.</p>';
          return;
        }
        let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';
        for (const s of schedules) {
          const statusColor = s.enabled ? "#22c55e" : "#6b7280";
          const statusText = s.enabled ? "enabled" : "disabled";
          const nextRun = s.next_run_at ? new Date(s.next_run_at).toLocaleString() : "N/A";
          const lastRun = s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "Never";
          html += `
            <div class="schedule-item" style="background: var(--secondary); border-radius: 8px; padding: 12px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong>${escapeHtml(s.name)}</strong>
                <span style="display: flex; align-items: center; gap: 6px;">
                  <span class="status-blinker" style="background-color: ${statusColor};"></span>
                  <span class="status-pill" style="background: ${statusColor};">${statusText}</span>
                </span>
              </div>
              <div style="font-size: 12px; color: var(--muted); display: grid; gap: 4px;">
                <div><strong>Cron:</strong> <code>${escapeHtml(s.cron_expression)}</code></div>
                <div><strong>Repo:</strong> ${escapeHtml(s.repo_path)}</div>
                <div><strong>Prompt:</strong> ${escapeHtml(s.prompt.substring(0, 80))}${s.prompt.length > 80 ? "..." : ""}</div>
                <div><strong>Next run:</strong> ${nextRun}</div>
                <div><strong>Last run:</strong> ${lastRun} (${s.run_count} runs)</div>
              </div>
              <div style="margin-top: 10px; display: flex; gap: 8px;">
                <button type="button" class="secondary" onclick="editSchedule('${s.schedule_id}')" style="font-size: 12px; padding: 4px 8px;">Edit</button>
                <button type="button" class="secondary" onclick="triggerSchedule('${s.schedule_id}')" style="font-size: 12px; padding: 4px 8px;">Run now</button>
                <button type="button" class="secondary" onclick="toggleSchedule('${s.schedule_id}', ${!s.enabled})" style="font-size: 12px; padding: 4px 8px;">${s.enabled ? "Disable" : "Enable"}</button>
                <button type="button" class="secondary" onclick="deleteSchedule('${s.schedule_id}')" style="font-size: 12px; padding: 4px 8px; color: #ef4444;">Delete</button>
              </div>
            </div>
          `;
        }
        html += '</div>';
        schedulesList.innerHTML = html;
      }

      function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str || "";
        return div.innerHTML;
      }

      scheduleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const scheduleId = document.getElementById("schedule_id").value;
        const payload = {
          name: document.getElementById("schedule_name").value,
          cron_expression: document.getElementById("schedule_cron").value,
          repo_path: document.getElementById("schedule_repo").value,
          prompt: document.getElementById("schedule_prompt").value,
          backend: document.getElementById("schedule_backend").value,
          model: document.getElementById("schedule_model").value || null,
          pr_number: document.getElementById("schedule_pr_number").value ? Number(document.getElementById("schedule_pr_number").value) : null,
          no_pr: document.getElementById("schedule_no_pr").checked,
          enabled: document.getElementById("schedule_enabled").checked,
          fix_ci: document.getElementById("schedule_fix_ci").checked,
          fix_conflicts: document.getElementById("schedule_fix_conflicts").checked,
          master_rebase: document.getElementById("schedule_master_rebase").checked
        };
        const schedGhToken = document.getElementById("schedule_github_token").value.trim();
        if (schedGhToken) {
          payload.github_token = schedGhToken;
        }
        const schedRefRepos = document.getElementById("schedule_reference_repos").value.trim();
        if (schedRefRepos) {
          payload.reference_repos = schedRefRepos.split(",").map(s => s.trim()).filter(s => s.length > 0);
        }

        try {
          const url = scheduleId ? `/schedules/${scheduleId}` : "/schedules";
          const method = scheduleId ? "PUT" : "POST";
          const response = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Failed to save schedule");
          }
          scheduleFormContainer.classList.add("is-hidden");
          // Remember repos for autocomplete
          addRecentRepo(payload.repo_path);
          for (const r of schedRefReposChip.getChips()) { addRecentRepo(r); }
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      });

      window.editSchedule = async function(scheduleId) {
        try {
          const response = await fetch(`/schedules/${scheduleId}`);
          if (!response.ok) throw new Error("Schedule not found");
          const s = await response.json();

          document.getElementById("schedule_id").value = s.schedule_id;
          document.getElementById("schedule_name").value = s.name;
          document.getElementById("schedule_cron").value = s.cron_expression;
          document.getElementById("schedule_repo").value = s.repo_path;
          document.getElementById("schedule_prompt").value = s.prompt;
          document.getElementById("schedule_backend").value = s.backend;
          document.getElementById("schedule_model").value = s.model || "";
          document.getElementById("schedule_pr_number").value = s.pr_number != null ? s.pr_number : "";
          document.getElementById("schedule_no_pr").checked = s.no_pr;
          document.getElementById("schedule_enabled").checked = s.enabled;
          document.getElementById("schedule_fix_ci").checked = s.fix_ci || false;
          document.getElementById("schedule_fix_conflicts").checked = s.fix_conflicts || false;
          document.getElementById("schedule_master_rebase").checked = s.master_rebase || false;
          document.getElementById("schedule_github_token").value = s.github_token || "";
          schedRefReposChip.setChips(s.reference_repos || []);

          scheduleFormTitle.textContent = "Edit schedule";
          scheduleSubmitBtn.textContent = "Update schedule";
          scheduleFormContainer.classList.remove("is-hidden");
        } catch (err) {
          alert("Error: " + err.message);
        }
      };

      window.triggerSchedule = async function(scheduleId) {
        if (!confirm("Run this schedule now?")) return;
        try {
          const response = await fetch(`/schedules/${scheduleId}/trigger`, { method: "POST" });
          if (!response.ok) throw new Error("Failed to trigger schedule");
          const data = await response.json();
          alert(`Triggered! Task ID: ${data.task_id}`);
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      };

      window.toggleSchedule = async function(scheduleId, enable) {
        try {
          const action = enable ? "enable" : "disable";
          const response = await fetch(`/schedules/${scheduleId}/${action}`, { method: "POST" });
          if (!response.ok) throw new Error(`Failed to ${action} schedule`);
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      };

      window.deleteSchedule = async function(scheduleId) {
        if (!confirm("Delete this schedule? This cannot be undone.")) return;
        try {
          const response = await fetch(`/schedules/${scheduleId}`, { method: "DELETE" });
          if (!response.ok) throw new Error("Failed to delete schedule");
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      };
    </script>
    <div id="toast-container" class="toast-container"></div>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    """Simple browser UI to submit and monitor build runs."""
    rendered = _UI_HTML.replace(
        "__DEFAULT_SMOKE_TEST_PROMPT__",
        html.escape(DEFAULT_SMOKE_TEST_PROMPT),
    )
    return HTMLResponse(rendered)


_NOTIF_SW_JS = """\
self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window" }).then(function(list) {
      for (var i = 0; i < list.length; i++) {
        if (list[i].url && "focus" in list[i]) return list[i].focus();
      }
      if (clients.openWindow) return clients.openWindow("/");
    })
  );
});
"""


@app.get("/notif-sw.js")
def notif_sw() -> Response:
    """Minimal service worker for OS notifications."""
    return Response(content=_NOTIF_SW_JS, media_type="application/javascript")


@app.get("/health/claude-usage", response_model=ClaudeUsageResponse)
def get_claude_usage(force: bool = False) -> ClaudeUsageResponse:
    """Return current Claude Code CLI usage metrics (cached 5 min)."""
    return _fetch_claude_usage(force=force)


# ---------------------------------------------------------------------------
# Arcade high scores (in-memory)
# ---------------------------------------------------------------------------

_MAX_HIGH_SCORES = 10


class ArcadeScoreEntry(BaseModel):
    """A single entry on the arcade high-score leaderboard."""

    name: str = Field(..., max_length=24)
    score: int = Field(..., ge=0)
    wave: int = Field(..., ge=1)
    submitted_at: str = ""


class ArcadeScoreSubmit(BaseModel):
    """Request body for submitting an arcade score."""

    name: str = Field(..., max_length=24)
    score: int = Field(..., ge=0)
    wave: int = Field(..., ge=1)


_arcade_high_scores: list[ArcadeScoreEntry] = []


@app.get("/arcade/high-scores", response_model=list[ArcadeScoreEntry])
def get_arcade_high_scores() -> list[ArcadeScoreEntry]:
    """Return the top arcade high scores."""
    return _arcade_high_scores


@app.post("/arcade/high-scores", response_model=list[ArcadeScoreEntry])
def submit_arcade_high_score(entry: ArcadeScoreSubmit) -> list[ArcadeScoreEntry]:
    """Submit a new arcade high score. Returns the updated leaderboard."""
    global _arcade_high_scores
    _arcade_high_scores.append(
        ArcadeScoreEntry(
            name=entry.name.strip() or "???",
            score=entry.score,
            wave=entry.wave,
            submitted_at=datetime.now(UTC).isoformat(),
        )
    )
    _arcade_high_scores.sort(key=lambda e: e.score, reverse=True)
    _arcade_high_scores = _arcade_high_scores[:_MAX_HIGH_SCORES]
    return _arcade_high_scores


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": _RESPONSE_STATUS_OK}


@app.get("/health/multiplayer")
def health_multiplayer() -> dict[str, object]:
    """Return multiplayer room/connection statistics."""
    return get_multiplayer_stats()


@app.get("/health/multiplayer/players")
def health_multiplayer_players() -> dict[str, object]:
    """Return list of currently connected players with positions."""
    return get_connected_players()


@app.get("/health/multiplayer/activity")
def health_multiplayer_activity() -> dict[str, object]:
    """Return player activity summary with validated awareness states."""
    return get_player_activity_summary()


@app.get("/health/multiplayer/decorations")
def health_multiplayer_decorations() -> dict[str, object]:
    """Return current shared world decoration state."""
    return get_decoration_state()


class ServiceHealthResponse(BaseModel):
    """Per-service connectivity status."""

    redis: Literal["ok", "error"]
    db: Literal["ok", "error", "na"]
    workers: Literal["ok", "error"]


def _check_redis_health() -> Literal["ok", "error"]:
    """Ping the Redis broker and return a health status string.

    Uses the Celery broker URL to connect with a short timeout. Failures
    (connection refused, timeout, missing ``redis`` package) are logged at
    debug level and reported as ``"error"``.

    Returns:
        ``"ok"`` if the ping succeeds, ``"error"`` otherwise.
    """
    try:
        import redis as redis_lib  # bundled with celery[redis]
    except ImportError:
        logger.debug("Redis health check failed: redis package not installed")
        return _RESPONSE_STATUS_ERROR

    try:
        broker_url = celery_app.conf.broker_url or _DEFAULT_REDIS_URL
        r = redis_lib.Redis.from_url(
            broker_url,
            socket_connect_timeout=_REDIS_HEALTH_TIMEOUT_S,
            socket_timeout=_REDIS_HEALTH_TIMEOUT_S,
        )
        r.ping()
        return _RESPONSE_STATUS_OK
    except (redis_lib.RedisError, OSError):
        logger.debug("Redis health check failed", exc_info=True)
        return _RESPONSE_STATUS_ERROR


def _check_db_health() -> Literal["ok", "error", "na"]:
    """Open a test connection to the PostgreSQL database.

    Reads ``DATABASE_URL`` from the environment. When the variable is unset
    or empty, returns ``"na"`` (not applicable). Otherwise attempts a
    short-lived ``psycopg2`` connection and reports the result.

    Returns:
        ``"ok"`` if the connection succeeds, ``"error"`` on failure, or
        ``"na"`` when no database URL is configured.
    """
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        return _RESPONSE_STATUS_NA
    try:
        import psycopg2  # psycopg2-binary is a declared dependency
    except ImportError:
        logger.debug("Database health check failed: psycopg2 not installed")
        return _RESPONSE_STATUS_ERROR

    try:
        conn = psycopg2.connect(db_url, connect_timeout=_DB_HEALTH_TIMEOUT_S)
        conn.close()
        return _RESPONSE_STATUS_OK
    except (psycopg2.Error, OSError):
        logger.debug("Database health check failed", exc_info=True)
        return _RESPONSE_STATUS_ERROR


def _check_workers_health() -> Literal["ok", "error"]:
    """Ping Celery workers via the control inspector.

    Sends a ping with a short timeout and checks whether any worker
    responds. Failures (no workers, timeout, broker unreachable) are
    logged at debug level and reported as ``"error"``.

    Returns:
        ``"ok"`` if at least one worker responds, ``"error"`` otherwise.
    """
    try:
        inspector = celery_app.control.inspect(timeout=_CELERY_HEALTH_TIMEOUT_S)
        ping = inspector.ping()
        return _RESPONSE_STATUS_OK if ping else _RESPONSE_STATUS_ERROR
    except (ConnectionError, OSError, TimeoutError):
        logger.debug("Workers health check failed", exc_info=True)
        return _RESPONSE_STATUS_ERROR


@app.get("/health/services", response_model=ServiceHealthResponse)
def health_services() -> ServiceHealthResponse:
    """Check connectivity to Redis, Postgres, and Celery workers."""
    return ServiceHealthResponse(
        redis=_check_redis_health(),
        db=_check_db_health(),
        workers=_check_workers_health(),
    )


class VersionResponse(BaseModel):
    """Per-component version map plus deploy-state signals."""

    backend: str
    workers: dict[str, str]
    git_sha: str
    commit_date: str | None
    is_deployed: bool
    sentinel_sha: str | None


@app.get("/health/version", response_model=VersionResponse)
def get_version() -> VersionResponse:
    """Return version identity for backend + workers and deploy state.

    Frontend bakes its own version into ``src/version-generated.ts`` (via
    ``write-version.mjs`` at vite startup) and compares against the values
    returned here to detect partial-deploy mismatches.

    Mounted under ``/health`` because the standalone ``/version`` proxy
    entry didn't match on lugia's vite for an unresolved reason — every
    other proxied prefix worked, but ``/version`` consistently fell
    through to the SPA fallback. ``/health`` is known-good, so we slot
    in there.
    """
    from helping_hands.lib.version import (
        get_version_info,
        read_sentinel_sha,
        read_worker_versions,
    )

    info = get_version_info()
    sentinel = read_sentinel_sha()

    workers: dict[str, str] = {}
    try:
        import redis as redis_lib
    except ImportError:
        logger.debug("redis package not installed; skipping worker versions")
    else:
        try:
            broker_url = celery_app.conf.broker_url or _DEFAULT_REDIS_URL
            client = redis_lib.Redis.from_url(
                broker_url,
                socket_connect_timeout=_REDIS_HEALTH_TIMEOUT_S,
                socket_timeout=_REDIS_HEALTH_TIMEOUT_S,
            )
            workers = read_worker_versions(client)
        except (redis_lib.RedisError, OSError):
            logger.debug("Could not read worker versions from Redis", exc_info=True)

    return VersionResponse(
        backend=info.display,
        workers=workers,
        git_sha=info.long_sha,
        commit_date=info.commit_date,
        is_deployed=sentinel is not None,
        sentinel_sha=sentinel,
    )


def _is_running_in_docker() -> bool:
    """Return True when the process is running inside a Docker container."""
    if Path("/.dockerenv").exists():
        return True
    return _is_truthy_env("HELPING_HANDS_IN_DOCKER")


@app.get("/config", response_model=ServerConfig)
def get_server_config() -> ServerConfig:
    """Return runtime configuration used to seed frontend defaults."""
    from helping_hands.lib.hands.v1.hand.factory import get_enabled_backends

    in_docker = _is_running_in_docker()
    claude_native = _is_truthy_env("HELPING_HANDS_CLAUDE_USE_NATIVE_CLI_AUTH")
    has_github_token = bool(os.environ.get("GITHUB_TOKEN", "").strip())
    default_repo = os.environ.get("HELPING_HANDS_DEFAULT_REPO", "").strip() or None
    return ServerConfig(
        in_docker=in_docker,
        native_auth_default=not in_docker,
        enabled_backends=get_enabled_backends(),
        claude_native_cli_auth=claude_native,
        has_github_token=has_github_token,
        default_repo=default_repo,
        grill_enabled=_grill_enabled(),
    )


def _enqueue_build_task(req: BuildRequest) -> BuildResponse:
    """Enqueue a build task and return a consistent response shape."""
    task = build_feature.delay(
        repo_path=req.repo_path,
        prompt=req.prompt,
        pr_number=req.pr_number,
        issue_number=req.issue_number,
        create_issue=req.create_issue,
        project_url=req.project_url,
        backend=req.backend,
        model=req.model,
        max_iterations=req.max_iterations,
        no_pr=req.no_pr,
        enable_execution=req.enable_execution,
        enable_web=req.enable_web,
        use_native_cli_auth=req.use_native_cli_auth,
        tools=req.tools,
        fix_ci=req.fix_ci,
        fix_conflicts=req.fix_conflicts,
        master_rebase=req.master_rebase,
        ci_check_wait_minutes=req.ci_check_wait_minutes,
        github_token=req.github_token,
        reference_repos=req.reference_repos,
    )
    return BuildResponse(task_id=task.id, status="queued", backend=req.backend)


def _parse_backend(value: str) -> BackendName:
    """Validate backend values coming from untyped form submissions."""
    normalized = value.strip().lower()
    backend = _BACKEND_LOOKUP.get(normalized)
    if backend is None:
        choices = ", ".join(_BACKEND_LOOKUP.keys())
        msg = f"unsupported backend {value!r}; expected one of: {choices}"
        raise ValueError(msg)
    return backend


def _validate_path_param(value: str, name: str) -> str:
    """Validate and strip a URL path parameter.

    Delegates to :func:`~helping_hands.lib.validation.require_non_empty_string`.

    Args:
        value: The raw path parameter value.
        name: The parameter name, used in error messages.

    Returns:
        The stripped parameter value.

    Raises:
        ValueError: If *value* is empty or whitespace-only.
    """
    return require_non_empty_string(value, name)


def _build_task_status(task_id: str) -> TaskStatus:
    """Fetch and normalize current Celery task status.

    Args:
        task_id: The Celery task UUID to look up.

    Returns:
        A ``TaskStatus`` with the current state and normalised result. Falls
        back to the persistent snapshot when Celery has lost the result (e.g.
        Redis result expiry on a long-completed run).
    """
    result = build_feature.AsyncResult(task_id)
    raw_result = result.result if result.ready() else result.info
    normalized_result = normalize_task_result(result.status, raw_result)
    # Live source wins. Fall back to snapshot only when Celery has nothing
    # useful — i.e. PENDING (the canonical "I don't know this id" state for
    # an expired result) and no live result data.
    if result.status == "PENDING" and normalized_result is None:
        snapshot = read_task_run(task_id)
        if snapshot is not None:
            return TaskStatus(
                task_id=task_id,
                status=str(snapshot.get("status") or "SUCCESS").upper(),
                result=snapshot.get("output") or {},
                from_snapshot=True,
            )
    return TaskStatus(
        task_id=task_id,
        status=result.status,
        result=normalized_result,
    )


def _task_state_priority(status: str) -> int:
    """Return a relative sort priority for active task states."""
    return _TASK_STATE_PRIORITY.get(status.upper(), 0)


def _normalize_task_status(raw: Any, *, default: str) -> str:
    """Normalize arbitrary state/status values into uppercase labels."""
    text = str(raw or "").strip().upper()
    return text or default


def _extract_nested_str_field(
    entry: dict[str, Any], keys: tuple[str, ...]
) -> str | None:
    """Extract a stripped string value from nested Celery/Flower payloads.

    Searches *entry* for the first key in *keys* whose value is a non-empty
    string.  Falls back to recursing into ``entry["request"]`` when present.

    Args:
        entry: Celery/Flower task payload dict.
        keys: Candidate key names to search, in priority order.

    Returns:
        Stripped string value, or ``None`` if not found.
    """
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    request_payload = entry.get("request")
    if isinstance(request_payload, dict):
        return _extract_nested_str_field(request_payload, keys)
    return None


def _extract_task_id(entry: dict[str, Any]) -> str | None:
    """Extract a task UUID from Celery/Flower payload shapes."""
    return _extract_nested_str_field(entry, ("task_id", "uuid", "id"))


def _extract_task_name(entry: dict[str, Any]) -> str | None:
    """Extract task name from Celery/Flower payload shapes."""
    return _extract_nested_str_field(entry, ("name", "task"))


def _extract_task_kwargs(entry: dict[str, Any]) -> dict[str, Any]:
    """Extract kwargs payload if available as an already-decoded mapping."""
    kwargs_payload = entry.get("kwargs")
    if isinstance(kwargs_payload, dict):
        return kwargs_payload
    if isinstance(kwargs_payload, str):
        parsed_kwargs = _parse_task_kwargs_str(kwargs_payload)
        if parsed_kwargs:
            return parsed_kwargs
    request_payload = entry.get("request")
    if isinstance(request_payload, dict):
        request_kwargs = request_payload.get("kwargs")
        if isinstance(request_kwargs, dict):
            return request_kwargs
        if isinstance(request_kwargs, str):
            parsed_request_kwargs = _parse_task_kwargs_str(request_kwargs)
            if parsed_request_kwargs:
                return parsed_request_kwargs
    return {}


def _coerce_optional_str(value: Any) -> str | None:
    """Convert arbitrary values into trimmed optional strings."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


_MAX_TASK_KWARGS_LEN = 1_000_000  # 1 MB — reject unreasonably large payloads


def _parse_task_kwargs_str(raw: str) -> dict[str, Any]:
    """Parse kwargs strings from Flower/Celery payloads into a mapping."""
    text = raw.strip()
    if not text:
        return {}
    if len(text) > _MAX_TASK_KWARGS_LEN:
        logger.warning(
            "Task kwargs string exceeds %d chars (%d), skipping parse",
            _MAX_TASK_KWARGS_LEN,
            len(text),
        )
        return {}
    try:
        json_payload = json.loads(text)
    except ValueError:
        json_payload = None
    if isinstance(json_payload, dict):
        return json_payload
    try:
        literal_payload = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        literal_payload = None
    if isinstance(literal_payload, dict):
        return literal_payload
    return {}


def _is_helping_hands_task(entry: dict[str, Any]) -> bool:
    """Filter out unrelated Celery tasks when task name is available."""
    task_name = _extract_task_name(entry)
    if not task_name:
        return True
    return task_name == _HELPING_HANDS_TASK_NAME


def _merge_source_tags(existing_source: str, new_tag: str) -> str:
    """Merge a new discovery-source tag into a ``+``-delimited source string.

    Source strings use ``"+"`` as the separator (e.g. ``"flower+inspect"``).
    This helper adds *new_tag* if it is not already present and returns the
    merged, sorted result.

    Args:
        existing_source: Current ``"+"``-delimited source string (may be empty).
        new_tag: Tag to add (ignored when empty).

    Returns:
        The merged source string with tags sorted alphabetically.
    """
    if not new_tag:
        return existing_source
    parts = {p for p in existing_source.split("+") if p}
    parts.add(new_tag)
    return "+".join(sorted(parts))


def _upsert_current_task(
    tasks_by_id: dict[str, dict[str, Any]],
    *,
    task_id: str,
    status: str,
    backend: str | None,
    repo_path: str | None,
    worker: str | None,
    source: str,
) -> None:
    """Insert/merge a discovered task summary keyed by UUID."""
    incoming = {
        "task_id": task_id,
        "status": status,
        "backend": backend,
        "repo_path": repo_path,
        "worker": worker,
        "source": source,
    }
    existing = tasks_by_id.get(task_id)
    if existing is None:
        tasks_by_id[task_id] = incoming
        return

    if _task_state_priority(status) >= _task_state_priority(existing["status"]):
        existing["status"] = status

    for key in ("backend", "repo_path", "worker"):
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]

    if source:
        existing["source"] = _merge_source_tags(str(existing.get("source", "")), source)


def _flower_timeout_seconds() -> float:
    """Resolve Flower HTTP timeout from env with safe bounds."""
    raw = os.environ.get(_FLOWER_API_TIMEOUT_SECONDS_ENV, "").strip()
    if not raw:
        return _DEFAULT_FLOWER_API_TIMEOUT_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return _DEFAULT_FLOWER_API_TIMEOUT_SECONDS
    return min(max(parsed, 0.1), 10.0)


def _flower_api_base_url() -> str | None:
    """Resolve Flower API base URL from env if configured."""
    raw = os.environ.get(_FLOWER_API_URL_ENV, "").strip()
    if not raw:
        return None
    return raw.rstrip("/")


def _is_recently_terminal(entry: dict[str, Any], status: str) -> bool:
    """Return True if a terminal task completed within the recent window.

    Flower stores completion timestamps as UNIX epoch floats in fields
    named after the terminal state (``failed``, ``succeeded``, etc.).
    """
    if status not in _TERMINAL_TASK_STATES:
        return False
    ts: Any = None
    if status == "FAILURE":
        ts = entry.get("failed")
    elif status == "SUCCESS":
        ts = entry.get("succeeded")
    if ts is None:
        ts = entry.get("timestamp")
    if not isinstance(ts, int | float):
        return False
    return (time.time() - ts) < _RECENT_TERMINAL_WINDOW_S


def _fetch_flower_current_tasks() -> list[dict[str, Any]]:
    """Fetch currently active tasks from Flower API when configured."""
    base_url = _flower_api_base_url()
    if not base_url:
        return []

    url = f"{base_url}/api/tasks?state=STARTED,RECEIVED,PENDING,PROGRESS,RETRY"
    request = urllib_request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib_request.urlopen(
            request, timeout=_flower_timeout_seconds()
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        TimeoutError,
        OSError,
        ValueError,
        UnicodeDecodeError,
        urllib_error.HTTPError,
        urllib_error.URLError,
    ):
        return []

    if not isinstance(payload, dict):
        return []

    tasks_by_id: dict[str, dict[str, Any]] = {}
    for key, raw_entry in payload.items():
        if not isinstance(raw_entry, dict):
            continue

        entry = dict(raw_entry)
        if isinstance(key, str) and key.strip() and "uuid" not in entry:
            entry["uuid"] = key.strip()
        if not _is_helping_hands_task(entry):
            continue

        task_id = _extract_task_id(entry)
        if not task_id:
            continue

        status = _normalize_task_status(
            entry.get("state") or entry.get("status"), default="PENDING"
        )
        if status not in _CURRENT_TASK_STATES and not _is_recently_terminal(
            entry, status
        ):
            continue

        kwargs_payload = _extract_task_kwargs(entry)
        backend = _coerce_optional_str(kwargs_payload.get("backend"))
        repo_path = _coerce_optional_str(kwargs_payload.get("repo_path"))
        worker = _coerce_optional_str(entry.get("worker"))
        _upsert_current_task(
            tasks_by_id,
            task_id=task_id,
            status=status,
            backend=backend,
            repo_path=repo_path,
            worker=worker,
            source="flower",
        )

    return list(tasks_by_id.values())


def _iter_worker_task_entries(payload: Any) -> list[tuple[str, dict[str, Any]]]:
    """Flatten worker->task payloads returned by Celery inspect APIs."""
    if not isinstance(payload, dict):
        return []

    entries: list[tuple[str, dict[str, Any]]] = []
    for worker, worker_tasks in payload.items():
        if not isinstance(worker, str):
            continue
        if not isinstance(worker_tasks, list):
            continue
        for task_entry in worker_tasks:
            if isinstance(task_entry, dict):
                entries.append((worker, task_entry))
    return entries


def _safe_inspect_call(inspector: Any, method_name: str) -> Any:
    """Call inspect methods safely so one failure doesn't break listing."""
    method = getattr(inspector, method_name, None)
    if not callable(method):
        return None
    try:
        return method()
    except (
        AttributeError,
        ConnectionError,
        OSError,
        RuntimeError,
        TimeoutError,
    ):  # pragma: no cover
        logger.debug(
            "inspect.%s() failed",
            method_name,
            exc_info=True,
        )
        return None


def _collect_celery_current_tasks() -> list[dict[str, Any]]:
    """Collect currently active/queued task summaries from Celery inspect."""
    try:
        inspector = celery_app.control.inspect(timeout=_CELERY_INSPECT_TIMEOUT_S)
    except (
        AttributeError,
        ConnectionError,
        OSError,
        RuntimeError,
        TimeoutError,
    ):  # pragma: no cover
        logger.debug("celery inspect init failed", exc_info=True)
        return []
    if inspector is None:
        return []

    tasks_by_id: dict[str, dict[str, Any]] = {}
    inspect_shapes = (
        ("active", "STARTED"),
        ("reserved", "RECEIVED"),
        ("scheduled", "SCHEDULED"),
    )

    for method_name, default_status in inspect_shapes:
        payload = _safe_inspect_call(inspector, method_name)
        for worker, entry in _iter_worker_task_entries(payload):
            if not _is_helping_hands_task(entry):
                continue
            task_id = _extract_task_id(entry)
            if not task_id:
                continue
            status = _normalize_task_status(
                entry.get("state") or entry.get("status"), default=default_status
            )
            if status not in _CURRENT_TASK_STATES:
                status = default_status
            kwargs_payload = _extract_task_kwargs(entry)
            backend = _coerce_optional_str(kwargs_payload.get("backend"))
            repo_path = _coerce_optional_str(kwargs_payload.get("repo_path"))
            _upsert_current_task(
                tasks_by_id,
                task_id=task_id,
                status=status,
                backend=backend,
                repo_path=repo_path,
                worker=worker,
                source="celery",
            )

    return list(tasks_by_id.values())


def _collect_current_tasks() -> CurrentTasksResponse:
    """Collect current task UUIDs from Flower and Celery inspect."""
    tasks_by_id: dict[str, dict[str, Any]] = {}
    sources: set[str] = set()

    for task in _fetch_flower_current_tasks():
        _upsert_current_task(tasks_by_id, **task)
        sources.add("flower")

    for task in _collect_celery_current_tasks():
        _upsert_current_task(tasks_by_id, **task)
        sources.add("celery")

    sorted_tasks = sorted(
        tasks_by_id.values(),
        key=lambda item: (-_task_state_priority(str(item["status"])), item["task_id"]),
    )
    response_source = "+".join(sorted(sources)) if sources else "none"
    return CurrentTasksResponse(
        tasks=[CurrentTask(**task) for task in sorted_tasks],
        source=response_source,
    )


def _render_monitor_page(task_status: TaskStatus) -> str:
    """Render a minimal monitor page that works without client JS."""
    payload = task_status.model_dump()
    status = task_status.status
    escaped_payload = html.escape(json.dumps(payload, indent=2))

    prompt = ""
    if isinstance(task_status.result, dict):
        raw_prompt = task_status.result.get("prompt")
        if isinstance(raw_prompt, str) and raw_prompt.strip():
            prompt = raw_prompt.strip()

    updates: list[str] = []
    if isinstance(task_status.result, dict):
        maybe_updates = task_status.result.get("updates")
        if isinstance(maybe_updates, list):
            updates = [str(item) for item in maybe_updates]
    updates_html = "<br/>".join(html.escape(line) for line in updates)
    if not updates_html:
        updates_html = "No updates yet."

    refresh_meta = (
        '<meta http-equiv="refresh" content="2">'
        if status not in _TERMINAL_TASK_STATES
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    {refresh_meta}
    <title>Task Monitor - {html.escape(task_status.task_id)}</title>
    <style>
      :root {{
        --background: #020817;
        --background-soft: #0b1220;
        --panel: #0f172a;
        --panel-elevated: #111b31;
        --foreground: #e2e8f0;
        --muted: #94a3b8;
        --border: #1f2937;
        --secondary: #1e293b;
        --secondary-hover: #334155;
        --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
      }}
      * {{
        box-sizing: border-box;
      }}
      html,
      body {{
        min-height: 100%;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Space Grotesk", "Segoe UI", sans-serif;
        color: var(--foreground);
        background:
          radial-gradient(circle at 10% -10%, #172554 0%, transparent 40%),
          radial-gradient(circle at 110% 0%, #1e1b4b 0%, transparent 42%),
          linear-gradient(180deg, var(--background-soft) 0%, var(--background) 100%);
      }}
      .page {{
        max-width: 1200px;
        min-height: 100vh;
        margin: 0 auto;
        padding: 28px 20px 36px;
        display: grid;
        gap: 14px;
      }}
      .card {{
        background: linear-gradient(
          180deg,
          var(--panel-elevated) 0%,
          var(--panel) 100%
        );
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 20px 40px rgba(2, 8, 23, 0.45);
      }}
      .meta {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
      }}
      .meta-item {{
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        background: #0b1326;
      }}
      .meta-label {{
        display: block;
        font-size: 0.82rem;
        color: var(--muted);
        margin-bottom: 4px;
      }}
      .meta-item strong {{
        display: block;
        font-family: var(--mono);
        font-size: 0.84rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
      }}
      pre {{
        margin: 0;
        min-height: 220px;
        max-height: min(68vh, 860px);
        overflow: auto;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #020817;
        color: #cbd5e1;
        font-family: var(--mono);
        font-size: 0.8rem;
        line-height: 1.45;
        white-space: pre-wrap;
        word-break: break-word;
      }}
      .updates {{
        min-height: 140px;
      }}
      .actions {{
        display: flex;
        gap: 9px;
        flex-wrap: wrap;
        margin-top: 12px;
      }}
      a {{
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 8px 12px;
        background: var(--secondary);
        color: var(--foreground);
        text-decoration: none;
      }}
      a:hover {{
        background: var(--secondary-hover);
      }}
      .cancel-btn {{
        border: 1px solid #7f1d1d;
        border-radius: 10px;
        padding: 8px 12px;
        background: #450a0a;
        color: #fca5a5;
        cursor: pointer;
        font-family: inherit;
        font-size: inherit;
      }}
      .cancel-btn:hover {{
        background: #7f1d1d;
      }}
      h2 {{
        margin: 0 0 8px;
        font-size: 1rem;
      }}
      @media (max-width: 720px) {{
        .meta {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <section class="card">
        <div class="meta">
          <div class="meta-item">
            <span class="meta-label">Task</span>
            <strong>{html.escape(task_status.task_id)}</strong>
          </div>
          <div class="meta-item">
            <span class="meta-label">Status</span>
            <strong>{html.escape(status)}</strong>
          </div>
          {
        ""
        if not prompt
        else f'''<div class="meta-item">
            <span class="meta-label">Prompt</span>
            <strong>{html.escape(prompt)}</strong>
          </div>'''
    }
          <div class="meta-item">
            <span class="meta-label">Polling</span>
            <strong>
              {"active" if status not in _TERMINAL_TASK_STATES else "off"}
            </strong>
          </div>
        </div>
        <div class="actions">
          <a href="/">Back to runner</a>
          <a href="/tasks/{html.escape(task_status.task_id)}">Raw JSON</a>
          {
        ""
        if status in _TERMINAL_TASK_STATES
        else f'''<button class="cancel-btn" onclick="cancelTask('{html.escape(task_status.task_id)}')">Cancel task</button>'''
    }
        </div>
      </section>
      <section class="card">
        <h2>Updates</h2>
        <pre class="updates">{updates_html}</pre>
      </section>
      <section class="card">
        <h2>Payload</h2>
        <pre>{escaped_payload}</pre>
      </section>
    </main>
    <script>
      function cancelTask(taskId) {{
        if (!confirm("Cancel this task?")) return;
        fetch("/tasks/" + encodeURIComponent(taskId) + "/cancel", {{
          method: "POST",
        }})
          .then(function (r) {{ return r.json(); }})
          .then(function () {{ location.reload(); }})
          .catch(function (e) {{ alert("Cancel failed: " + e.message); }});
      }}
    </script>
  </body>
</html>
"""


@app.get("/repos/{owner}/{repo}/issues")
def list_repo_issues(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
    github_token: str | None = None,
) -> list[dict[str, Any]]:
    """List open issues for a GitHub repository."""
    from helping_hands.lib.github import GitHubClient

    token = github_token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="No GitHub token available")
    client = GitHubClient(token=token)
    return client.list_issues(f"{owner}/{repo}", state=state, per_page=per_page)


class CreateIssueRequest(BaseModel):
    title: str
    body: str = ""
    labels: list[str] | None = None
    github_token: str | None = None


@app.post("/repos/{owner}/{repo}/issues")
def create_repo_issue(
    owner: str,
    repo: str,
    request: CreateIssueRequest,
) -> dict[str, Any]:
    """Create a new issue on a GitHub repository."""
    from helping_hands.lib.github import GitHubClient

    token = request.github_token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="No GitHub token available")
    client = GitHubClient(token=token)
    return client.create_issue(
        f"{owner}/{repo}",
        title=request.title,
        body=request.body,
        labels=request.labels,
    )


@app.post("/build", response_model=BuildResponse)
def enqueue_build(req: BuildRequest) -> BuildResponse:
    """Enqueue a hand task and return the task ID.

    Supports E2E and iterative backends (`basic-langgraph`, `basic-atomic`,
    `basic-agent`) plus CLI-driven backends (`codexcli`, `claudecodecli`,
    `goose`, `geminicli`, `opencodecli`, `devincli`) using CLI-equivalent backend options.
    """
    return _enqueue_build_task(req)


def _first_validation_error_msg(
    exc: ValidationError,
    fallback: str = "Invalid form submission.",
) -> str:
    """Extract a human-readable message from the first Pydantic error.

    Args:
        exc: The Pydantic ``ValidationError``.
        fallback: Message returned when no usable error string is found.

    Returns:
        The ``msg`` field of the first error dict, or *fallback*.
    """
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        if isinstance(first_error, dict):
            maybe_msg = first_error.get("msg")
            if isinstance(maybe_msg, str):
                return maybe_msg
    return fallback


def _build_form_redirect_query(
    *,
    repo_path: str,
    prompt: str,
    backend: str,
    max_iterations: int,
    error: str,
    model: str | None = None,
    no_pr: bool = False,
    enable_execution: bool = False,
    enable_web: bool = False,
    use_native_cli_auth: bool = False,
    fix_ci: bool = False,
    fix_conflicts: bool = False,
    master_rebase: bool = False,
    ci_check_wait_minutes: float = _DEFAULT_CI_WAIT_MINUTES,
    pr_number: int | None = None,
    tools: str | None = None,
) -> dict[str, str]:
    """Build the query dict for form error redirects back to the index page."""
    query: dict[str, str] = {
        "repo_path": repo_path,
        "prompt": prompt,
        "backend": backend,
        "max_iterations": str(max_iterations),
        "error": error,
    }
    if model:
        query["model"] = model
    if no_pr:
        query["no_pr"] = "1"
    if enable_execution:
        query["enable_execution"] = "1"
    if enable_web:
        query["enable_web"] = "1"
    if use_native_cli_auth:
        query["use_native_cli_auth"] = "1"
    if fix_ci:
        query["fix_ci"] = "1"
    if fix_conflicts:
        query["fix_conflicts"] = "1"
    if master_rebase:
        query["master_rebase"] = "1"
    if ci_check_wait_minutes != _DEFAULT_CI_WAIT_MINUTES:
        query["ci_check_wait_minutes"] = str(ci_check_wait_minutes)
    if pr_number is not None:
        query["pr_number"] = str(pr_number)
    if tools and tools.strip():
        query["tools"] = tools
    return query


@app.post("/build/form")
def enqueue_build_form(
    repo_path: str = Form(...),
    prompt: str = Form(...),
    backend: str = Form(_DEFAULT_BACKEND),
    model: str | None = Form(None),
    max_iterations: int = Form(_DEFAULT_MAX_ITERATIONS),
    no_pr: bool = Form(False),
    enable_execution: bool = Form(False),
    enable_web: bool = Form(False),
    use_native_cli_auth: bool = Form(False),
    pr_number: int | None = Form(None),
    issue_number: int | None = Form(None),
    create_issue: bool = Form(False),
    project_url: str | None = Form(None),
    tools: str | None = Form(None),
    fix_ci: bool = Form(False),
    fix_conflicts: bool = Form(False),
    master_rebase: bool = Form(False),
    ci_check_wait_minutes: float = Form(_DEFAULT_CI_WAIT_MINUTES),
    github_token: str | None = Form(None),
    reference_repos: str | None = Form(None),
) -> RedirectResponse:
    """Fallback form endpoint so UI submits still enqueue without JS."""
    try:
        validated_backend = _parse_backend(backend)
    except ValueError as exc:
        query = _build_form_redirect_query(
            repo_path=repo_path,
            prompt=prompt,
            backend=backend,
            max_iterations=max_iterations,
            error=str(exc),
            model=model,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            fix_ci=fix_ci,
            fix_conflicts=fix_conflicts,
            master_rebase=master_rebase,
            ci_check_wait_minutes=ci_check_wait_minutes,
            pr_number=pr_number,
            tools=tools,
        )
        return RedirectResponse(url=f"/?{urlencode(query)}", status_code=303)

    try:
        req = BuildRequest(
            repo_path=repo_path,
            prompt=prompt,
            backend=validated_backend,
            model=model,
            max_iterations=max_iterations,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            pr_number=pr_number,
            issue_number=issue_number,
            create_issue=create_issue,
            project_url=project_url,
            fix_ci=fix_ci,
            fix_conflicts=fix_conflicts,
            master_rebase=master_rebase,
            ci_check_wait_minutes=ci_check_wait_minutes,
            tools=list(meta_tools.normalize_tool_selection(tools)),
            github_token=github_token
            if github_token and github_token.strip()
            else None,
            reference_repos=list(parse_comma_list(reference_repos or "")),
        )
    except ValidationError as exc:
        error_msg = _first_validation_error_msg(exc)

        query = _build_form_redirect_query(
            repo_path=repo_path,
            prompt=prompt,
            backend=backend,
            max_iterations=max_iterations,
            error=error_msg,
            model=model,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            fix_ci=fix_ci,
            fix_conflicts=fix_conflicts,
            master_rebase=master_rebase,
            ci_check_wait_minutes=ci_check_wait_minutes,
            pr_number=pr_number,
            tools=tools,
        )
        return RedirectResponse(url=f"/?{urlencode(query)}", status_code=303)

    response = _enqueue_build_task(req)
    query = {
        "repo_path": req.repo_path,
        "prompt": req.prompt,
        "backend": req.backend,
        "max_iterations": str(req.max_iterations),
        "task_id": response.task_id,
        "status": response.status,
    }
    if req.model:
        query["model"] = req.model
    if req.no_pr:
        query["no_pr"] = "1"
    if req.enable_execution:
        query["enable_execution"] = "1"
    if req.enable_web:
        query["enable_web"] = "1"
    if req.use_native_cli_auth:
        query["use_native_cli_auth"] = "1"
    if req.fix_ci:
        query["fix_ci"] = "1"
    if req.fix_conflicts:
        query["fix_conflicts"] = "1"
    if req.master_rebase:
        query["master_rebase"] = "1"
    if req.pr_number is not None:
        query["pr_number"] = str(req.pr_number)
    if req.tools:
        query["tools"] = ",".join(req.tools)
    return RedirectResponse(url=f"/monitor/{response.task_id}", status_code=303)


@app.get("/monitor/{task_id}", response_class=HTMLResponse)
def monitor(task_id: str) -> HTMLResponse:
    """No-JS monitor page with auto-refresh for task status/updates."""
    task_id = _validate_path_param(task_id, "task_id")
    task_status = _build_task_status(task_id)
    return HTMLResponse(_render_monitor_page(task_status))


def _resolve_worker_capacity() -> WorkerCapacityResponse:
    """Resolve max worker capacity: Celery inspect stats > env override > default."""
    per_worker: dict[str, int] = {}
    try:
        inspector = celery_app.control.inspect(timeout=_CELERY_INSPECT_TIMEOUT_S)
        if inspector is not None:
            stats = _safe_inspect_call(inspector, "stats")
            if isinstance(stats, dict):
                for worker_name, worker_stats in stats.items():
                    if not isinstance(worker_stats, dict):
                        continue
                    pool = worker_stats.get("pool", {})
                    if isinstance(pool, dict):
                        concurrency = pool.get("max-concurrency")
                        if isinstance(concurrency, int) and concurrency > 0:
                            per_worker[worker_name] = concurrency
    except (ConnectionError, OSError, TimeoutError):
        logger.debug("Failed to resolve worker capacity", exc_info=True)

    if per_worker:
        return WorkerCapacityResponse(
            max_workers=sum(per_worker.values()),
            source="celery",
            workers=per_worker,
        )

    for env_var in _WORKER_CAPACITY_ENV_VARS:
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            continue
        try:
            parsed = int(raw)
        except ValueError:
            continue
        if parsed >= 1:
            return WorkerCapacityResponse(
                max_workers=parsed,
                source=f"env:{env_var}",
                workers={},
            )

    return WorkerCapacityResponse(
        max_workers=_DEFAULT_WORKER_CAPACITY,
        source="default",
        workers={},
    )


@app.get("/workers/capacity", response_model=WorkerCapacityResponse)
def get_worker_capacity() -> WorkerCapacityResponse:
    """Report current max worker capacity for the cluster."""
    return _resolve_worker_capacity()


def _collect_queue_depth() -> QueueDepthResponse:
    """Aggregate worker-side and broker-side task counts.

    active/reserved/scheduled come from ``celery inspect`` (sum of entries
    across workers); broker_depth is the raw LLEN of the default ``celery``
    queue in Redis. Either side failing degrades gracefully — counts that
    couldn't be read stay 0 and ``source`` reflects what succeeded.
    """
    active = 0
    reserved = 0
    scheduled = 0
    celery_ok = False
    try:
        inspector = celery_app.control.inspect(timeout=_CELERY_INSPECT_TIMEOUT_S)
    except (ConnectionError, OSError, TimeoutError):
        logger.debug("queue-depth inspect init failed", exc_info=True)
        inspector = None

    if inspector is not None:
        for method, target in (
            ("active", "active"),
            ("reserved", "reserved"),
            ("scheduled", "scheduled"),
        ):
            payload = _safe_inspect_call(inspector, method)
            if payload is None:
                continue
            celery_ok = True
            if not isinstance(payload, dict):
                continue
            count = 0
            for entries in payload.values():
                if isinstance(entries, list):
                    count += len(entries)
            if target == "active":
                active = count
            elif target == "reserved":
                reserved = count
            else:
                scheduled = count

    broker_depth = 0
    redis_ok = False
    try:
        import redis as redis_lib
    except ImportError:
        logger.debug("queue-depth: redis package not installed")
    else:
        try:
            broker_url = celery_app.conf.broker_url or _DEFAULT_REDIS_URL
            r = redis_lib.Redis.from_url(
                broker_url,
                socket_connect_timeout=_REDIS_HEALTH_TIMEOUT_S,
                socket_timeout=_REDIS_HEALTH_TIMEOUT_S,
            )
            # redis-py types llen as Awaitable[int] | int because the same
            # client class also covers async usage; we use the sync client so
            # the result is always int, but the type checker can't prove it.
            raw_depth = r.llen("celery")
            if isinstance(raw_depth, int):
                broker_depth = raw_depth
                redis_ok = True
        except (redis_lib.RedisError, OSError, ValueError):
            logger.debug("queue-depth: redis llen failed", exc_info=True)

    if celery_ok and redis_ok:
        source = "celery+redis"
    elif celery_ok:
        source = "celery"
    elif redis_ok:
        source = "redis"
    else:
        source = "unavailable"

    return QueueDepthResponse(
        active=active,
        reserved=reserved,
        scheduled=scheduled,
        broker_depth=broker_depth,
        source=source,
    )


@app.get("/tasks/queue-depth", response_model=QueueDepthResponse)
def get_queue_depth() -> QueueDepthResponse:
    """Report aggregate active/reserved/scheduled/broker queue counts."""
    return _collect_queue_depth()


@app.get("/tasks/current", response_model=CurrentTasksResponse)
def get_current_tasks() -> CurrentTasksResponse:
    """List currently active/queued task UUIDs discovered by Flower/Celery."""
    return _collect_current_tasks()


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    """Check the status of an enqueued task."""
    task_id = _validate_path_param(task_id, "task_id")
    return _build_task_status(task_id)


class TaskDiffFile(BaseModel):
    """A single file's diff hunks."""

    filename: str
    status: str  # "modified", "added", "deleted", "renamed"
    diff: str


class TaskDiffResponse(BaseModel):
    """Response for uncommitted diff of a running task."""

    task_id: str
    workspace: str | None = None
    files: list[TaskDiffFile] = Field(default_factory=list)
    error: str | None = None
    from_snapshot: bool = False


@app.get("/tasks/{task_id}/diff", response_model=TaskDiffResponse)
def get_task_diff(task_id: str) -> TaskDiffResponse:
    """Return the uncommitted git diff for a task's workspace.

    Falls back to the persistent snapshot when the live workspace is gone
    (cleaned up after task completion).
    """
    task_id = _validate_path_param(task_id, "task_id")
    response = _build_task_diff(task_id)
    if response.error and not response.files:
        snapshot = read_task_run(task_id)
        if snapshot is not None:
            files = [
                TaskDiffFile(
                    filename=str(item.get("filename") or ""),
                    status=str(item.get("status") or "modified"),
                    diff=str(item.get("diff") or ""),
                )
                for item in snapshot.get("diff_files") or []
                if isinstance(item, dict)
            ]
            return TaskDiffResponse(
                task_id=task_id,
                workspace=response.workspace,
                files=files,
                from_snapshot=True,
            )
    return response


def _resolve_task_workspace(
    task_id: str,
) -> tuple[Path | None, str | None, bool, str | None]:
    """Resolve the workspace directory for a task.

    Returns:
        (workspace_path, workspace_str, task_ready, error)
    """
    result = build_feature.AsyncResult(task_id)
    task_ready = result.ready()
    raw = result.result if task_ready else result.info
    workspace: str | None = None
    repo_path: str | None = None
    if isinstance(raw, dict):
        workspace = raw.get("workspace")
        repo_path = raw.get("repo_path") or raw.get("repo")
    if not workspace and repo_path:
        candidate = Path(repo_path).expanduser().resolve()
        if candidate.is_dir():
            workspace = str(candidate)
    if not workspace:
        return None, None, task_ready, "Workspace not available yet"
    workspace_path = Path(workspace)
    if not workspace_path.is_dir():
        if task_ready:
            return (
                None,
                workspace,
                task_ready,
                ("Workspace was cleaned up after task completed"),
            )
        return None, workspace, task_ready, "Workspace directory not found"
    return workspace_path, workspace, task_ready, None


def _build_task_diff(task_id: str) -> TaskDiffResponse:
    """Fetch workspace from task metadata and run git diff."""
    workspace_path, workspace, _task_ready, error = _resolve_task_workspace(task_id)
    if error:
        return TaskDiffResponse(
            task_id=task_id,
            workspace=workspace,
            error=error,
        )
    assert workspace_path is not None  # guaranteed by _resolve_task_workspace
    try:
        # Staged + unstaged changes against HEAD
        diff_output = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=15,
        )
        # Fallback: if HEAD doesn't exist yet, diff the index
        if diff_output.returncode != 0:
            diff_output = subprocess.run(
                ["git", "diff"],
                capture_output=True,
                text=True,
                cwd=workspace_path,
                timeout=15,
            )
        untracked_output = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return TaskDiffResponse(
            task_id=task_id,
            workspace=workspace,
            error=f"Git command failed: {exc}",
        )

    files: list[TaskDiffFile] = []

    # Parse unified diff into per-file entries
    if diff_output.stdout.strip():
        current_filename: str | None = None
        current_lines: list[str] = []
        current_status = "modified"

        for line in diff_output.stdout.splitlines(keepends=True):
            if line.startswith("diff --git "):
                if current_filename and current_lines:
                    files.append(
                        TaskDiffFile(
                            filename=current_filename,
                            status=current_status,
                            diff="".join(current_lines),
                        )
                    )
                parts = line.strip().split(" b/", 1)
                current_filename = parts[1] if len(parts) > 1 else "unknown"
                current_lines = [line]
                current_status = "modified"
            else:
                current_lines.append(line)
                if line.startswith("new file"):
                    current_status = "added"
                elif line.startswith("deleted file"):
                    current_status = "deleted"
                elif line.startswith("rename from"):
                    current_status = "renamed"

        if current_filename and current_lines:
            files.append(
                TaskDiffFile(
                    filename=current_filename,
                    status=current_status,
                    diff="".join(current_lines),
                )
            )

    # Add untracked files as "added" with full content
    if untracked_output.stdout.strip():
        for untracked in untracked_output.stdout.strip().splitlines():
            untracked = untracked.strip()
            if not untracked:
                continue
            try:
                content = (workspace_path / untracked).read_text(errors="replace")
                numbered = "\n".join(f"+{ln}" for ln in content.splitlines())
                diff_text = (
                    f"diff --git a/{untracked} b/{untracked}\n"
                    f"new file mode 100644\n"
                    f"--- /dev/null\n"
                    f"+++ b/{untracked}\n"
                    f"@@ -0,0 +1,{len(content.splitlines())} @@\n"
                    f"{numbered}\n"
                )
                files.append(
                    TaskDiffFile(
                        filename=untracked,
                        status="added",
                        diff=diff_text,
                    )
                )
            except OSError:
                pass

    return TaskDiffResponse(
        task_id=task_id,
        workspace=workspace,
        files=files,
    )


# --- File Tree / File Content Endpoints ---


class FileTreeEntry(BaseModel):
    """A single entry in the workspace file tree."""

    path: str
    name: str
    type: str  # "file" or "dir"
    status: str | None = None  # "modified", "added", "deleted", None (unchanged)


class TaskFileTreeResponse(BaseModel):
    """Response for the workspace file tree."""

    task_id: str
    workspace: str | None = None
    tree: list[FileTreeEntry] = Field(default_factory=list)
    error: str | None = None
    from_snapshot: bool = False


class TaskFileContentResponse(BaseModel):
    """Response for reading a single file's content."""

    task_id: str
    path: str
    content: str | None = None
    diff: str | None = None
    status: str | None = None  # change status of this file
    error: str | None = None


_FILE_TREE_MAX_ENTRIES = 5000
_FILE_CONTENT_MAX_BYTES = 512_000


@app.get("/tasks/{task_id}/tree", response_model=TaskFileTreeResponse)
def get_task_tree(task_id: str) -> TaskFileTreeResponse:
    """Return the full file tree of a task's workspace with change status.

    Falls back to the persistent snapshot when the live workspace is gone.
    """
    task_id = _validate_path_param(task_id, "task_id")
    response = _build_task_tree(task_id)
    if response.error and not response.tree:
        snapshot = read_task_run(task_id)
        if snapshot is not None:
            entries = [
                FileTreeEntry(
                    path=str(item.get("path") or ""),
                    name=str(item.get("name") or ""),
                    type=str(item.get("type") or "file"),
                    status=item.get("status"),
                )
                for item in snapshot.get("tree_entries") or []
                if isinstance(item, dict)
            ]
            return TaskFileTreeResponse(
                task_id=task_id,
                workspace=response.workspace,
                tree=entries,
                from_snapshot=True,
            )
    return response


@app.get(
    "/tasks/{task_id}/file/{file_path:path}",
    response_model=TaskFileContentResponse,
)
def get_task_file(task_id: str, file_path: str) -> TaskFileContentResponse:
    """Return the content of a single file in a task's workspace."""
    task_id = _validate_path_param(task_id, "task_id")
    return _read_task_file(task_id, file_path)


def _build_task_tree(task_id: str) -> TaskFileTreeResponse:
    """Build the workspace file tree with git change status annotations."""
    workspace_path, workspace, _task_ready, error = _resolve_task_workspace(task_id)
    if error:
        return TaskFileTreeResponse(task_id=task_id, workspace=workspace, error=error)
    assert workspace_path is not None

    # Collect changed file statuses via git
    changed: dict[str, str] = {}
    try:
        # Tracked changes (staged + unstaged)
        status_out = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=15,
        )
        if status_out.returncode == 0:
            for line in status_out.stdout.splitlines():
                if len(line) < 4:
                    continue
                xy = line[:2]
                fpath = line[3:].strip()
                # Handle renames: "R  old -> new"
                if " -> " in fpath:
                    fpath = fpath.split(" -> ", 1)[1]
                if "?" in xy or "A" in xy:
                    changed[fpath] = "added"
                elif "D" in xy:
                    changed[fpath] = "deleted"
                elif xy[0] == "R" or xy[1] == "R":
                    changed[fpath] = "renamed"
                else:
                    changed[fpath] = "modified"
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Walk the workspace to build the tree, excluding .git
    entries: list[FileTreeEntry] = []
    dirs_seen: set[str] = set()
    try:
        for item in sorted(workspace_path.rglob("*")):
            try:
                rel = str(item.relative_to(workspace_path))
            except ValueError:
                continue
            # Skip .git internals
            if rel.startswith(".git") and (
                rel == ".git" or rel.startswith(".git/") or rel.startswith(".git\\")
            ):
                continue
            if len(entries) >= _FILE_TREE_MAX_ENTRIES:
                break
            if item.is_dir():
                if rel not in dirs_seen:
                    dirs_seen.add(rel)
                    entries.append(
                        FileTreeEntry(
                            path=rel,
                            name=item.name,
                            type="dir",
                            status=None,
                        )
                    )
            else:
                # Ensure parent dirs are in the tree
                parts = Path(rel).parts
                for i in range(1, len(parts)):
                    parent = str(Path(*parts[:i]))
                    if parent not in dirs_seen:
                        dirs_seen.add(parent)
                        entries.append(
                            FileTreeEntry(
                                path=parent,
                                name=parts[i - 1],
                                type="dir",
                                status=None,
                            )
                        )
                entries.append(
                    FileTreeEntry(
                        path=rel,
                        name=item.name,
                        type="file",
                        status=changed.get(rel),
                    )
                )
    except PermissionError:
        pass

    return TaskFileTreeResponse(
        task_id=task_id,
        workspace=workspace,
        tree=entries,
    )


def _read_task_file(task_id: str, file_path: str) -> TaskFileContentResponse:
    """Read a single file from the task workspace."""
    workspace_path, _workspace, _task_ready, error = _resolve_task_workspace(task_id)
    if error:
        return TaskFileContentResponse(task_id=task_id, path=file_path, error=error)
    assert workspace_path is not None

    # Resolve and validate the path stays within workspace
    target = (workspace_path / file_path).resolve()
    try:
        target.relative_to(workspace_path)
    except ValueError:
        return TaskFileContentResponse(
            task_id=task_id,
            path=file_path,
            error="Path traversal not allowed",
        )

    if not target.is_file():
        return TaskFileContentResponse(
            task_id=task_id,
            path=file_path,
            error="File not found",
        )

    # Read content (with size limit)
    try:
        size = target.stat().st_size
        if size > _FILE_CONTENT_MAX_BYTES:
            return TaskFileContentResponse(
                task_id=task_id,
                path=file_path,
                error=f"File too large ({size:,} bytes, limit {_FILE_CONTENT_MAX_BYTES:,})",
            )
        content = target.read_text(errors="replace")
    except OSError as exc:
        return TaskFileContentResponse(
            task_id=task_id,
            path=file_path,
            error=f"Cannot read file: {exc}",
        )

    # Get diff for this specific file if it has changes
    diff: str | None = None
    status: str | None = None
    try:
        diff_out = subprocess.run(
            ["git", "diff", "HEAD", "--", file_path],
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=10,
        )
        if diff_out.stdout.strip():
            diff = diff_out.stdout
            # Detect status from diff headers
            status = "modified"
            for dline in diff_out.stdout.splitlines()[:10]:
                if dline.startswith("new file"):
                    status = "added"
                    break
                if dline.startswith("deleted file"):
                    status = "deleted"
                    break
        else:
            # Check if untracked
            ls_out = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", "--", file_path],
                capture_output=True,
                text=True,
                cwd=workspace_path,
                timeout=5,
            )
            if ls_out.stdout.strip():
                status = "added"
                numbered = "\n".join(f"+{ln}" for ln in content.splitlines())
                diff = (
                    f"diff --git a/{file_path} b/{file_path}\n"
                    f"new file mode 100644\n"
                    f"--- /dev/null\n"
                    f"+++ b/{file_path}\n"
                    f"@@ -0,0 +1,{len(content.splitlines())} @@\n"
                    f"{numbered}\n"
                )
    except (subprocess.TimeoutExpired, OSError):
        pass

    return TaskFileContentResponse(
        task_id=task_id,
        path=file_path,
        content=content,
        diff=diff,
        status=status,
    )


@app.post("/tasks/{task_id}/cancel", response_model=TaskCancelResponse)
def cancel_task(task_id: str) -> TaskCancelResponse:
    """Cancel a running or queued task by revoking it via Celery."""
    return _cancel_task(task_id)


def _cancel_task(task_id: str) -> TaskCancelResponse:
    """Revoke a Celery task, sending SIGTERM to terminate it if running."""
    task_id = _validate_path_param(task_id, "task_id")
    result = build_feature.AsyncResult(task_id)
    current_status = result.status

    if current_status in _TERMINAL_TASK_STATES:
        return TaskCancelResponse(
            task_id=task_id,
            cancelled=False,
            detail=f"Task already in terminal state: {current_status}",
        )

    celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
    logger.info("Revoked task %s (was %s)", task_id, current_status)

    return TaskCancelResponse(
        task_id=task_id,
        cancelled=True,
        detail=f"Task revoked (was {current_status})",
    )


# --- Schedule Endpoints ---


def _get_schedule_manager() -> ScheduleManager:
    """Get or create the schedule manager singleton."""
    global _schedule_manager
    if _schedule_manager is None:
        try:
            from helping_hands.server.schedules import get_schedule_manager

            _schedule_manager = get_schedule_manager(celery_app)
        except ImportError as exc:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=503,
                detail=f"Scheduling not available: {exc}. {install_hint('server')}",
            ) from exc
    return _schedule_manager


def _server_has_github_token() -> bool:
    """Return whether the server has global GitHub credentials configured.

    True when either a ``GITHUB_TOKEN`` env var is set or a GitHub App is
    configured (see :mod:`helping_hands.lib.github_app`). In both cases the
    server owns the credentials, so per-user token ownership is not enforced.
    """
    if os.environ.get("GITHUB_TOKEN", "").strip():
        return True
    from helping_hands.lib.github_app import github_app_configured

    return github_app_configured()


def _hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of a token string."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def _get_request_token(request) -> str | None:
    """Extract the GitHub token from the X-GitHub-Token header."""
    value = request.headers.get("X-GitHub-Token", "").strip()
    return value or None


def _check_schedule_owner(request, task) -> None:
    """Enforce ownership when the server has no global GITHUB_TOKEN.

    Raises:
        HTTPException: 401 if no token provided, 403 if not the owner.
    """
    from fastapi import HTTPException

    if _server_has_github_token():
        return

    token = _get_request_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub token required")

    admin_token = os.environ.get("ADMIN_GITHUB_TOKEN", "").strip()
    if admin_token and token == admin_token:
        return

    if task.owner_token_hash and _hash_token(token) == task.owner_token_hash:
        return

    raise HTTPException(
        status_code=403, detail="Not authorized to modify this schedule"
    )


def _is_schedule_visible(task, request) -> bool:
    """Check if a schedule should be visible to the requesting user.

    When the server has a global GITHUB_TOKEN, all schedules are visible.
    Otherwise, only schedules owned by the requesting user (or admin) are shown.
    """
    if _server_has_github_token():
        return True

    token = _get_request_token(request)
    if not token:
        return False

    admin_token = os.environ.get("ADMIN_GITHUB_TOKEN", "").strip()
    if admin_token and token == admin_token:
        return True

    return bool(task.owner_token_hash and _hash_token(token) == task.owner_token_hash)


def _check_watch_issues_uniqueness(
    schedule_type: str,
    repo_path: str,
    enabled: bool,
    exclude_schedule_id: str | None = None,
) -> None:
    """Reject a second enabled auto-implement-issues schedule for the same repo.

    Auto-implement schedules use shared GitHub labels (``helping-hands:queued``,
    ``done``, ``failed``) for per-issue de-duplication; two concurrent schedules
    on the same repo would race over those labels. Enforce one global per repo.
    Disabled schedules are exempt so swapping owners is possible.
    """
    from fastapi import HTTPException

    if schedule_type != "watch_issues" or not enabled:
        return

    normalized = (repo_path or "").strip().lower()
    if not normalized:
        return

    manager = _get_schedule_manager()
    for existing in manager.list_schedules():
        if existing.schedule_id == exclude_schedule_id:
            continue
        if existing.schedule_type != "watch_issues" or not existing.enabled:
            continue
        if (existing.repo_path or "").strip().lower() == normalized:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Another auto-implement issues schedule is already enabled "
                    f"for {existing.repo_path}. Disable or delete it first."
                ),
            )


def _schedule_to_response(task) -> ScheduleResponse:
    """Convert a ScheduledTask to a ScheduleResponse.

    Args:
        task: A ``ScheduledTask`` instance to convert.

    Returns:
        A ``ScheduleResponse`` with computed ``next_run`` and redacted token.
    """
    from helping_hands.server.schedules import next_interval_run_time, next_run_time

    next_run = None
    if task.enabled:
        try:
            if task.schedule_type == _SCHEDULE_TYPE_INTERVAL and task.interval_seconds:
                next_run = next_interval_run_time(
                    task.interval_seconds, task.last_run_at
                ).isoformat()
            elif task.cron_expression:
                next_run = next_run_time(task.cron_expression).isoformat()
        except (ValueError, TypeError):
            logger.debug(
                "Failed to calculate next run for schedule %s",
                task.schedule_id,
                exc_info=True,
            )

    return ScheduleResponse(
        schedule_id=task.schedule_id,
        name=task.name,
        schedule_type=task.schedule_type,
        cron_expression=task.cron_expression,
        interval_seconds=task.interval_seconds,
        repo_path=task.repo_path,
        prompt=task.prompt,
        backend=task.backend,
        model=task.model,
        max_iterations=task.max_iterations,
        pr_number=task.pr_number,
        no_pr=task.no_pr,
        enable_execution=task.enable_execution,
        enable_web=task.enable_web,
        use_native_cli_auth=task.use_native_cli_auth,
        fix_ci=task.fix_ci,
        fix_conflicts=task.fix_conflicts,
        master_rebase=task.master_rebase,
        ci_check_wait_minutes=task.ci_check_wait_minutes,
        github_token=_redact_token(task.github_token),
        reference_repos=task.reference_repos,
        tools=task.tools,
        watch_labels=task.watch_labels,
        enabled=task.enabled,
        created_at=task.created_at,
        last_run_at=task.last_run_at,
        last_run_task_id=task.last_run_task_id,
        run_count=task.run_count,
        next_run_at=next_run,
    )


@app.get("/schedules/presets", response_model=CronPresetsResponse)
def get_cron_presets() -> CronPresetsResponse:
    """Get available cron expression presets and interval presets."""
    from helping_hands.server.schedules import CRON_PRESETS

    return CronPresetsResponse(
        presets=CRON_PRESETS,
        interval_presets=_INTERVAL_PRESETS,
    )


@app.get("/schedules", response_model=ScheduleListResponse)
def list_schedules(request: Request) -> ScheduleListResponse:
    """List all scheduled tasks."""
    manager = _get_schedule_manager()
    tasks = manager.list_schedules()
    visible = [t for t in tasks if _is_schedule_visible(t, request)]
    return ScheduleListResponse(
        schedules=[_schedule_to_response(t) for t in visible],
        total=len(visible),
    )


@app.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    request: ScheduleRequest, http_request: Request
) -> ScheduleResponse:
    """Create a new scheduled task."""
    from fastapi import HTTPException

    from helping_hands.server.schedules import ScheduledTask, generate_schedule_id

    _check_watch_issues_uniqueness(
        request.schedule_type, request.repo_path, request.enabled
    )

    manager = _get_schedule_manager()

    # Determine owner token: prefer header, fall back to body field.
    owner_token = (
        _get_request_token(http_request) or (request.github_token or "").strip()
    )
    owner_hash = _hash_token(owner_token) if owner_token else None

    task = ScheduledTask(
        schedule_id=generate_schedule_id(),
        name=request.name,
        schedule_type=request.schedule_type,
        cron_expression=request.cron_expression,
        interval_seconds=request.interval_seconds,
        repo_path=request.repo_path,
        prompt=request.prompt,
        backend=request.backend,
        model=request.model,
        max_iterations=request.max_iterations,
        pr_number=request.pr_number,
        no_pr=request.no_pr,
        enable_execution=request.enable_execution,
        enable_web=request.enable_web,
        use_native_cli_auth=request.use_native_cli_auth,
        fix_ci=request.fix_ci,
        fix_conflicts=request.fix_conflicts,
        master_rebase=request.master_rebase,
        ci_check_wait_minutes=request.ci_check_wait_minutes,
        github_token=request.github_token,
        owner_token_hash=owner_hash,
        reference_repos=request.reference_repos,
        tools=request.tools,
        watch_labels=request.watch_labels,
        enabled=request.enabled,
    )

    try:
        created = manager.create_schedule(task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _schedule_to_response(created)


@app.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: str, request: Request) -> ScheduleResponse:
    """Get a scheduled task by ID."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.get_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    _check_schedule_owner(request, task)
    return _schedule_to_response(task)


@app.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: str, request: ScheduleRequest, http_request: Request
) -> ScheduleResponse:
    """Update a scheduled task."""
    from fastapi import HTTPException

    from helping_hands.server.schedules import ScheduledTask

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()

    existing = manager.get_schedule(schedule_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)

    _check_schedule_owner(http_request, existing)

    _check_watch_issues_uniqueness(
        request.schedule_type,
        request.repo_path,
        request.enabled,
        exclude_schedule_id=schedule_id,
    )

    # If the token looks redacted (contains ***), preserve the existing one.
    github_token = request.github_token
    if github_token and "***" in github_token:
        github_token = existing.github_token

    task = ScheduledTask(
        schedule_id=schedule_id,
        name=request.name,
        schedule_type=request.schedule_type,
        cron_expression=request.cron_expression,
        interval_seconds=request.interval_seconds,
        repo_path=request.repo_path,
        prompt=request.prompt,
        backend=request.backend,
        model=request.model,
        max_iterations=request.max_iterations,
        pr_number=request.pr_number,
        no_pr=request.no_pr,
        enable_execution=request.enable_execution,
        enable_web=request.enable_web,
        use_native_cli_auth=request.use_native_cli_auth,
        fix_ci=request.fix_ci,
        fix_conflicts=request.fix_conflicts,
        master_rebase=request.master_rebase,
        ci_check_wait_minutes=request.ci_check_wait_minutes,
        github_token=github_token,
        owner_token_hash=existing.owner_token_hash,
        reference_repos=request.reference_repos,
        tools=request.tools,
        watch_labels=request.watch_labels,
        enabled=request.enabled,
    )

    try:
        updated = manager.update_schedule(task)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _schedule_to_response(updated)


@app.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, request: Request) -> None:
    """Delete a scheduled task."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.get_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    _check_schedule_owner(request, task)
    manager.delete_schedule(schedule_id)


@app.post("/schedules/{schedule_id}/enable", response_model=ScheduleResponse)
def enable_schedule(schedule_id: str, request: Request) -> ScheduleResponse:
    """Enable a scheduled task."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.get_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    _check_schedule_owner(request, task)
    _check_watch_issues_uniqueness(
        task.schedule_type,
        task.repo_path,
        enabled=True,
        exclude_schedule_id=schedule_id,
    )
    task = manager.enable_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    return _schedule_to_response(task)


@app.post("/schedules/{schedule_id}/disable", response_model=ScheduleResponse)
def disable_schedule(schedule_id: str, request: Request) -> ScheduleResponse:
    """Disable a scheduled task."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.get_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    _check_schedule_owner(request, task)
    task = manager.disable_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    return _schedule_to_response(task)


@app.post("/schedules/{schedule_id}/trigger", response_model=ScheduleTriggerResponse)
def trigger_schedule(schedule_id: str, request: Request) -> ScheduleTriggerResponse:
    """Manually trigger a scheduled task to run immediately."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.get_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    _check_schedule_owner(request, task)
    task_id = manager.trigger_now(schedule_id)
    if task_id is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)

    return ScheduleTriggerResponse(
        schedule_id=schedule_id,
        task_id=task_id,
        message="Schedule triggered successfully",
    )


# --- Template Endpoints ---


_template_manager: TemplateManager | None = None


def _get_template_manager() -> TemplateManager:
    """Get or create the template manager singleton."""
    global _template_manager
    if _template_manager is None:
        from helping_hands.server.templates import TemplateManager

        _template_manager = TemplateManager()
    return _template_manager


def _check_template_owner(request: Request, template: Any) -> None:
    """Enforce ownership for template mutation endpoints.

    Templates are globally readable but only the creator (or admin) can
    modify/delete. When the server has a global ``GITHUB_TOKEN`` set,
    ownership checks are skipped (same pattern as schedules).

    Raises:
        HTTPException: 401 if no token provided, 403 if not the owner.
    """
    from fastapi import HTTPException

    if _server_has_github_token():
        return

    token = _get_request_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub token required")

    admin_token = os.environ.get("ADMIN_GITHUB_TOKEN", "").strip()
    if admin_token and token == admin_token:
        return

    if template.owner_token_hash and _hash_token(token) == template.owner_token_hash:
        return

    raise HTTPException(
        status_code=403, detail="Not authorized to modify this template"
    )


def _template_to_response(template: Any) -> TemplateResponse:
    """Convert a TaskTemplate to a TemplateResponse."""
    return TemplateResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        owner_token_hash=template.owner_token_hash,
        created_at=template.created_at,
        updated_at=template.updated_at,
        repo_path=template.repo_path,
        prompt=template.prompt,
        backend=template.backend,
        model=template.model,
        max_iterations=template.max_iterations,
        pr_number=template.pr_number,
        issue_number=template.issue_number,
        create_issue=template.create_issue,
        project_url=template.project_url,
        no_pr=template.no_pr,
        enable_execution=template.enable_execution,
        enable_web=template.enable_web,
        use_native_cli_auth=template.use_native_cli_auth,
        fix_ci=template.fix_ci,
        fix_conflicts=template.fix_conflicts,
        master_rebase=template.master_rebase,
        ci_check_wait_minutes=template.ci_check_wait_minutes,
        reference_repos=template.reference_repos,
        tools=template.tools,
    )


@app.get("/templates", response_model=TemplateListResponse)
def list_templates() -> TemplateListResponse:
    """List all task templates."""
    manager = _get_template_manager()
    templates = manager.list_templates()
    return TemplateListResponse(
        templates=[_template_to_response(t) for t in templates],
        total=len(templates),
    )


@app.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(
    request: TemplateRequest, http_request: Request
) -> TemplateResponse:
    """Create a new task template."""
    from fastapi import HTTPException

    from helping_hands.server.templates import TaskTemplate, generate_template_id

    token = _get_request_token(http_request)
    if not token and not _server_has_github_token():
        raise HTTPException(status_code=401, detail="GitHub token required")

    owner_hash = _hash_token(token) if token else None

    template = TaskTemplate(
        template_id=generate_template_id(),
        name=request.name,
        description=request.description,
        owner_token_hash=owner_hash,
        repo_path=request.repo_path,
        prompt=request.prompt,
        backend=request.backend,
        model=request.model,
        max_iterations=request.max_iterations,
        pr_number=request.pr_number,
        issue_number=request.issue_number,
        create_issue=request.create_issue,
        project_url=request.project_url,
        no_pr=request.no_pr,
        enable_execution=request.enable_execution,
        enable_web=request.enable_web,
        use_native_cli_auth=request.use_native_cli_auth,
        fix_ci=request.fix_ci,
        fix_conflicts=request.fix_conflicts,
        master_rebase=request.master_rebase,
        ci_check_wait_minutes=request.ci_check_wait_minutes,
        reference_repos=request.reference_repos,
        tools=request.tools,
    )

    manager = _get_template_manager()
    try:
        created = manager.create_template(template)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return _template_to_response(created)


@app.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(template_id: str) -> TemplateResponse:
    """Get a task template by ID."""
    from fastapi import HTTPException

    template_id = _validate_path_param(template_id, "template_id")
    manager = _get_template_manager()
    template = manager.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=_TEMPLATE_NOT_FOUND_DETAIL)
    return _template_to_response(template)


@app.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str, request: TemplateRequest, http_request: Request
) -> TemplateResponse:
    """Update a task template."""
    from fastapi import HTTPException

    from helping_hands.server.templates import TaskTemplate

    template_id = _validate_path_param(template_id, "template_id")
    manager = _get_template_manager()

    existing = manager.get_template(template_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=_TEMPLATE_NOT_FOUND_DETAIL)

    _check_template_owner(http_request, existing)

    template = TaskTemplate(
        template_id=template_id,
        name=request.name,
        description=request.description,
        owner_token_hash=existing.owner_token_hash,
        repo_path=request.repo_path,
        prompt=request.prompt,
        backend=request.backend,
        model=request.model,
        max_iterations=request.max_iterations,
        pr_number=request.pr_number,
        issue_number=request.issue_number,
        create_issue=request.create_issue,
        project_url=request.project_url,
        no_pr=request.no_pr,
        enable_execution=request.enable_execution,
        enable_web=request.enable_web,
        use_native_cli_auth=request.use_native_cli_auth,
        fix_ci=request.fix_ci,
        fix_conflicts=request.fix_conflicts,
        master_rebase=request.master_rebase,
        ci_check_wait_minutes=request.ci_check_wait_minutes,
        reference_repos=request.reference_repos,
        tools=request.tools,
    )

    try:
        updated = manager.update_template(template)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return _template_to_response(updated)


@app.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: str, request: Request) -> None:
    """Delete a task template."""
    from fastapi import HTTPException

    template_id = _validate_path_param(template_id, "template_id")
    manager = _get_template_manager()
    template = manager.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=_TEMPLATE_NOT_FOUND_DETAIL)
    _check_template_owner(request, template)
    manager.delete_template(template_id)


# ---------------------------------------------------------------------------
# Grill Me — interactive AI interview sessions
# ---------------------------------------------------------------------------


def _grill_enabled() -> bool:
    """Return whether the Grill Me feature is enabled via environment."""
    return _is_truthy_env(_GRILL_ME_ENABLED_ENV_VAR)


class GrillRequest(BaseModel):
    """Request body for starting a grill session."""

    repo_path: str = Field(min_length=1, max_length=_MAX_REPO_PATH_LENGTH)
    prompt: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH)
    model: str | None = Field(default=None, max_length=_MAX_MODEL_LENGTH)
    github_token: str | None = Field(default=None, max_length=_MAX_GITHUB_TOKEN_LENGTH)
    reference_repos: list[str] = Field(
        default_factory=list, max_length=_MAX_REFERENCE_REPOS
    )
    backend: str = Field(default="claudecodecli", max_length=_MAX_MODEL_LENGTH)


class GrillStartResponse(BaseModel):
    """Response for a newly started grill session."""

    session_id: str
    status: str


class GrillMessageRequest(BaseModel):
    """Request body for sending a message to a grill session."""

    content: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH)
    type: str = "message"


class GrillMessageOut(BaseModel):
    """A single message from the grill session outbound queue."""

    id: str
    role: str
    content: str
    type: str
    timestamp: float


class GrillPollResponse(BaseModel):
    """Response for polling grill session state + new messages."""

    session_id: str
    status: str
    messages: list[GrillMessageOut]


@app.post("/grill", response_model=GrillStartResponse, status_code=201)
def start_grill(req: GrillRequest) -> GrillStartResponse:
    """Start a new interactive grill session."""
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    from helping_hands.server.grill import grill_session

    task = grill_session.delay(
        repo_path=req.repo_path,
        prompt=req.prompt,
        model=req.model,
        github_token=req.github_token,
        reference_repos=req.reference_repos,
        backend=req.backend,
    )
    return GrillStartResponse(session_id=task.id, status="starting")


@app.post("/grill/{session_id}/message")
def send_grill_message(session_id: str, req: GrillMessageRequest) -> dict[str, str]:
    """Send a user message to an active grill session."""
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    import json as _json

    import redis

    session_id = _validate_path_param(session_id, "session_id")
    redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
    r = redis.from_url(redis_url, decode_responses=True)

    # Check session exists
    state_key = f"grill:{session_id}:state"
    state_raw = r.get(state_key)
    if state_raw is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Grill session not found")

    # Push message to user queue
    msg_key = f"grill:{session_id}:user_msgs"
    now = time.time()
    msg = {
        "content": req.content,
        "type": req.type,
        "timestamp": now,
    }
    r.rpush(msg_key, _json.dumps(msg))
    r.expire(msg_key, 3600)

    # Also append to the persistent transcript so the chat view can be
    # reconstructed when a suspended session is resumed.
    import uuid as _uuid

    transcript_key = f"grill:{session_id}:transcript"
    transcript_msg = {
        "id": str(_uuid.uuid4()),
        "role": "user",
        "content": req.content,
        "type": req.type,
        "timestamp": now,
    }
    r.rpush(transcript_key, _json.dumps(transcript_msg))
    r.expire(transcript_key, 3600)

    # Auto-resume suspended sessions
    state = _json.loads(state_raw)
    if state.get("status") == "suspended":
        from helping_hands.server.grill import resume_grill_session

        resume_grill_session.delay(original_session_id=session_id)

    return {"status": "sent"}


@app.get("/grill/{session_id}", response_model=GrillPollResponse)
def poll_grill(session_id: str) -> GrillPollResponse:
    """Poll for new AI messages and session state."""
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    import json as _json

    import redis

    session_id = _validate_path_param(session_id, "session_id")
    redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
    r = redis.from_url(redis_url, decode_responses=True)

    # Get state
    state_key = f"grill:{session_id}:state"
    state_raw = r.get(state_key)
    if state_raw is None:
        return GrillPollResponse(session_id=session_id, status="not_found", messages=[])

    state = _json.loads(state_raw)
    status = state.get("status", "unknown")

    r.set(f"grill:{session_id}:last_seen", str(time.time()), ex=600)

    # Drain all pending AI messages
    ai_key = f"grill:{session_id}:ai_msgs"
    messages: list[GrillMessageOut] = []
    while True:
        raw = r.lpop(ai_key)
        if raw is None:
            break
        msg = _json.loads(raw)
        messages.append(GrillMessageOut(**msg))

    return GrillPollResponse(
        session_id=session_id,
        status=status,
        messages=messages,
    )


@app.get("/grill/{session_id}/transcript", response_model=GrillPollResponse)
def get_grill_transcript(session_id: str) -> GrillPollResponse:
    """Return the full message history for a grill session.

    Used when resuming a suspended session: the polling endpoint drains the
    AI message queue destructively, so it cannot replay history. The
    transcript list is append-only and survives polls.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    import json as _json

    import redis

    session_id = _validate_path_param(session_id, "session_id")
    redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
    r = redis.from_url(redis_url, decode_responses=True)

    state_key = f"grill:{session_id}:state"
    state_raw = r.get(state_key)
    if state_raw is None:
        return GrillPollResponse(session_id=session_id, status="not_found", messages=[])

    state = _json.loads(state_raw)
    status = state.get("status", "unknown")

    transcript_key = f"grill:{session_id}:transcript"
    raws = r.lrange(transcript_key, 0, -1)
    messages = [GrillMessageOut(**_json.loads(raw)) for raw in raws]

    # Drain any AI messages still queued so the next poll doesn't re-deliver
    # them as duplicates of what we just returned via the transcript.
    ai_key = f"grill:{session_id}:ai_msgs"
    while r.lpop(ai_key) is not None:
        pass

    return GrillPollResponse(
        session_id=session_id,
        status=status,
        messages=messages,
    )


class GrillSessionSummary(BaseModel):
    """Summary of a resumable solo grill session."""

    session_id: str
    status: str
    repo_path: str
    prompt: str
    model: str
    backend: str
    turn_count: int


class GrillResumableListResponse(BaseModel):
    """Response listing resumable solo grill sessions."""

    sessions: list[GrillSessionSummary]
    total: int


@app.get("/grill/sessions/resumable", response_model=GrillResumableListResponse)
def grill_resumable_sessions() -> GrillResumableListResponse:
    """List solo grill sessions that can be resumed (suspended status)."""
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    import json as _json

    import redis

    redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
    r = redis.from_url(redis_url, decode_responses=True)

    sessions: list[GrillSessionSummary] = []
    cursor = "0"
    while True:
        cursor, keys = r.scan(cursor=cursor, match="grill:*:state", count=100)
        for key in keys:
            raw = r.get(key)
            if raw is None:
                continue
            state = _json.loads(raw)
            if state.get("status") != "suspended":
                continue
            sid = key.split(":")[1]
            sessions.append(
                GrillSessionSummary(
                    session_id=sid,
                    status="suspended",
                    repo_path=state.get("repo_path", ""),
                    prompt=state.get("prompt", ""),
                    model=state.get("model", ""),
                    backend=state.get("backend", "claudecodecli"),
                    turn_count=int(state.get("turn_count", 0)),
                )
            )
        if cursor == "0" or cursor == 0:
            break

    sessions.sort(key=lambda s: s.turn_count, reverse=True)
    return GrillResumableListResponse(sessions=sessions, total=len(sessions))


# ---------------------------------------------------------------------------
# Multiplayer Grill Me — collaborative AI interview sessions
# ---------------------------------------------------------------------------
#
# Transport split:
#   * Yjs room ``mgrill-{session_id}`` is authoritative for transcript
#     (``messages`` Y.Array), vote tally (``votes`` Y.Map), and the pending
#     batch (``pending`` Y.Map).  The frontend subscribes directly via
#     ``WebsocketProvider``; the server mutates these same structures
#     in-process so the changes sync automatically.
#   * Redis is authoritative for the session registry, creator identity,
#     turn count + status (everything that REST endpoints and the Celery
#     worker need without touching the Y.Doc), and the ``user_msgs`` queue
#     that the worker consumes.
#   * AI-produced messages travel ``worker → Redis mgrill:ai_outbox →
#     mgrill_bridge task → Y.Array "messages"``.  See mgrill_bridge.py.


_MGRILL_MAX_NAME_LENGTH = 50
_MGRILL_MAX_PENDING = 20
_MGRILL_LOBBY_CAP = 50
_MGRILL_CREATOR_HANDOFF_S = 60


class MGrillCreateRequest(BaseModel):
    """Request body for creating a new multiplayer grill session."""

    repo_path: str = Field(min_length=1, max_length=_MAX_REPO_PATH_LENGTH)
    prompt: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH)
    model: str | None = Field(default=None, max_length=_MAX_MODEL_LENGTH)
    creator_name: str = Field(default="Creator", max_length=_MGRILL_MAX_NAME_LENGTH)
    creator_player_id: str | None = Field(default=None, max_length=64)
    reference_repos: list[str] = Field(
        default_factory=list, max_length=_MAX_REFERENCE_REPOS
    )
    backend: str = Field(default="claudecodecli", max_length=_MAX_MODEL_LENGTH)


class MGrillCreateResponse(BaseModel):
    """Response for a newly created multiplayer grill session."""

    session_id: str
    status: str


class MGrillSessionSummary(BaseModel):
    """Lobby listing for a single active multiplayer grill session."""

    session_id: str
    status: str
    creator_name: str
    repo_path: str
    prompt: str
    turn_count: int
    created_at: float
    last_activity_ts: float
    participant_count: int = 0
    has_final_plan: bool = False


class MGrillListResponse(BaseModel):
    """Response for the lobby session list."""

    sessions: list[MGrillSessionSummary]
    total: int


class MGrillPollResponse(BaseModel):
    """State snapshot for a multiplayer grill session.

    The transcript, pending batch, and vote map live in the Yjs room — the
    frontend subscribes to those directly.  This endpoint only returns what
    lives in Redis and the room-awareness view.
    """

    session_id: str
    status: str
    creator_name: str
    creator_token_hash: str | None
    creator_player_id: str | None
    creator_last_seen_ts: float
    is_creator: bool
    can_act_as_creator: bool
    repo_path: str
    prompt: str
    model: str | None
    backend: str
    turn_count: int
    participant_count: int
    submitted_task_id: str | None


class MGrillPendingRequest(BaseModel):
    """Add a pending-batch message."""

    player_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=_MGRILL_MAX_NAME_LENGTH)
    content: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH)


class MGrillVoteRequest(BaseModel):
    """Cast or update a vote."""

    player_id: str = Field(min_length=1, max_length=64)
    vote: str = Field(pattern="^(up|down|clear)$")


class MGrillHeartbeatRequest(BaseModel):
    """Creator heartbeat (refreshes creator_last_seen_ts)."""

    player_id: str | None = Field(default=None, max_length=64)


def _mgrill_redis():  # pragma: no cover — needs redis
    """Return a Redis client configured from the REDIS_URL env."""
    import redis

    redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
    return redis.from_url(redis_url, decode_responses=True)


def _mgrill_read_state(r, session_id: str) -> dict[str, Any] | None:
    """Read and JSON-decode the session state, or return None."""
    raw = r.get(f"mgrill:{session_id}:state")
    if raw is None:
        return None
    return json.loads(raw)


def _mgrill_touch_activity(r, session_id: str) -> None:
    """Bump this session's registry score to now()."""
    r.zadd("mgrill:sessions", {session_id: time.time()})


def _mgrill_write_state(r, session_id: str, state: dict[str, Any]) -> None:
    """Write session state + refresh TTL + bump registry activity."""
    r.set(f"mgrill:{session_id}:state", json.dumps(state), ex=3600)
    state["last_activity_ts"] = time.time()
    _mgrill_touch_activity(r, session_id)


def _mgrill_require_state(r, session_id: str) -> dict[str, Any]:
    """Return state or raise 404."""
    from fastapi import HTTPException

    state = _mgrill_read_state(r, session_id)
    if state is None:
        raise HTTPException(
            status_code=404, detail="Multiplayer grill session not found"
        )
    return state


def _mgrill_effective_token(request: Request) -> str | None:
    """Return the effective GitHub token for an mgrill action.

    Falls back to the server-wide ``GITHUB_TOKEN`` env var when the client
    hasn't sent ``X-GitHub-Token``.  Mirrors the schedules ownership pattern
    where server-configured tokens satisfy auth for all users.
    """
    client = _get_request_token(request)
    if client:
        return client
    server_token = os.environ.get("GITHUB_TOKEN", "").strip()
    return server_token or None


def _mgrill_require_token(request: Request) -> str:
    """Return an effective token or raise 401.

    When the server has global credentials configured (``GITHUB_TOKEN`` or a
    GitHub App), client tokens are optional. With a GitHub App and no client
    token this returns ``""`` — a sentinel meaning "use the server's
    credentials", which downstream resolves to a freshly minted installation
    token at clone time. Otherwise the client must provide ``X-GitHub-Token``.
    """
    from fastapi import HTTPException

    token = _mgrill_effective_token(request)
    if token:
        return token
    if _server_has_github_token():
        # GitHub App is configured; the worker mints an installation token.
        return ""
    raise HTTPException(status_code=401, detail="GitHub token required")


def _mgrill_require_creator(state: dict[str, Any], token_hash: str) -> None:
    """Raise 403 if *token_hash* is not the creator's.

    Bypassed when the server has a global ``GITHUB_TOKEN`` — in that mode
    identity is server-owned, not per-user, so any authenticated caller
    may act as the creator (submit, keep-grilling, heartbeat, etc.).
    """
    from fastapi import HTTPException

    if _server_has_github_token():
        return
    creator_hash = state.get("creator_token_hash")
    if creator_hash and token_hash == creator_hash:
        return
    admin_token = os.environ.get("ADMIN_GITHUB_TOKEN", "").strip()
    if admin_token and token_hash == _hash_token(admin_token):
        return
    raise HTTPException(status_code=403, detail="Creator-only action")


async def _mgrill_room(session_id: str) -> Any | None:
    """Return the Yjs room for *session_id*, creating it if needed.

    Returns ``None`` when the Yjs server is unavailable (pycrdt-websocket not
    installed).  The underlying ``get_room`` call is idempotent and also
    starts the room, so this is safe to call repeatedly.
    """
    server = _multiplayer_yjs.yjs_websocket_server
    if server is None:
        return None
    try:
        return await server.get_room(_mgrill_room_name(session_id))
    except Exception:
        logger.exception("mgrill: failed to get Yjs room for session %s", session_id)
        return None


def _ydoc_array(ydoc: Any, key: str) -> Any:
    """Return ``ydoc[key]`` as a Y.Array, creating it if missing."""
    from pycrdt import Array

    try:
        return ydoc[key]
    except KeyError:
        ydoc[key] = Array()
        return ydoc[key]


def _ydoc_map(ydoc: Any, key: str) -> Any:
    """Return ``ydoc[key]`` as a Y.Map, creating it if missing."""
    from pycrdt import Map

    try:
        return ydoc[key]
    except KeyError:
        ydoc[key] = Map()
        return ydoc[key]


def _ydoc_append_system_hint(ydoc: Any, content: str) -> None:
    """Append a system message to the room's transcript Y.Array."""
    arr = _ydoc_array(ydoc, "messages")
    arr.append(
        {
            "id": str(uuid.uuid4()),
            "role": "system",
            "content": content,
            "type": "message",
            "author_player_id": None,
            "author_name": None,
            "timestamp": time.time(),
        }
    )


def _mgrill_participant_count(session_id: str) -> int:
    """Count clients currently connected to the session's Yjs room."""
    server = _multiplayer_yjs.yjs_websocket_server
    if server is None:
        return 0
    room = getattr(server, "rooms", {}).get(_mgrill_room_name(session_id))
    if room is None:
        return 0
    return len(getattr(room, "clients", ()) or ())


def _mgrill_has_final_plan(ydoc: Any) -> bool:
    """Return True when the transcript contains a ``type == "plan"`` entry."""
    try:
        arr = ydoc["messages"]
    except KeyError:
        return False
    return any(isinstance(msg, dict) and msg.get("type") == "plan" for msg in arr)


def _mgrill_final_plan_text(ydoc: Any) -> str | None:
    """Return the content of the most recent ``type == "plan"`` transcript
    entry, or ``None`` if no plan has been emitted."""
    try:
        arr = ydoc["messages"]
    except KeyError:
        return None
    latest: str | None = None
    for msg in arr:
        if isinstance(msg, dict) and msg.get("type") == "plan":
            content = msg.get("content")
            if isinstance(content, str):
                latest = content
    return latest


def _mgrill_vote_tally(ydoc: Any) -> tuple[int, int, int]:
    """Return ``(up, down, total)`` from the room's ``votes`` Y.Map."""
    try:
        votes = ydoc["votes"]
    except KeyError:
        return 0, 0, 0
    up = down = total = 0
    for _pid, vote in dict(votes).items():
        total += 1
        if vote == "up":
            up += 1
        elif vote == "down":
            down += 1
    return up, down, total


@app.post("/mgrill/sessions", response_model=MGrillCreateResponse, status_code=201)
def mgrill_create(
    req: MGrillCreateRequest, http_request: Request
) -> MGrillCreateResponse:
    """Create a new multiplayer grill session.

    Requires ``X-GitHub-Token`` — the creator is the accountable user
    (owns Submit).  The session's Celery task id is returned as
    ``session_id`` and is used as the Yjs room id (``mgrill-{session_id}``).
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    token = _mgrill_require_token(http_request)
    token_hash = _hash_token(token)

    from helping_hands.server.multiplayer_grill import mgrill_session

    task = mgrill_session.delay(
        repo_path=req.repo_path,
        prompt=req.prompt,
        model=req.model,
        github_token=token,
        reference_repos=req.reference_repos,
        backend=req.backend,
        creator_name=req.creator_name,
        creator_token_hash=token_hash,
        creator_player_id=req.creator_player_id,
    )
    return MGrillCreateResponse(session_id=task.id, status="starting")


@app.get("/mgrill/sessions", response_model=MGrillListResponse)
def mgrill_list() -> MGrillListResponse:
    """List active multiplayer grill sessions, sorted by last activity."""
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    r = _mgrill_redis()
    ids = r.zrevrange("mgrill:sessions", 0, _MGRILL_LOBBY_CAP - 1)
    sessions: list[MGrillSessionSummary] = []
    server = _multiplayer_yjs.yjs_websocket_server
    for sid in ids:
        state = _mgrill_read_state(r, sid)
        if state is None:
            # Stale registry entry — evict.
            r.zrem("mgrill:sessions", sid)
            continue
        status = state.get("status", "unknown")
        if status in ("error", "timeout", "max_turns"):
            continue
        # Participant count + plan presence come from the Yjs room (if live).
        participant_count = 0
        has_final_plan = False
        if server is not None:
            room = getattr(server, "rooms", {}).get(_mgrill_room_name(sid))
            if room is not None:
                participant_count = len(getattr(room, "clients", ()) or ())
                ydoc = getattr(room, "ydoc", None)
                if ydoc is not None:
                    has_final_plan = _mgrill_has_final_plan(ydoc)
        sessions.append(
            MGrillSessionSummary(
                session_id=sid,
                status=status,
                creator_name=state.get("creator_name", ""),
                repo_path=state.get("repo_path", ""),
                prompt=state.get("prompt", ""),
                turn_count=int(state.get("turn_count", 0)),
                created_at=float(state.get("created_at", 0)),
                last_activity_ts=float(state.get("last_activity_ts", 0)),
                participant_count=participant_count,
                has_final_plan=has_final_plan,
            )
        )
    return MGrillListResponse(sessions=sessions, total=len(sessions))


@app.get("/mgrill/{session_id}", response_model=MGrillPollResponse)
def mgrill_poll(session_id: str, request: Request) -> MGrillPollResponse:
    """Return the Redis-side session state + the Yjs participant count.

    Transcript, pending batch, and votes are NOT included — the frontend
    reads those from the Yjs room directly.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)

    r.set(f"mgrill:{session_id}:last_seen", str(time.time()), ex=3600)

    # is_creator: true only when the caller actually created this session.
    # can_act_as_creator: true when the caller may Submit/Keep Grilling
    # (always true when the server has a global GITHUB_TOKEN).
    request_token = _get_request_token(request)
    is_creator = False
    if request_token:
        request_hash = _hash_token(request_token)
        if state.get("creator_token_hash") and request_hash == state.get(
            "creator_token_hash"
        ):
            is_creator = True
        else:
            admin = os.environ.get("ADMIN_GITHUB_TOKEN", "").strip()
            if admin and request_hash == _hash_token(admin):
                is_creator = True

    can_act_as_creator = is_creator or _server_has_github_token()

    return MGrillPollResponse(
        session_id=session_id,
        status=state.get("status", "unknown"),
        creator_name=state.get("creator_name", ""),
        creator_token_hash=state.get("creator_token_hash"),
        creator_player_id=state.get("creator_player_id"),
        creator_last_seen_ts=float(state.get("creator_last_seen_ts", 0)),
        is_creator=is_creator,
        can_act_as_creator=can_act_as_creator,
        repo_path=state.get("repo_path", ""),
        prompt=state.get("prompt", ""),
        model=state.get("model") or None,
        backend=state.get("backend", "claudecodecli"),
        turn_count=int(state.get("turn_count", 0)),
        participant_count=_mgrill_participant_count(session_id),
        submitted_task_id=state.get("submitted_task_id"),
    )


@app.post("/mgrill/{session_id}/pending")
async def mgrill_add_pending(
    session_id: str,
    req: MGrillPendingRequest,
    http_request: Request,
) -> dict[str, str]:
    """Add a message to the pending batch (any participant).

    Writes directly into the room's ``pending`` Y.Map so all connected
    participants see the addition via their Yjs subscription.  No GitHub
    token required — anyone can participate in chat.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    _mgrill_require_state(r, session_id)

    room = await _mgrill_room(session_id)
    if room is None:
        raise HTTPException(status_code=503, detail="Yjs server unavailable")
    pending = _ydoc_map(room.ydoc, "pending")
    if len(dict(pending)) >= _MGRILL_MAX_PENDING:
        raise HTTPException(status_code=429, detail="Pending batch is full")

    pending_id = str(uuid.uuid4())
    pending[pending_id] = {
        "player_id": req.player_id,
        "name": req.name[:_MGRILL_MAX_NAME_LENGTH],
        "content": req.content,
        "timestamp": time.time(),
    }
    _mgrill_touch_activity(r, session_id)
    return {"status": "queued", "pending_id": pending_id}


@app.delete("/mgrill/{session_id}/pending/{pending_id}")
async def mgrill_remove_pending(
    session_id: str,
    pending_id: str,
    http_request: Request,
) -> dict[str, str]:
    """Remove a pending message (author or creator).

    Uses player_id from the ``X-MGrill-Player-Id`` header for author
    matching.  Creator can delete any entry; other participants can only
    delete their own.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    session_id = _validate_path_param(session_id, "session_id")
    pending_id = _validate_path_param(pending_id, "pending_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)

    room = await _mgrill_room(session_id)
    if room is None:
        raise HTTPException(status_code=503, detail="Yjs server unavailable")
    pending = _ydoc_map(room.ydoc, "pending")
    entry = dict(pending).get(pending_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Pending message not found")

    request_token = _get_request_token(http_request)
    is_creator = False
    if request_token:
        is_creator = state.get("creator_token_hash") == _hash_token(request_token)
    if _server_has_github_token():
        is_creator = True
    if not is_creator:
        player_id = http_request.headers.get("X-MGrill-Player-Id", "").strip()
        if not player_id or entry.get("player_id") != player_id:
            raise HTTPException(status_code=403, detail="Not author of this message")

    del pending[pending_id]
    _mgrill_touch_activity(r, session_id)
    return {"status": "removed"}


@app.post("/mgrill/{session_id}/send")
async def mgrill_send_to_ai(
    session_id: str,
    http_request: Request,
) -> dict[str, Any]:
    """Bundle the pending batch and enqueue as a single AI turn.

    Any participant may press Send — no GitHub token required.  Reads the
    room's ``pending`` Y.Map, appends one transcript entry per author to
    the ``messages`` Y.Array, clears the Y.Map, and pushes the bundled
    text (``[Name]: ...`` joined by blank lines) to the worker's Redis
    ``user_msgs`` queue.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)

    if state.get("status") == "thinking":
        raise HTTPException(status_code=409, detail="AI is already thinking")

    room = await _mgrill_room(session_id)
    if room is None:
        raise HTTPException(status_code=503, detail="Yjs server unavailable")

    pending = _ydoc_map(room.ydoc, "pending")
    entries = [dict(e) for e in dict(pending).values()]
    if not entries:
        raise HTTPException(status_code=400, detail="No pending messages to send")
    entries.sort(key=lambda e: e.get("timestamp", 0))

    messages = _ydoc_array(room.ydoc, "messages")
    for e in entries:
        messages.append(
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": e["content"],
                "type": "message",
                "author_player_id": e.get("player_id"),
                "author_name": e.get("name"),
                "timestamp": e.get("timestamp", time.time()),
            }
        )

    bundled = "\n\n".join(
        f"[{e.get('name') or 'Anonymous'}]: {e['content']}" for e in entries
    )
    r.rpush(
        f"mgrill:{session_id}:user_msgs",
        json.dumps({"content": bundled, "type": "message", "timestamp": time.time()}),
    )
    r.expire(f"mgrill:{session_id}:user_msgs", 3600)

    # Clear pending batch (Y.Map iteration + delete; pycrdt doesn't expose
    # ``.clear()`` directly, so we pop each key).
    for key in list(dict(pending).keys()):
        del pending[key]

    # Auto-resume suspended sessions
    if state.get("status") == "suspended":
        from helping_hands.server.multiplayer_grill import resume_mgrill_session

        resume_mgrill_session.delay(original_session_id=session_id)

    _mgrill_touch_activity(r, session_id)
    return {"status": "sent", "count": len(entries)}


@app.post("/mgrill/{session_id}/vote")
async def mgrill_vote(
    session_id: str,
    req: MGrillVoteRequest,
) -> dict[str, str]:
    """Cast, change, or clear a vote (player_id-keyed, no token required).

    Writes directly into the room's ``votes`` Y.Map so all connected
    participants see the update via their Yjs subscription.  Per-tab dedup:
    the UI surfaces "1 vote per participant" as a hint, but a determined
    user with multiple tabs can double-vote.  Acceptable for v1 — voting is
    advisory, the creator is the sole decider.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    _mgrill_require_state(r, session_id)

    room = await _mgrill_room(session_id)
    if room is None:
        raise HTTPException(status_code=503, detail="Yjs server unavailable")
    votes = _ydoc_map(room.ydoc, "votes")

    if req.vote == "clear":
        if req.player_id in dict(votes):
            del votes[req.player_id]
    else:
        votes[req.player_id] = req.vote

    _mgrill_touch_activity(r, session_id)
    return {"status": _RESPONSE_STATUS_OK}


class MGrillSubmitResponse(BaseModel):
    """Response for a submitted plan (returns the downstream Celery task id)."""

    task_id: str
    session_id: str
    override: bool
    status: str


@app.post("/mgrill/{session_id}/submit", response_model=MGrillSubmitResponse)
async def mgrill_submit(
    session_id: str,
    http_request: Request,
    override: bool = False,
) -> MGrillSubmitResponse:
    """Submit the final plan as a Helping Hands build task (creator-only).

    Reads the most recent ``type == "plan"`` entry from the room's
    ``messages`` Y.Array and the vote tally from the ``votes`` Y.Map.  If
    any ``down`` vote is present and ``override`` is not true, returns
    **409 Conflict** so the UI can prompt for confirmation.  Override is
    recorded in session state (``submit_override_count``) — server-side
    log only, never prepended to the task prompt.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    token = _mgrill_require_token(http_request)
    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)
    _mgrill_require_creator(state, _hash_token(token))

    room = await _mgrill_room(session_id)
    if room is None:
        raise HTTPException(status_code=503, detail="Yjs server unavailable")
    final_plan = _mgrill_final_plan_text(room.ydoc)
    if not final_plan:
        raise HTTPException(status_code=400, detail="No final plan to submit")

    up_count, down_count, total_votes = _mgrill_vote_tally(room.ydoc)

    if down_count > 0 and not override:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "dissent",
                "down_votes": down_count,
                "up_votes": up_count,
                "total_votes": total_votes,
            },
        )

    plan_body = final_plan
    idx = plan_body.find("## FINAL PLAN")
    if idx >= 0:
        plan_body = plan_body[idx + len("## FINAL PLAN") :].lstrip("\n ")

    task = build_feature.delay(
        repo_path=state.get("repo_path", ""),
        prompt=plan_body,
        github_token=token,
        model=state.get("model") or None,
        backend=state.get("backend", "claudecodecli"),
    )

    state["submitted_task_id"] = task.id
    if override and down_count > 0:
        state["submit_override_count"] = int(state.get("submit_override_count", 0)) + 1
        logger.info(
            "Multiplayer grill %s submitted with override (down=%d, up=%d)",
            session_id,
            down_count,
            up_count,
        )
    _mgrill_write_state(r, session_id, state)

    return MGrillSubmitResponse(
        task_id=task.id,
        session_id=session_id,
        override=bool(override and down_count > 0),
        status="submitted",
    )


@app.post("/mgrill/{session_id}/keep-grilling")
async def mgrill_keep_grilling(
    session_id: str, http_request: Request
) -> dict[str, str]:
    """Reset votes and resume grilling (creator-only).

    Clears the room's ``votes`` Y.Map, flips session status back to
    ``active``, and appends a system hint to the transcript.  The FINAL
    PLAN entry itself stays in the transcript history — the AI sees it
    when the next user batch is sent (per the locked plan).
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    token = _mgrill_require_token(http_request)
    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)
    _mgrill_require_creator(state, _hash_token(token))

    room = await _mgrill_room(session_id)
    if room is None:
        raise HTTPException(status_code=503, detail="Yjs server unavailable")

    votes = _ydoc_map(room.ydoc, "votes")
    for key in list(dict(votes).keys()):
        del votes[key]

    _ydoc_append_system_hint(
        room.ydoc, "Keep Grilling — votes reset. Continue the interview."
    )

    state["status"] = "active"
    _mgrill_write_state(r, session_id, state)
    return {"status": _RESPONSE_STATUS_OK}


@app.post("/mgrill/{session_id}/request-plan")
async def mgrill_request_plan(session_id: str, http_request: Request) -> dict[str, str]:
    """Request the AI to produce a final plan (any participant).

    Sends a ``type: "end"`` message to the worker queue, which instructs
    the AI to consolidate the discussion and output ``## FINAL PLAN``.
    Any pending batch entries are bundled and included so the AI sees the
    latest context.  No GitHub token required.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)

    if state.get("status") == "thinking":
        raise HTTPException(status_code=409, detail="AI is already thinking")
    if state.get("status") == "completed":
        raise HTTPException(status_code=409, detail="Session already has a final plan")

    room = await _mgrill_room(session_id)
    if room is None:
        raise HTTPException(status_code=503, detail="Yjs server unavailable")

    # Bundle any pending messages (optional — request-plan works with or
    # without pending entries).
    bundled_parts: list[str] = []
    pending = _ydoc_map(room.ydoc, "pending")
    entries = [dict(e) for e in dict(pending).values()]
    if entries:
        entries.sort(key=lambda e: e.get("timestamp", 0))
        messages = _ydoc_array(room.ydoc, "messages")
        for e in entries:
            messages.append(
                {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": e["content"],
                    "type": "message",
                    "author_player_id": e.get("player_id"),
                    "author_name": e.get("name"),
                    "timestamp": e.get("timestamp", time.time()),
                }
            )
        bundled_parts = [
            f"[{e.get('name') or 'Anonymous'}]: {e['content']}" for e in entries
        ]
        for key in list(dict(pending).keys()):
            del pending[key]

    content = "\n\n".join(bundled_parts) if bundled_parts else ""
    r.rpush(
        f"mgrill:{session_id}:user_msgs",
        json.dumps({"content": content, "type": "end", "timestamp": time.time()}),
    )
    r.expire(f"mgrill:{session_id}:user_msgs", 3600)

    _ydoc_append_system_hint(
        room.ydoc, "Final plan requested — AI is consolidating the discussion."
    )

    # Auto-resume suspended sessions
    if state.get("status") == "suspended":
        from helping_hands.server.multiplayer_grill import resume_mgrill_session

        resume_mgrill_session.delay(original_session_id=session_id)

    _mgrill_touch_activity(r, session_id)
    return {"status": "requested"}


@app.post("/mgrill/{session_id}/claim-creator")
async def mgrill_claim_creator(
    session_id: str,
    req: MGrillHeartbeatRequest,
    http_request: Request,
) -> dict[str, Any]:
    """Claim the creator role when the current creator has been absent.

    Gated on ``now - creator_last_seen_ts > _MGRILL_CREATOR_HANDOFF_S`` and a
    valid ``X-GitHub-Token``.  Updates ``creator_token_hash``,
    ``creator_name``, and ``creator_player_id`` in Redis state, and
    broadcasts a system hint into the transcript Y.Array.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    token = _mgrill_require_token(http_request)
    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)

    age = time.time() - float(state.get("creator_last_seen_ts", 0))
    current_hash = state.get("creator_token_hash")
    token_hash = _hash_token(token)

    if current_hash == token_hash:
        # Already creator — this is effectively a heartbeat.
        state["creator_last_seen_ts"] = time.time()
        _mgrill_write_state(r, session_id, state)
        return {
            "status": "already_creator",
            "creator_last_seen_ts": state["creator_last_seen_ts"],
        }

    if age < _MGRILL_CREATOR_HANDOFF_S:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "creator still active",
                "seconds_remaining": int(_MGRILL_CREATOR_HANDOFF_S - age),
            },
        )

    prev_name = state.get("creator_name", "previous creator")
    new_name = (
        http_request.headers.get("X-MGrill-Player-Name", "").strip()[
            :_MGRILL_MAX_NAME_LENGTH
        ]
        or prev_name
    )
    state["creator_token_hash"] = token_hash
    state["creator_name"] = new_name
    state["creator_player_id"] = req.player_id
    state["creator_last_seen_ts"] = time.time()
    _mgrill_write_state(r, session_id, state)

    room = await _mgrill_room(session_id)
    if room is not None:
        _ydoc_append_system_hint(
            room.ydoc,
            f"{new_name} claimed the creator role (previous: {prev_name}).",
        )

    return {"status": "claimed", "creator_name": new_name}


@app.post("/mgrill/{session_id}/heartbeat")
def mgrill_heartbeat(
    session_id: str,
    req: MGrillHeartbeatRequest,
    http_request: Request,
) -> dict[str, Any]:
    """Refresh ``creator_last_seen_ts`` (creator-only, idempotent).

    Called periodically by the creator's frontend (~every 20s) while viewing
    the session to prevent handoff timeout.
    """
    from fastapi import HTTPException

    if not _grill_enabled():
        raise HTTPException(status_code=404, detail="Grill Me feature is disabled")

    token = _mgrill_require_token(http_request)
    session_id = _validate_path_param(session_id, "session_id")
    r = _mgrill_redis()
    state = _mgrill_require_state(r, session_id)
    _mgrill_require_creator(state, _hash_token(token))

    state["creator_last_seen_ts"] = time.time()
    if req.player_id:
        state["creator_player_id"] = req.player_id
    _mgrill_write_state(r, session_id, state)
    return {
        "status": _RESPONSE_STATUS_OK,
        "creator_last_seen_ts": state["creator_last_seen_ts"],
    }
