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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib import error as urllib_error, request as urllib_request
from urllib.parse import urlencode

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, ValidationError, field_validator

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
from helping_hands.lib.meta import skills as meta_skills
from helping_hands.lib.meta.tools import registry as meta_tools
from helping_hands.lib.validation import (
    install_hint,
    parse_comma_list,
    require_non_empty_string,
)
from helping_hands.server.celery_app import build_feature, celery_app
from helping_hands.server.constants import (
    ANTHROPIC_BETA_HEADER as _ANTHROPIC_BETA_HEADER,
    ANTHROPIC_USAGE_URL as _ANTHROPIC_USAGE_URL,
    DEFAULT_BACKEND as _DEFAULT_BACKEND,
    DEFAULT_CI_WAIT_MINUTES as _DEFAULT_CI_WAIT_MINUTES,
    DEFAULT_MAX_ITERATIONS as _DEFAULT_MAX_ITERATIONS,
    DEFAULT_REDIS_URL as _DEFAULT_REDIS_URL,
    JWT_TOKEN_PREFIX as _JWT_TOKEN_PREFIX,
    KEYCHAIN_ACCESS_TOKEN_KEY as _KEYCHAIN_ACCESS_TOKEN_KEY,
    KEYCHAIN_OAUTH_KEY as _KEYCHAIN_OAUTH_KEY,
    KEYCHAIN_SERVICE_NAME as _KEYCHAIN_SERVICE_NAME,
    KEYCHAIN_TIMEOUT_S as _KEYCHAIN_TIMEOUT_S,
    MAX_CI_WAIT_MINUTES as _MAX_CI_WAIT_MINUTES,
    MAX_GITHUB_TOKEN_LENGTH as _MAX_GITHUB_TOKEN_LENGTH,
    MAX_ITERATIONS_UPPER_BOUND as _MAX_ITERATIONS_UPPER_BOUND,
    MAX_MODEL_LENGTH as _MAX_MODEL_LENGTH,
    MAX_PROMPT_LENGTH as _MAX_PROMPT_LENGTH,
    MAX_REFERENCE_REPOS as _MAX_REFERENCE_REPOS,
    MAX_REPO_PATH_LENGTH as _MAX_REPO_PATH_LENGTH,
    MIN_CI_WAIT_MINUTES as _MIN_CI_WAIT_MINUTES,
    RESPONSE_STATUS_ERROR as _RESPONSE_STATUS_ERROR,
    RESPONSE_STATUS_NA as _RESPONSE_STATUS_NA,
    RESPONSE_STATUS_OK as _RESPONSE_STATUS_OK,
    USAGE_API_TIMEOUT_S as _USAGE_API_TIMEOUT_S,
    USAGE_CACHE_TTL_S as _USAGE_CACHE_TTL_S,
    USAGE_USER_AGENT as _USAGE_USER_AGENT,
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

if TYPE_CHECKING:
    from helping_hands.server.schedules import ScheduleManager

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
    "WorkerCapacityResponse",
    "app",
]

# Lazy import for optional schedule dependencies
_schedule_manager: ScheduleManager | None = None

# Maximum number of tool or skill entries in a single request.
_MAX_TOOL_SKILL_ITEMS = 50

# --- Health-check timeout constants (seconds) ---
_REDIS_HEALTH_TIMEOUT_S = 2
_DB_HEALTH_TIMEOUT_S = 3
_CELERY_HEALTH_TIMEOUT_S = 2.0
_CELERY_INSPECT_TIMEOUT_S = 1.0

# --- Preview truncation limits for error/debug messages ---
_HTTP_ERROR_BODY_PREVIEW_LENGTH = 200
_USAGE_DATA_PREVIEW_LENGTH = 300

# --- Token redaction parameters ---
_REDACT_TOKEN_PREFIX_LEN = 4
"""Number of leading characters to keep when redacting a token."""

_REDACT_TOKEN_SUFFIX_LEN = 4
"""Number of trailing characters to keep when redacting a token."""

_REDACT_TOKEN_MIN_PARTIAL_LEN = 12
"""Minimum token length for partial redaction (show prefix/suffix).

Tokens at or below this length are fully masked to ``"***"`` to avoid
leaking a disproportionate fraction of the secret.  At the default values
(prefix=4, suffix=4), a 12-character token would expose 8 of 12 characters
(67%), which is too much for meaningful redaction.
"""

# --- Schedule endpoint constants ---
_SCHEDULE_NOT_FOUND_DETAIL = "Schedule not found"
"""HTTP 404 detail message for missing schedule resources."""


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage server lifecycle — start/stop the Yjs WebSocket server."""
    await start_yjs_server()
    yield
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


class _ToolSkillValidatorMixin(BaseModel):
    """Shared coercion and validation for tools/skills list fields."""

    tools: list[str] = Field(default_factory=list, max_length=_MAX_TOOL_SKILL_ITEMS)
    skills: list[str] = Field(default_factory=list, max_length=_MAX_TOOL_SKILL_ITEMS)

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

    @field_validator("skills", mode="before")
    @classmethod
    def _coerce_skills(
        cls, value: str | list[str] | tuple[str, ...] | None
    ) -> list[str]:
        """Normalize raw skill input into a list of skill names.

        Accepts comma-separated strings, sequences, or ``None`` and
        delegates to ``normalize_skill_selection``.

        Args:
            value: Raw skill selection from the request body.

        Returns:
            A normalized list of skill name strings.
        """
        normalized = meta_skills.normalize_skill_selection(value)
        return list(normalized)

    @field_validator("skills")
    @classmethod
    def _validate_skills(cls, value: list[str]) -> list[str]:
        """Validate that all skill names are recognized.

        Args:
            value: List of skill names to validate.

        Returns:
            The unchanged list if all names are valid.

        Raises:
            ValueError: If any name is not a known skill.
        """
        meta_skills.validate_skill_names(tuple(value))
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


class BuildRequest(_ToolSkillValidatorMixin):
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
    fix_ci: bool = False
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


class ServerConfig(BaseModel):
    """Runtime configuration exposed to the frontend."""

    in_docker: bool
    native_auth_default: bool
    enabled_backends: list[str]
    claude_native_cli_auth: bool


# --- Scheduled Task Models ---


class ScheduleRequest(_ToolSkillValidatorMixin):
    """Request body for creating/updating a scheduled task."""

    name: str = Field(min_length=1, max_length=100)
    cron_expression: str = Field(
        min_length=1,
        max_length=100,
        description="Cron expression (e.g., '0 0 * * *') or preset name",
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
    ci_check_wait_minutes: float = Field(
        default=_DEFAULT_CI_WAIT_MINUTES,
        ge=_MIN_CI_WAIT_MINUTES,
        le=_MAX_CI_WAIT_MINUTES,
    )
    github_token: str | None = Field(default=None, max_length=_MAX_GITHUB_TOKEN_LENGTH)
    reference_repos: list[str] = Field(
        default_factory=list, max_length=_MAX_REFERENCE_REPOS
    )
    enabled: bool = True


class ScheduleResponse(BaseModel):
    """Response for a scheduled task."""

    schedule_id: str
    name: str
    cron_expression: str
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
    ci_check_wait_minutes: float = _DEFAULT_CI_WAIT_MINUTES
    github_token: str | None = None
    reference_repos: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
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


class CronPresetsResponse(BaseModel):
    """Response for listing available cron presets."""

    presets: dict[str, str]


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


def _get_claude_oauth_token() -> str | None:
    """Read the Claude Code OAuth token from the macOS Keychain."""
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                _KEYCHAIN_SERVICE_NAME,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=_KEYCHAIN_TIMEOUT_S,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        raw = result.stdout.strip()
        # The keychain value is JSON — extract the OAuth access token
        try:
            creds = json.loads(raw)
            return creds.get(_KEYCHAIN_OAUTH_KEY, {}).get(_KEYCHAIN_ACCESS_TOKEN_KEY)
        except (json.JSONDecodeError, AttributeError):
            # Maybe stored as plain token
            return raw if raw.startswith(_JWT_TOKEN_PREFIX) else None
    except (subprocess.SubprocessError, OSError):
        logger.debug("Failed to read Claude OAuth token from Keychain", exc_info=True)
        return None


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
            error="Could not read Claude Code credentials from Keychain",
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
_DEFAULT_WORKER_CAPACITY = 8


_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _load_ui_template() -> str:
    """Load the main UI HTML template from disk.

    The template is read once at module import time and cached in
    the module-level ``_UI_HTML`` variable.  Contains a
    ``__DEFAULT_SMOKE_TEST_PROMPT__`` placeholder that is replaced
    at request time by the ``home()`` endpoint.
    """
    template_path = _TEMPLATES_DIR / "ui.html"
    return template_path.read_text(encoding="utf-8")


_UI_HTML = _load_ui_template()


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
    return ServerConfig(
        in_docker=in_docker,
        native_auth_default=not in_docker,
        enabled_backends=get_enabled_backends(),
        claude_native_cli_auth=claude_native,
    )


def _enqueue_build_task(req: BuildRequest) -> BuildResponse:
    """Enqueue a build task and return a consistent response shape."""
    task = build_feature.delay(
        repo_path=req.repo_path,
        prompt=req.prompt,
        pr_number=req.pr_number,
        backend=req.backend,
        model=req.model,
        max_iterations=req.max_iterations,
        no_pr=req.no_pr,
        enable_execution=req.enable_execution,
        enable_web=req.enable_web,
        use_native_cli_auth=req.use_native_cli_auth,
        tools=req.tools,
        skills=req.skills,
        fix_ci=req.fix_ci,
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
        A ``TaskStatus`` with the current state and normalised result.
    """
    result = build_feature.AsyncResult(task_id)
    raw_result = result.result if result.ready() else result.info
    normalized_result = normalize_task_result(result.status, raw_result)
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


def _fetch_flower_current_tasks() -> list[dict[str, Any]]:
    """Fetch currently active tasks from Flower API when configured."""
    base_url = _flower_api_base_url()
    if not base_url:
        return []

    url = f"{base_url}/api/tasks"
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
        if status not in _CURRENT_TASK_STATES:
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
    ci_check_wait_minutes: float = _DEFAULT_CI_WAIT_MINUTES,
    pr_number: int | None = None,
    tools: str | None = None,
    skills: str | None = None,
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
    if ci_check_wait_minutes != _DEFAULT_CI_WAIT_MINUTES:
        query["ci_check_wait_minutes"] = str(ci_check_wait_minutes)
    if pr_number is not None:
        query["pr_number"] = str(pr_number)
    if tools and tools.strip():
        query["tools"] = tools
    if skills and skills.strip():
        query["skills"] = skills
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
    tools: str | None = Form(None),
    skills: str | None = Form(None),
    fix_ci: bool = Form(False),
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
            ci_check_wait_minutes=ci_check_wait_minutes,
            pr_number=pr_number,
            tools=tools,
            skills=skills,
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
            fix_ci=fix_ci,
            ci_check_wait_minutes=ci_check_wait_minutes,
            tools=list(meta_tools.normalize_tool_selection(tools)),
            skills=list(meta_skills.normalize_skill_selection(skills)),
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
            ci_check_wait_minutes=ci_check_wait_minutes,
            pr_number=pr_number,
            tools=tools,
            skills=skills,
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
    if req.pr_number is not None:
        query["pr_number"] = str(req.pr_number)
    if req.tools:
        query["tools"] = ",".join(req.tools)
    if req.skills:
        query["skills"] = ",".join(req.skills)
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


@app.get("/tasks/current", response_model=CurrentTasksResponse)
def get_current_tasks() -> CurrentTasksResponse:
    """List currently active/queued task UUIDs discovered by Flower/Celery."""
    return _collect_current_tasks()


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    """Check the status of an enqueued task."""
    task_id = _validate_path_param(task_id, "task_id")
    return _build_task_status(task_id)


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


def _redact_token(token: str | None) -> str | None:
    """Redact a token, keeping only the first and last few characters.

    Tokens at or below :data:`_REDACT_TOKEN_MIN_PARTIAL_LEN` are fully
    masked to avoid leaking a meaningful portion of the secret.

    Args:
        token: Raw token string, or ``None``.

    Returns:
        Redacted string with prefix/suffix visible, ``"***"`` for short
        tokens, or ``None`` when *token* is falsy.
    """
    if not token:
        return None
    if len(token) <= _REDACT_TOKEN_MIN_PARTIAL_LEN:
        return "***"
    return f"{token[:_REDACT_TOKEN_PREFIX_LEN]}***{token[-_REDACT_TOKEN_SUFFIX_LEN:]}"


def _schedule_to_response(task) -> ScheduleResponse:
    """Convert a ScheduledTask to a ScheduleResponse.

    Args:
        task: A ``ScheduledTask`` instance to convert.

    Returns:
        A ``ScheduleResponse`` with computed ``next_run`` and redacted token.
    """
    from helping_hands.server.schedules import next_run_time

    next_run = None
    if task.enabled:
        try:
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
        cron_expression=task.cron_expression,
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
        ci_check_wait_minutes=task.ci_check_wait_minutes,
        github_token=_redact_token(task.github_token),
        reference_repos=task.reference_repos,
        tools=task.tools,
        skills=task.skills,
        enabled=task.enabled,
        created_at=task.created_at,
        last_run_at=task.last_run_at,
        last_run_task_id=task.last_run_task_id,
        run_count=task.run_count,
        next_run_at=next_run,
    )


@app.get("/schedules/presets", response_model=CronPresetsResponse)
def get_cron_presets() -> CronPresetsResponse:
    """Get available cron expression presets."""
    from helping_hands.server.schedules import CRON_PRESETS

    return CronPresetsResponse(presets=CRON_PRESETS)


@app.get("/schedules", response_model=ScheduleListResponse)
def list_schedules() -> ScheduleListResponse:
    """List all scheduled tasks."""
    manager = _get_schedule_manager()
    tasks = manager.list_schedules()
    return ScheduleListResponse(
        schedules=[_schedule_to_response(t) for t in tasks],
        total=len(tasks),
    )


@app.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(request: ScheduleRequest) -> ScheduleResponse:
    """Create a new scheduled task."""
    from fastapi import HTTPException

    from helping_hands.server.schedules import ScheduledTask, generate_schedule_id

    manager = _get_schedule_manager()

    task = ScheduledTask(
        schedule_id=generate_schedule_id(),
        name=request.name,
        cron_expression=request.cron_expression,
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
        ci_check_wait_minutes=request.ci_check_wait_minutes,
        github_token=request.github_token,
        reference_repos=request.reference_repos,
        tools=request.tools,
        skills=request.skills,
        enabled=request.enabled,
    )

    try:
        created = manager.create_schedule(task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _schedule_to_response(created)


@app.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: str) -> ScheduleResponse:
    """Get a scheduled task by ID."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.get_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    return _schedule_to_response(task)


@app.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: str, request: ScheduleRequest) -> ScheduleResponse:
    """Update a scheduled task."""
    from fastapi import HTTPException

    from helping_hands.server.schedules import ScheduledTask

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()

    # If the token looks redacted (contains ***), preserve the existing one.
    github_token = request.github_token
    if github_token and "***" in github_token:
        existing = manager.get_schedule(schedule_id)
        github_token = existing.github_token if existing else None

    task = ScheduledTask(
        schedule_id=schedule_id,
        name=request.name,
        cron_expression=request.cron_expression,
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
        ci_check_wait_minutes=request.ci_check_wait_minutes,
        github_token=github_token,
        reference_repos=request.reference_repos,
        tools=request.tools,
        skills=request.skills,
        enabled=request.enabled,
    )

    try:
        updated = manager.update_schedule(task)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _schedule_to_response(updated)


@app.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str) -> None:
    """Delete a scheduled task."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    if not manager.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)


@app.post("/schedules/{schedule_id}/enable", response_model=ScheduleResponse)
def enable_schedule(schedule_id: str) -> ScheduleResponse:
    """Enable a scheduled task."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.enable_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    return _schedule_to_response(task)


@app.post("/schedules/{schedule_id}/disable", response_model=ScheduleResponse)
def disable_schedule(schedule_id: str) -> ScheduleResponse:
    """Disable a scheduled task."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task = manager.disable_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)
    return _schedule_to_response(task)


@app.post("/schedules/{schedule_id}/trigger", response_model=ScheduleTriggerResponse)
def trigger_schedule(schedule_id: str) -> ScheduleTriggerResponse:
    """Manually trigger a scheduled task to run immediately."""
    from fastapi import HTTPException

    schedule_id = _validate_path_param(schedule_id, "schedule_id")
    manager = _get_schedule_manager()
    task_id = manager.trigger_now(schedule_id)
    if task_id is None:
        raise HTTPException(status_code=404, detail=_SCHEDULE_NOT_FOUND_DETAIL)

    return ScheduleTriggerResponse(
        schedule_id=schedule_id,
        task_id=task_id,
        message="Schedule triggered successfully",
    )
