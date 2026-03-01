"""Configuration loading: CLI flags → env vars → TOML file."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from helping_hands.lib.meta import skills as meta_skills

logger = logging.getLogger(__name__)

_OWNER_REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9._:/-]+$")

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency safety
    load_dotenv = None  # type: ignore[assignment]

ConfigValue = str | bool | tuple[str, ...] | None


def _validate_repo(repo: str) -> None:
    """Validate repo format: must be empty, a filesystem path, or owner/repo."""
    if not repo:
        return
    if _OWNER_REPO_PATTERN.match(repo):
        return
    path = Path(repo).expanduser()
    if path.exists() or path.parent.exists():
        return
    msg = (
        f"Invalid repo '{repo}': must be a local path or 'owner/repo' format. "
        "Example: /path/to/repo or suryarastogi/helping_hands"
    )
    raise ValueError(msg)


def _validate_model(model: str) -> None:
    """Warn if model string doesn't match expected patterns."""
    if not model or model == "default":
        return
    if not _MODEL_PATTERN.match(model):
        logger.warning(
            "Model '%s' contains unexpected characters; "
            "expected bare name (e.g. 'gpt-5.2') or "
            "'provider/model' (e.g. 'anthropic/claude-sonnet-4-5')",
            model,
        )


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

    def __post_init__(self) -> None:
        """Validate config fields on creation.

        Checks that ``repo`` is either empty, a filesystem path, or an
        ``owner/repo`` GitHub reference.  Logs a warning when ``model``
        contains unexpected characters (expected: bare name like
        ``gpt-5.2`` or ``provider/model`` like
        ``anthropic/claude-sonnet-4-5``).
        """
        _validate_repo(self.repo)
        _validate_model(self.model)

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
