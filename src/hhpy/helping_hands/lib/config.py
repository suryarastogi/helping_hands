"""Configuration loading: CLI flags → env vars → TOML file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
        env_values: dict[str, str | bool | None] = {
            "model": os.environ.get("HELPING_HANDS_MODEL"),
            "verbose": os.environ.get("HELPING_HANDS_VERBOSE", "").lower()
            in ("1", "true", "yes"),
        }

        merged = {k: v for k, v in env_values.items() if v}
        if overrides:
            merged.update({k: v for k, v in overrides.items() if v is not None})

        return cls(
            repo=str(merged.get("repo", cls.repo)),
            model=str(merged.get("model", cls.model)),
            verbose=bool(merged.get("verbose", cls.verbose)),
        )
