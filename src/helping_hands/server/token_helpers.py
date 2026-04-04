"""Pure helper functions for token redaction and Claude credential reading.

These functions have **no** FastAPI, Celery, or Redis dependency and can be
imported and tested in any environment.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from helping_hands.server.constants import (
    JWT_TOKEN_PREFIX,
    KEYCHAIN_ACCESS_TOKEN_KEY,
    KEYCHAIN_OAUTH_KEY,
    KEYCHAIN_SERVICE_NAME,
    KEYCHAIN_TIMEOUT_S,
)

logger = logging.getLogger(__name__)

__all__ = [
    "get_claude_oauth_token",
    "read_claude_credentials_file",
    "redact_token",
]

# --- Token redaction parameters -----------------------------------------------

REDACT_TOKEN_PREFIX_LEN = 4
"""Number of leading characters to keep when redacting a token."""

REDACT_TOKEN_SUFFIX_LEN = 4
"""Number of trailing characters to keep when redacting a token."""

REDACT_TOKEN_MIN_PARTIAL_LEN = 12
"""Minimum token length for partial redaction (show prefix/suffix).

Tokens at or below this length are fully masked to ``"***"`` to avoid
leaking a meaningful portion of the secret.
"""


def redact_token(token: str | None) -> str | None:
    """Redact a token, keeping only the first and last few characters.

    Tokens at or below :data:`REDACT_TOKEN_MIN_PARTIAL_LEN` are fully
    masked to avoid leaking a meaningful portion of the secret.

    Args:
        token: Raw token string, or ``None``.

    Returns:
        Redacted string with prefix/suffix visible, ``"***"`` for short
        tokens, or ``None`` when *token* is falsy.
    """
    if not token:
        return None
    if len(token) <= REDACT_TOKEN_MIN_PARTIAL_LEN:
        return "***"
    return f"{token[:REDACT_TOKEN_PREFIX_LEN]}***{token[-REDACT_TOKEN_SUFFIX_LEN:]}"


def read_claude_credentials_file() -> str | None:
    """Read the OAuth access token from ``~/.claude/.credentials.json``.

    Returns:
        The access token string, or ``None`` if the file is missing,
        unreadable, or does not contain the expected JSON structure.
    """
    creds_path = Path.home() / ".claude" / ".credentials.json"
    try:
        if not creds_path.is_file():
            return None
        creds = json.loads(creds_path.read_text(encoding="utf-8"))
        return creds.get(KEYCHAIN_OAUTH_KEY, {}).get(KEYCHAIN_ACCESS_TOKEN_KEY)
    except (json.JSONDecodeError, AttributeError, OSError):
        logger.debug("Failed to read Claude credentials file", exc_info=True)
        return None


def get_claude_oauth_token() -> str | None:
    """Read the Claude Code OAuth token.

    Tries the CLI credentials file first (``~/.claude/.credentials.json``),
    then falls back to the macOS Keychain for backwards-compatibility.

    Returns:
        The OAuth access token string, or ``None`` if no credential source
        yields a valid token.
    """
    # 1) CLI credentials file (works on all platforms)
    token = read_claude_credentials_file()
    if token:
        return token

    # 2) macOS Keychain fallback
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE_NAME,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=KEYCHAIN_TIMEOUT_S,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        raw = result.stdout.strip()
        try:
            creds = json.loads(raw)
            return creds.get(KEYCHAIN_OAUTH_KEY, {}).get(KEYCHAIN_ACCESS_TOKEN_KEY)
        except (json.JSONDecodeError, AttributeError):
            return raw if raw.startswith(JWT_TOKEN_PREFIX) else None
    except (subprocess.SubprocessError, OSError):
        logger.debug("Failed to read Claude OAuth token from Keychain", exc_info=True)
        return None
