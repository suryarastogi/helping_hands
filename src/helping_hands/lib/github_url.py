"""Shared GitHub URL helpers used by CLI, server, and library code.

Centralises clone-URL construction, credential redaction, repo-spec
validation, and non-interactive git environment setup so that every
call-site shares the same logic.
"""

from __future__ import annotations

import os
import re

__all__ = [
    "GITHUB_HOSTNAME",
    "GITHUB_TOKEN_USER",
    "build_clone_url",
    "noninteractive_env",
    "redact_credentials",
    "validate_repo_spec",
]

GITHUB_TOKEN_USER = "x-access-token"
"""Username used in token-authenticated GitHub HTTPS clone URLs."""

GITHUB_HOSTNAME = "github.com"
"""Hostname matched when extracting ``owner/repo`` from git remote URLs."""


def validate_repo_spec(repo: str) -> None:
    """Validate that *repo* looks like ``owner/repo`` before embedding in a URL.

    Args:
        repo: The repository specification to validate.

    Raises:
        ValueError: If *repo* is empty or not in ``owner/repo`` format.
    """
    if not repo or not repo.strip():
        raise ValueError("repo spec must not be empty")
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
    effective_token = (token or "").strip() or os.environ.get(
        "GITHUB_TOKEN", os.environ.get("GH_TOKEN", "")
    ).strip()
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
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return env
