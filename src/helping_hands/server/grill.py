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

__all__ = ["grill_session"]

# --- Constants ---------------------------------------------------------------

_SESSION_TTL_S = 3600
"""Sessions expire from Redis after 1 hour of inactivity."""

_POLL_INTERVAL_S = 1.0
"""How often the worker checks for new user messages."""

_IDLE_TIMEOUT_S = 300
"""Max seconds to wait for a user message before ending the session."""

_MAX_CONVERSATION_TURNS = 100
"""Hard limit on total conversation turns to prevent runaway sessions."""

_CLAUDE_TURN_TIMEOUT_S = 300
"""Max seconds to wait for a single Claude CLI response."""


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
    """Push an AI message to the outbound queue."""
    key = f"grill:{session_id}:ai_msgs"
    msg = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "type": msg_type,
        "timestamp": time.time(),
    }
    r.rpush(key, json.dumps(msg))
    r.expire(key, _SESSION_TTL_S)


def _pop_user_msg(r: Any, session_id: str) -> dict[str, Any] | None:
    """Pop the next user message from the inbound queue (non-blocking)."""
    key = f"grill:{session_id}:user_msgs"
    raw = r.lpop(key)
    if raw is None:
        return None
    return json.loads(raw)


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
    ) -> dict[str, Any]:
        """Long-running Celery task for interactive grill sessions.

        Clones the repo, builds context, then enters a message loop.
        Each AI turn is a ``claude -p`` subprocess call using
        ``--session-id`` / ``--resume`` for conversation continuity.
        """
        return _grill_session_body(
            self, repo_path, prompt, model, github_token, reference_repos
        )

except ImportError:
    pass


def _grill_session_body(  # pragma: no cover — requires celery + redis
    self: Task,
    repo_path: str,
    prompt: str,
    model: str | None = None,
    github_token: str | None = None,
    reference_repos: list[str] | None = None,
) -> dict[str, Any]:
    """Long-running Celery task for interactive grill sessions.

    Clones the repo, builds context, then enters a message loop.
    Each AI turn is a ``claude -p`` subprocess call using
    ``--session-id`` / ``--resume`` for conversation continuity.
    """
    session_id = self.request.id
    r = _redis_client()
    tmp_roots: list[Path] = []
    # Separate UUID for the Claude CLI session (Celery task IDs aren't
    # always valid UUIDs in the format Claude expects).
    claude_session_id = str(uuid.uuid4())

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

        _push_ai_msg(
            r,
            session_id,
            "system",
            f"Starting grill session{f' with {resolved_model}' if resolved_model else ''}...",
        )

        _set_state(
            r,
            session_id,
            {
                "status": "thinking",
                "repo_path": repo_path,
                "prompt": prompt,
                "model": resolved_model,
                "turn_count": 0,
            },
        )

        # -- First turn: send the plan and get the first question --------------
        try:
            ai_text = _invoke_claude_turn(
                prompt=(
                    "Begin the interview. Start with the highest-level "
                    "architectural question about this plan."
                ),
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
                "turn_count": turn_count,
            },
        )

        # -- Message loop ------------------------------------------------------
        last_activity = time.monotonic()

        while turn_count < _MAX_CONVERSATION_TURNS:
            user_msg = _pop_user_msg(r, session_id)

            if user_msg is None:
                if time.monotonic() - last_activity > _IDLE_TIMEOUT_S:
                    _push_ai_msg(
                        r,
                        session_id,
                        "system",
                        "Session timed out due to inactivity.",
                        msg_type="timeout",
                    )
                    _set_state(
                        r,
                        session_id,
                        {"status": "timeout", "turn_count": turn_count},
                    )
                    return {"status": "timeout", "turn_count": turn_count}

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
                    "turn_count": turn_count,
                },
            )

            try:
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
                logger.exception("Claude CLI failed in grill session %s", session_id)
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
        for root in tmp_roots:
            shutil.rmtree(root, ignore_errors=True)
