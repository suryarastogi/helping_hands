"""Scheduled task management using RedBeat for Redis-backed cron scheduling.

Provides CRUD operations for scheduled build tasks, persisting schedules to Redis
via celery-redbeat and supporting standard cron expressions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from celery import Celery

# Lazy imports for optional dependencies
_redbeat_available = True
try:
    from redbeat import RedBeatSchedulerEntry
    from redbeat.decoder import RedBeatJSONDecoder, RedBeatJSONEncoder
except ImportError:
    _redbeat_available = False
    RedBeatSchedulerEntry = None  # type: ignore[assignment]
    RedBeatJSONDecoder = None  # type: ignore[assignment]
    RedBeatJSONEncoder = None  # type: ignore[assignment]

try:
    from croniter import croniter
except ImportError:
    croniter = None  # type: ignore[assignment]


def _check_redbeat() -> None:
    """Raise ImportError if redbeat is not available."""
    if not _redbeat_available:
        msg = (
            "celery-redbeat is required for scheduling. "
            "Install with: uv sync --extra server"
        )
        raise ImportError(msg)


def _check_croniter() -> None:
    """Raise ImportError if croniter is not available."""
    if croniter is None:
        msg = (
            "croniter is required for cron expression parsing. "
            "Install with: uv sync --extra server"
        )
        raise ImportError(msg)


@dataclass
class ScheduledTask:
    """A scheduled build task definition."""

    schedule_id: str
    name: str
    cron_expression: str
    repo_path: str
    prompt: str
    backend: str = "claudecodecli"
    model: str | None = None
    max_iterations: int = 6
    pr_number: int | None = None
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    skills: list[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = ""
    last_run_at: str | None = None
    last_run_task_id: str | None = None
    run_count: int = 0

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "cron_expression": self.cron_expression,
            "repo_path": self.repo_path,
            "prompt": self.prompt,
            "backend": self.backend,
            "model": self.model,
            "max_iterations": self.max_iterations,
            "pr_number": self.pr_number,
            "no_pr": self.no_pr,
            "enable_execution": self.enable_execution,
            "enable_web": self.enable_web,
            "use_native_cli_auth": self.use_native_cli_auth,
            "skills": self.skills,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_run_at": self.last_run_at,
            "last_run_task_id": self.last_run_task_id,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledTask:
        """Create from dictionary."""
        return cls(
            schedule_id=data["schedule_id"],
            name=data["name"],
            cron_expression=data["cron_expression"],
            repo_path=data["repo_path"],
            prompt=data["prompt"],
            backend=data.get("backend", "claudecodecli"),
            model=data.get("model"),
            max_iterations=data.get("max_iterations", 6),
            pr_number=data.get("pr_number"),
            no_pr=data.get("no_pr", False),
            enable_execution=data.get("enable_execution", False),
            enable_web=data.get("enable_web", False),
            use_native_cli_auth=data.get("use_native_cli_auth", False),
            skills=data.get("skills", []),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            last_run_at=data.get("last_run_at"),
            last_run_task_id=data.get("last_run_task_id"),
            run_count=data.get("run_count", 0),
        )


# Common cron presets for user convenience
CRON_PRESETS: dict[str, str] = {
    "every_minute": "* * * * *",
    "every_5_minutes": "*/5 * * * *",
    "every_15_minutes": "*/15 * * * *",
    "every_30_minutes": "*/30 * * * *",
    "hourly": "0 * * * *",
    "daily": "0 0 * * *",
    "midnight": "0 0 * * *",
    "weekly": "0 0 * * 0",
    "monthly": "0 0 1 * *",
    "weekdays": "0 9 * * 1-5",
}

# Schedule metadata key prefix in Redis
_SCHEDULE_META_PREFIX = "helping_hands:schedule:meta:"


def validate_cron_expression(cron_expr: str) -> str:
    """Validate and normalize a cron expression.

    Args:
        cron_expr: A cron expression string or preset name.

    Returns:
        The validated/normalized cron expression.

    Raises:
        ValueError: If the cron expression is invalid.
    """
    _check_croniter()

    # Check if it's a preset
    if cron_expr in CRON_PRESETS:
        cron_expr = CRON_PRESETS[cron_expr]

    # Validate using croniter
    try:
        croniter(cron_expr)
    except (ValueError, KeyError) as exc:
        msg = f"Invalid cron expression '{cron_expr}': {exc}"
        raise ValueError(msg) from exc

    return cron_expr


def next_run_time(cron_expr: str, base_time: datetime | None = None) -> datetime:
    """Calculate the next run time for a cron expression.

    Args:
        cron_expr: A valid cron expression.
        base_time: Base time to calculate from (defaults to now UTC).

    Returns:
        The next scheduled run time.
    """
    _check_croniter()

    if base_time is None:
        base_time = datetime.now(UTC)

    cron = croniter(cron_expr, base_time)
    return cron.get_next(datetime)


def generate_schedule_id() -> str:
    """Generate a unique schedule ID."""
    return f"sched_{uuid.uuid4().hex[:12]}"


class ScheduleManager:
    """Manages scheduled tasks using RedBeat for Redis persistence."""

    def __init__(self, celery_app: Celery) -> None:
        """Initialize the schedule manager.

        Args:
            celery_app: The Celery application instance.
        """
        _check_redbeat()
        self._app = celery_app
        self._redis = self._get_redis_client()

    def _get_redis_client(self) -> Any:
        """Get the Redis client from Celery's connection pool."""
        # RedBeat stores its own redis URL in redbeat_redis_url or uses broker
        redis_url = self._app.conf.get("redbeat_redis_url", self._app.conf.broker_url)
        import redis

        return redis.from_url(redis_url)

    def _meta_key(self, schedule_id: str) -> str:
        """Generate Redis key for schedule metadata."""
        return f"{_SCHEDULE_META_PREFIX}{schedule_id}"

    def _save_meta(self, task: ScheduledTask) -> None:
        """Save schedule metadata to Redis."""
        self._redis.set(
            self._meta_key(task.schedule_id),
            json.dumps(task.to_dict()),
        )

    def _load_meta(self, schedule_id: str) -> ScheduledTask | None:
        """Load schedule metadata from Redis."""
        data = self._redis.get(self._meta_key(schedule_id))
        if data is None:
            return None
        return ScheduledTask.from_dict(json.loads(data))

    def _delete_meta(self, schedule_id: str) -> None:
        """Delete schedule metadata from Redis."""
        self._redis.delete(self._meta_key(schedule_id))

    def _list_meta_keys(self) -> list[str]:
        """List all schedule metadata keys."""
        pattern = f"{_SCHEDULE_META_PREFIX}*"
        keys = self._redis.keys(pattern)
        return [k.decode() if isinstance(k, bytes) else k for k in keys]

    def create_schedule(self, task: ScheduledTask) -> ScheduledTask:
        """Create a new scheduled task.

        Args:
            task: The scheduled task definition.

        Returns:
            The created task with generated ID if needed.

        Raises:
            ValueError: If the schedule already exists or cron is invalid.
        """
        # Validate cron expression
        task.cron_expression = validate_cron_expression(task.cron_expression)

        # Generate ID if not provided
        if not task.schedule_id:
            task.schedule_id = generate_schedule_id()

        # Check for duplicates
        existing = self._load_meta(task.schedule_id)
        if existing is not None:
            msg = f"Schedule with ID '{task.schedule_id}' already exists"
            raise ValueError(msg)

        # Create RedBeat entry
        if task.enabled:
            self._create_redbeat_entry(task)

        # Save metadata
        self._save_meta(task)

        return task

    def _create_redbeat_entry(self, task: ScheduledTask) -> None:
        """Create or update the RedBeat scheduler entry."""
        from celery.schedules import crontab

        # Parse cron expression into crontab parts
        parts = task.cron_expression.split()
        if len(parts) != 5:
            msg = f"Invalid cron expression: {task.cron_expression}"
            raise ValueError(msg)

        minute, hour, day_of_month, month, day_of_week = parts

        schedule = crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month,
            day_of_week=day_of_week,
        )

        entry = RedBeatSchedulerEntry(
            name=f"helping_hands:scheduled:{task.schedule_id}",
            task="helping_hands.scheduled_build",
            schedule=schedule,
            args=[task.schedule_id],
            app=self._app,
        )
        entry.save()

    def _delete_redbeat_entry(self, schedule_id: str) -> None:
        """Delete the RedBeat scheduler entry."""
        entry_name = f"helping_hands:scheduled:{schedule_id}"
        try:
            entry = RedBeatSchedulerEntry.from_key(
                f"redbeat:{entry_name}", app=self._app
            )
            entry.delete()
        except KeyError:
            pass  # Entry doesn't exist, nothing to delete

    def get_schedule(self, schedule_id: str) -> ScheduledTask | None:
        """Get a scheduled task by ID.

        Args:
            schedule_id: The schedule ID.

        Returns:
            The scheduled task or None if not found.
        """
        return self._load_meta(schedule_id)

    def list_schedules(self) -> list[ScheduledTask]:
        """List all scheduled tasks.

        Returns:
            List of all scheduled tasks.
        """
        tasks = []
        for key in self._list_meta_keys():
            schedule_id = key.replace(_SCHEDULE_META_PREFIX, "")
            task = self._load_meta(schedule_id)
            if task is not None:
                tasks.append(task)
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def update_schedule(self, task: ScheduledTask) -> ScheduledTask:
        """Update an existing scheduled task.

        Args:
            task: The updated task definition.

        Returns:
            The updated task.

        Raises:
            ValueError: If the schedule doesn't exist.
        """
        existing = self._load_meta(task.schedule_id)
        if existing is None:
            msg = f"Schedule with ID '{task.schedule_id}' not found"
            raise ValueError(msg)

        # Validate cron expression
        task.cron_expression = validate_cron_expression(task.cron_expression)

        # Preserve metadata
        task.created_at = existing.created_at
        task.last_run_at = existing.last_run_at
        task.last_run_task_id = existing.last_run_task_id
        task.run_count = existing.run_count

        # Update RedBeat entry
        self._delete_redbeat_entry(task.schedule_id)
        if task.enabled:
            self._create_redbeat_entry(task)

        # Save metadata
        self._save_meta(task)

        return task

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a scheduled task.

        Args:
            schedule_id: The schedule ID.

        Returns:
            True if deleted, False if not found.
        """
        existing = self._load_meta(schedule_id)
        if existing is None:
            return False

        self._delete_redbeat_entry(schedule_id)
        self._delete_meta(schedule_id)
        return True

    def enable_schedule(self, schedule_id: str) -> ScheduledTask | None:
        """Enable a scheduled task.

        Args:
            schedule_id: The schedule ID.

        Returns:
            The updated task or None if not found.
        """
        task = self._load_meta(schedule_id)
        if task is None:
            return None

        if not task.enabled:
            task.enabled = True
            self._create_redbeat_entry(task)
            self._save_meta(task)

        return task

    def disable_schedule(self, schedule_id: str) -> ScheduledTask | None:
        """Disable a scheduled task.

        Args:
            schedule_id: The schedule ID.

        Returns:
            The updated task or None if not found.
        """
        task = self._load_meta(schedule_id)
        if task is None:
            return None

        if task.enabled:
            task.enabled = False
            self._delete_redbeat_entry(schedule_id)
            self._save_meta(task)

        return task

    def record_run(self, schedule_id: str, task_id: str) -> None:
        """Record that a scheduled task was run.

        Args:
            schedule_id: The schedule ID.
            task_id: The Celery task ID of the run.
        """
        task = self._load_meta(schedule_id)
        if task is None:
            return

        task.last_run_at = datetime.now(UTC).isoformat()
        task.last_run_task_id = task_id
        task.run_count += 1
        self._save_meta(task)

    def trigger_now(self, schedule_id: str) -> str | None:
        """Manually trigger a scheduled task to run immediately.

        Args:
            schedule_id: The schedule ID.

        Returns:
            The Celery task ID if triggered, None if schedule not found.
        """
        task = self._load_meta(schedule_id)
        if task is None:
            return None

        # Import here to avoid circular dependency
        from helping_hands.server.celery_app import build_feature

        result = build_feature.delay(
            repo_path=task.repo_path,
            prompt=task.prompt,
            pr_number=task.pr_number,
            backend=task.backend,
            model=task.model,
            max_iterations=task.max_iterations,
            no_pr=task.no_pr,
            enable_execution=task.enable_execution,
            enable_web=task.enable_web,
            use_native_cli_auth=task.use_native_cli_auth,
            skills=task.skills,
        )

        self.record_run(schedule_id, result.id)
        return result.id


def get_schedule_manager(celery_app: Celery) -> ScheduleManager:
    """Get a ScheduleManager instance.

    Args:
        celery_app: The Celery application instance.

    Returns:
        A ScheduleManager instance.
    """
    return ScheduleManager(celery_app)
