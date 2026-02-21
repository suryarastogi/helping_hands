"""MCP server for helping_hands.

Exposes repo-building capabilities over the Model Context Protocol so AI
clients (Claude Desktop, Cursor, etc.) can use helping_hands as a tool
provider.

Tools:
  - index_repo: Walk a local repo and return its file listing.
  - build_feature: (async via Celery) Enqueue a repo-build task.
  - get_task_status: Check the status of an enqueued task.

Resources:
  - repo://{path}: Read a file from an indexed repo.

Run with:
  uv run helping-hands-mcp          (stdio, for Claude Desktop / Cursor)
  uv run helping-hands-mcp --http   (streamable-http, for networked clients)
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from helping_hands.lib.config import Config
from helping_hands.lib.repo import RepoIndex

mcp = FastMCP(
    "helping_hands",
    instructions=(
        "helping_hands MCP server. Use index_repo to load a repository, "
        "then build_feature to request AI-driven changes."
    ),
)

_indexed_repos: dict[str, RepoIndex] = {}


@mcp.tool()
def index_repo(repo_path: str) -> dict:
    """Index a local git repository and return its file listing.

    Args:
        repo_path: Absolute path to the repository on disk.

    Returns:
        Dict with root path, file count, and first 200 file paths.
    """
    path = Path(repo_path).resolve()
    idx = RepoIndex.from_path(path)
    _indexed_repos[str(path)] = idx
    return {
        "root": str(idx.root),
        "file_count": len(idx.files),
        "files": idx.files[:200],
    }


@mcp.tool()
def build_feature(repo_path: str, prompt: str) -> dict:
    """Enqueue a repo-building task via Celery and return the task ID.

    The repo must already be indexed via index_repo, or exist on disk.

    Args:
        repo_path: Absolute path to the repository.
        prompt: Description of the feature or change to build.

    Returns:
        Dict with task_id and status.
    """
    from helping_hands.server.celery_app import (
        build_feature as celery_build,
    )

    task = celery_build.delay(repo_path, prompt)
    return {"task_id": task.id, "status": "queued"}


@mcp.tool()
def get_task_status(task_id: str) -> dict:
    """Check the status of a previously enqueued build task.

    Args:
        task_id: The Celery task ID returned by build_feature.

    Returns:
        Dict with task_id, status, and result (if complete).
    """
    from helping_hands.server.celery_app import (
        build_feature as celery_build,
    )

    result = celery_build.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@mcp.tool()
def read_file(repo_path: str, file_path: str) -> str:
    """Read a file from a repository.

    Args:
        repo_path: Absolute path to the repository root.
        file_path: Path relative to the repo root.

    Returns:
        The file contents as a string.
    """
    full = Path(repo_path).resolve() / file_path
    if not full.is_file():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)
    return full.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def get_config() -> dict:
    """Return the current helping_hands configuration (from env vars)."""
    cfg = Config.from_env()
    return {
        "model": cfg.model,
        "verbose": cfg.verbose,
        "repo": cfg.repo or None,
    }


@mcp.resource("repo://indexed")
def list_indexed_repos() -> str:
    """List all currently indexed repositories."""
    if not _indexed_repos:
        return "No repositories indexed yet. Use the index_repo tool first."
    lines = [
        f"- {root} ({len(idx.files)} files)" for root, idx in _indexed_repos.items()
    ]
    return "\n".join(lines)


def main() -> None:
    """Entry point for the MCP server."""
    transport = "streamable-http" if "--http" in sys.argv else "stdio"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
