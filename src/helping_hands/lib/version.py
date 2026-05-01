"""Process version identity for backend and worker.

Each backend/worker process computes its version once at startup as
``<nominal>+<short-sha>[-dirty]`` (e.g. ``0.1.0+abc1234`` or
``0.1.0+abc1234-dirty``). The nominal version is read from ``pyproject.toml``;
the SHA and dirty flag are read live from the project's git working tree.

Workers register their version in Redis on ``worker_ready`` so the FastAPI
``/version`` endpoint can surface per-worker versions to the frontend, which
uses the values to detect partial-deploy mismatches.
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

WORKER_VERSION_KEY_PREFIX = "hh:worker:version:"
WORKER_VERSION_TTL_S = 60
SENTINEL_PATH_RELATIVE = "runs/local-stack/.deployed-version"


@dataclass(frozen=True)
class VersionInfo:
    """Resolved version identity for a process."""

    nominal: str
    """Nominal semver (read from ``pyproject.toml``)."""

    short_sha: str
    """Short git SHA, or ``"unknown"`` if git is unavailable."""

    long_sha: str
    """Full git SHA, or ``"unknown"`` if git is unavailable."""

    dirty: bool
    """True iff the working tree had uncommitted changes at process start."""

    commit_date: str | None
    """ISO 8601 commit timestamp (UTC), or ``None`` if git is unavailable."""

    @property
    def display(self) -> str:
        """Display string: ``<nominal>+<short_sha>[-dirty]``."""
        suffix = "-dirty" if self.dirty else ""
        return f"{self.nominal}+{self.short_sha}{suffix}"


def project_root() -> Path:
    """Locate the project root by walking up from this file."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    return here.parents[3]


def _read_nominal_version(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version")
        if isinstance(version, str) and version:
            return version
    except (OSError, tomllib.TOMLDecodeError):
        logger.debug("Could not read pyproject.toml version", exc_info=True)
    return "0.0.0"


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ("git", *args),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None


@lru_cache(maxsize=1)
def get_version_info() -> VersionInfo:
    """Compute version once per process and cache."""
    root = project_root()
    nominal = _read_nominal_version(root)

    long_sha = _git(root, "rev-parse", "HEAD")
    short_sha_raw = _git(root, "rev-parse", "--short", "HEAD")
    porcelain = _git(root, "status", "--porcelain")
    commit_date = _git(root, "log", "-1", "--format=%cI")

    if long_sha is None or short_sha_raw is None:
        env_version = os.environ.get("HH_VERSION")
        if env_version:
            return VersionInfo(
                nominal=nominal,
                short_sha=env_version,
                long_sha=env_version,
                dirty=False,
                commit_date=None,
            )
        return VersionInfo(
            nominal=nominal,
            short_sha="unknown",
            long_sha="unknown",
            dirty=False,
            commit_date=None,
        )

    return VersionInfo(
        nominal=nominal,
        short_sha=short_sha_raw,
        long_sha=long_sha,
        dirty=bool(porcelain),
        commit_date=commit_date or None,
    )


def read_sentinel_sha() -> str | None:
    """Return the SHA written by the deploy workflow, or None when absent."""
    sentinel = project_root() / SENTINEL_PATH_RELATIVE
    try:
        contents = sentinel.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return contents.split()[0] if contents else None


def worker_version_key(hostname: str | None = None) -> str:
    """Redis key used to register a worker's version."""
    return f"{WORKER_VERSION_KEY_PREFIX}{hostname or socket.gethostname()}"


def register_worker_version(redis_client: object, version: str) -> None:
    """Register or refresh this worker's version in Redis.

    Failures are logged at debug level; the worker should never crash on
    a Redis hiccup.
    """
    try:
        setex = redis_client.setex  # type: ignore[attr-defined]
        setex(worker_version_key(), WORKER_VERSION_TTL_S, version)
    except Exception:  # pragma: no cover - defensive
        logger.debug("Failed to register worker version", exc_info=True)


def read_worker_versions(redis_client: object) -> dict[str, str]:
    """Read all live worker versions from Redis, keyed by hostname."""
    try:
        scan_iter = redis_client.scan_iter  # type: ignore[attr-defined]
        get = redis_client.get  # type: ignore[attr-defined]
    except AttributeError:
        return {}

    out: dict[str, str] = {}
    try:
        for raw_key in scan_iter(match=f"{WORKER_VERSION_KEY_PREFIX}*"):
            key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
            host = key[len(WORKER_VERSION_KEY_PREFIX) :]
            value = get(raw_key)
            if value is None:
                continue
            out[host] = value.decode() if isinstance(value, bytes) else str(value)
    except Exception:  # pragma: no cover - defensive
        logger.debug("Failed to read worker versions", exc_info=True)
        return {}
    return out
