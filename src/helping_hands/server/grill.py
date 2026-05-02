"""Grill Me: interactive AI interview sessions.

This module implements a long-running Celery task that maintains a
multi-turn conversation between the user and an AI interviewer.  The AI
explores the target codebase and relentlessly grills the user about their
plan until a shared understanding is reached.

Communication uses Redis lists as message queues:
- ``grill:{session_id}:user_msgs``  — user → worker (JSON-encoded dicts)
- ``grill:{session_id}:ai_msgs``    — worker → frontend (JSON-encoded dicts)
- ``grill:{session_id}:state``      — session metadata (JSON string)

Each AI turn is a separate ``claude -p`` subprocess call.  The first call
uses ``--session-id`` to create a named session; subsequent calls use
``--resume`` to continue that session.  This reuses the Claude Code CLI
infrastructure and maintains full conversation state natively.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from subprocess import TimeoutExpired
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any

from helping_hands.lib.github_url import (
    DEFAULT_CLONE_ERROR_MSG as _DEFAULT_CLONE_ERROR_MSG,
    GIT_CLONE_TIMEOUT_S as _GIT_CLONE_TIMEOUT_S,
    REPO_SPEC_PATTERN as _REPO_SPEC_PATTERN,
    build_clone_url as _build_clone_url,
    noninteractive_env as _git_noninteractive_env,
    redact_credentials as _redact_sensitive,
    repo_tmp_dir as _repo_tmp_dir,
    validate_repo_spec as _validate_repo_spec,
)
from helping_hands.lib.repo import RepoIndex

if TYPE_CHECKING:
    from celery import Task

logger = logging.getLogger(__name__)

__all__ = ["grill_session", "resume_grill_session"]

# --- Constants ---------------------------------------------------------------

_SESSION_TTL_S = 3600
"""Sessions expire from Redis after 1 hour of inactivity."""

_POLL_INTERVAL_S = 1.0
"""How often the worker checks for new user messages."""

_IDLE_SUSPEND_S = 300
"""Seconds of inactivity before the worker suspends (session stays resumable)."""

_MAX_CONVERSATION_TURNS = 100
"""Hard limit on total conversation turns to prevent runaway sessions."""

_CLAUDE_TURN_TIMEOUT_S = 300
"""Max seconds to wait for a single Claude CLI response."""

_CODEX_TURN_TIMEOUT_S = 300
"""Max seconds to wait for a single Codex CLI response."""


# --- Redis helpers -----------------------------------------------------------


def _redis_client() -> Any:
    """Get a Redis client from the Celery broker connection pool."""
    import redis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(redis_url, decode_responses=True)


def _set_state(r: Any, session_id: str, state: dict[str, Any]) -> None:
    """Write session state to Redis with TTL refresh."""
    key = f"grill:{session_id}:state"
    r.set(key, json.dumps(state), ex=_SESSION_TTL_S)


def _get_state(r: Any, session_id: str) -> dict[str, Any] | None:
    """Read session state from Redis."""
    key = f"grill:{session_id}:state"
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def _push_ai_msg(
    r: Any,
    session_id: str,
    role: str,
    content: str,
    *,
    msg_type: str = "message",
) -> None:
    """Push an AI message to the outbound queue.

    Also appends to a persistent transcript list used to repopulate the chat
    view when a suspended session is resumed (the queue is drained
    destructively by polling, so it can't serve as history on its own).
    """
    payload = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "type": msg_type,
        "timestamp": time.time(),
    }
    encoded = json.dumps(payload)
    queue_key = f"grill:{session_id}:ai_msgs"
    transcript_key = f"grill:{session_id}:transcript"
    r.rpush(queue_key, encoded)
    r.expire(queue_key, _SESSION_TTL_S)
    r.rpush(transcript_key, encoded)
    r.expire(transcript_key, _SESSION_TTL_S)


def _pop_user_msg(r: Any, session_id: str) -> dict[str, Any] | None:
    """Pop the next user message from the inbound queue (non-blocking)."""
    key = f"grill:{session_id}:user_msgs"
    raw = r.lpop(key)
    if raw is None:
        return None
    return json.loads(raw)


def _save_resume_state(r: Any, session_id: str, state: dict[str, Any]) -> None:
    """Persist state needed to resume a suspended session."""
    key = f"grill:{session_id}:resume"
    r.set(key, json.dumps(state), ex=_SESSION_TTL_S)


def _load_resume_state(r: Any, session_id: str) -> dict[str, Any] | None:
    """Load previously saved resume state."""
    key = f"grill:{session_id}:resume"
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def _clear_resume_state(r: Any, session_id: str) -> None:
    """Remove resume state after a session resumes or completes."""
    r.delete(f"grill:{session_id}:resume")


# --- CLI diagnostics ---------------------------------------------------------


def _cli_not_found_diagnostics(
    binary: str,
    *,
    exc: FileNotFoundError | None = None,
    cwd: str | None = None,
) -> str:
    """Build a short, low-disclosure diagnostic suffix for CLI-missing errors.

    Surfaced in the chat view and persisted to the transcript, so it must
    avoid leaking the full ``PATH`` (which contains the deployer's home dir,
    custom worktrees, etc.). We expose only:

    - ``shutil.which(binary)`` — tells us whether the worker can see the
      binary at all.
    - ``shutil.which("node")`` — node-based CLIs may have a node shebang;
      if node isn't on PATH the kernel surfaces ``ENOENT`` for the wrapper.
    - The original ``FileNotFoundError``'s ``errno`` and ``filename`` —
      ``Popen`` can raise this for the missing executable *or* a missing
      ``cwd``. ``filename`` (when set by Python) disambiguates which.
    - ``cwd`` plus its existence flag — covers the "tmp clone dir got
      reaped between turns" case where ``cwd`` is the actual culprit.
    - Boolean flags for the per-user bin dirs ``augment_path_for_cli_hands``
      is supposed to add (under tilde labels so they don't collide).
    """
    resolved = shutil.which(binary) or "not found"
    node = shutil.which("node") or "not found"
    home = os.path.expanduser("~")
    path_entries = (os.environ.get("PATH") or "").split(os.pathsep)
    candidate_dirs = [
        (f"{home}/.local/bin", "~/.local/bin"),
        (f"{home}/.npm-global/bin", "~/.npm-global/bin"),
    ]
    flags = ", ".join(
        f"{label}={'yes' if abs_path in path_entries else 'no'}"
        for abs_path, label in candidate_dirs
    )

    parts = [f"which={resolved}", f"node={node}"]
    if cwd is not None:
        parts.append(f"cwd={cwd}")
        parts.append(f"cwd-exists={'yes' if os.path.isdir(cwd) else 'no'}")
    if exc is not None:
        parts.append(f"exc-filename={exc.filename or 'none'}")
        parts.append(f"exc-errno={exc.errno or 'none'}")
    parts.append(f"path-has[{flags}]")
    return " (" + "; ".join(parts) + ")"


# --- Repo helpers ------------------------------------------------------------


def _build_system_prompt(repo_index: RepoIndex, user_prompt: str) -> str:
    """Build the grill-me system prompt with repo context injected."""
    readme_content = ""
    for candidate in ("README.md", "README.rst", "README.txt", "README"):
        readme_path = repo_index.root / candidate
        if readme_path.is_file():
            try:
                readme_content = readme_path.read_text(errors="replace")[:8000]
                break
            except OSError:
                pass

    file_tree = "\n".join(f"  {f}" for f in repo_index.files[:500])
    if len(repo_index.files) > 500:
        file_tree += f"\n  ... and {len(repo_index.files) - 500} more files"

    ref_section = ""
    if repo_index.reference_repos:
        ref_parts = []
        for name, path in repo_index.reference_repos:
            try:
                ref_idx = RepoIndex.from_path(path)
                ref_tree = "\n".join(f"    {f}" for f in ref_idx.files[:200])
                ref_parts.append(f"  [{name}]\n{ref_tree}")
            except Exception:
                ref_parts.append(f"  [{name}] (failed to index)")
        ref_section = "\n\nReference repositories:\n" + "\n".join(ref_parts)

    readme_block = (
        f"README.md content:\n{readme_content}"
        if readme_content
        else "No README found."
    )

    return (
        "Interview me about every aspect of this plan until we reach a shared "
        "understanding. Walk down each branch of the design tree, resolving "
        "dependencies between decisions one-by-one. For each question, provide "
        "your recommended answer.\n\n"
        "Ask the questions one at a time.\n\n"
        "If a question can be answered by exploring the codebase, explore the "
        "codebase instead.\n\n"
        "IMPORTANT: You are ONLY interviewing and planning. Do NOT write, "
        "edit, or create any files. Do NOT implement any changes. Your job "
        "is to ask questions and produce a plan, nothing else.\n\n"
        "Once you feel all major branches of the decision tree have been "
        "resolved and you have enough detail to produce an actionable plan, "
        "STOP asking questions and immediately output your final consolidated "
        'plan prefixed with "## FINAL PLAN" on its own line. Do not ask for '
        "confirmation before producing the plan — just produce it when ready. "
        "The user can always ask you to keep grilling if they want more depth.\n\n"
        f"## Codebase Context\n\n"
        f"Repository root: {repo_index.root}\n\n"
        f"File tree:\n{file_tree}\n"
        f"{ref_section}\n\n"
        f"{readme_block}\n\n"
        f"## User's Plan/Task\n\n{user_prompt}"
    )


def _clone_repo(
    repo_path: str,
    github_token: str | None,
) -> tuple[Path, str | None, Path | None]:
    """Clone a repo spec to a temp directory, or use a local path."""
    path = Path(repo_path).expanduser().resolve()
    if path.is_dir():
        return path, None, None

    if re.fullmatch(_REPO_SPEC_PATTERN, repo_path):
        dest_root = Path(mkdtemp(prefix="helping_hands_grill_", dir=_repo_tmp_dir()))
        dest = dest_root / "repo"
        url = _build_clone_url(repo_path, token=github_token)
        clone_cmd = ["git", "clone", "--depth", "1", url, str(dest)]
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
                f"git clone timed out after {_GIT_CLONE_TIMEOUT_S}s for {repo_path}"
            ) from exc
        if result.returncode != 0:
            shutil.rmtree(dest_root, ignore_errors=True)
            stderr = result.stderr.strip() or _DEFAULT_CLONE_ERROR_MSG
            stderr = _redact_sensitive(stderr)
            raise ValueError(f"failed to clone {repo_path}: {stderr}")
        return dest.resolve(), repo_path, dest_root

    raise ValueError(f"Invalid repo path: {repo_path}")


# --- Claude CLI turn execution -----------------------------------------------

# Tool name → input key for one-line summaries
_TOOL_SUMMARY_KEY: dict[str, str] = {
    "Read": "file_path",
    "Glob": "pattern",
}


def _summarize_tool_use(name: str, input_data: dict) -> str:
    """Build a short human-readable summary of a tool call."""
    key = _TOOL_SUMMARY_KEY.get(name)
    if key:
        return f"{name} {input_data.get(key, '')}"
    if name == "Grep":
        pattern = input_data.get("pattern", "")
        return f"Grep /{pattern}/"
    return f"tool: {name}"


def _invoke_claude_turn(
    *,
    prompt: str,
    cwd: str,
    claude_session_id: str,
    is_first_turn: bool,
    system_prompt: str | None = None,
    model: str | None = None,
    github_token: str | None = None,
    on_status: Any | None = None,
) -> str:
    """Execute a single Claude CLI turn and return the response text.

    Uses ``--output-format stream-json --verbose`` so we can parse
    intermediate events (thinking, tool use) and push them to the
    frontend via the *on_status* callback in real-time.

    Args:
        prompt: The user message for this turn.
        cwd: Working directory (repo root).
        claude_session_id: UUID for the Claude session.
        is_first_turn: Whether this is the first turn (creates session).
        system_prompt: System prompt (only used on first turn).
        model: Model override.
        github_token: Optional GitHub token for env.
        on_status: Optional ``(text: str) -> None`` callback for
            intermediate status messages (thinking, tool use, etc.).

    Returns:
        The assistant's response text.

    Raises:
        RuntimeError: If Claude CLI is not found or returns an error.
    """
    cmd = [
        "claude",
        "-p",
        "--dangerously-skip-permissions",
        "--output-format",
        "stream-json",
        "--verbose",
    ]

    if is_first_turn:
        cmd.extend(["--session-id", claude_session_id])
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])
    else:
        cmd.extend(["--resume", claude_session_id])

    if model:
        cmd.extend(["--model", model])

    # Read-only: explicitly deny all write/execute tools so the grill session
    # can only explore the codebase, never modify it.
    cmd.extend(
        [
            "--allowedTools",
            "Read,Glob,Grep",
            "--disallowedTools",
            "Edit,Write,Bash,Agent,NotebookEdit,TodoWrite,WebFetch,WebSearch",
        ]
    )

    env = os.environ.copy()
    if github_token:
        env["GITHUB_TOKEN"] = github_token

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Claude Code CLI ('claude') is not installed or not on PATH. "
            "Install with: npm install -g @anthropic-ai/claude-code"
            + _cli_not_found_diagnostics("claude", exc=exc, cwd=cwd)
        ) from exc

    # Write prompt to stdin and close it
    try:
        proc.stdin.write(prompt.encode("utf-8"))
        proc.stdin.close()
    except OSError as exc:
        proc.kill()
        raise RuntimeError(f"Failed to send prompt to Claude CLI: {exc}") from exc

    # Stream stdout line-by-line, parsing stream-json events
    result_text = ""
    text_parts: list[str] = []
    emitted_thinking = False
    stdout = proc.stdout
    assert stdout is not None  # guaranteed by Popen(stdout=PIPE)

    try:
        for raw_line in stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(event, dict):
                continue

            event_type = event.get("type", "")

            if event_type == "assistant":
                message = event.get("message", {})
                if not isinstance(message, dict):
                    continue
                for block in message.get("content", []):
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type", "")

                    if block_type == "thinking" and on_status:
                        # Emit a short "Thinking..." status once
                        if not emitted_thinking:
                            on_status("Thinking...")
                            emitted_thinking = True

                    elif block_type == "tool_use" and on_status:
                        name = block.get("name", "unknown")
                        input_data = block.get("input", {})
                        summary = _summarize_tool_use(name, input_data)
                        on_status(f"Exploring: {summary}")
                        emitted_thinking = False

                    elif block_type == "text":
                        text = block.get("text", "")
                        if text:
                            text_parts.append(text)

            elif event_type == "result":
                result_text = event.get("result", "")
                cost = event.get("total_cost_usd")
                duration = event.get("duration_ms")
                if on_status and (cost is not None or duration is not None):
                    parts: list[str] = []
                    if duration is not None:
                        parts.append(f"{duration / 1000:.1f}s")
                    if cost is not None:
                        parts.append(f"${cost:.4f}")
                    on_status(f"Turn complete ({', '.join(parts)})")

    except Exception:
        logger.exception("Error reading Claude CLI stream")
    finally:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    if proc.returncode != 0:
        stderr = proc.stderr.read().decode("utf-8", errors="replace").strip()
        error_text = stderr or f"exit code {proc.returncode}"
        raise RuntimeError(f"Claude CLI error: {error_text[:500]}")

    return result_text or "\n".join(text_parts)


# --- Codex CLI turn execution ------------------------------------------------


def _build_codex_full_prompt(
    system_prompt: str,
    conversation_history: list[dict[str, str]],
    user_message: str,
) -> str:
    """Build a single prompt embedding system context, history, and new message.

    Codex CLI has no native session/resume capability, so every turn must
    include the full conversation transcript.

    Args:
        system_prompt: System instructions + repo context (from
            :func:`_build_system_prompt`).
        conversation_history: Prior turns as ``[{"role": "assistant"|"user",
            "content": "..."}]``.
        user_message: The new user message for this turn.

    Returns:
        A single string suitable for passing directly to ``codex exec``.
    """
    if conversation_history:
        history_parts: list[str] = []
        for turn in conversation_history:
            prefix = "AI" if turn["role"] == "assistant" else "User"
            history_parts.append(f"{prefix}: {turn['content']}")
        history_block = "\n\n".join(history_parts)
        return (
            f"{system_prompt}\n\n"
            f"---\nConversation so far:\n\n{history_block}\n\n"
            f"---\nUser: {user_message}\n\n"
            "Respond as the AI interviewer. Output only your reply with no 'AI:' prefix."
        )
    return (
        f"{system_prompt}\n\n"
        f"User: {user_message}\n\n"
        "Begin the interview. Output only your reply with no 'AI:' prefix."
    )


def _invoke_codex_turn(
    *,
    user_message: str,
    cwd: str,
    system_prompt: str,
    conversation_history: list[dict[str, str]],
    model: str | None = None,
    on_status: Any | None = None,
) -> str:
    """Execute a single Codex CLI turn and return the response text.

    Codex CLI has no native session/resume capability, so the full
    conversation history is embedded in each invocation prompt.

    Args:
        user_message: The new user message for this turn.
        cwd: Working directory (repo root).
        system_prompt: System instructions + repo context.
        conversation_history: Prior turns as ``[{"role", "content"}]``.
        model: Model override (e.g. ``"gpt-5.2"``).
        on_status: Optional ``(text: str) -> None`` callback for status.

    Returns:
        The assistant's response text.

    Raises:
        RuntimeError: If Codex CLI is not found, times out, or returns an error.
    """
    from pathlib import Path

    full_prompt = _build_codex_full_prompt(
        system_prompt, conversation_history, user_message
    )

    sandbox_mode = (os.environ.get("HELPING_HANDS_CODEX_SANDBOX_MODE") or "").strip()
    if not sandbox_mode:
        sandbox_mode = (
            "danger-full-access" if Path("/.dockerenv").exists() else "workspace-write"
        )

    cmd = [
        "codex",
        "exec",
        "--sandbox",
        sandbox_mode,
        "--skip-git-repo-check",
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.append(full_prompt)

    if on_status:
        on_status("Thinking...")

    env = os.environ.copy()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=_CODEX_TURN_TIMEOUT_S,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Codex CLI ('codex') is not installed or not on PATH. "
            "Install with: npm install -g @openai/codex"
            + _cli_not_found_diagnostics("codex", exc=exc, cwd=cwd)
        ) from exc
    except TimeoutExpired as exc:
        raise RuntimeError(
            f"Codex CLI timed out after {_CODEX_TURN_TIMEOUT_S}s"
        ) from exc

    if on_status:
        on_status("Turn complete")

    if result.returncode != 0:
        error_text = result.stderr.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Codex CLI error: {error_text[:500]}")

    return result.stdout.strip()


# --- Celery task -------------------------------------------------------------

try:  # pragma: no cover — requires celery extra
    from helping_hands.server.celery_app import celery_app as _celery_app

    @_celery_app.task(bind=True, name="helping_hands.grill_session")
    def grill_session(
        self: Task,
        repo_path: str,
        prompt: str,
        model: str | None = None,
        github_token: str | None = None,
        reference_repos: list[str] | None = None,
        backend: str = "claudecodecli",
    ) -> dict[str, Any]:
        """Long-running Celery task for interactive grill sessions.

        Clones the repo, builds context, then enters a message loop.
        Supports ``claudecodecli`` (default) and ``codexcli`` backends.
        """
        return _grill_session_body(
            self, repo_path, prompt, model, github_token, reference_repos, backend
        )

    @_celery_app.task(bind=True, name="helping_hands.resume_grill_session")
    def resume_grill_session(
        self: Task,
        original_session_id: str,
    ) -> dict[str, Any]:
        """Resume a suspended grill session.

        Loads saved state from Redis and re-enters the message loop
        using the original Claude session ID (for --resume) or Codex
        conversation history.
        """
        return _resume_grill_session_body(self, original_session_id)

except ImportError:
    pass


def _grill_session_body(  # pragma: no cover — requires celery + redis
    self: Task,
    repo_path: str,
    prompt: str,
    model: str | None = None,
    github_token: str | None = None,
    reference_repos: list[str] | None = None,
    backend: str = "claudecodecli",
) -> dict[str, Any]:
    """Long-running Celery task for interactive grill sessions.

    Clones the repo, builds context, then enters a message loop.
    Supports ``claudecodecli`` (uses ``--session-id``/``--resume``) and
    ``codexcli`` (embeds full conversation history in each prompt).
    """
    session_id = self.request.id
    r = _redis_client()
    tmp_roots: list[Path] = []
    # Set to True when the task suspends — the resumed task takes ownership
    # of cleanup, so we must NOT rmtree the clone dirs out from under it.
    suspended = False
    # Separate UUID for the Claude CLI session (Celery task IDs aren't
    # always valid UUIDs in the format Claude expects).
    claude_session_id = str(uuid.uuid4())
    use_codex = backend == "codexcli"
    # Conversation history for Codex (stateless) turns
    codex_history: list[dict[str, str]] = []

    try:
        # -- Set initial state -------------------------------------------------
        _set_state(
            r,
            session_id,
            {
                "status": "cloning",
                "repo_path": repo_path,
                "prompt": prompt,
                "model": model,
                "backend": backend,
                "turn_count": 0,
            },
        )

        # -- Clone repo --------------------------------------------------------
        _push_ai_msg(r, session_id, "system", "Cloning repository...")
        try:
            resolved_path, _cloned_from, tmp_root = _clone_repo(repo_path, github_token)
        except ValueError as exc:
            _push_ai_msg(r, session_id, "system", f"Error: {exc}", msg_type="error")
            _set_state(r, session_id, {"status": "error", "error": str(exc)})
            return {"status": "error", "error": str(exc)}

        if tmp_root:
            tmp_roots.append(tmp_root)

        # -- Index repo --------------------------------------------------------
        _push_ai_msg(r, session_id, "system", "Indexing repository...")
        repo_index = RepoIndex.from_path(resolved_path)

        # -- Clone reference repos ---------------------------------------------
        for ref_spec in reference_repos or []:
            try:
                _validate_repo_spec(ref_spec)
            except ValueError:
                _push_ai_msg(
                    r,
                    session_id,
                    "system",
                    f"Skipping invalid reference repo: {ref_spec}",
                )
                continue
            safe_name = ref_spec.replace("/", "_")
            ref_root = Path(
                mkdtemp(
                    prefix=f"helping_hands_grill_ref_{safe_name}_",
                    dir=_repo_tmp_dir(),
                )
            )
            tmp_roots.append(ref_root)
            ref_dest = ref_root / "repo"
            ref_url = _build_clone_url(ref_spec, token=github_token)
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
                _push_ai_msg(
                    r,
                    session_id,
                    "system",
                    f"Reference repo clone timed out: {ref_spec}",
                )
                continue
            if ref_result.returncode != 0:
                stderr = _redact_sensitive(
                    ref_result.stderr.strip() or _DEFAULT_CLONE_ERROR_MSG
                )
                _push_ai_msg(
                    r,
                    session_id,
                    "system",
                    f"Failed to clone reference repo {ref_spec}: {stderr}",
                )
                continue
            repo_index.reference_repos.append((ref_spec, ref_dest.resolve()))
            _push_ai_msg(
                r,
                session_id,
                "system",
                f"Cloned reference repo: {ref_spec}",
            )

        # -- Build system prompt -----------------------------------------------
        system_prompt = _build_system_prompt(repo_index, prompt)
        cwd = str(resolved_path)
        resolved_model = model or ""

        def _emit_status(text: str) -> None:
            """Push an intermediate status message to the frontend."""
            _push_ai_msg(r, session_id, "system", text)

        backend_label = "Codex CLI" if use_codex else "Claude Code CLI"
        _push_ai_msg(
            r,
            session_id,
            "system",
            f"Starting grill session{f' with {resolved_model}' if resolved_model else ''} ({backend_label})...",
        )

        _set_state(
            r,
            session_id,
            {
                "status": "thinking",
                "repo_path": repo_path,
                "prompt": prompt,
                "model": resolved_model,
                "backend": backend,
                "turn_count": 0,
            },
        )

        # -- First turn: send the plan and get the first question --------------
        _first_turn_msg = (
            "Begin the interview. Start with the highest-level "
            "architectural question about this plan."
        )
        try:
            if use_codex:
                ai_text = _invoke_codex_turn(
                    user_message=_first_turn_msg,
                    cwd=cwd,
                    system_prompt=system_prompt,
                    conversation_history=codex_history,
                    model=resolved_model or None,
                    on_status=_emit_status,
                )
            else:
                ai_text = _invoke_claude_turn(
                    prompt=_first_turn_msg,
                    cwd=cwd,
                    claude_session_id=claude_session_id,
                    is_first_turn=True,
                    system_prompt=system_prompt,
                    model=resolved_model or None,
                    github_token=github_token,
                    on_status=_emit_status,
                )
        except RuntimeError as exc:
            _push_ai_msg(r, session_id, "system", str(exc), msg_type="error")
            _set_state(r, session_id, {"status": "error", "error": str(exc)})
            return {"status": "error", "error": str(exc)}

        turn_count = 1

        # Track history for Codex stateless turns
        if use_codex:
            codex_history.append({"role": "assistant", "content": ai_text})

        is_final = "## FINAL PLAN" in ai_text
        msg_type = "plan" if is_final else "message"
        _push_ai_msg(r, session_id, "assistant", ai_text, msg_type=msg_type)

        if is_final:
            _set_state(
                r,
                session_id,
                {
                    "status": "completed",
                    "repo_path": repo_path,
                    "prompt": prompt,
                    "model": resolved_model,
                    "backend": backend,
                    "turn_count": turn_count,
                },
            )
            return {"status": "completed", "turn_count": turn_count}

        _set_state(
            r,
            session_id,
            {
                "status": "active",
                "repo_path": repo_path,
                "prompt": prompt,
                "model": resolved_model,
                "backend": backend,
                "turn_count": turn_count,
            },
        )

        # -- Message loop ------------------------------------------------------
        last_activity = time.monotonic()

        while turn_count < _MAX_CONVERSATION_TURNS:
            user_msg = _pop_user_msg(r, session_id)

            if user_msg is None:
                if time.monotonic() - last_activity > _IDLE_SUSPEND_S:
                    # Suspend: save state so the session can be resumed later.
                    # Pass tmp_roots through so the resumed task can clean up
                    # — and skip our own cleanup so the clone dir survives.
                    _save_resume_state(
                        r,
                        session_id,
                        {
                            "claude_session_id": claude_session_id,
                            "codex_history": codex_history,
                            "cwd": cwd,
                            "system_prompt": system_prompt,
                            "model": resolved_model,
                            "repo_path": repo_path,
                            "prompt": prompt,
                            "backend": backend,
                            "turn_count": turn_count,
                            "use_codex": use_codex,
                            "github_token": github_token,
                            "tmp_roots": [str(p) for p in tmp_roots],
                        },
                    )
                    _set_state(
                        r,
                        session_id,
                        {
                            "status": "suspended",
                            "repo_path": repo_path,
                            "prompt": prompt,
                            "model": resolved_model,
                            "backend": backend,
                            "turn_count": turn_count,
                        },
                    )
                    suspended = True
                    return {"status": "suspended", "turn_count": turn_count}

                state = _get_state(r, session_id)
                if state and state.get("status") == "ending":
                    break

                time.sleep(_POLL_INTERVAL_S)
                continue

            last_activity = time.monotonic()
            user_text = user_msg.get("content", "")

            if user_msg.get("type") == "end":
                user_text = (
                    f"{user_text}\n\n"
                    "Based on our discussion, please produce the final "
                    "consolidated plan. Start with '## FINAL PLAN' on its "
                    "own line, then provide the complete plan."
                )

            _set_state(
                r,
                session_id,
                {
                    "status": "thinking",
                    "repo_path": repo_path,
                    "prompt": prompt,
                    "model": resolved_model,
                    "backend": backend,
                    "turn_count": turn_count,
                },
            )

            try:
                if use_codex:
                    ai_text = _invoke_codex_turn(
                        user_message=user_text,
                        cwd=cwd,
                        system_prompt=system_prompt,
                        conversation_history=codex_history,
                        model=resolved_model or None,
                        on_status=_emit_status,
                    )
                else:
                    ai_text = _invoke_claude_turn(
                        prompt=user_text,
                        cwd=cwd,
                        claude_session_id=claude_session_id,
                        is_first_turn=False,
                        model=resolved_model or None,
                        github_token=github_token,
                        on_status=_emit_status,
                    )
            except RuntimeError as exc:
                cli_label = "Codex" if use_codex else "Claude"
                logger.exception(
                    "%s CLI failed in grill session %s", cli_label, session_id
                )
                _push_ai_msg(r, session_id, "system", str(exc), msg_type="error")
                # Don't end session — let user retry
                _set_state(
                    r,
                    session_id,
                    {
                        "status": "active",
                        "repo_path": repo_path,
                        "prompt": prompt,
                        "model": resolved_model,
                        "backend": backend,
                        "turn_count": turn_count,
                    },
                )
                continue

            turn_count += 1

            if not ai_text:
                _push_ai_msg(
                    r,
                    session_id,
                    "system",
                    "No response received from AI.",
                    msg_type="error",
                )
                continue

            # Record the exchange in Codex history
            if use_codex:
                codex_history.append({"role": "user", "content": user_text})
                codex_history.append({"role": "assistant", "content": ai_text})

            is_final = "## FINAL PLAN" in ai_text
            msg_type_out = "plan" if is_final else "message"
            _push_ai_msg(r, session_id, "assistant", ai_text, msg_type=msg_type_out)

            _set_state(
                r,
                session_id,
                {
                    "status": "completed" if is_final else "active",
                    "repo_path": repo_path,
                    "prompt": prompt,
                    "model": resolved_model,
                    "backend": backend,
                    "turn_count": turn_count,
                },
            )

            if is_final:
                return {"status": "completed", "turn_count": turn_count}

        _push_ai_msg(
            r,
            session_id,
            "system",
            "Maximum conversation turns reached.",
            msg_type="timeout",
        )
        _set_state(r, session_id, {"status": "max_turns", "turn_count": turn_count})
        return {"status": "max_turns", "turn_count": turn_count}

    except Exception as exc:
        logger.exception("Grill session %s failed", session_id)
        try:
            _push_ai_msg(
                r,
                session_id,
                "system",
                f"Session error: {exc}",
                msg_type="error",
            )
            _set_state(r, session_id, {"status": "error", "error": str(exc)})
        except Exception:
            pass
        return {"status": "error", "error": str(exc)}

    finally:
        # Don't clean up on suspend — the resumed task uses these dirs as cwd
        # for the next claude/codex turn. The resume body's finally clause
        # owns cleanup once the session completes or errors there. /tmp is
        # tmpfs-reaped by systemd-tmpfiles eventually if the user never
        # resumes, so we don't leak indefinitely.
        if not suspended:
            for root in tmp_roots:
                shutil.rmtree(root, ignore_errors=True)


def _resume_grill_session_body(  # pragma: no cover — requires celery + redis
    self: Task,
    original_session_id: str,
) -> dict[str, Any]:
    """Resume a suspended grill session from saved state.

    Uses the original session_id for Redis keys so the frontend sees
    continuity. The Claude CLI session is resumed via ``--resume``.
    """
    session_id = original_session_id
    r = _redis_client()

    resume_state = _load_resume_state(r, session_id)
    if resume_state is None:
        _set_state(r, session_id, {"status": "error", "error": "No resume state"})
        return {"status": "error", "error": "No resume state found"}

    claude_session_id = resume_state["claude_session_id"]
    codex_history: list[dict[str, str]] = resume_state.get("codex_history", [])
    cwd = resume_state["cwd"]
    system_prompt = resume_state["system_prompt"]
    resolved_model = resume_state.get("model", "")
    repo_path = resume_state["repo_path"]
    prompt = resume_state["prompt"]
    backend = resume_state.get("backend", "claudecodecli")
    turn_count: int = resume_state.get("turn_count", 0)
    use_codex = resume_state.get("use_codex", False)
    github_token = resume_state.get("github_token")
    # Inherit clone tmp dirs from the original task — we own cleanup now.
    # ``.get`` with a default keeps pre-fix suspended sessions resumable
    # (their tmp dirs were already deleted; nothing to clean).
    tmp_roots: list[Path] = [Path(p) for p in resume_state.get("tmp_roots", [])]
    suspended = False

    _clear_resume_state(r, session_id)

    def _emit_status(text: str) -> None:
        _push_ai_msg(r, session_id, "system", text)

    try:
        _set_state(
            r,
            session_id,
            {
                "status": "active",
                "repo_path": repo_path,
                "prompt": prompt,
                "model": resolved_model,
                "backend": backend,
                "turn_count": turn_count,
            },
        )

        last_activity = time.monotonic()

        while turn_count < _MAX_CONVERSATION_TURNS:
            user_msg = _pop_user_msg(r, session_id)

            if user_msg is None:
                if time.monotonic() - last_activity > _IDLE_SUSPEND_S:
                    _save_resume_state(
                        r,
                        session_id,
                        {
                            "claude_session_id": claude_session_id,
                            "codex_history": codex_history,
                            "cwd": cwd,
                            "system_prompt": system_prompt,
                            "model": resolved_model,
                            "repo_path": repo_path,
                            "prompt": prompt,
                            "backend": backend,
                            "turn_count": turn_count,
                            "use_codex": use_codex,
                            "github_token": github_token,
                            "tmp_roots": [str(p) for p in tmp_roots],
                        },
                    )
                    _set_state(
                        r,
                        session_id,
                        {
                            "status": "suspended",
                            "repo_path": repo_path,
                            "prompt": prompt,
                            "model": resolved_model,
                            "backend": backend,
                            "turn_count": turn_count,
                        },
                    )
                    suspended = True
                    return {"status": "suspended", "turn_count": turn_count}

                state = _get_state(r, session_id)
                if state and state.get("status") == "ending":
                    break

                time.sleep(_POLL_INTERVAL_S)
                continue

            last_activity = time.monotonic()
            user_text = user_msg.get("content", "")

            if user_msg.get("type") == "end":
                user_text = (
                    f"{user_text}\n\n"
                    "Based on our discussion, please produce the final "
                    "consolidated plan. Start with '## FINAL PLAN' on its "
                    "own line, then provide the complete plan."
                )

            _set_state(
                r,
                session_id,
                {
                    "status": "thinking",
                    "repo_path": repo_path,
                    "prompt": prompt,
                    "model": resolved_model,
                    "backend": backend,
                    "turn_count": turn_count,
                },
            )

            try:
                if use_codex:
                    ai_text = _invoke_codex_turn(
                        user_message=user_text,
                        cwd=cwd,
                        system_prompt=system_prompt,
                        conversation_history=codex_history,
                        model=resolved_model or None,
                        on_status=_emit_status,
                    )
                else:
                    ai_text = _invoke_claude_turn(
                        prompt=user_text,
                        cwd=cwd,
                        claude_session_id=claude_session_id,
                        is_first_turn=False,
                        model=resolved_model or None,
                        github_token=github_token,
                        on_status=_emit_status,
                    )
            except RuntimeError as exc:
                cli_label = "Codex" if use_codex else "Claude"
                logger.exception(
                    "%s CLI failed in resumed grill session %s", cli_label, session_id
                )
                _push_ai_msg(r, session_id, "system", str(exc), msg_type="error")
                _set_state(
                    r,
                    session_id,
                    {
                        "status": "active",
                        "repo_path": repo_path,
                        "prompt": prompt,
                        "model": resolved_model,
                        "backend": backend,
                        "turn_count": turn_count,
                    },
                )
                continue

            turn_count += 1

            if not ai_text:
                _push_ai_msg(
                    r,
                    session_id,
                    "system",
                    "No response received from AI.",
                    msg_type="error",
                )
                continue

            if use_codex:
                codex_history.append({"role": "user", "content": user_text})
                codex_history.append({"role": "assistant", "content": ai_text})

            is_final = "## FINAL PLAN" in ai_text
            msg_type_out = "plan" if is_final else "message"
            _push_ai_msg(r, session_id, "assistant", ai_text, msg_type=msg_type_out)

            _set_state(
                r,
                session_id,
                {
                    "status": "completed" if is_final else "active",
                    "repo_path": repo_path,
                    "prompt": prompt,
                    "model": resolved_model,
                    "backend": backend,
                    "turn_count": turn_count,
                },
            )

            if is_final:
                return {"status": "completed", "turn_count": turn_count}

        _push_ai_msg(
            r,
            session_id,
            "system",
            "Maximum conversation turns reached.",
            msg_type="timeout",
        )
        _set_state(r, session_id, {"status": "max_turns", "turn_count": turn_count})
        return {"status": "max_turns", "turn_count": turn_count}

    except Exception as exc:
        logger.exception("Resumed grill session %s failed", session_id)
        try:
            _push_ai_msg(
                r,
                session_id,
                "system",
                f"Session error: {exc}",
                msg_type="error",
            )
            _set_state(r, session_id, {"status": "error", "error": str(exc)})
        except Exception:
            pass
        return {"status": "error", "error": str(exc)}

    finally:
        if not suspended:
            for root in tmp_roots:
                shutil.rmtree(root, ignore_errors=True)
