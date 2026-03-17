"""Shared constants for the server package (app + celery worker).

Constants that are used by both ``app.py`` and ``celery_app.py`` live
here to avoid duplication and ensure they stay in sync.
"""

from __future__ import annotations

from typing import Final, Literal

from helping_hands.lib.hands.v1.hand.factory import (
    BACKEND_CLAUDECODECLI as _BACKEND_CLAUDECODECLI,
)
from helping_hands.lib.hands.v1.hand.iterative import (
    DEFAULT_MAX_ITERATIONS as DEFAULT_MAX_ITERATIONS,
)

__all__ = [
    "ANTHROPIC_BETA_HEADER",
    "ANTHROPIC_USAGE_URL",
    "DEFAULT_BACKEND",
    "DEFAULT_CI_WAIT_MINUTES",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_REDIS_URL",
    "JWT_TOKEN_PREFIX",
    "KEYCHAIN_ACCESS_TOKEN_KEY",
    "KEYCHAIN_OAUTH_KEY",
    "KEYCHAIN_SERVICE_NAME",
    "KEYCHAIN_TIMEOUT_S",
    "MAX_CI_WAIT_MINUTES",
    "MAX_GITHUB_TOKEN_LENGTH",
    "MAX_ITERATIONS_UPPER_BOUND",
    "MAX_MODEL_LENGTH",
    "MAX_PROMPT_LENGTH",
    "MAX_REFERENCE_REPOS",
    "MAX_REPO_PATH_LENGTH",
    "MIN_CI_WAIT_MINUTES",
    "REDBEAT_KEY_PREFIX",
    "REDBEAT_SCHEDULE_ENTRY_PREFIX",
    "REDBEAT_USAGE_ENTRY_NAME",
    "RESPONSE_STATUS_ERROR",
    "RESPONSE_STATUS_NA",
    "RESPONSE_STATUS_OK",
    "TASK_NAME_LOG_USAGE",
    "TASK_NAME_SCHEDULED_BUILD",
    "USAGE_API_TIMEOUT_S",
    "USAGE_CACHE_TTL_S",
    "USAGE_USER_AGENT",
]

# --- Anthropic usage API ---------------------------------------------------

ANTHROPIC_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
"""Endpoint for querying Claude usage quotas via OAuth."""

ANTHROPIC_BETA_HEADER = "oauth-2025-04-20"
"""``anthropic-beta`` header value required by the usage endpoint."""

USAGE_USER_AGENT = "claude-code/2.0.32"
"""User-Agent string sent with Anthropic usage API requests."""

USAGE_API_TIMEOUT_S = 10
"""Timeout in seconds for Anthropic usage API HTTP requests."""

# --- macOS Keychain --------------------------------------------------------

KEYCHAIN_SERVICE_NAME = "Claude Code-credentials"
"""macOS Keychain service name for Claude Code OAuth credentials."""

KEYCHAIN_OAUTH_KEY = "claudeAiOauth"
"""Top-level JSON key in the Keychain credential payload."""

KEYCHAIN_ACCESS_TOKEN_KEY = "accessToken"
"""Nested JSON key for the OAuth access token."""

KEYCHAIN_TIMEOUT_S = 5
"""Timeout in seconds for macOS Keychain subprocess calls."""

# --- Token heuristics ------------------------------------------------------

JWT_TOKEN_PREFIX = "ey"
"""Base64-encoded JWT header prefix used for raw token heuristic detection."""

# --- Redis default URL --------------------------------------------------------

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
"""Fallback Redis URL used when no broker/backend URL is configured."""

# --- Build / schedule defaults ------------------------------------------------

DEFAULT_BACKEND: Final[Literal["claudecodecli"]] = _BACKEND_CLAUDECODECLI
"""Default hand backend slug for build and schedule requests."""

DEFAULT_CI_WAIT_MINUTES = 3.0
"""Default minutes to wait between CI check polls."""

MAX_REFERENCE_REPOS = 10
"""Maximum number of reference repos allowed in a single request."""

# --- Usage cache --------------------------------------------------------------

USAGE_CACHE_TTL_S = 300
"""Seconds to cache Claude usage API responses (5 minutes)."""

# --- Field validation bounds --------------------------------------------------

MAX_ITERATIONS_UPPER_BOUND = 100
"""Upper bound for ``max_iterations`` in build/schedule requests."""

MIN_CI_WAIT_MINUTES = 0.5
"""Minimum ``ci_check_wait_minutes`` for build/schedule requests."""

MAX_CI_WAIT_MINUTES = 30.0
"""Maximum ``ci_check_wait_minutes`` for build/schedule requests."""

MAX_REPO_PATH_LENGTH = 500
"""Maximum character length for ``repo_path`` fields."""

MAX_PROMPT_LENGTH = 50_000
"""Maximum character length for ``prompt`` fields."""

MAX_MODEL_LENGTH = 200
"""Maximum character length for ``model`` fields."""

MAX_GITHUB_TOKEN_LENGTH = 500
"""Maximum character length for ``github_token`` fields."""

# --- RedBeat scheduler ---------------------------------------------------------

REDBEAT_KEY_PREFIX = "redbeat:"
"""Key prefix used by RedBeat for scheduler entries in Redis."""

REDBEAT_SCHEDULE_ENTRY_PREFIX = "helping_hands:scheduled:"
"""Name prefix for RedBeat entries backing cron-scheduled build tasks."""

REDBEAT_USAGE_ENTRY_NAME = "helping_hands:usage-logger"
"""RedBeat entry name for the hourly Claude usage logging schedule."""

# --- Celery task names ---------------------------------------------------------

TASK_NAME_SCHEDULED_BUILD = "helping_hands.scheduled_build"
"""Celery task name for scheduled build executions."""

TASK_NAME_LOG_USAGE = "helping_hands.log_claude_usage"
"""Celery task name for the periodic Claude usage logger."""

# --- Response status values ---------------------------------------------------

RESPONSE_STATUS_OK = "ok"
"""Status value for successful task/health-check responses."""

RESPONSE_STATUS_ERROR = "error"
"""Status value for failed task/health-check responses."""

RESPONSE_STATUS_NA = "na"
"""Status value when a service is not configured or unavailable."""
