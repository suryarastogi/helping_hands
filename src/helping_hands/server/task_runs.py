"""Persistent snapshots of completed task runs (`/run/<uuid>` shareable links).

A snapshot captures task params + final output + diff + tree at terminal state,
written to Postgres (durable) with a Redis 24h read-through cache. The snapshot
becomes the fallback source for the existing ``/tasks/{id}*`` endpoints once the
workspace has been cleaned up.

Design decisions (see PR description for the full rationale):

* Single hybrid table; queryable columns at top, JSONB blobs for content.
* Schema is bootstrapped at server startup with ``CREATE TABLE IF NOT EXISTS``.
* Writes happen inline at the end of the Celery task body (before ``rmtree``).
* Failures are best-effort: log and continue; the share link will simply 404.
* Cache: absolute 24h TTL, write-through alongside the DB write.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "compute_diff_files",
    "compute_tree_entries",
    "init_task_runs_schema",
    "read_task_run",
    "snapshot_task_run",
]

_DB_CONNECT_TIMEOUT_S = 5
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h, absolute
_FILE_TREE_MAX_ENTRIES = 5000
_GIT_DIFF_TIMEOUT_S = 15
_GIT_TREE_TIMEOUT_S = 15

_TASK_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS task_runs (
    uuid TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    repo_path TEXT,
    backend TEXT,
    model TEXT,
    params JSONB NOT NULL,
    output JSONB NOT NULL,
    diff_files JSONB NOT NULL,
    tree_entries JSONB NOT NULL,
    error JSONB
);
CREATE INDEX IF NOT EXISTS idx_task_runs_created_at
    ON task_runs (created_at DESC);
"""

_TASK_RUNS_UPSERT = """
INSERT INTO task_runs
    (uuid, status, finished_at, repo_path, backend, model,
     params, output, diff_files, tree_entries, error)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (uuid) DO UPDATE SET
    status = EXCLUDED.status,
    finished_at = EXCLUDED.finished_at,
    repo_path = EXCLUDED.repo_path,
    backend = EXCLUDED.backend,
    model = EXCLUDED.model,
    params = EXCLUDED.params,
    output = EXCLUDED.output,
    diff_files = EXCLUDED.diff_files,
    tree_entries = EXCLUDED.tree_entries,
    error = EXCLUDED.error;
"""

_TASK_RUNS_SELECT = """
SELECT uuid, status, created_at, finished_at, repo_path, backend, model,
       params, output, diff_files, tree_entries, error
FROM task_runs
WHERE uuid = %s;
"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    return url or None


def _connect() -> Any:
    """Return a psycopg2 connection or raise."""
    import psycopg2

    url = _get_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(url, connect_timeout=_DB_CONNECT_TIMEOUT_S)


def init_task_runs_schema() -> None:
    """Create the ``task_runs`` table if it does not exist.

    Best-effort: failures (no DATABASE_URL, DB unreachable, psycopg2 missing)
    are logged but never raised — the server boots regardless.
    """
    if not _get_database_url():
        logger.info("task_runs: DATABASE_URL unset, skipping schema bootstrap")
        return
    try:
        import psycopg2
    except ImportError:
        logger.warning("task_runs: psycopg2 not available, skipping bootstrap")
        return
    try:
        conn = _connect()
    except (psycopg2.Error, OSError, RuntimeError) as exc:
        logger.warning("task_runs: schema bootstrap connect failed: %s", exc)
        return
    try:
        with conn.cursor() as cur:
            cur.execute(_TASK_RUNS_DDL)
        conn.commit()
        logger.info("task_runs: schema ready")
    except psycopg2.Error as exc:
        logger.warning("task_runs: schema bootstrap exec failed: %s", exc)
    finally:
        with contextlib.suppress(Exception):
            conn.close()


# ---------------------------------------------------------------------------
# Redis cache
# ---------------------------------------------------------------------------


def _cache_key(task_id: str) -> str:
    return f"task_run:{task_id}"


def _redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def _redis_client() -> Any:
    """Return a synchronous Redis client (decode_responses=True) or None."""
    try:
        import redis
    except ImportError:
        return None
    try:
        return redis.from_url(_redis_url(), decode_responses=True)
    except Exception as exc:
        logger.debug("task_runs: redis client init failed: %s", exc)
        return None


def _cache_set(task_id: str, payload: dict[str, Any]) -> None:
    client = _redis_client()
    if client is None:
        return
    try:
        client.set(_cache_key(task_id), json.dumps(payload), ex=_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.debug("task_runs: cache set failed: %s", exc)


def _cache_get(task_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    if client is None:
        return None
    try:
        raw = client.get(_cache_key(task_id))
    except Exception as exc:
        logger.debug("task_runs: cache get failed: %s", exc)
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Pure compute (workspace -> diff/tree). Shared by snapshot + live endpoints.
# ---------------------------------------------------------------------------


def compute_diff_files(workspace_path: Path) -> list[dict[str, Any]]:
    """Run ``git diff HEAD`` against *workspace_path* and parse per-file entries.

    Returns a list of ``{"filename": str, "status": str, "diff": str}`` dicts.
    Untracked files are emitted as ``"added"`` with synthesized unified-diff
    content, mirroring :func:`server.app._build_task_diff`.
    """
    try:
        diff_output = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=_GIT_DIFF_TIMEOUT_S,
        )
        if diff_output.returncode != 0:
            diff_output = subprocess.run(
                ["git", "diff"],
                capture_output=True,
                text=True,
                cwd=workspace_path,
                timeout=_GIT_DIFF_TIMEOUT_S,
            )
        untracked_output = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("task_runs: git diff failed: %s", exc)
        return []

    files: list[dict[str, Any]] = []

    if diff_output.stdout.strip():
        current_filename: str | None = None
        current_lines: list[str] = []
        current_status = "modified"

        def _flush() -> None:
            if current_filename and current_lines:
                files.append(
                    {
                        "filename": current_filename,
                        "status": current_status,
                        "diff": "".join(current_lines),
                    }
                )

        for line in diff_output.stdout.splitlines(keepends=True):
            if line.startswith("diff --git "):
                _flush()
                parts = line.strip().split(" b/", 1)
                current_filename = parts[1] if len(parts) > 1 else "unknown"
                current_lines = [line]
                current_status = "modified"
            else:
                current_lines.append(line)
                if line.startswith("new file"):
                    current_status = "added"
                elif line.startswith("deleted file"):
                    current_status = "deleted"
                elif line.startswith("rename from"):
                    current_status = "renamed"
        _flush()

    if untracked_output.stdout.strip():
        for raw_path in untracked_output.stdout.strip().splitlines():
            untracked = raw_path.strip()
            if not untracked:
                continue
            try:
                content = (workspace_path / untracked).read_text(errors="replace")
            except OSError:
                continue
            numbered = "\n".join(f"+{ln}" for ln in content.splitlines())
            diff_text = (
                f"diff --git a/{untracked} b/{untracked}\n"
                f"new file mode 100644\n"
                f"--- /dev/null\n"
                f"+++ b/{untracked}\n"
                f"@@ -0,0 +1,{len(content.splitlines())} @@\n"
                f"{numbered}\n"
            )
            files.append({"filename": untracked, "status": "added", "diff": diff_text})

    return files


def compute_tree_entries(workspace_path: Path) -> list[dict[str, Any]]:
    """Walk *workspace_path* and return tree entries with git change status.

    Mirrors :func:`server.app._build_task_tree` but takes a path directly.
    Returns ``[{"path": str, "name": str, "type": "file"|"dir", "status": ...}]``.
    """
    changed: dict[str, str] = {}
    try:
        status_out = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=_GIT_TREE_TIMEOUT_S,
        )
        if status_out.returncode == 0:
            for line in status_out.stdout.splitlines():
                if len(line) < 4:
                    continue
                xy = line[:2]
                fpath = line[3:].strip()
                if " -> " in fpath:
                    fpath = fpath.split(" -> ", 1)[1]
                if "?" in xy or "A" in xy:
                    changed[fpath] = "added"
                elif "D" in xy:
                    changed[fpath] = "deleted"
                elif xy[0] == "R" or xy[1] == "R":
                    changed[fpath] = "renamed"
                else:
                    changed[fpath] = "modified"
    except (subprocess.TimeoutExpired, OSError):
        pass

    entries: list[dict[str, Any]] = []
    dirs_seen: set[str] = set()
    try:
        for item in sorted(workspace_path.rglob("*")):
            try:
                rel = str(item.relative_to(workspace_path))
            except ValueError:
                continue
            if rel.startswith(".git") and (
                rel == ".git" or rel.startswith(".git/") or rel.startswith(".git\\")
            ):
                continue
            if len(entries) >= _FILE_TREE_MAX_ENTRIES:
                break
            if item.is_dir():
                if rel not in dirs_seen:
                    dirs_seen.add(rel)
                    entries.append(
                        {"path": rel, "name": item.name, "type": "dir", "status": None}
                    )
            else:
                parts = Path(rel).parts
                for i in range(1, len(parts)):
                    parent = str(Path(*parts[:i]))
                    if parent not in dirs_seen:
                        dirs_seen.add(parent)
                        entries.append(
                            {
                                "path": parent,
                                "name": parts[i - 1],
                                "type": "dir",
                                "status": None,
                            }
                        )
                entries.append(
                    {
                        "path": rel,
                        "name": item.name,
                        "type": "file",
                        "status": changed.get(rel),
                    }
                )
    except PermissionError:
        pass

    return entries


# ---------------------------------------------------------------------------
# Snapshot writer
# ---------------------------------------------------------------------------


def snapshot_task_run(
    *,
    task_id: str,
    status: str,
    params: dict[str, Any],
    output: dict[str, Any],
    workspace_path: Path | None,
    error: dict[str, Any] | None = None,
    finished_at: str | None = None,
) -> bool:
    """Persist a terminal-state snapshot of a task run.

    *workspace_path* may be ``None`` (e.g. failure before workspace setup); in
    that case diff and tree are recorded as empty lists. The DB row is still
    written so the share link resolves.

    Returns True if the row was written; False on any failure (logged).
    """
    if not task_id:
        return False
    diff_files: list[dict[str, Any]] = []
    tree_entries: list[dict[str, Any]] = []
    if workspace_path is not None and workspace_path.is_dir():
        try:
            diff_files = compute_diff_files(workspace_path)
        except Exception as exc:
            logger.warning("task_runs: diff capture failed: %s", exc)
        try:
            tree_entries = compute_tree_entries(workspace_path)
        except Exception as exc:
            logger.warning("task_runs: tree capture failed: %s", exc)

    repo_path = _safe_str(params.get("repo_path"))
    backend = _safe_str(params.get("backend"))
    model = _safe_str(params.get("model"))

    payload = {
        "uuid": task_id,
        "status": status,
        "finished_at": finished_at,
        "repo_path": repo_path,
        "backend": backend,
        "model": model,
        "params": params,
        "output": output,
        "diff_files": diff_files,
        "tree_entries": tree_entries,
        "error": error,
    }

    if not _get_database_url():
        logger.info("task_runs: DATABASE_URL unset, skipping snapshot for %s", task_id)
        return False

    try:
        import psycopg2
    except ImportError:
        logger.warning("task_runs: psycopg2 unavailable, snapshot skipped")
        return False

    try:
        conn = _connect()
    except (psycopg2.Error, OSError, RuntimeError) as exc:
        logger.warning("task_runs: connect for snapshot failed: %s", exc)
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                _TASK_RUNS_UPSERT,
                (
                    task_id,
                    status,
                    finished_at,
                    repo_path,
                    backend,
                    model,
                    json.dumps(params, default=str),
                    json.dumps(output, default=str),
                    json.dumps(diff_files, default=str),
                    json.dumps(tree_entries, default=str),
                    json.dumps(error, default=str) if error is not None else None,
                ),
            )
        conn.commit()
    except psycopg2.Error as exc:
        logger.warning("task_runs: snapshot write failed for %s: %s", task_id, exc)
        return False
    finally:
        with contextlib.suppress(Exception):
            conn.close()

    # Write-through cache (best-effort).
    _cache_set(task_id, payload)
    return True


# ---------------------------------------------------------------------------
# Snapshot reader
# ---------------------------------------------------------------------------


def read_task_run(task_id: str) -> dict[str, Any] | None:
    """Return a snapshot dict for *task_id*, or ``None`` if not found.

    Tries the Redis cache first, falls back to Postgres. Cache misses populate
    the cache on success.
    """
    if not task_id:
        return None
    cached = _cache_get(task_id)
    if cached is not None:
        return cached
    if not _get_database_url():
        return None
    try:
        import psycopg2
    except ImportError:
        return None
    try:
        conn = _connect()
    except (psycopg2.Error, OSError, RuntimeError) as exc:
        logger.debug("task_runs: read connect failed: %s", exc)
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(_TASK_RUNS_SELECT, (task_id,))
            row = cur.fetchone()
    except psycopg2.Error as exc:
        logger.debug("task_runs: read select failed: %s", exc)
        return None
    finally:
        with contextlib.suppress(Exception):
            conn.close()

    if row is None:
        return None

    (
        uuid_,
        status,
        created_at,
        finished_at,
        repo_path,
        backend,
        model,
        params,
        output,
        diff_files,
        tree_entries,
        error,
    ) = row

    payload = {
        "uuid": uuid_,
        "status": status,
        "created_at": _to_iso(created_at),
        "finished_at": _to_iso(finished_at),
        "repo_path": repo_path,
        "backend": backend,
        "model": model,
        "params": params or {},
        "output": output or {},
        "diff_files": diff_files or [],
        "tree_entries": tree_entries or [],
        "error": error,
    }
    _cache_set(task_id, payload)
    return payload


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return str(value)
