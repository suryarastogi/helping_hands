"""Celery application and task definitions."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from subprocess import TimeoutExpired
from tempfile import mkdtemp
from typing import Any

from celery import Celery

from helping_hands.lib.config import _TRUTHY_VALUES
from helping_hands.lib.github_url import (
    GIT_CLONE_TIMEOUT_S as _GIT_CLONE_TIMEOUT_S,
)
from helping_hands.lib.github_url import (
    UNKNOWN_CLONE_ERROR as _UNKNOWN_CLONE_ERROR,
)
from helping_hands.lib.github_url import (
    build_clone_url as _build_clone_url,
)
from helping_hands.lib.github_url import (
    noninteractive_env as _git_noninteractive_env,
)
from helping_hands.lib.github_url import (
    redact_credentials as _redact_sensitive,
)
from helping_hands.lib.github_url import (
    ref_repo_tmp_prefix as _ref_repo_tmp_prefix,
)
from helping_hands.lib.github_url import (
    validate_repo_spec as _validate_repo_spec,
)
from helping_hands.lib.hands.v1.hand.base import (
    _TRUNCATION_MARKER,
)
from helping_hands.server.constants import (
    ANTHROPIC_BETA_HEADER as _ANTHROPIC_BETA_HEADER,
)
from helping_hands.server.constants import (
    ANTHROPIC_USAGE_URL as _ANTHROPIC_USAGE_URL,
)
from helping_hands.server.constants import (
    JWT_TOKEN_PREFIX as _JWT_TOKEN_PREFIX,
)
from helping_hands.server.constants import (
    KEYCHAIN_ACCESS_TOKEN_KEY as _KEYCHAIN_ACCESS_TOKEN_KEY,
)
from helping_hands.server.constants import (
    KEYCHAIN_OAUTH_KEY as _KEYCHAIN_OAUTH_KEY,
)
from helping_hands.server.constants import (
    KEYCHAIN_SERVICE_NAME as _KEYCHAIN_SERVICE_NAME,
)
from helping_hands.server.constants import (
    USAGE_USER_AGENT as _USAGE_USER_AGENT,
)

logger = logging.getLogger(__name__)

__all__ = ["build_feature", "celery_app"]


def _resolve_celery_urls() -> tuple[str, str]:
    """Resolve broker/result backend URLs with sensible env fallbacks.

    Priority order:
    1. `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`
    2. shared `REDIS_URL`
    3. local default (`redis://localhost:6379/0`)
    """
    redis_url = os.environ.get("REDIS_URL")
    broker_url = (
        os.environ.get("CELERY_BROKER_URL") or redis_url or "redis://localhost:6379/0"
    )
    # Fall back to broker URL so polling still works when only broker is set.
    backend_url = os.environ.get("CELERY_RESULT_BACKEND") or redis_url or broker_url
    return broker_url, backend_url


_BROKER_URL, _RESULT_BACKEND_URL = _resolve_celery_urls()

celery_app = Celery(
    "helping_hands",
    broker=_BROKER_URL,
    backend=_RESULT_BACKEND_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # RedBeat scheduler configuration for cron-scheduled tasks
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=_BROKER_URL,
    redbeat_key_prefix="redbeat:",
)


_USAGE_LOG_INTERVAL_S = 3600.0
"""Interval in seconds between automatic Claude usage log entries."""

_USAGE_API_TIMEOUT_S = 10

_KEYCHAIN_TIMEOUT_S = 5
"""Timeout in seconds for macOS Keychain subprocess calls."""

_DB_CONNECT_TIMEOUT_S = 5
"""Timeout in seconds for PostgreSQL connection attempts."""

_SUPPORTED_BACKENDS = {
    "e2e",
    "basic-langgraph",
    "basic-atomic",
    "basic-agent",
    "codexcli",
    "claudecodecli",
    "docker-sandbox-claude",
    "goose",
    "geminicli",
    "opencodecli",
}
_VERBOSE = os.environ.get("HELPING_HANDS_VERBOSE", "").lower() in _TRUTHY_VALUES
_MAX_STORED_UPDATES = 2000 if _VERBOSE else 200
_MAX_UPDATE_LINE_CHARS = 4000 if _VERBOSE else 800
_BUFFER_FLUSH_CHARS = 40 if _VERBOSE else 180


def _github_clone_url(repo: str, token: str | None = None) -> str:
    """Build the HTTPS clone URL for a GitHub repository.

    Delegates to :func:`helping_hands.lib.github_url.build_clone_url`.
    Kept as a module-level alias for backward compatibility with tests.
    """
    return _build_clone_url(repo, token=token)


def _repo_tmp_dir() -> Path | None:
    """Return the directory to use for temporary repo clones.

    Reads HELPING_HANDS_REPO_TMP; falls back to the OS default temp dir.
    """
    d = os.environ.get("HELPING_HANDS_REPO_TMP", "").strip()
    if d:
        p = Path(d).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return None


def _resolve_repo_path(
    repo: str,
    *,
    pr_number: int | None = None,
    token: str | None = None,
) -> tuple[Path, str | None, Path | None]:
    """Resolve local repo path or clone an owner/repo reference.

    Returns (repo_path, cloned_from, temp_root) where temp_root is the
    directory to clean up after use (None for local paths).

    When *pr_number* is given the clone uses ``--no-single-branch`` so that
    the PR branch can be fetched and pushed back without history issues.
    """
    path = Path(repo).expanduser().resolve()
    if path.is_dir():
        return path, None, None

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        dest_root = Path(mkdtemp(prefix="helping_hands_repo_", dir=_repo_tmp_dir()))
        dest = dest_root / "repo"
        url = _github_clone_url(repo, token=token)
        clone_cmd = ["git", "clone", "--depth", "1"]
        if pr_number is not None:
            clone_cmd.append("--no-single-branch")
        clone_cmd += [url, str(dest)]
        try:
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                check=False,
                env=_git_noninteractive_env(),
                timeout=_GIT_CLONE_TIMEOUT_S,
            )
        except TimeoutExpired as exc:
            shutil.rmtree(dest_root, ignore_errors=True)
            raise ValueError(
                f"git clone timed out after {_GIT_CLONE_TIMEOUT_S}s for {repo}"
            ) from exc
        if result.returncode != 0:
            shutil.rmtree(dest_root, ignore_errors=True)
            stderr = result.stderr.strip() or _UNKNOWN_CLONE_ERROR
            stderr = _redact_sensitive(stderr)
            msg = f"failed to clone {repo}: {stderr}"
            raise ValueError(msg)
        return dest.resolve(), repo, dest_root

    raise ValueError(f"{repo} is not a directory or owner/repo reference")


def _normalize_backend(backend: str | None) -> tuple[str, str]:
    """Resolve requested backend and runtime backend implementation."""
    requested = (backend or "codexcli").strip().lower()
    if requested not in _SUPPORTED_BACKENDS:
        choices = ", ".join(sorted(_SUPPORTED_BACKENDS))
        msg = f"unsupported backend {requested!r}; expected one of: {choices}"
        raise ValueError(msg)

    runtime = "basic-atomic" if requested == "basic-agent" else requested
    return requested, runtime


def _has_codex_auth() -> bool:
    """Return whether runtime has credentials for Codex CLI calls."""
    if os.environ.get("OPENAI_API_KEY"):
        return True
    auth_file = Path.home() / ".codex" / "auth.json"
    return auth_file.is_file()


def _has_gemini_auth() -> bool:
    """Return whether runtime has credentials for Gemini CLI calls."""
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _trim_updates(updates: list[str]) -> None:
    """Trim the update list in-place to at most ``_MAX_STORED_UPDATES`` entries.

    Removes the oldest entries (from the front) when the list exceeds the
    configured maximum length, keeping only the most recent updates.

    Args:
        updates: Mutable list of progress update strings to trim.
    """
    if len(updates) > _MAX_STORED_UPDATES:
        del updates[: len(updates) - _MAX_STORED_UPDATES]


def _append_update(updates: list[str], text: str) -> None:
    """Append a progress update line after stripping and truncating.

    Strips leading/trailing whitespace from *text*.  Empty or
    whitespace-only strings are silently ignored.  Lines longer than
    ``_MAX_UPDATE_LINE_CHARS`` are truncated with a ``...[truncated]``
    suffix.  After appending, the list is trimmed via
    :func:`_trim_updates`.

    Args:
        updates: Mutable list of progress update strings.
        text: Raw update text to clean and append.
    """
    clean = text.strip()
    if not clean:
        return
    if len(clean) > _MAX_UPDATE_LINE_CHARS:
        clean = clean[:_MAX_UPDATE_LINE_CHARS] + " " + _TRUNCATION_MARKER
    updates.append(clean)
    _trim_updates(updates)


class _UpdateCollector:
    """Collect and compact stream chunks into line-like update entries."""

    def __init__(self, updates: list[str]) -> None:
        """Initialise the collector with a shared update list.

        Args:
            updates: Mutable list that receives compacted update lines.
        """
        self._updates = updates
        self._buffer = ""

    def feed(self, chunk: str) -> None:
        """Ingest a raw stream chunk, splitting on newlines.

        Complete lines (terminated by ``\\n``) are immediately appended
        via :func:`_append_update`.  Partial lines are buffered until
        the next newline arrives or the buffer reaches
        ``_BUFFER_FLUSH_CHARS``, at which point it is flushed as a
        standalone update.  Empty chunks are silently ignored.

        Args:
            chunk: Raw text fragment from the AI stream.
        """
        if not chunk:
            return
        self._buffer += chunk
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            _append_update(self._updates, line)
        if len(self._buffer) >= _BUFFER_FLUSH_CHARS:
            _append_update(self._updates, self._buffer)
            self._buffer = ""

    def flush(self) -> None:
        """Flush any remaining buffered text as a final update line.

        Should be called when the stream ends to ensure the last
        partial line is not lost.
        """
        if self._buffer:
            _append_update(self._updates, self._buffer)
            self._buffer = ""


def _update_progress(
    task: object,
    *,
    task_id: str | None,
    stage: str,
    updates: list[str],
    prompt: str,
    pr_number: int | None,
    backend: str,
    runtime_backend: str,
    repo_path: str,
    model: str | None,
    max_iterations: int,
    no_pr: bool,
    enable_execution: bool,
    enable_web: bool,
    use_native_cli_auth: bool,
    tools: tuple[str, ...],
    skills: tuple[str, ...],
    fix_ci: bool = False,
    ci_check_wait_minutes: float = 3.0,
    reference_repos: list[str] | None = None,
    workspace: str | None = None,
    started_at: str | None = None,
) -> None:
    """Push a PROGRESS state update to Celery for the running task.

    Builds a metadata dict from all keyword arguments and calls
    ``task.update_state(state="PROGRESS", meta=...)``.  If *task* does
    not expose a callable ``update_state`` attribute (e.g. when running
    outside a Celery worker), the call is silently skipped.

    Args:
        task: The Celery task instance (or any object with an
            ``update_state`` method).
        task_id: Celery task identifier.
        stage: Human-readable stage label (e.g. ``"running"``,
            ``"finalizing"``).
        updates: List of progress update strings collected so far.
        prompt: Original user prompt for this build.
        pr_number: GitHub PR number if resuming an existing PR.
        backend: Requested backend name from the user.
        runtime_backend: Resolved runtime backend actually in use.
        repo_path: Local path to the repository being modified.
        model: AI model identifier, or ``None`` for default.
        max_iterations: Maximum number of agent iterations.
        no_pr: Whether PR creation is disabled.
        enable_execution: Whether command execution tools are enabled.
        enable_web: Whether web search/browse tools are enabled.
        use_native_cli_auth: Whether to use native CLI authentication.
        tools: Tuple of enabled tool category names.
        skills: Tuple of enabled skill names.
        fix_ci: Whether to attempt CI fix after PR creation.
        ci_check_wait_minutes: Minutes to wait for CI checks.
        reference_repos: Optional list of reference repo specs.
        workspace: Optional workspace identifier.
        started_at: ISO-format timestamp when the task started.
    """
    update_state = getattr(task, "update_state", None)
    if not callable(update_state):
        return
    meta: dict[str, Any] = {
        "task_id": task_id,
        "stage": stage,
        "prompt": prompt,
        "pr_number": pr_number,
        "backend": backend,
        "runtime_backend": runtime_backend,
        "repo_path": repo_path,
        "model": model,
        "max_iterations": max_iterations,
        "no_pr": no_pr,
        "enable_execution": enable_execution,
        "enable_web": enable_web,
        "use_native_cli_auth": use_native_cli_auth,
        "fix_ci": fix_ci,
        "ci_check_wait_minutes": ci_check_wait_minutes,
        "tools": list(tools),
        "skills": list(skills),
        "reference_repos": list(reference_repos or []),
        "updates": list(updates),
    }
    if workspace:
        meta["workspace"] = workspace
    if started_at:
        meta["started_at"] = started_at
    update_state(state="PROGRESS", meta=meta)


def _format_runtime(elapsed_seconds: float) -> str:
    """Format an elapsed time as a human-readable string.

    Returns ``"Xm Ys"`` when the elapsed time is at least one minute,
    otherwise ``"X.Ys"``.
    """
    minutes, seconds = divmod(elapsed_seconds, 60)
    if minutes >= 1:
        return f"{int(minutes)}m {seconds:.0f}s"
    return f"{seconds:.1f}s"


async def _collect_stream(
    hand: Any,
    prompt: str,
    *,
    task: object,
    task_id: str | None,
    pr_number: int | None,
    updates: list[str],
    backend: str,
    runtime_backend: str,
    repo_path: str,
    model: str | None,
    max_iterations: int,
    no_pr: bool,
    enable_execution: bool,
    enable_web: bool,
    use_native_cli_auth: bool,
    tools: tuple[str, ...],
    skills: tuple[str, ...],
    fix_ci: bool = False,
    ci_check_wait_minutes: float = 3.0,
    reference_repos: list[str] | None = None,
    workspace: str | None = None,
    started_at: str | None = None,
) -> str:
    parts: list[str] = []
    collector = _UpdateCollector(updates)
    chunk_count = 0

    async for chunk in hand.stream(prompt):
        text = str(chunk)
        parts.append(text)
        collector.feed(text)
        chunk_count += 1
        if chunk_count % (2 if _VERBOSE else 8) == 0:
            _update_progress(
                task,
                task_id=task_id,
                stage="running",
                updates=updates,
                prompt=prompt,
                pr_number=pr_number,
                backend=backend,
                runtime_backend=runtime_backend,
                repo_path=repo_path,
                model=model,
                max_iterations=max_iterations,
                no_pr=no_pr,
                enable_execution=enable_execution,
                enable_web=enable_web,
                use_native_cli_auth=use_native_cli_auth,
                tools=tools,
                skills=skills,
                fix_ci=fix_ci,
                ci_check_wait_minutes=ci_check_wait_minutes,
                reference_repos=reference_repos,
                workspace=workspace,
                started_at=started_at,
            )

    collector.flush()
    _update_progress(
        task,
        task_id=task_id,
        stage="running",
        updates=updates,
        prompt=prompt,
        pr_number=pr_number,
        backend=backend,
        runtime_backend=runtime_backend,
        repo_path=repo_path,
        model=model,
        max_iterations=max_iterations,
        no_pr=no_pr,
        enable_execution=enable_execution,
        enable_web=enable_web,
        use_native_cli_auth=use_native_cli_auth,
        tools=tools,
        skills=skills,
        fix_ci=fix_ci,
        ci_check_wait_minutes=ci_check_wait_minutes,
        reference_repos=reference_repos,
        workspace=workspace,
        started_at=started_at,
    )
    return "".join(parts)


@celery_app.task(bind=True, name="helping_hands.build_feature")
def build_feature(
    self: object,
    repo_path: str,
    prompt: str,
    pr_number: int | None = None,
    backend: str = "codexcli",
    model: str | None = None,
    max_iterations: int = 6,
    no_pr: bool = False,
    enable_execution: bool = False,
    enable_web: bool = False,
    use_native_cli_auth: bool = False,
    tools: list[str] | None = None,
    skills: list[str] | None = None,
    fix_ci: bool = False,
    ci_check_wait_minutes: float = 3.0,
    github_token: str | None = None,
    reference_repos: list[str] | None = None,
) -> dict[str, Any]:  # pragma: no cover - exercised in integration
    """Async task: run a hand against a GitHub repo with a user prompt.

    This is the primary unit of work in app mode. The server enqueues this
    task; a worker picks it up, runs the hand, and stores the result.
    The Celery task ID is used as the hand UUID.
    """
    from helping_hands.lib.config import Config, ConfigValue
    from helping_hands.lib.hands.v1.hand import (
        BasicAtomicHand,
        BasicLangGraphHand,
        ClaudeCodeHand,
        CodexCLIHand,
        DockerSandboxClaudeCodeHand,
        E2EHand,
        GeminiCLIHand,
        GooseCLIHand,
        OpenCodeCLIHand,
    )
    from helping_hands.lib.meta import skills as meta_skills
    from helping_hands.lib.meta.tools import registry as meta_tools
    from helping_hands.lib.repo import RepoIndex

    task_id = getattr(getattr(self, "request", None), "id", None)
    requested_backend, runtime_backend = _normalize_backend(backend)
    resolved_iterations = max(1, int(max_iterations))
    selected_tools = meta_tools.normalize_tool_selection(tools)
    meta_tools.validate_tool_category_names(selected_tools)
    selected_skills = meta_skills.normalize_skill_selection(skills)
    meta_skills.validate_skill_names(selected_skills)
    task_started_at = datetime.now(UTC).isoformat()
    updates: list[str] = []
    _append_update(
        updates,
        (
            f"Task received. backend={requested_backend}, model={model or 'default'}, "
            f"repo={repo_path}, max_iterations={resolved_iterations}, "
            f"no_pr={no_pr}, enable_execution={enable_execution}, "
            f"enable_web={enable_web}, use_native_cli_auth={use_native_cli_auth}, "
            f"tools={','.join(selected_tools) or 'none'}, "
            f"skills={','.join(selected_skills) or 'none'}, "
            f"reference_repos={','.join(reference_repos) if reference_repos else 'none'}"
        ),
    )
    _update_progress(
        self,
        task_id=task_id,
        stage="starting",
        updates=updates,
        prompt=prompt,
        pr_number=pr_number,
        backend=requested_backend,
        runtime_backend=runtime_backend,
        repo_path=repo_path,
        model=model,
        max_iterations=resolved_iterations,
        no_pr=no_pr,
        enable_execution=enable_execution,
        enable_web=enable_web,
        use_native_cli_auth=use_native_cli_auth,
        tools=selected_tools,
        skills=selected_skills,
        fix_ci=fix_ci,
        ci_check_wait_minutes=ci_check_wait_minutes,
        reference_repos=list(reference_repos or []),
        started_at=task_started_at,
    )

    if runtime_backend == "e2e":
        config = Config.from_env(
            overrides={
                "repo": repo_path,
                "model": model,
                "enable_execution": enable_execution,
                "enable_web": enable_web,
                "use_native_cli_auth": use_native_cli_auth,
                "enabled_tools": selected_tools,
                "enabled_skills": selected_skills,
                "github_token": github_token,
                "reference_repos": tuple(reference_repos) if reference_repos else (),
            }
        )
        repo_index = RepoIndex(root=Path(config.repo or "."), files=[])
        hand = E2EHand(config, repo_index)
        _append_update(updates, "Running E2E hand.")
        _update_progress(
            self,
            task_id=task_id,
            stage="running",
            updates=updates,
            prompt=prompt,
            pr_number=pr_number,
            backend=requested_backend,
            runtime_backend=runtime_backend,
            repo_path=repo_path,
            model=config.model,
            max_iterations=resolved_iterations,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            tools=selected_tools,
            skills=selected_skills,
            fix_ci=fix_ci,
            ci_check_wait_minutes=ci_check_wait_minutes,
            reference_repos=list(reference_repos or []),
            started_at=task_started_at,
        )
        response = hand.run(
            prompt,
            hand_uuid=task_id,
            pr_number=pr_number,
            dry_run=no_pr,
        )
        _append_update(updates, response.message)
        return {
            "status": "ok",
            "prompt": prompt,
            "pr_number": pr_number,
            "repo_path": repo_path,
            "backend": requested_backend,
            "runtime_backend": runtime_backend,
            "message": response.message,
            "updates": updates,
            **response.metadata,
        }

    try:
        resolved_repo_path, cloned_from, _tmp_root = _resolve_repo_path(
            repo_path, pr_number=pr_number, token=github_token
        )
    except ValueError as exc:
        _append_update(updates, f"Repo resolution failed: {exc}")
        raise

    try:
        overrides: dict[str, ConfigValue] = {
            "repo": str(resolved_repo_path),
            "model": model,
        }
        overrides["enable_execution"] = enable_execution
        overrides["enable_web"] = enable_web
        overrides["use_native_cli_auth"] = use_native_cli_auth
        overrides["enabled_tools"] = selected_tools
        overrides["enabled_skills"] = selected_skills
        overrides["github_token"] = github_token
        overrides["reference_repos"] = tuple(reference_repos) if reference_repos else ()
        config = Config.from_env(overrides=overrides)
        repo_index = RepoIndex.from_path(Path(config.repo))

        # Clone reference repos as read-only context
        ref_tmp_roots: list[Path] = []
        for ref_spec in config.reference_repos:
            try:
                _validate_repo_spec(ref_spec)
            except ValueError:
                _append_update(updates, f"Skipping invalid reference repo: {ref_spec}")
                continue
            ref_root = Path(
                mkdtemp(prefix=_ref_repo_tmp_prefix(ref_spec), dir=_repo_tmp_dir())
            )
            ref_tmp_roots.append(ref_root)
            ref_dest = ref_root / "repo"
            ref_url = _github_clone_url(ref_spec, token=config.github_token)
            try:
                ref_result = subprocess.run(
                    ["git", "clone", "--depth", "1", ref_url, str(ref_dest)],
                    capture_output=True,
                    text=True,
                    check=False,
                    env=_git_noninteractive_env(),
                    timeout=_GIT_CLONE_TIMEOUT_S,
                )
            except TimeoutExpired:
                _append_update(
                    updates,
                    f"Reference repo clone timed out: {ref_spec}",
                )
                continue
            if ref_result.returncode != 0:
                stderr = _redact_sensitive(
                    ref_result.stderr.strip() or _UNKNOWN_CLONE_ERROR
                )
                _append_update(
                    updates,
                    f"Failed to clone reference repo {ref_spec}: {stderr}",
                )
                continue
            repo_index.reference_repos.append((ref_spec, ref_dest.resolve()))
            _append_update(updates, f"Cloned reference repo {ref_spec}")

        if cloned_from:
            _append_update(updates, f"Cloned {cloned_from} to {resolved_repo_path}")
        if pr_number is not None and cloned_from:
            _append_update(updates, f"Checking out PR #{pr_number} branch...")
            from helping_hands.lib.github import GitHubClient as _GHClient

            with _GHClient() as _gh:
                _pr_info = _gh.get_pr(cloned_from, pr_number)
                _pr_branch = str(_pr_info["head"])
                _gh.fetch_branch(resolved_repo_path, _pr_branch)
                _gh.switch_branch(resolved_repo_path, _pr_branch)
                _gh.pull(resolved_repo_path, branch=_pr_branch)
            _append_update(
                updates,
                f"Checked out branch {_pr_branch} for PR #{pr_number} (up to date)",
            )
            repo_index = RepoIndex.from_path(Path(config.repo))
        if runtime_backend == "codexcli" and not _has_codex_auth():
            msg = (
                "Codex authentication is missing in worker runtime. "
                "Set OPENAI_API_KEY in .env and recreate containers, "
                "or run `codex login` in the worker environment."
            )
            _append_update(updates, msg)
            raise RuntimeError(msg)
        if runtime_backend == "geminicli" and not _has_gemini_auth():
            msg = (
                "Gemini authentication is missing in worker runtime. "
                "Set GEMINI_API_KEY in .env and recreate containers."
            )
            _append_update(updates, msg)
            raise RuntimeError(msg)
        _append_update(
            updates,
            (
                f"Running hand. backend={requested_backend} "
                f"(runtime={runtime_backend}), model={config.model}"
            ),
        )
        _update_progress(
            self,
            task_id=task_id,
            stage="running",
            updates=updates,
            prompt=prompt,
            pr_number=pr_number,
            backend=requested_backend,
            runtime_backend=runtime_backend,
            repo_path=repo_path,
            model=config.model,
            max_iterations=resolved_iterations,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            tools=selected_tools,
            skills=selected_skills,
            fix_ci=fix_ci,
            ci_check_wait_minutes=ci_check_wait_minutes,
            reference_repos=list(reference_repos or []),
            workspace=str(resolved_repo_path),
            started_at=task_started_at,
        )

        try:
            if runtime_backend == "basic-langgraph":
                hand = BasicLangGraphHand(
                    config,
                    repo_index,
                    max_iterations=resolved_iterations,
                )
            elif runtime_backend == "codexcli":
                hand = CodexCLIHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "claudecodecli":
                hand = ClaudeCodeHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "docker-sandbox-claude":
                hand = DockerSandboxClaudeCodeHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "goose":
                hand = GooseCLIHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "geminicli":
                hand = GeminiCLIHand(
                    config,
                    repo_index,
                )
            elif runtime_backend == "opencodecli":
                hand = OpenCodeCLIHand(
                    config,
                    repo_index,
                )
            else:
                hand = BasicAtomicHand(
                    config,
                    repo_index,
                    max_iterations=resolved_iterations,
                )
        except ModuleNotFoundError as exc:
            if runtime_backend == "basic-langgraph":
                extra = "langchain"
            elif runtime_backend in {"basic-atomic", "basic-agent"}:
                extra = "atomic"
            else:
                extra = None
            if extra:
                install_hint = f"Install with: uv sync --extra {extra}"
            else:
                install_hint = "Check runtime setup."
            msg = (
                f"Missing dependency for backend {requested_backend}:"
                f" {exc}. {install_hint}"
            )
            _append_update(updates, msg)
            raise RuntimeError(msg) from exc

        hand.auto_pr = not no_pr
        hand.pr_number = pr_number
        hand.fix_ci = fix_ci
        hand.ci_check_wait_minutes = ci_check_wait_minutes
        hand_start = time.monotonic()
        message = asyncio.run(
            _collect_stream(
                hand,
                prompt,
                task=self,
                task_id=task_id,
                pr_number=pr_number,
                updates=updates,
                backend=requested_backend,
                runtime_backend=runtime_backend,
                repo_path=repo_path,
                model=config.model,
                max_iterations=resolved_iterations,
                no_pr=no_pr,
                enable_execution=enable_execution,
                enable_web=enable_web,
                use_native_cli_auth=use_native_cli_auth,
                tools=selected_tools,
                skills=selected_skills,
                fix_ci=fix_ci,
                ci_check_wait_minutes=ci_check_wait_minutes,
                reference_repos=list(reference_repos or []),
                workspace=str(resolved_repo_path),
                started_at=task_started_at,
            )
        )
        hand_elapsed = time.monotonic() - hand_start
        runtime_str = _format_runtime(hand_elapsed)
        _append_update(updates, f"Task complete. Runtime: {runtime_str}")
        return {
            "status": "ok",
            "prompt": prompt,
            "pr_number": pr_number,
            "backend": requested_backend,
            "runtime_backend": runtime_backend,
            "repo": repo_path,
            "workspace": str(resolved_repo_path),
            "model": config.model,
            "started_at": task_started_at,
            "max_iterations": str(resolved_iterations),
            "no_pr": str(no_pr).lower(),
            "enable_execution": str(enable_execution).lower(),
            "enable_web": str(enable_web).lower(),
            "use_native_cli_auth": str(use_native_cli_auth).lower(),
            "fix_ci": str(fix_ci).lower(),
            "ci_check_wait_minutes": str(ci_check_wait_minutes),
            "tools": list(selected_tools),
            "skills": list(selected_skills),
            "runtime": runtime_str,
            "message": message,
            "updates": updates,
        }
    finally:
        if _tmp_root is not None:
            shutil.rmtree(_tmp_root, ignore_errors=True)
        for ref_root in ref_tmp_roots:
            shutil.rmtree(ref_root, ignore_errors=True)


@celery_app.task(bind=True, name="helping_hands.scheduled_build")
def scheduled_build(
    self: object,
    schedule_id: str,
) -> dict[str, Any]:  # pragma: no cover - exercised in integration
    """Execute a scheduled build task.

    This task is triggered by RedBeat scheduler and looks up the schedule
    configuration to run the appropriate build_feature task.
    """
    from helping_hands.server.schedules import get_schedule_manager

    manager = get_schedule_manager(celery_app)
    schedule = manager.get_schedule(schedule_id)

    if schedule is None:
        return {
            "status": "error",
            "message": f"Schedule {schedule_id} not found",
            "schedule_id": schedule_id,
        }

    if not schedule.enabled:
        return {
            "status": "skipped",
            "message": f"Schedule {schedule_id} is disabled",
            "schedule_id": schedule_id,
        }

    # Trigger the actual build task
    result = build_feature.delay(
        repo_path=schedule.repo_path,
        prompt=schedule.prompt,
        pr_number=schedule.pr_number,
        backend=schedule.backend,
        model=schedule.model,
        max_iterations=schedule.max_iterations,
        no_pr=schedule.no_pr,
        enable_execution=schedule.enable_execution,
        enable_web=schedule.enable_web,
        use_native_cli_auth=schedule.use_native_cli_auth,
        tools=getattr(schedule, "tools", []),
        skills=schedule.skills,
        fix_ci=getattr(schedule, "fix_ci", False),
        ci_check_wait_minutes=getattr(schedule, "ci_check_wait_minutes", 3.0),
        reference_repos=getattr(schedule, "reference_repos", []),
    )

    # Record the run
    manager.record_run(schedule_id, result.id)

    return {
        "status": "triggered",
        "schedule_id": schedule_id,
        "schedule_name": schedule.name,
        "build_task_id": result.id,
        "prompt": schedule.prompt,
        "repo_path": schedule.repo_path,
    }


def _get_db_url_writer() -> str:
    """Return the DATABASE_URL for writing (must point to a writer role).

    Raises:
        RuntimeError: If the ``DATABASE_URL`` environment variable is not set
            or is empty.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required for usage logging"
        )
    return url


_USAGE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS claude_usage_log (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_pct DOUBLE PRECISION,
    session_resets_at TEXT,
    weekly_pct DOUBLE PRECISION,
    weekly_resets_at TEXT,
    raw_response JSONB
);
"""

_USAGE_INSERT = """
INSERT INTO claude_usage_log
    (recorded_at, session_pct, session_resets_at, weekly_pct, weekly_resets_at, raw_response)
VALUES
    (NOW(), %s, %s, %s, %s, %s);
"""


@celery_app.task(name="helping_hands.log_claude_usage")
def log_claude_usage() -> dict[str, Any]:
    """Fetch Claude Code usage from the OAuth API and log it to Postgres."""
    import json as _json
    from urllib import error as _url_error
    from urllib import request as _url_request

    # --- Fetch OAuth token from macOS Keychain ---
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                _KEYCHAIN_SERVICE_NAME,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=_KEYCHAIN_TIMEOUT_S,
        )
        raw = result.stdout.strip() if result.returncode == 0 else ""
        try:
            creds = _json.loads(raw)
            token = creds.get(_KEYCHAIN_OAUTH_KEY, {}).get(_KEYCHAIN_ACCESS_TOKEN_KEY)
        except (_json.JSONDecodeError, AttributeError):
            token = raw if raw.startswith(_JWT_TOKEN_PREFIX) else None
    except Exception as exc:
        return {"status": "error", "message": f"Keychain read failed: {exc}"}

    if not token:
        return {"status": "error", "message": "No OAuth token found in Keychain"}

    # --- Call the Anthropic usage API ---
    try:
        req = _url_request.Request(
            _ANTHROPIC_USAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": _ANTHROPIC_BETA_HEADER,
                "User-Agent": _USAGE_USER_AGENT,
            },
        )
        with _url_request.urlopen(req, timeout=_USAGE_API_TIMEOUT_S) as resp:
            data = _json.loads(resp.read().decode())
    except _url_error.HTTPError as exc:
        return {"status": "error", "message": f"Usage API HTTP {exc.code}"}
    except Exception as exc:
        return {"status": "error", "message": f"Usage API failed: {exc}"}

    five_hour = data.get("five_hour", {})
    seven_day = data.get("seven_day", {})
    session_pct = five_hour.get("utilization")
    session_resets = five_hour.get("resets_at")
    weekly_pct = seven_day.get("utilization")
    weekly_resets = seven_day.get("resets_at")

    # --- Write to Postgres ---
    try:
        import psycopg2

        conn = psycopg2.connect(
            _get_db_url_writer(), connect_timeout=_DB_CONNECT_TIMEOUT_S
        )
        try:
            with conn.cursor() as cur:
                cur.execute(_USAGE_TABLE_DDL)
                cur.execute(
                    _USAGE_INSERT,
                    (
                        session_pct,
                        session_resets,
                        weekly_pct,
                        weekly_resets,
                        _json.dumps(data),
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        return {
            "status": "error",
            "message": f"DB write failed: {exc}",
            "session_pct": session_pct,
            "weekly_pct": weekly_pct,
        }

    return {
        "status": "ok",
        "session_pct": session_pct,
        "weekly_pct": weekly_pct,
    }


def ensure_usage_schedule() -> None:
    """Register the hourly claude-usage logging schedule in RedBeat (idempotent)."""
    try:
        from celery.schedules import schedule as interval_schedule
        from redbeat import RedBeatSchedulerEntry

        entry_name = "helping_hands:usage-logger"
        try:
            existing = RedBeatSchedulerEntry.from_key(
                f"redbeat:{entry_name}", app=celery_app
            )
            if existing:
                return  # already registered
        except Exception:
            logger.debug("Usage schedule entry not found, creating", exc_info=True)

        entry = RedBeatSchedulerEntry(
            name=entry_name,
            task="helping_hands.log_claude_usage",
            schedule=interval_schedule(run_every=_USAGE_LOG_INTERVAL_S),
            app=celery_app,
        )
        entry.save()
    except Exception:
        logger.debug(
            "Failed to register usage schedule (Redis/redbeat unavailable)",
            exc_info=True,
        )


@celery_app.on_after_finalize.connect  # type: ignore[union-attr]
def _setup_periodic_tasks(sender: Any, **_kwargs: Any) -> None:
    """Register periodic tasks after Celery app finalization.

    Connected to ``celery_app.on_after_finalize`` signal.  Delegates to
    :func:`ensure_usage_schedule` to idempotently register the hourly
    Claude usage logging schedule in RedBeat.

    Args:
        sender: The Celery app instance that emitted the signal.
    """
    ensure_usage_schedule()
