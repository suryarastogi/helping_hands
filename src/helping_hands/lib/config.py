"""Configuration loading: CLI flags → env vars → TOML file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency safety
    load_dotenv = None  # type: ignore[assignment]


def _load_env_files(repo: str | None = None) -> None:
    """Load dotenv files from cwd and target repo (if available)."""
    if load_dotenv is None:
        return

    load_dotenv(Path.cwd() / ".env", override=False)
    if repo:
        repo_path = Path(repo).expanduser()
        if repo_path.is_dir():
            load_dotenv(repo_path / ".env", override=False)


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    repo: str = ""
    model: str = "default"
    verbose: bool = False
    config_path: Path | None = None

    @classmethod
    def from_env(cls, overrides: dict[str, str | bool | None] | None = None) -> Config:
        """Build config from environment variables, then apply overrides.

        Priority: overrides (CLI flags) > env vars > defaults.
        """
        repo_override = overrides.get("repo") if overrides else None
        _load_env_files(str(repo_override) if isinstance(repo_override, str) else None)

        raw_model = os.environ.get("HELPING_HANDS_MODEL")
        raw_verbose = os.environ.get("HELPING_HANDS_VERBOSE")

        env_values: dict[str, str | bool | None] = {
            "model": raw_model if raw_model not in (None, "") else None,
            "verbose": (
                raw_verbose.lower() in ("1", "true", "yes")
                if raw_verbose not in (None, "")
                else None
            ),
        }

        # Only drop None (unset). Keep falsy but valid values (e.g. False, "").
        merged = {k: v for k, v in env_values.items() if v is not None}
        if overrides:
            merged.update({k: v for k, v in overrides.items() if v is not None})

        return cls(
            repo=str(merged.get("repo", cls.repo)),
            model=str(merged.get("model", cls.model)),
            verbose=bool(merged.get("verbose", cls.verbose)),
        )