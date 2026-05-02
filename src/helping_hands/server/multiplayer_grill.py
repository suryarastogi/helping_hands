"""Multiplayer Grill Me: collaborative AI interview sessions.

A parallel feature to :mod:`helping_hands.server.grill` that lets multiple
participants collaborate on interviewing the AI about a plan.  Keeps the
existing solo Grill Me untouched.

Key differences from solo grill:

* **Registry**: active sessions are discoverable via the Redis sorted set
  ``mgrill:sessions`` (scored by last activity), so a lobby UI can list them.
* **Collaborative batched turns**: participants each add messages to a
  shared pending batch; any token-holder clicks "Send to AI" to bundle
  them (prefixed ``[Name]: ...``) into a single worker turn.
* **Full transcript**: unlike solo grill which drains ``ai_msgs``, the
  multiplayer flow keeps the entire message log in ``mgrill:{id}:messages``
  so late joiners see history.
* **Creator role with handoff**: ``creator_token_hash`` identifies the
  accountable user (owns Submit).  If the creator's heartbeat lapses for
  ``_CREATOR_HANDOFF_S`` seconds, any token-holder may claim the role.
* **Voting**: a ``Y.Map``-like Redis hash ``mgrill:{id}:votes`` records
  each participant's up/down vote on the final plan.  Advisory only —
  the creator is the sole decider at submit time.

Redis keyspace (all TTL ``_SESSION_TTL_S``):

* ``mgrill:sessions``               — sorted set, score = last_activity_ts
* ``mgrill:{id}:state``             — JSON: status, creator_*, turn_count, …
* ``mgrill:{id}:user_msgs``         — FIFO queue consumed by the worker
* ``mgrill:ai_outbox``              — shared cross-session list; the
  ``mgrill_bridge`` drains this and appends each entry to the matching
  room's ``messages`` Y.Array in-process (see :mod:`mgrill_bridge`)

The Yjs room ``mgrill-{id}`` is authoritative for transcript + votes +
pending batch; the frontend subscribes to it via ``WebsocketProvider`` and
never polls those fields.  Authoritative server state (status, creator,
turn_count) stays in Redis so the REST endpoints + worker can agree without
holding the Y.Doc lock.
"""

from __future__ import annotations

import json
import logging
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
    build_clone_url as _build_clone_url,
    noninteractive_env as _git_noninteractive_env,
    redact_credentials as _redact_sensitive,
    repo_tmp_dir as _repo_tmp_dir,
    validate_repo_spec as _validate_repo_spec,
)
from helping_hands.lib.repo import RepoIndex
from helping_hands.server.grill import (
    _build_system_prompt,
    _clone_repo,
    _invoke_claude_turn,
    _invoke_codex_turn,
)
from helping_hands.server.mgrill_bridge import AI_OUTBOX_KEY

if TYPE_CHECKING:
    from celery import Task

logger = logging.getLogger(__name__)

__all__ = ["mgrill_session", "resume_mgrill_session"]

# --- Constants ---------------------------------------------------------------

_SESSION_TTL_S = 3600
"""Sessions expire from Redis after 1 hour of inactivity."""

_POLL_INTERVAL_S = 1.0
"""How often the worker checks for new user messages."""

_IDLE_SUSPEND_S = 300
"""Seconds of inactivity before the worker suspends (session stays resumable)."""

_MAX_CONVERSATION_TURNS = 100
"""Hard cap on total AI turns per session."""

_CREATOR_HANDOFF_S = 60
"""Seconds of creator-absence after which any token-holder may claim creator."""


# --- Redis helpers -----------------------------------------------------------


def _redis_client() -> Any:
    """Get a Redis client from the Celery broker connection pool."""
    import os

    import redis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(redis_url, decode_responses=True)


def _state_key(session_id: str) -> str:
    return f"mgrill:{session_id}:state"


def _user_msgs_key(session_id: str) -> str:
    return f"mgrill:{session_id}:user_msgs"


_REGISTRY_KEY = "mgrill:sessions"


def _touch_activity(r: Any, session_id: str) -> None:
    """Bump this session's score in the registry to now()."""
    now = time.time()
    r.zadd(_REGISTRY_KEY, {session_id: now})


def _set_state(r: Any, session_id: str, state: dict[str, Any]) -> None:
    """Write session state to Redis with TTL refresh."""
    r.set(_state_key(session_id), json.dumps(state), ex=_SESSION_TTL_S)
    _touch_activity(r, session_id)


def _get_state(r: Any, session_id: str) -> dict[str, Any] | None:
    """Read session state from Redis."""
    raw = r.get(_state_key(session_id))
    if raw is None:
        return None
    return json.loads(raw)


def _update_state(r: Any, session_id: str, **fields: Any) -> dict[str, Any] | None:
    """Merge *fields* into the existing session state and persist."""
    state = _get_state(r, session_id)
    if state is None:
        return None
    state.update(fields)
    _set_state(r, session_id, state)
    return state


def _emit_message(
    r: Any,
    session_id: str,
    *,
    role: str,
    content: str,
    author_player_id: str | None = None,
    author_name: str | None = None,
    msg_type: str = "message",
) -> dict[str, Any]:
    """Emit a message to the bridge's shared outbox.

    The :mod:`mgrill_bridge` task in the FastAPI process drains
    :data:`AI_OUTBOX_KEY` and appends each envelope to the matching Yjs
    room's ``messages`` Y.Array, which then syncs to all participants.

    The ``session_id`` field in the envelope tells the bridge which room
    to write to.  Returns the envelope (without the session_id) so callers
    can log or correlate — matches the old ``_append_message`` shape.
    """
    envelope = {
        "session_id": session_id,
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "type": msg_type,
        "author_player_id": author_player_id,
        "author_name": author_name,
        "timestamp": time.time(),
    }
    r.rpush(AI_OUTBOX_KEY, json.dumps(envelope))
    r.expire(AI_OUTBOX_KEY, _SESSION_TTL_S)
    _touch_activity(r, session_id)
    # Strip session_id from the returned dict — the bridge does the same
    # before appending to the Y.Array, so this matches what participants see.
    return {k: v for k, v in envelope.items() if k != "session_id"}


def _pop_user_msg(r: Any, session_id: str) -> dict[str, Any] | None:
    """Pop the next user message from the inbound queue (non-blocking)."""
    raw = r.lpop(_user_msgs_key(session_id))
    if raw is None:
        return None
    return json.loads(raw)


def _save_resume_state(r: Any, session_id: str, state: dict[str, Any]) -> None:
    """Persist state needed to resume a suspended multiplayer session."""
    key = f"mgrill:{session_id}:resume"
    r.set(key, json.dumps(state), ex=_SESSION_TTL_S)


def _load_resume_state(r: Any, session_id: str) -> dict[str, Any] | None:
    """Load previously saved resume state."""
    key = f"mgrill:{session_id}:resume"
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def _clear_resume_state(r: Any, session_id: str) -> None:
    """Remove resume state after a session resumes or completes."""
    r.delete(f"mgrill:{session_id}:resume")


# --- Celery task -------------------------------------------------------------

try:  # pragma: no cover — requires celery extra
    from helping_hands.server.celery_app import celery_app as _celery_app

    @_celery_app.task(bind=True, name="helping_hands.mgrill_session")
    def mgrill_session(
        self: Task,
        repo_path: str,
        prompt: str,
        model: str | None = None,
        github_token: str | None = None,
        reference_repos: list[str] | None = None,
        backend: str = "claudecodecli",
        creator_name: str = "Creator",
        creator_token_hash: str | None = None,
        creator_player_id: str | None = None,
    ) -> dict[str, Any]:
        """Long-running Celery task for multiplayer grill sessions."""
        return _mgrill_session_body(
            self,
            repo_path=repo_path,
            prompt=prompt,
            model=model,
            github_token=github_token,
            reference_repos=reference_repos,
            backend=backend,
            creator_name=creator_name,
            creator_token_hash=creator_token_hash,
            creator_player_id=creator_player_id,
        )

    @_celery_app.task(bind=True, name="helping_hands.resume_mgrill_session")
    def resume_mgrill_session(
        self: Task,
        original_session_id: str,
    ) -> dict[str, Any]:
        """Resume a suspended multiplayer grill session."""
        return _resume_mgrill_session_body(self, original_session_id)

except ImportError:
    pass


def _mgrill_session_body(  # pragma: no cover — requires celery + redis
    self: Task,
    *,
    repo_path: str,
    prompt: str,
    model: str | None,
    github_token: str | None,
    reference_repos: list[str] | None,
    backend: str,
    creator_name: str,
    creator_token_hash: str | None,
    creator_player_id: str | None,
) -> dict[str, Any]:
    """Body of the ``mgrill_session`` task (separate for testability)."""
    session_id = self.request.id
    r = _redis_client()
    tmp_roots: list[Path] = []
    claude_session_id = str(uuid.uuid4())
    use_codex = backend == "codexcli"
    codex_history: list[dict[str, str]] = []
    now = time.time()

    try:
        # -- Initial state ----------------------------------------------------
        _set_state(
            r,
            session_id,
            {
                "status": "cloning",
                "repo_path": repo_path,
                "prompt": prompt,
                "model": model or "",
                "backend": backend,
                "turn_count": 0,
                "creator_name": creator_name,
                "creator_token_hash": creator_token_hash,
                "creator_player_id": creator_player_id,
                "creator_last_seen_ts": now,
                "created_at": now,
                "last_activity_ts": now,
                "submit_override_count": 0,
                "submitted_task_id": None,
            },
        )

        # -- Clone repo -------------------------------------------------------
        _emit_message(r, session_id, role="system", content="Cloning repository...")
        try:
            resolved_path, _cloned_from, tmp_root = _clone_repo(repo_path, github_token)
        except ValueError as exc:
            _emit_message(
                r, session_id, role="system", content=f"Error: {exc}", msg_type="error"
            )
            _update_state(r, session_id, status="error", error=str(exc))
            return {"status": "error", "error": str(exc)}

        if tmp_root:
            tmp_roots.append(tmp_root)

        # -- Index repo -------------------------------------------------------
        _emit_message(r, session_id, role="system", content="Indexing repository...")
        repo_index = RepoIndex.from_path(resolved_path)

        # -- Reference repos --------------------------------------------------
        for ref_spec in reference_repos or []:
            try:
                _validate_repo_spec(ref_spec)
            except ValueError:
                _emit_message(
                    r,
                    session_id,
                    role="system",
                    content=f"Skipping invalid reference repo: {ref_spec}",
                )
                continue
            safe_name = ref_spec.replace("/", "_")
            ref_root = Path(
                mkdtemp(
                    prefix=f"helping_hands_mgrill_ref_{safe_name}_",
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
                _emit_message(
                    r,
                    session_id,
                    role="system",
                    content=f"Reference repo clone timed out: {ref_spec}",
                )
                continue
            if ref_result.returncode != 0:
                stderr = _redact_sensitive(
                    ref_result.stderr.strip() or _DEFAULT_CLONE_ERROR_MSG
                )
                _emit_message(
                    r,
                    session_id,
                    role="system",
                    content=f"Failed to clone reference repo {ref_spec}: {stderr}",
                )
                continue
            repo_index.reference_repos.append((ref_spec, ref_dest.resolve()))
            _emit_message(
                r,
                session_id,
                role="system",
                content=f"Cloned reference repo: {ref_spec}",
            )

        # -- Build prompt (adds multi-party note) -----------------------------
        base_prompt = _build_system_prompt(repo_index, prompt)
        system_prompt = (
            base_prompt
            + "\n\nIMPORTANT: Multiple participants may collaboratively answer. "
            "Each turn you receive may contain messages from multiple users, "
            "formatted as `[Name]: <message>`. Address participants by name "
            "when their answers conflict or when directing follow-ups."
        )
        cwd = str(resolved_path)
        resolved_model = model or ""

        def _emit_status(text: str) -> None:
            _emit_message(r, session_id, role="system", content=text)

        backend_label = "Codex CLI" if use_codex else "Claude Code CLI"
        _emit_message(
            r,
            session_id,
            role="system",
            content=(
                f"Starting multiplayer grill session"
                f"{f' with {resolved_model}' if resolved_model else ''} "
                f"({backend_label})..."
            ),
        )
        _update_state(r, session_id, status="thinking")

        # -- First turn -------------------------------------------------------
        first_turn_msg = (
            "Begin the interview. Start with the highest-level "
            "architectural question about this plan."
        )
        try:
            if use_codex:
                ai_text = _invoke_codex_turn(
                    user_message=first_turn_msg,
                    cwd=cwd,
                    system_prompt=system_prompt,
                    conversation_history=codex_history,
                    model=resolved_model or None,
                    on_status=_emit_status,
                )
            else:
                ai_text = _invoke_claude_turn(
                    prompt=first_turn_msg,
                    cwd=cwd,
                    claude_session_id=claude_session_id,
                    is_first_turn=True,
                    system_prompt=system_prompt,
                    model=resolved_model or None,
                    github_token=github_token,
                    on_status=_emit_status,
                )
        except RuntimeError as exc:
            _emit_message(
                r, session_id, role="system", content=str(exc), msg_type="error"
            )
            _update_state(r, session_id, status="error", error=str(exc))
            return {"status": "error", "error": str(exc)}

        turn_count = 1
        if use_codex:
            codex_history.append({"role": "assistant", "content": ai_text})

        is_final = "## FINAL PLAN" in ai_text
        _emit_message(
            r,
            session_id,
            role="assistant",
            content=ai_text,
            author_name="Interviewer",
            msg_type="plan" if is_final else "message",
        )
        if is_final:
            _update_state(r, session_id, status="completed", turn_count=turn_count)
        else:
            _update_state(r, session_id, status="active", turn_count=turn_count)

        # -- Message loop -----------------------------------------------------
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
                            "creator_name": creator_name,
                            "creator_token_hash": creator_token_hash,
                            "creator_player_id": creator_player_id,
                        },
                    )
                    _update_state(r, session_id, status="suspended")
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

            _update_state(r, session_id, status="thinking")

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
                    "%s CLI failed in multiplayer grill %s",
                    cli_label,
                    session_id,
                )
                _emit_message(
                    r, session_id, role="system", content=str(exc), msg_type="error"
                )
                _update_state(r, session_id, status="active")
                continue

            turn_count += 1

            if not ai_text:
                _emit_message(
                    r,
                    session_id,
                    role="system",
                    content="No response received from AI.",
                    msg_type="error",
                )
                _update_state(r, session_id, status="active")
                continue

            if use_codex:
                codex_history.append({"role": "user", "content": user_text})
                codex_history.append({"role": "assistant", "content": ai_text})

            is_final = "## FINAL PLAN" in ai_text
            _emit_message(
                r,
                session_id,
                role="assistant",
                content=ai_text,
                author_name="Interviewer",
                msg_type="plan" if is_final else "message",
            )
            if is_final:
                _update_state(r, session_id, status="completed", turn_count=turn_count)
            else:
                _update_state(r, session_id, status="active", turn_count=turn_count)

        _emit_message(
            r,
            session_id,
            role="system",
            content="Maximum conversation turns reached.",
            msg_type="timeout",
        )
        _update_state(r, session_id, status="max_turns", turn_count=turn_count)
        return {"status": "max_turns", "turn_count": turn_count}

    except Exception as exc:
        logger.exception("Multiplayer grill session %s failed", session_id)
        try:
            _emit_message(
                r,
                session_id,
                role="system",
                content=f"Session error: {exc}",
                msg_type="error",
            )
            _update_state(r, session_id, status="error", error=str(exc))
        except Exception:
            pass
        return {"status": "error", "error": str(exc)}

    finally:
        # Remove from registry if session terminated unhealthily; the
        # state blob itself is retained for TTL so participants see
        # the final error.
        for root in tmp_roots:
            shutil.rmtree(root, ignore_errors=True)


def _resume_mgrill_session_body(  # pragma: no cover — requires celery + redis
    self: Task,
    original_session_id: str,
) -> dict[str, Any]:
    """Resume a suspended multiplayer grill session from saved state."""
    session_id = original_session_id
    r = _redis_client()

    resume_state = _load_resume_state(r, session_id)
    if resume_state is None:
        _update_state(r, session_id, status="error", error="No resume state")
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

    _clear_resume_state(r, session_id)

    def _emit_status(text: str) -> None:
        _emit_message(r, session_id, role="system", content=text)

    try:
        _update_state(r, session_id, status="active")

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
                            "creator_name": resume_state.get("creator_name", "Creator"),
                            "creator_token_hash": resume_state.get(
                                "creator_token_hash"
                            ),
                            "creator_player_id": resume_state.get("creator_player_id"),
                        },
                    )
                    _update_state(r, session_id, status="suspended")
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

            _update_state(r, session_id, status="thinking")

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
                    "%s CLI failed in resumed mgrill session %s",
                    cli_label,
                    session_id,
                )
                _emit_message(
                    r, session_id, role="system", content=str(exc), msg_type="error"
                )
                _update_state(r, session_id, status="active")
                continue

            turn_count += 1

            if not ai_text:
                _emit_message(
                    r,
                    session_id,
                    role="system",
                    content="No response received from AI.",
                    msg_type="error",
                )
                _update_state(r, session_id, status="active")
                continue

            if use_codex:
                codex_history.append({"role": "user", "content": user_text})
                codex_history.append({"role": "assistant", "content": ai_text})

            is_final = "## FINAL PLAN" in ai_text
            _emit_message(
                r,
                session_id,
                role="assistant",
                content=ai_text,
                author_name="Interviewer",
                msg_type="plan" if is_final else "message",
            )
            if is_final:
                _update_state(r, session_id, status="completed", turn_count=turn_count)
            else:
                _update_state(r, session_id, status="active", turn_count=turn_count)

        _emit_message(
            r,
            session_id,
            role="system",
            content="Maximum conversation turns reached.",
            msg_type="timeout",
        )
        _update_state(r, session_id, status="max_turns", turn_count=turn_count)
        return {"status": "max_turns", "turn_count": turn_count}

    except Exception as exc:
        logger.exception("Resumed mgrill session %s failed", session_id)
        try:
            _emit_message(
                r,
                session_id,
                role="system",
                content=f"Session error: {exc}",
                msg_type="error",
            )
            _update_state(r, session_id, status="error", error=str(exc))
        except Exception:
            pass
        return {"status": "error", "error": str(exc)}
