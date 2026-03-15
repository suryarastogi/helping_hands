"""Configuration loading: CLI flags → env vars → TOML file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from helping_hands.lib.meta import skills as meta_skills
from helping_hands.lib.meta.tools import registry as meta_tools

__all__ = ["Config"]

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency safety
    load_dotenv = None  # type: ignore[assignment]

ConfigValue = str | bool | tuple[str, ...] | None

_TRUTHY_VALUES = frozenset({"1", "true", "yes"})
"""Lowercase string values treated as boolean True for environment variables."""


def _is_truthy_env(name: str, default: str = "") -> bool:
    """Check whether an environment variable holds a truthy value.

    Args:
        name: Environment variable name to look up.
        default: Fallback if the variable is unset.

    Returns:
        True if the lowercased value is in ``_TRUTHY_VALUES``.
    """
    return os.environ.get(name, default).lower() in _TRUTHY_VALUES


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
    """Immutable application configuration.

    Attributes:
        repo: Local filesystem path or ``owner/repo`` slug for the target
            repository.
        model: Model identifier passed to the AI provider (e.g.
            ``"gpt-5.2"``, ``"anthropic/claude-sonnet-4-5"``).
        verbose: Whether to emit detailed progress output during hand
            execution.
        enable_execution: Allow execution tools (Python/Bash) in iterative
            hands.
        enable_web: Allow web search and browsing tools in iterative hands.
        use_native_cli_auth: Prefer the CLI backend's built-in authentication
            instead of token-based auth.
        enabled_tools: Normalised tool category names selected via
            ``--tools`` or ``HELPING_HANDS_TOOLS``.
        enabled_skills: Normalised skill names selected via ``--skills`` or
            ``HELPING_HANDS_SKILLS``.
        github_token: Per-task GitHub personal access token; overrides the
            default ``GITHUB_TOKEN`` when non-empty.
        reference_repos: Additional ``owner/repo`` slugs cloned as read-only
            shallow references for context.
        config_path: Optional path to a TOML configuration file (reserved for
            future use).
    """

    repo: str = ""
    model: str = "default"
    verbose: bool = True
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    enabled_tools: tuple[str, ...] = ()
    enabled_skills: tuple[str, ...] = ()
    github_token: str = ""
    reference_repos: tuple[str, ...] = ()
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
            "verbose": _is_truthy_env("HELPING_HANDS_VERBOSE"),
            "enable_execution": _is_truthy_env("HELPING_HANDS_ENABLE_EXECUTION"),
            "enable_web": _is_truthy_env("HELPING_HANDS_ENABLE_WEB"),
            "use_native_cli_auth": _is_truthy_env("HELPING_HANDS_USE_NATIVE_CLI_AUTH"),
            "enabled_tools": os.environ.get("HELPING_HANDS_TOOLS"),
            "enabled_skills": os.environ.get("HELPING_HANDS_SKILLS"),
            "github_token": os.environ.get("HELPING_HANDS_GITHUB_TOKEN"),
            "reference_repos": os.environ.get("HELPING_HANDS_REFERENCE_REPOS"),
        }

        merged = {k: v for k, v in env_values.items() if v}
        if overrides:
            merged.update({k: v for k, v in overrides.items() if v is not None})

        raw_tool_selection = merged.get("enabled_tools", cls.enabled_tools)
        if isinstance(raw_tool_selection, bool):
            normalized_tools_input: str | tuple[str, ...] | None = ()
        else:
            normalized_tools_input = raw_tool_selection

        raw_skill_selection = merged.get("enabled_skills", cls.enabled_skills)
        if isinstance(raw_skill_selection, bool):
            normalized_skills_input: str | tuple[str, ...] | None = ()
        else:
            normalized_skills_input = raw_skill_selection

        raw_ref_repos = merged.get("reference_repos", cls.reference_repos)
        if isinstance(raw_ref_repos, str):
            ref_repos = tuple(r.strip() for r in raw_ref_repos.split(",") if r.strip())
        elif isinstance(raw_ref_repos, list | tuple):
            ref_repos = tuple(str(r).strip() for r in raw_ref_repos if str(r).strip())
        else:
            ref_repos = ()

        return cls(
            repo=str(merged.get("repo", cls.repo)).strip(),
            model=str(merged.get("model", cls.model)).strip(),
            verbose=bool(merged.get("verbose", cls.verbose)),
            enable_execution=bool(merged.get("enable_execution", cls.enable_execution)),
            enable_web=bool(merged.get("enable_web", cls.enable_web)),
            use_native_cli_auth=bool(
                merged.get("use_native_cli_auth", cls.use_native_cli_auth)
            ),
            enabled_tools=meta_tools.normalize_tool_selection(normalized_tools_input),
            enabled_skills=meta_skills.normalize_skill_selection(
                normalized_skills_input
            ),
            github_token=str(merged.get("github_token", cls.github_token)).strip(),
            reference_repos=ref_repos,
        )
