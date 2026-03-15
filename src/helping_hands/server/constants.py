"""Shared constants for the server package (app + celery worker).

Constants that are used by both ``app.py`` and ``celery_app.py`` live
here to avoid duplication and ensure they stay in sync.
"""

from __future__ import annotations

__all__ = [
    "ANTHROPIC_BETA_HEADER",
    "ANTHROPIC_USAGE_URL",
    "JWT_TOKEN_PREFIX",
    "KEYCHAIN_ACCESS_TOKEN_KEY",
    "KEYCHAIN_OAUTH_KEY",
    "KEYCHAIN_SERVICE_NAME",
    "SUPPORTED_BACKENDS",
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

# --- Backend registry -------------------------------------------------------

SUPPORTED_BACKENDS: frozenset[str] = frozenset(
    {
        "e2e",
        "basic-langgraph",
        "basic-atomic",
        "basic-agent",
        "codexcli",
        "claudecodecli",
        "docker-sandbox-claude",
        "goose",
        "geminicli",
        "opencodecli",
    }
)
"""Canonical set of backend names accepted by build_feature endpoints."""
