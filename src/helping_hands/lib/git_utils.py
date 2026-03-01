"""Shared git/repo helper utilities.

Centralises token-authenticated clone URL construction, non-interactive
git environment setup, credential redaction, and temporary clone directory
management.  Consumed by ``cli.main``, ``server.celery_app``, and
``lib.github``.
"""

from __future__ import annotations

__all__ = [
    "git_noninteractive_env",
    "github_clone_url",
    "redact_sensitive",
    "repo_tmp_dir",
]

import os
import re
from pathlib import Path


def github_clone_url(repo: str) -> str:
    """Build a GitHub clone URL, using token auth when available.

    Args:
        repo: GitHub ``owner/repo`` reference.

    Returns:
        HTTPS clone URL, optionally prefixed with an ``x-access-token``
        credential when ``GITHUB_TOKEN`` or ``GH_TOKEN`` is set.
    """
    token = os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN", "")).strip()
    if token:
        return f"https://x-access-token:{token}@github.com/{repo}.git"
    return f"https://github.com/{repo}.git"


def git_noninteractive_env() -> dict[str, str]:
    """Return a copy of the environment with interactive git prompts disabled.

    Sets ``GIT_TERMINAL_PROMPT=0`` and ``GCM_INTERACTIVE=never`` so that
    credential helpers never block on stdin in automated contexts.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return env


def redact_sensitive(text: str) -> str:
    """Replace GitHub access tokens in URLs with ``***``.

    Args:
        text: String that may contain ``x-access-token`` URLs.

    Returns:
        Sanitised string safe for logging and error messages.
    """
    return re.sub(
        r"(https://x-access-token:)[^@]+(@github\.com/)",
        r"\1***\2",
        text,
    )


def repo_tmp_dir() -> Path | None:
    """Return the directory to use for temporary repo clones.

    Reads ``HELPING_HANDS_REPO_TMP``; falls back to the OS default temp
    dir (returns ``None`` so callers can pass it to ``tempfile.mkdtemp``).
    """
    d = os.environ.get("HELPING_HANDS_REPO_TMP", "").strip()
    if d:
        p = Path(d).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return None
