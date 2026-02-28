"""Configuration loading: CLI flags → env vars → .env files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from helping_hands.lib.meta import skills as meta_skills

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency safety
    load_dotenv = None  # type: ignore[assignment]

ConfigValue = str | bool | tuple[str, ...] | None


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
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    enabled_skills: tuple[str, ...] = ()
    config_path: Path | None = None

    @classmethod
    def from_env(cls, overrides: dict[str, ConfigValue] | None = None) -> Config:
        """Build config from environment variables, then apply overrides.

        Priority: overrides (CLI flags) > env vars > defaults.
        """
        repo_override = overrides.get("repo") if overrides else None
        _load_env_files(str(repo_override) if isinstance(repo_override, str) else None)

        env_values: dict[str, ConfigValue] = {
            "model": os.environ.get("HELPING_HANDS_MODEL"),
            "verbose": os.environ.get("HELPING_HANDS_VERBOSE", "").lower()
            in ("1", "true", "yes"),
            "enable_execution": os.environ.get(
                "HELPING_HANDS_ENABLE_EXECUTION", ""
            ).lower()
            in ("1", "true", "yes"),
            "enable_web": os.environ.get("HELPING_HANDS_ENABLE_WEB", "").lower()
            in ("1", "true", "yes"),
            "use_native_cli_auth": os.environ.get(
                "HELPING_HANDS_USE_NATIVE_CLI_AUTH", ""
            ).lower()
            in ("1", "true", "yes"),
            "enabled_skills": os.environ.get("HELPING_HANDS_SKILLS"),
        }

        merged = {k: v for k, v in env_values.items() if v}
        if overrides:
            merged.update({k: v for k, v in overrides.items() if v is not None})

        raw_skill_selection = merged.get("enabled_skills", cls.enabled_skills)
        if isinstance(raw_skill_selection, bool):
            normalized_skills_input: str | tuple[str, ...] | None = ()
        else:
            normalized_skills_input = raw_skill_selection

        return cls(
            repo=str(merged.get("repo", cls.repo)),
            model=str(merged.get("model", cls.model)),
            verbose=bool(merged.get("verbose", cls.verbose)),
            enable_execution=bool(merged.get("enable_execution", cls.enable_execution)),
            enable_web=bool(merged.get("enable_web", cls.enable_web)),
            use_native_cli_auth=bool(
                merged.get("use_native_cli_auth", cls.use_native_cli_auth)
            ),
            enabled_skills=meta_skills.normalize_skill_selection(
                normalized_skills_input
            ),
        )
