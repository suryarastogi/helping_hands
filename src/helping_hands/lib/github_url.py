"""Shared GitHub URL helpers used by CLI, server, and library code.

Centralises clone-URL construction, credential redaction, repo-spec
validation, and non-interactive git environment setup so that every
call-site shares the same logic.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from helping_hands.lib.validation import require_non_empty_string

__all__ = [
    "DEFAULT_CLONE_ERROR_MSG",
    "ENV_GCM_INTERACTIVE",
    "ENV_GIT_TERMINAL_PROMPT",
    "GITHUB_HOSTNAME",
    "GITHUB_TOKEN_USER",
    "GIT_CLONE_TIMEOUT_S",
    "REPO_SPEC_PATTERN",
    "build_clone_url",
    "invalid_repo_msg",
    "noninteractive_env",
    "redact_credentials",
    "repo_tmp_dir",
    "resolve_github_token",
    "validate_repo_spec",
]

DEFAULT_CLONE_ERROR_MSG = "unknown git clone error"
"""Fallback error message when ``git clone`` fails with empty stderr."""

GITHUB_TOKEN_USER = "x-access-token"
"""Username used in token-authenticated GitHub HTTPS clone URLs."""

GITHUB_HOSTNAME = "github.com"
"""Hostname matched when extracting ``owner/repo`` from git remote URLs."""

ENV_GIT_TERMINAL_PROMPT = "GIT_TERMINAL_PROMPT"
"""Env var that git checks before opening a terminal prompt (``0`` = suppress)."""

ENV_GCM_INTERACTIVE = "GCM_INTERACTIVE"
"""Env var that Git Credential Manager checks (``never`` = suppress)."""

GIT_CLONE_TIMEOUT_S = 120
"""Timeout in seconds for git clone subprocess calls."""

REPO_SPEC_PATTERN = r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
"""Regex matching a GitHub ``owner/repo`` specifier (no anchors)."""

_ENV_GITHUB_TOKEN = "GITHUB_TOKEN"
"""Primary env var for GitHub personal/fine-grained access tokens."""

_ENV_GH_TOKEN = "GH_TOKEN"
"""Fallback env var for GitHub tokens (used by ``gh`` CLI)."""

_ENV_REPO_TMP = "HELPING_HANDS_REPO_TMP"
"""Env var for overriding the temp directory used for repo clones."""


def invalid_repo_msg(repo: str) -> str:
    """Format a user-facing error for an unrecognised repo argument.

    Args:
        repo: The invalid repository argument.

    Returns:
        An error message string.
    """
    return f"{repo} is not a directory or owner/repo reference"


def resolve_github_token(token: str = "") -> str:
    """Resolve a GitHub token from an explicit value or environment variables.

    Checks the given *token* first, then ``GITHUB_TOKEN``, then ``GH_TOKEN``.

    Args:
        token: Explicit token value (takes priority over env vars).

    Returns:
        The resolved token string, or ``""`` if none is available.
    """
    return (
        (token or "").strip()
        or os.environ.get(_ENV_GITHUB_TOKEN, "").strip()
        or os.environ.get(_ENV_GH_TOKEN, "").strip()
    )


def repo_tmp_dir() -> Path | None:
    """Return the directory to use for temporary repo clones.

    Reads ``HELPING_HANDS_REPO_TMP``; returns ``None`` to let callers
    fall back to the OS default temp dir.  When set, the directory is
    created if it does not already exist.
    """
    d = os.environ.get(_ENV_REPO_TMP, "").strip()
    if d:
        p = Path(d).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return None


def validate_repo_spec(repo: str) -> None:
    """Validate that *repo* looks like ``owner/repo`` before embedding in a URL.

    Args:
        repo: The repository specification to validate.

    Raises:
        ValueError: If *repo* is empty or not in ``owner/repo`` format.
    """
    require_non_empty_string(repo, "repo spec")
    parts = repo.strip().split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"repo spec must be in 'owner/repo' format, got {repo!r}")


def build_clone_url(repo: str, token: str | None = None) -> str:
    """Build the HTTPS clone URL for a GitHub repository.

    Uses token-authenticated URL when a token is provided or available
    in ``GITHUB_TOKEN`` / ``GH_TOKEN`` environment variables.

    Args:
        repo: GitHub repository in ``owner/repo`` format.
        token: Optional explicit GitHub token (overrides env vars).

    Returns:
        The HTTPS clone URL string.

    Raises:
        ValueError: If *repo* is not in valid ``owner/repo`` format.
    """
    validate_repo_spec(repo)
    effective_token = resolve_github_token(token or "")
    if effective_token:
        return (
            f"https://{GITHUB_TOKEN_USER}:{effective_token}"
            f"@{GITHUB_HOSTNAME}/{repo}.git"
        )
    return f"https://{GITHUB_HOSTNAME}/{repo}.git"


def redact_credentials(text: str) -> str:
    """Replace GitHub token values in URLs with ``***``.

    Args:
        text: Text that may contain token-authenticated GitHub URLs.

    Returns:
        The text with credentials replaced by ``***``.
    """
    return re.sub(
        rf"(https://{re.escape(GITHUB_TOKEN_USER)}:)[^@]+(@{re.escape(GITHUB_HOSTNAME)}/)",
        r"\1***\2",
        text,
    )


def noninteractive_env() -> dict[str, str]:
    """Build an environment dict that disables interactive git prompts.

    Sets ``GIT_TERMINAL_PROMPT=0`` and ``GCM_INTERACTIVE=never`` to prevent
    git and Git Credential Manager from blocking on user input during
    automated clone operations.

    Returns:
        A copy of the current environment with non-interactive git settings.
    """
    env = os.environ.copy()
    env[ENV_GIT_TERMINAL_PROMPT] = "0"
    env[ENV_GCM_INTERACTIVE] = "never"
    return env
