"""Task template management using Redis for persistence.

Provides CRUD operations for reusable task templates that let users save
and share pre-configured form states for task submission.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from helping_hands.server.constants import (
    DEFAULT_REDIS_URL as _DEFAULT_REDIS_URL,
    TEMPLATE_KEY_PREFIX as _TEMPLATE_KEY_PREFIX,
)

logger = logging.getLogger(__name__)

__all__ = [
    "TaskTemplate",
    "TemplateManager",
    "generate_template_id",
]

_TEMPLATE_ID_HEX_LENGTH = 12
"""Number of hex characters used from uuid4 in template IDs."""


@dataclass
class TaskTemplate:
    """A reusable task template definition.

    Attributes:
        template_id: Unique identifier (e.g. ``"tmpl_a1b2c3d4e5f6"``).
        name: Human-readable template name.
        description: Optional description of the template's purpose.
        owner_token_hash: SHA-256 hex digest of the creator's GitHub token,
            used for ownership checks when the server has no global token.
        created_at: ISO 8601 creation timestamp (auto-set on init).
        updated_at: ISO 8601 last-update timestamp (auto-set on init).
        repo_path: Target repository, or ``None`` to leave form default.
        prompt: Task prompt, or ``None`` to leave form default.
        backend: Hand backend slug, or ``None`` to leave form default.
        model: AI model identifier, or ``None`` to leave form default.
        max_iterations: Max loop iterations, or ``None`` to leave form default.
        pr_number: Existing PR number, or ``None`` to leave form default.
        issue_number: Issue number, or ``None`` to leave form default.
        create_issue: Whether to create an issue, or ``None`` to leave form default.
        project_url: Project URL, or ``None`` to leave form default.
        no_pr: Skip PR creation, or ``None`` to leave form default.
        enable_execution: Enable execution tools, or ``None`` to leave form default.
        enable_web: Enable web tools, or ``None`` to leave form default.
        use_native_cli_auth: Use native CLI auth, or ``None`` to leave form default.
        fix_ci: Attempt CI fix, or ``None`` to leave form default.
        fix_conflicts: Attempt conflict resolution, or ``None`` to leave form default.
        master_rebase: Rebase on master, or ``None`` to leave form default.
        ci_check_wait_minutes: CI poll interval, or ``None`` to leave form default.
        reference_repos: Additional repos for context, or ``None`` to leave form default.
        tools: Selected tool categories, or ``None`` to leave form default.
    """

    template_id: str
    name: str
    description: str = ""
    owner_token_hash: str | None = None
    created_at: str = ""
    updated_at: str = ""
    repo_path: str | None = None
    prompt: str | None = None
    backend: str | None = None
    model: str | None = None
    max_iterations: int | None = None
    pr_number: int | None = None
    issue_number: int | None = None
    create_issue: bool | None = None
    project_url: str | None = None
    no_pr: bool | None = None
    enable_execution: bool | None = None
    enable_web: bool | None = None
    use_native_cli_auth: bool | None = None
    fix_ci: bool | None = None
    fix_conflicts: bool | None = None
    master_rebase: bool | None = None
    ci_check_wait_minutes: float | None = None
    reference_repos: list[str] | None = None
    tools: list[str] | None = None

    def __post_init__(self) -> None:
        now = datetime.now(UTC).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "owner_token_hash": self.owner_token_hash,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "repo_path": self.repo_path,
            "prompt": self.prompt,
            "backend": self.backend,
            "model": self.model,
            "max_iterations": self.max_iterations,
            "pr_number": self.pr_number,
            "issue_number": self.issue_number,
            "create_issue": self.create_issue,
            "project_url": self.project_url,
            "no_pr": self.no_pr,
            "enable_execution": self.enable_execution,
            "enable_web": self.enable_web,
            "use_native_cli_auth": self.use_native_cli_auth,
            "fix_ci": self.fix_ci,
            "fix_conflicts": self.fix_conflicts,
            "master_rebase": self.master_rebase,
            "ci_check_wait_minutes": self.ci_check_wait_minutes,
            "reference_repos": self.reference_repos,
            "tools": self.tools,
        }

    _REQUIRED_FIELDS = ("template_id", "name")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskTemplate:
        """Create from dictionary.

        Raises:
            ValueError: If any required field is missing or empty/whitespace.
        """
        missing = [f for f in cls._REQUIRED_FIELDS if f not in data]
        if missing:
            msg = f"Missing required fields: {', '.join(missing)}"
            raise ValueError(msg)
        empty = [
            f
            for f in cls._REQUIRED_FIELDS
            if isinstance(data[f], str) and not data[f].strip()
        ]
        if empty:
            msg = f"Required fields must not be empty: {', '.join(empty)}"
            raise ValueError(msg)

        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data.get("description", ""),
            owner_token_hash=data.get("owner_token_hash"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            repo_path=data.get("repo_path"),
            prompt=data.get("prompt"),
            backend=data.get("backend"),
            model=data.get("model"),
            max_iterations=data.get("max_iterations"),
            pr_number=data.get("pr_number"),
            issue_number=data.get("issue_number"),
            create_issue=data.get("create_issue"),
            project_url=data.get("project_url"),
            no_pr=data.get("no_pr"),
            enable_execution=data.get("enable_execution"),
            enable_web=data.get("enable_web"),
            use_native_cli_auth=data.get("use_native_cli_auth"),
            fix_ci=data.get("fix_ci"),
            fix_conflicts=data.get("fix_conflicts"),
            master_rebase=data.get("master_rebase"),
            ci_check_wait_minutes=data.get("ci_check_wait_minutes"),
            reference_repos=data.get("reference_repos"),
            tools=data.get("tools"),
        )


def generate_template_id() -> str:
    """Generate a unique template ID."""
    return f"tmpl_{uuid.uuid4().hex[:_TEMPLATE_ID_HEX_LENGTH]}"


class TemplateManager:
    """Manages task templates using Redis with JSON file fallback."""

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize the template manager.

        Args:
            redis_url: Redis connection URL. Falls back to ``REDIS_URL``
                environment variable or the default localhost URL.
        """
        import os
        from pathlib import Path

        self._redis = None
        self._fallback_dir: Path | None = None

        try:
            import redis as _redis_mod

            url = redis_url or os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
            client = _redis_mod.from_url(url)
            client.ping()
            self._redis = client
        except Exception as exc:
            logger.warning(
                "Redis unavailable for templates, using file fallback: %s", exc
            )
            self._fallback_dir = Path(
                os.environ.get("TEMPLATE_STORAGE_DIR", "/tmp/helping_hands_templates")
            )
            self._fallback_dir.mkdir(parents=True, exist_ok=True)

    def _meta_key(self, template_id: str) -> str:
        """Generate Redis key for template metadata."""
        return f"{_TEMPLATE_KEY_PREFIX}{template_id}"

    def _file_path(self, template_id: str):
        """Get the JSON file path for a template (fallback mode)."""
        assert self._fallback_dir is not None
        return self._fallback_dir / f"{template_id}.json"

    def _save_meta(self, template: TaskTemplate) -> None:
        """Save template metadata.

        Raises:
            RuntimeError: If the write fails.
        """
        payload = json.dumps(template.to_dict())
        if self._redis is not None:
            try:
                self._redis.set(
                    self._meta_key(template.template_id),
                    payload,
                )
            except (OSError, Exception) as exc:
                logger.warning(
                    "Failed to save template metadata for %s: %s",
                    template.template_id,
                    exc,
                )
                msg = f"Failed to persist template {template.template_id}"
                raise RuntimeError(msg) from exc
        else:
            try:
                self._file_path(template.template_id).write_text(payload)
            except (OSError, Exception) as exc:
                logger.warning(
                    "Failed to save template file for %s: %s",
                    template.template_id,
                    exc,
                )
                msg = f"Failed to persist template {template.template_id}"
                raise RuntimeError(msg) from exc

    def _load_meta(self, template_id: str) -> TaskTemplate | None:
        """Load template metadata.

        Returns None if the data is missing, corrupted, or storage is unavailable.
        """
        if self._redis is not None:
            try:
                data = self._redis.get(self._meta_key(template_id))
            except (OSError, Exception) as exc:
                logger.warning(
                    "Failed to read template metadata for %s: %s",
                    template_id,
                    exc,
                )
                return None
            if data is None:
                return None
            raw = data
        else:
            fp = self._file_path(template_id)
            if not fp.exists():
                return None
            try:
                raw = fp.read_text()
            except (OSError, Exception) as exc:
                logger.warning(
                    "Failed to read template file for %s: %s",
                    template_id,
                    exc,
                )
                return None
        try:
            return TaskTemplate.from_dict(json.loads(raw))
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(
                "Corrupted template metadata for %s, skipping: %s",
                template_id,
                exc,
            )
            return None

    def _delete_meta(self, template_id: str) -> None:
        """Delete template metadata."""
        if self._redis is not None:
            try:
                self._redis.delete(self._meta_key(template_id))
            except (OSError, Exception) as exc:
                logger.warning(
                    "Failed to delete template metadata for %s: %s",
                    template_id,
                    exc,
                )
        else:
            fp = self._file_path(template_id)
            try:
                fp.unlink(missing_ok=True)
            except (OSError, Exception) as exc:
                logger.warning(
                    "Failed to delete template file for %s: %s",
                    template_id,
                    exc,
                )

    def _list_meta_keys(self) -> list[str]:
        """List all template metadata keys."""
        if self._redis is not None:
            pattern = f"{_TEMPLATE_KEY_PREFIX}*"
            try:
                keys = self._redis.keys(pattern)
            except (OSError, Exception) as exc:
                logger.warning("Failed to list template metadata keys: %s", exc)
                return []
            return [k.decode() if isinstance(k, bytes) else k for k in keys]
        else:
            try:
                files = list(self._fallback_dir.glob("tmpl_*.json"))
            except (OSError, Exception) as exc:
                logger.warning("Failed to list template files: %s", exc)
                return []
            return [f"{_TEMPLATE_KEY_PREFIX}{f.stem}" for f in files]

    def create_template(self, template: TaskTemplate) -> TaskTemplate:
        """Create a new task template.

        Args:
            template: The task template definition.

        Returns:
            The created template with generated ID if needed.

        Raises:
            ValueError: If a template with the same ID already exists.
        """
        if not template.template_id:
            template.template_id = generate_template_id()

        existing = self._load_meta(template.template_id)
        if existing is not None:
            msg = f"Template with ID '{template.template_id}' already exists"
            raise ValueError(msg)

        self._save_meta(template)
        return template

    def get_template(self, template_id: str) -> TaskTemplate | None:
        """Get a task template by ID.

        Args:
            template_id: The template ID.

        Returns:
            The task template or None if not found.
        """
        return self._load_meta(template_id)

    def list_templates(self) -> list[TaskTemplate]:
        """List all task templates.

        Returns:
            List of all task templates, newest first.
        """
        templates = []
        for key in self._list_meta_keys():
            template_id = key.replace(_TEMPLATE_KEY_PREFIX, "")
            template = self._load_meta(template_id)
            if template is not None:
                templates.append(template)
        return sorted(templates, key=lambda t: t.created_at, reverse=True)

    def update_template(self, template: TaskTemplate) -> TaskTemplate:
        """Update an existing task template.

        Args:
            template: The updated template definition.

        Returns:
            The updated template.

        Raises:
            ValueError: If the template doesn't exist.
        """
        existing = self._load_meta(template.template_id)
        if existing is None:
            msg = f"Template with ID '{template.template_id}' not found"
            raise ValueError(msg)

        template.created_at = existing.created_at
        template.updated_at = datetime.now(UTC).isoformat()
        self._save_meta(template)
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a task template.

        Args:
            template_id: The template ID.

        Returns:
            True if deleted, False if not found.
        """
        existing = self._load_meta(template_id)
        if existing is None:
            return False
        self._delete_meta(template_id)
        return True
