"""Shared constants for the server package (app + celery worker).

Constants that are used by both ``app.py`` and ``celery_app.py`` live
here to avoid duplication and ensure they stay in sync.
"""

from __future__ import annotations

__all__ = [
    "ANTHROPIC_BETA_HEADER",
    "ANTHROPIC_USAGE_URL",
    "DEFAULT_BACKEND",
    "DEFAULT_CI_WAIT_MINUTES",
    "DEFAULT_MAX_ITERATIONS",
    "JWT_TOKEN_PREFIX",
    "KEYCHAIN_ACCESS_TOKEN_KEY",
    "KEYCHAIN_OAUTH_KEY",
    "KEYCHAIN_SERVICE_NAME",
    "MAX_CI_WAIT_MINUTES",
    "MAX_GITHUB_TOKEN_LENGTH",
    "MAX_ITERATIONS_UPPER_BOUND",
    "MAX_MODEL_LENGTH",
    "MAX_PROMPT_LENGTH",
    "MAX_REFERENCE_REPOS",
    "MAX_REPO_PATH_LENGTH",
    "MIN_CI_WAIT_MINUTES",
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

# --- macOS Keychain --------------------------------------------------------

KEYCHAIN_SERVICE_NAME = "Claude Code-credentials"
"""macOS Keychain service name for Claude Code OAuth credentials."""

KEYCHAIN_OAUTH_KEY = "claudeAiOauth"
"""Top-level JSON key in the Keychain credential payload."""

KEYCHAIN_ACCESS_TOKEN_KEY = "accessToken"
"""Nested JSON key for the OAuth access token."""

# --- Token heuristics ------------------------------------------------------

JWT_TOKEN_PREFIX = "ey"
"""Base64-encoded JWT header prefix used for raw token heuristic detection."""

# --- Build / schedule defaults ------------------------------------------------

DEFAULT_BACKEND = "claudecodecli"
"""Default hand backend slug for build and schedule requests."""

DEFAULT_MAX_ITERATIONS = 6
"""Default maximum iterative hand loop iterations."""

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
