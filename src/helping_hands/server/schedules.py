"""Scheduled task management using RedBeat for Redis-backed cron scheduling.

Provides CRUD operations for scheduled build tasks, persisting schedules to Redis
via celery-redbeat and supporting standard cron expressions.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from celery import Celery

from helping_hands.lib.validation import install_hint
from helping_hands.server.constants import (
    DEFAULT_BACKEND as _DEFAULT_BACKEND,
    DEFAULT_CI_WAIT_MINUTES as _DEFAULT_CI_WAIT_MINUTES,
    DEFAULT_MAX_ITERATIONS as _DEFAULT_MAX_ITERATIONS,
    MAX_INTERVAL_SECONDS as _MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS as _MIN_INTERVAL_SECONDS,
    REDBEAT_KEY_PREFIX as _REDBEAT_KEY_PREFIX,
    REDBEAT_SCHEDULE_ENTRY_PREFIX as _REDBEAT_SCHEDULE_ENTRY_PREFIX,
    SCHEDULE_TYPE_CRON as _SCHEDULE_TYPE_CRON,
    SCHEDULE_TYPE_INTERVAL as _SCHEDULE_TYPE_INTERVAL,
    TASK_NAME_SCHEDULED_BUILD as _TASK_NAME_SCHEDULED_BUILD,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CRON_PRESETS",
    "ScheduleManager",
    "ScheduledTask",
    "generate_schedule_id",
    "get_schedule_manager",
    "next_run_time",
    "validate_cron_expression",
    "validate_interval_seconds",
]

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


def _check_optional_dep(available: bool | object, name: str, extra: str) -> None:
    """Raise ``ImportError`` if an optional dependency is missing.

    Args:
        available: Truthy if the dependency was imported successfully,
            falsy (``False`` or ``None``) otherwise.
        name: Human-readable package description for the error message.
        extra: The uv extra that provides the dependency.

    Raises:
        ImportError: When *available* is falsy.
    """
    if not available:
        msg = f"{name}. {install_hint(extra)}"
        raise ImportError(msg)


def _check_redbeat() -> None:
    """Raise ImportError if redbeat is not available."""
    _check_optional_dep(
        _redbeat_available,
        "celery-redbeat is required for scheduling",
        "server",
    )


def _check_croniter() -> None:
    """Raise ImportError if croniter is not available."""
    _check_optional_dep(
        croniter is not None,
        "croniter is required for cron expression parsing",
        "server",
    )


@dataclass
class ScheduledTask:
    """A scheduled build task definition.

    Attributes:
        schedule_id: Unique identifier (e.g. ``"sched_a1b2c3d4e5f6"``).
        name: Human-readable schedule name.
        schedule_type: ``"cron"`` for fixed-time schedules (via RedBeat) or
            ``"interval"`` for non-concurrent delay-after-completion schedules.
        cron_expression: Standard five-field cron expression or preset name.
            Required for ``"cron"`` schedules, ignored for ``"interval"``.
        interval_seconds: Seconds to wait after a build completes before
            starting the next one.  Required for ``"interval"`` schedules.
        repo_path: Local path or ``owner/repo`` specifier for the target repository.
        prompt: Task prompt passed to the hand backend.
        backend: Hand backend slug (default ``"claudecodecli"``).
        model: AI model identifier, or ``None`` for the backend default.
        max_iterations: Maximum iterative hand loop iterations.
        pr_number: Existing PR number to update, or ``None`` for new PRs.
            When set by the user this acts as a *pinned* target: every
            scheduled run checks out that PR's branch and pushes to it.
            If a push conflict creates a follow-up PR, the schedule
            retains the original PR number for the next run.  When
            ``None``, the first build that creates a PR auto-persists
            the number so subsequent runs reuse the same PR.
        no_pr: If ``True``, skip PR creation after changes.
        enable_execution: Enable runtime execution tools.
        enable_web: Enable web search/browse tools.
        use_native_cli_auth: Use native CLI auth instead of token-based.
        fix_ci: Attempt automated CI fix retries after PR creation.
        ci_check_wait_minutes: Minutes to wait between CI check polls.
        github_token: Per-task GitHub token override, or ``None``.
        reference_repos: Additional repos cloned as read-only context.
        tools: Selected tool category names.
        skills: Selected skill names.
        enabled: Whether the schedule is active in RedBeat.
        created_at: ISO 8601 creation timestamp (auto-set on init).
        last_run_at: ISO 8601 timestamp of the most recent run, or ``None``.
        last_run_task_id: Celery task ID of the most recent run, or ``None``.
        run_count: Total number of times this schedule has been triggered.
    """

    schedule_id: str
    name: str
    cron_expression: str
    repo_path: str
    prompt: str
    schedule_type: str = _SCHEDULE_TYPE_CRON
    interval_seconds: int | None = None
    backend: str = _DEFAULT_BACKEND
    model: str | None = None
    max_iterations: int = _DEFAULT_MAX_ITERATIONS
    pr_number: int | None = None
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    fix_ci: bool = False
    ci_check_wait_minutes: float = _DEFAULT_CI_WAIT_MINUTES
    github_token: str | None = None
    reference_repos: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
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
            "schedule_type": self.schedule_type,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
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
            "fix_ci": self.fix_ci,
            "ci_check_wait_minutes": self.ci_check_wait_minutes,
            "github_token": self.github_token,
            "reference_repos": self.reference_repos,
            "tools": self.tools,
            "skills": self.skills,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_run_at": self.last_run_at,
            "last_run_task_id": self.last_run_task_id,
            "run_count": self.run_count,
        }

    _REQUIRED_FIELDS = (
        "schedule_id",
        "name",
        "repo_path",
        "prompt",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledTask:
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

        schedule_type = data.get("schedule_type", _SCHEDULE_TYPE_CRON)
        cron_expression = data.get("cron_expression", "")

        # Cron schedules must have a cron_expression
        if schedule_type == _SCHEDULE_TYPE_CRON and not cron_expression.strip():
            msg = "cron_expression is required for cron schedules"
            raise ValueError(msg)

        return cls(
            schedule_id=data["schedule_id"],
            name=data["name"],
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval_seconds=data.get("interval_seconds"),
            repo_path=data["repo_path"],
            prompt=data["prompt"],
            backend=data.get("backend", _DEFAULT_BACKEND),
            model=data.get("model"),
            max_iterations=data.get("max_iterations", _DEFAULT_MAX_ITERATIONS),
            pr_number=data.get("pr_number"),
            no_pr=data.get("no_pr", False),
            enable_execution=data.get("enable_execution", False),
            enable_web=data.get("enable_web", False),
            use_native_cli_auth=data.get("use_native_cli_auth", False),
            fix_ci=data.get("fix_ci", False),
            ci_check_wait_minutes=data.get(
                "ci_check_wait_minutes", _DEFAULT_CI_WAIT_MINUTES
            ),
            github_token=data.get("github_token"),
            reference_repos=data.get("reference_repos", []),
            tools=data.get("tools", []),
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

_SCHEDULE_ID_HEX_LENGTH = 12
"""Number of hex characters used from uuid4 in schedule IDs."""


def validate_interval_seconds(seconds: int | None) -> int:
    """Validate an interval duration in seconds.

    Args:
        seconds: The interval in seconds.

    Returns:
        The validated interval.

    Raises:
        ValueError: If the interval is out of bounds or missing.
    """
    if seconds is None:
        msg = "interval_seconds is required for interval schedules"
        raise ValueError(msg)
    if seconds < _MIN_INTERVAL_SECONDS:
        msg = f"interval_seconds must be >= {_MIN_INTERVAL_SECONDS}"
        raise ValueError(msg)
    if seconds > _MAX_INTERVAL_SECONDS:
        msg = f"interval_seconds must be <= {_MAX_INTERVAL_SECONDS}"
        raise ValueError(msg)
    return seconds


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

    cron_expr = cron_expr.strip()

    # Check if it's a preset
    if cron_expr in CRON_PRESETS:
        cron_expr = CRON_PRESETS[cron_expr]

    # Validate using croniter
    if croniter is None:
        raise RuntimeError("croniter unavailable after _check_croniter")
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

    if croniter is None:
        raise RuntimeError("croniter unavailable after _check_croniter")
    cron = croniter(cron_expr, base_time)
    return cron.get_next(datetime)


def next_interval_run_time(
    interval_seconds: int,
    last_run_at: str | None = None,
) -> datetime:
    """Estimate the next run time for an interval schedule.

    For interval schedules the next run depends on when the *previous* run
    **completes**, not when it starts.  Since we don't track completion time we
    use ``last_run_at + interval_seconds`` as a best-effort estimate.  If the
    schedule has never run the next run is *now*.

    Args:
        interval_seconds: Delay in seconds between completion and next start.
        last_run_at: ISO 8601 timestamp of the last run start, or ``None``.

    Returns:
        Estimated next run time (UTC).
    """
    from datetime import timedelta

    if last_run_at is None:
        return datetime.now(UTC)

    last = datetime.fromisoformat(last_run_at)
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return last + timedelta(seconds=interval_seconds)


def generate_schedule_id() -> str:
    """Generate a unique schedule ID."""
    return f"sched_{uuid.uuid4().hex[:_SCHEDULE_ID_HEX_LENGTH]}"


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
        """Save schedule metadata to Redis.

        Raises:
            RuntimeError: If the Redis write fails.
        """
        import redis

        try:
            self._redis.set(
                self._meta_key(task.schedule_id),
                json.dumps(task.to_dict()),
            )
        except (redis.RedisError, OSError) as exc:
            logger.warning(
                "Failed to save schedule metadata for %s: %s",
                task.schedule_id,
                exc,
            )
            msg = f"Failed to persist schedule {task.schedule_id}"
            raise RuntimeError(msg) from exc

    def _load_meta(self, schedule_id: str) -> ScheduledTask | None:
        """Load schedule metadata from Redis.

        Returns None if the data is missing or corrupted (invalid JSON or
        missing required fields).
        """
        data = self._redis.get(self._meta_key(schedule_id))
        if data is None:
            return None
        try:
            return ScheduledTask.from_dict(json.loads(data))
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(
                "Corrupted schedule metadata for %s, skipping: %s",
                schedule_id,
                exc,
            )
            return None

    def _delete_meta(self, schedule_id: str) -> None:
        """Delete schedule metadata from Redis.

        Logs a warning on failure but does not raise, consistent with
        ``_load_meta`` graceful degradation.
        """
        import redis

        try:
            self._redis.delete(self._meta_key(schedule_id))
        except (redis.RedisError, OSError) as exc:
            logger.warning(
                "Failed to delete schedule metadata for %s: %s",
                schedule_id,
                exc,
            )

    def _list_meta_keys(self) -> list[str]:
        """List all schedule metadata keys.

        Returns an empty list on Redis errors to allow graceful degradation.
        """
        pattern = f"{_SCHEDULE_META_PREFIX}*"
        import redis

        try:
            keys = self._redis.keys(pattern)
        except (redis.RedisError, OSError) as exc:
            logger.warning("Failed to list schedule metadata keys: %s", exc)
            return []
        return [k.decode() if isinstance(k, bytes) else k for k in keys]

    def create_schedule(self, task: ScheduledTask) -> ScheduledTask:
        """Create a new scheduled task.

        Args:
            task: The scheduled task definition.

        Returns:
            The created task with generated ID if needed.

        Raises:
            ValueError: If the schedule already exists, cron is invalid,
                or interval_seconds is out of bounds.
        """
        # Validate based on schedule type
        if task.schedule_type == _SCHEDULE_TYPE_INTERVAL:
            task.interval_seconds = validate_interval_seconds(task.interval_seconds)
        else:
            task.cron_expression = validate_cron_expression(task.cron_expression)

        # Generate ID if not provided
        if not task.schedule_id:
            task.schedule_id = generate_schedule_id()

        # Check for duplicates
        existing = self._load_meta(task.schedule_id)
        if existing is not None:
            msg = f"Schedule with ID '{task.schedule_id}' already exists"
            raise ValueError(msg)

        # Create scheduler entry (RedBeat for cron, Celery chain for interval)
        if task.enabled:
            if task.schedule_type == _SCHEDULE_TYPE_INTERVAL:
                self._launch_interval_chain(task, countdown=0)
            else:
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

        if RedBeatSchedulerEntry is None:
            raise RuntimeError("RedBeatSchedulerEntry unavailable after _check_redbeat")
        entry = RedBeatSchedulerEntry(
            name=f"{_REDBEAT_SCHEDULE_ENTRY_PREFIX}{task.schedule_id}",
            task=_TASK_NAME_SCHEDULED_BUILD,
            schedule=schedule,
            args=[task.schedule_id],
            app=self._app,
        )
        entry.save()

    def _revoke_interval_chain(self, task: ScheduledTask) -> None:
        """Best-effort revoke of any pending Celery tasks for an interval schedule.

        Revokes the ``last_run_task_id`` (the most recently dispatched
        build_feature) so that a countdown-delayed build won't start, and
        invalidates the chain nonce so any stale ``interval_reschedule``
        callbacks from old chains will detect they are outdated and stop.

        Even if the revoke doesn't reach every queued task, ``build_feature``
        itself checks the enabled flag at startup and will bail out.
        """
        # Invalidate the chain nonce first — this is the primary mechanism
        # that prevents stale reschedule callbacks from spawning new builds.
        self._delete_chain_nonce(task.schedule_id)

        if not task.last_run_task_id:
            return
        try:
            self._app.control.revoke(task.last_run_task_id, terminate=False)
            logger.debug(
                "Revoked task %s for interval schedule %s",
                task.last_run_task_id,
                task.schedule_id,
            )
        except Exception:
            logger.debug(
                "Failed to revoke task %s for schedule %s (best-effort)",
                task.last_run_task_id,
                task.schedule_id,
                exc_info=True,
            )

    def _launch_interval_chain(
        self, task: ScheduledTask, countdown: int = 0
    ) -> str | None:
        """Dispatch a ``build_feature`` task with an interval-reschedule callback.

        The callback (``interval_reschedule``) fires after the build completes
        and enqueues the *next* iteration with the configured delay, ensuring
        non-concurrent execution.

        Before dispatching, any previously queued build for this schedule is
        revoked so that at most one chain is active at any time.

        Args:
            task: The interval schedule definition.
            countdown: Initial delay in seconds before the first build starts.

        Returns:
            The Celery ``AsyncResult.id`` of the dispatched build, or ``None``
            on failure.
        """
        # Revoke any previously queued build to prevent duplicate chains.
        self._revoke_interval_chain(task)

        try:
            from helping_hands.server.celery_app import (
                build_feature,
                interval_reschedule,
            )
        except ImportError:
            logger.warning("Could not import celery tasks for interval chain")
            return None

        # Generate a unique nonce for this chain generation so stale
        # reschedule callbacks from a previous chain can detect they are
        # outdated and stop.
        chain_nonce = uuid.uuid4().hex[:12]

        result = build_feature.apply_async(
            kwargs={
                "repo_path": task.repo_path,
                "prompt": task.prompt,
                "pr_number": task.pr_number,
                "backend": task.backend,
                "model": task.model,
                "max_iterations": task.max_iterations,
                "no_pr": task.no_pr,
                "enable_execution": task.enable_execution,
                "enable_web": task.enable_web,
                "use_native_cli_auth": task.use_native_cli_auth,
                "tools": task.tools,
                "skills": task.skills,
                "fix_ci": task.fix_ci,
                "ci_check_wait_minutes": task.ci_check_wait_minutes,
                "reference_repos": task.reference_repos,
                "schedule_id": task.schedule_id,
            },
            link=interval_reschedule.si(task.schedule_id, chain_nonce),
            link_error=interval_reschedule.si(task.schedule_id, chain_nonce),
            countdown=countdown,
        )

        # Persist both the task ID (for revocation) and the chain nonce
        # (for stale-chain detection) atomically with the run record.
        task.last_run_task_id = result.id
        task.last_run_at = datetime.now(UTC).isoformat()
        task.run_count += 1
        # Store chain_nonce in the schedule metadata so interval_reschedule
        # can verify it is still the active chain.
        self._save_chain_nonce(task.schedule_id, chain_nonce)
        self._save_meta(task)
        return result.id

    def _save_chain_nonce(self, schedule_id: str, nonce: str) -> None:
        """Store the active chain nonce for an interval schedule."""
        key = f"helping_hands:schedule:chain_nonce:{schedule_id}"
        import redis as _redis_mod

        try:
            self._redis.set(key, nonce)
        except (_redis_mod.RedisError, OSError) as exc:
            logger.debug("Failed to save chain nonce for %s: %s", schedule_id, exc)

    def get_chain_nonce(self, schedule_id: str) -> str | None:
        """Read the active chain nonce for an interval schedule."""
        key = f"helping_hands:schedule:chain_nonce:{schedule_id}"
        import redis as _redis_mod

        try:
            data = self._redis.get(key)
            if data is None:
                return None
            return data.decode() if isinstance(data, bytes) else data
        except (_redis_mod.RedisError, OSError) as exc:
            logger.debug("Failed to read chain nonce for %s: %s", schedule_id, exc)
            return None

    def _delete_chain_nonce(self, schedule_id: str) -> None:
        """Remove the chain nonce when disabling/deleting a schedule."""
        key = f"helping_hands:schedule:chain_nonce:{schedule_id}"
        import redis as _redis_mod

        try:
            self._redis.delete(key)
        except (_redis_mod.RedisError, OSError) as exc:
            logger.debug("Failed to delete chain nonce for %s: %s", schedule_id, exc)

    def _delete_redbeat_entry(self, schedule_id: str) -> None:
        """Delete the RedBeat scheduler entry."""
        entry_name = f"{_REDBEAT_SCHEDULE_ENTRY_PREFIX}{schedule_id}"
        try:
            if RedBeatSchedulerEntry is None:
                raise RuntimeError(
                    "RedBeatSchedulerEntry unavailable after _check_redbeat"
                )
            entry = RedBeatSchedulerEntry.from_key(
                f"{_REDBEAT_KEY_PREFIX}{entry_name}", app=self._app
            )
            entry.delete()
        except KeyError:
            logger.debug("RedBeat entry not found for schedule %s", schedule_id)

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

        # Validate based on schedule type
        if task.schedule_type == _SCHEDULE_TYPE_INTERVAL:
            task.interval_seconds = validate_interval_seconds(task.interval_seconds)
        else:
            task.cron_expression = validate_cron_expression(task.cron_expression)

        # Preserve metadata
        task.created_at = existing.created_at
        task.last_run_at = existing.last_run_at
        task.last_run_task_id = existing.last_run_task_id
        task.run_count = existing.run_count

        # Tear down old scheduler entries (both types, in case type changed)
        self._delete_redbeat_entry(task.schedule_id)
        if existing.schedule_type == _SCHEDULE_TYPE_INTERVAL:
            self._revoke_interval_chain(existing)

        # Set up new scheduler entry
        if task.enabled:
            if task.schedule_type == _SCHEDULE_TYPE_INTERVAL:
                self._launch_interval_chain(task, countdown=0)
            else:
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

        if existing.schedule_type == _SCHEDULE_TYPE_INTERVAL:
            self._revoke_interval_chain(existing)
        else:
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
            if task.schedule_type == _SCHEDULE_TYPE_INTERVAL:
                self._launch_interval_chain(task, countdown=0)
            else:
                self._create_redbeat_entry(task)
            self._save_meta(task)

        return task

    def disable_schedule(self, schedule_id: str) -> ScheduledTask | None:
        """Disable a scheduled task.

        Args:
            schedule_id: The schedule ID.

        Returns:
            The updated task or None if not found.

        For interval schedules the enabled flag is cleared **and** the last
        known Celery task is revoked so the chain stops immediately rather
        than waiting for a countdown to expire.  For cron schedules the
        RedBeat entry is deleted.
        """
        task = self._load_meta(schedule_id)
        if task is None:
            return None

        if task.enabled:
            task.enabled = False
            if task.schedule_type == _SCHEDULE_TYPE_INTERVAL:
                self._revoke_interval_chain(task)
            else:
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

    def update_pr_number(self, schedule_id: str, pr_number: int) -> bool:
        """Auto-persist a PR number back to a schedule after first creation.

        Called after a scheduled build creates a new PR so that subsequent
        runs push to the same PR instead of creating new ones.

        **Will not overwrite** an existing ``pr_number`` on the schedule.
        If the user (or a previous auto-persist) already set a PR number,
        the schedule is treated as *pinned* to that PR and this method is
        a no-op.  This guarantees that a user-specified PR target is never
        silently replaced by a newly created PR (e.g. due to a push conflict
        creating a follow-up PR).

        Args:
            schedule_id: The schedule ID.
            pr_number: The PR number to persist.

        Returns:
            True if updated, False if not found or already pinned.
        """
        task = self._load_meta(schedule_id)
        if task is None:
            return False

        if task.pr_number is not None:
            logger.debug(
                "Skipping auto-persist PR #%d to schedule %s: already pinned to PR #%d",
                pr_number,
                schedule_id,
                task.pr_number,
            )
            return False

        task.pr_number = pr_number
        self._save_meta(task)
        logger.info("Auto-persisted PR #%d to schedule %s", pr_number, schedule_id)
        return True

    def trigger_now(self, schedule_id: str) -> str | None:
        """Manually trigger a scheduled task to run immediately.

        For **interval** schedules the existing chain is replaced with a fresh
        one (countdown=0) so that exactly one build runs and the chain
        continues normally afterwards.  This avoids spawning a parallel build
        alongside the active chain.

        For **cron** schedules a standalone ``build_feature`` task is
        dispatched (the RedBeat entry is unaffected).

        Args:
            schedule_id: The schedule ID.

        Returns:
            The Celery task ID if triggered, None if schedule not found.
        """
        task = self._load_meta(schedule_id)
        if task is None:
            return None

        # Interval schedules: restart the chain so there is exactly one
        # active build at a time.
        if task.schedule_type == _SCHEDULE_TYPE_INTERVAL:
            return self._launch_interval_chain(task, countdown=0)

        # Cron / other: dispatch a one-off build (doesn't affect RedBeat).
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
            tools=task.tools,
            skills=task.skills,
            fix_ci=task.fix_ci,
            ci_check_wait_minutes=task.ci_check_wait_minutes,
            github_token=task.github_token,
            reference_repos=task.reference_repos,
            schedule_id=task.schedule_id,
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
