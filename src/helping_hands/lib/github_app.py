"""GitHub App authentication: mint short-lived installation access tokens.

A GitHub App configured via environment variables is a server-level
alternative to a personal access token. GitHub App *installation access
tokens* behave exactly like a PAT for both the REST API
(PyGithub ``Auth.Token``) and token-authenticated HTTPS clone URLs
(``https://x-access-token:<token>@github.com/...``), so the rest of the
codebase needs no special handling — :func:`resolve_app_installation_token`
mints one on demand and :func:`resolve_github_token` falls back to it
transparently when no PAT is available.

Configuration (all read from the environment):

- ``GITHUB_APP_ID`` — the App's numeric app id (or client id).
- ``GITHUB_APP_PRIVATE_KEY_PATH`` — path to the App's ``.pem`` private key.
- ``GITHUB_APP_PRIVATE_KEY`` — the private key contents inline (alternative to
  the path; literal ``\\n`` escapes are unescaped). The path takes precedence
  when both are set.
- ``GITHUB_APP_INSTALLATION_ID`` — optional installation id. When omitted and
  the App has exactly one installation, that installation is used; otherwise
  an explicit id is required.

Installation tokens expire after ~1 hour, so minted tokens are cached
per-process (keyed by app id + installation id) and refreshed automatically a
few minutes before expiry. PyGithub (the ``github`` extra) is imported lazily
so this module stays importable without it.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "GitHubAppError",
    "github_app_configured",
    "resolve_app_installation_token",
]

_ENV_APP_ID = "GITHUB_APP_ID"
"""Env var for the GitHub App id (numeric app id or client id)."""

_ENV_PRIVATE_KEY_PATH = "GITHUB_APP_PRIVATE_KEY_PATH"
"""Env var for the filesystem path to the App's ``.pem`` private key."""

_ENV_PRIVATE_KEY = "GITHUB_APP_PRIVATE_KEY"
"""Env var for the App's private key contents (inline alternative to the path)."""

_ENV_INSTALLATION_ID = "GITHUB_APP_INSTALLATION_ID"
"""Env var for the installation id (optional when the App has one installation)."""

_REFRESH_MARGIN = timedelta(minutes=5)
"""Refresh a cached installation token this long before it expires."""


class GitHubAppError(RuntimeError):
    """Raised when GitHub App auth is configured but a token cannot be minted."""


@dataclass(frozen=True)
class _CachedToken:
    """An installation access token with its expiry, held in the process cache."""

    token: str
    expires_at: datetime

    def is_fresh(self, now: datetime) -> bool:
        """Whether the token is still valid past the refresh safety margin."""
        return self.expires_at - now > _REFRESH_MARGIN


_token_cache: dict[tuple[str, str], _CachedToken] = {}
"""Per-process cache of minted tokens, keyed by (app id, installation-id env)."""

_cache_lock = threading.Lock()
"""Guards :data:`_token_cache` against concurrent mints across threads."""


def github_app_configured() -> bool:
    """Return whether GitHub App credentials are present in the environment.

    Requires ``GITHUB_APP_ID`` plus a private key source (either
    ``GITHUB_APP_PRIVATE_KEY_PATH`` or ``GITHUB_APP_PRIVATE_KEY``). This is a
    cheap env-only check — it does not read the key file or contact GitHub.

    Returns:
        True when an app id and a private key source are both configured.
    """
    app_id = os.environ.get(_ENV_APP_ID, "").strip()
    has_key = bool(
        os.environ.get(_ENV_PRIVATE_KEY_PATH, "").strip()
        or os.environ.get(_ENV_PRIVATE_KEY, "").strip()
    )
    return bool(app_id) and has_key


def resolve_app_installation_token() -> str | None:
    """Return a GitHub App installation access token, minting if needed.

    Returns ``None`` when no GitHub App is configured, so callers can fall
    through to other auth sources. When an App *is* configured, a token is
    minted (or returned from the per-process cache) and any failure raises
    :class:`GitHubAppError` rather than returning ``None`` — a configured but
    broken App is a real error, not a reason to fall back to anonymous access.

    Returns:
        The installation token string, or ``None`` if no App is configured.

    Raises:
        GitHubAppError: If an App is configured but a token cannot be minted
            (missing/unreadable key, no matching installation, API failure).
    """
    if not github_app_configured():
        return None

    key = _cache_key()
    now = datetime.now(UTC)
    with _cache_lock:
        cached = _token_cache.get(key)
        if cached and cached.is_fresh(now):
            return cached.token
        minted = _mint_token()
        _token_cache[key] = minted
        logger.info(
            "Minted GitHub App installation token (expires %s)",
            minted.expires_at.isoformat(),
        )
        return minted.token


def _cache_key() -> tuple[str, str]:
    """Build the cache key from the app id and installation-id env value."""
    return (
        os.environ.get(_ENV_APP_ID, "").strip(),
        os.environ.get(_ENV_INSTALLATION_ID, "").strip(),
    )


def _load_private_key() -> str:
    """Load the App private key from the path, then the inline env var.

    Returns:
        The PEM private key contents.

    Raises:
        GitHubAppError: If neither source is set or the file cannot be read.
    """
    path = os.environ.get(_ENV_PRIVATE_KEY_PATH, "").strip()
    if path:
        try:
            return Path(path).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise GitHubAppError(
                f"could not read GitHub App private key from "
                f"{_ENV_PRIVATE_KEY_PATH}={path!r}: {exc}"
            ) from exc

    inline = os.environ.get(_ENV_PRIVATE_KEY, "")
    if inline.strip():
        # Some secret stores inject the key as a single line with literal \n.
        if "\\n" in inline and "\n" not in inline.strip():
            inline = inline.replace("\\n", "\n")
        return inline

    raise GitHubAppError(
        f"GitHub App private key not configured; set "
        f"{_ENV_PRIVATE_KEY_PATH} or {_ENV_PRIVATE_KEY}"
    )


def _resolve_installation_id(integration: object) -> int:
    """Resolve the installation id from env, else auto-discover a sole install.

    Args:
        integration: A PyGithub ``GithubIntegration`` instance.

    Returns:
        The numeric installation id to mint a token for.

    Raises:
        GitHubAppError: If the env value is non-numeric, or auto-discovery
            finds zero or more than one installation.
    """
    explicit = os.environ.get(_ENV_INSTALLATION_ID, "").strip()
    if explicit:
        try:
            return int(explicit)
        except ValueError as exc:
            raise GitHubAppError(
                f"{_ENV_INSTALLATION_ID} must be an integer, got {explicit!r}"
            ) from exc

    installations = list(integration.get_installations())  # type: ignore[attr-defined]
    if len(installations) == 1:
        return installations[0].id
    if not installations:
        raise GitHubAppError(
            "GitHub App is not installed on any account; install it on the "
            f"target org/user and/or set {_ENV_INSTALLATION_ID}"
        )
    available = ", ".join(str(inst.id) for inst in installations)
    raise GitHubAppError(
        f"GitHub App has multiple installations ({available}); set "
        f"{_ENV_INSTALLATION_ID} to select one"
    )


def _mint_token() -> _CachedToken:
    """Mint a fresh installation access token via the GitHub App credentials.

    Returns:
        A :class:`_CachedToken` with the token and its expiry.

    Raises:
        GitHubAppError: If PyGithub is unavailable or the API call fails.
    """
    try:
        from github import Auth, GithubIntegration
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise GitHubAppError(
            "GitHub App auth requires the 'github' extra (PyGithub); install "
            "with `uv sync --extra github`"
        ) from exc

    app_id = os.environ.get(_ENV_APP_ID, "").strip()
    private_key = _load_private_key()
    try:
        auth = Auth.AppAuth(app_id, private_key)
        integration = GithubIntegration(auth=auth)
        installation_id = _resolve_installation_id(integration)
        access = integration.get_access_token(installation_id)
    except GitHubAppError:
        raise
    except Exception as exc:  # normalise any PyGithub/JWT failure into our error
        raise GitHubAppError(
            f"failed to mint GitHub App installation token: {exc}"
        ) from exc

    expires_at = access.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return _CachedToken(token=access.token, expires_at=expires_at)
