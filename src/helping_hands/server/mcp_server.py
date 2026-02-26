"""MCP server for helping_hands.

Exposes repo-building capabilities over the Model Context Protocol so AI
clients (Claude Desktop, Cursor, etc.) can use helping_hands as a tool
provider.

Tools:
  - index_repo: Walk a local repo and return its file listing.
  - build_feature: (async via Celery) Enqueue a hand task.
  - get_task_status: Check the status of an enqueued task.
  - read_file: Read a UTF-8 file from a repository.
  - write_file: Write a UTF-8 file in a repository.
  - mkdir: Create a directory in a repository.
  - path_exists: Check whether a repo-relative path exists.

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
from helping_hands.lib.meta.tools import filesystem as fs_tools
from helping_hands.lib.repo import RepoIndex
from helping_hands.server.task_result import normalize_task_result

mcp = FastMCP(
    "helping_hands",
    instructions=(
        "helping_hands MCP server. Use index_repo to load a repository, "
        "then build_feature to request AI-driven changes."
    ),
)

_indexed_repos: dict[str, RepoIndex] = {}


def _repo_root(repo_path: str) -> Path:
    """Resolve and validate a repository root path."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        msg = f"Repository path not found: {repo_path}"
        raise FileNotFoundError(msg)
    return root


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
def build_feature(
    repo_path: str,
    prompt: str,
    pr_number: int | None = None,
    backend: str = "e2e",
    model: str | None = None,
    max_iterations: int = 6,
    no_pr: bool = False,
) -> dict:
    """Enqueue a hand task via Celery and return the task ID.

    Args:
        repo_path: Local path or GitHub repo reference in `owner/repo` format.
        prompt: Description of the feature or change to build.
        pr_number: Optional existing PR number to resume/update.
        backend: One of e2e/basic-langgraph/basic-atomic/basic-agent/
            codexcli/claudecodecli/goose.
        model: Optional model override.
        max_iterations: Iteration cap for basic backends.
        no_pr: Disable final PR push/create side effects.

    Returns:
        Dict with task_id and status.
    """
    from helping_hands.server.celery_app import (
        build_feature as celery_build,
    )

    task = celery_build.delay(
        repo_path=repo_path,
        prompt=prompt,
        pr_number=pr_number,
        backend=backend,
        model=model,
        max_iterations=max_iterations,
        no_pr=no_pr,
    )
    return {"task_id": task.id, "status": "queued", "backend": backend}


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
    raw_result = result.result if result.ready() else result.info
    return {
        "task_id": task_id,
        "status": result.status,
        "result": normalize_task_result(result.status, raw_result),
    }


@mcp.tool()
def read_file(repo_path: str, file_path: str, max_chars: int | None = None) -> str:
    """Read a file from a repository.

    Args:
        repo_path: Absolute path to the repository root.
        file_path: Path relative to the repo root.
        max_chars: Optional max number of chars to return.

    Returns:
        The file contents as a string.
    """
    root = _repo_root(repo_path)
    try:
        text, _, _ = fs_tools.read_text_file(root, file_path, max_chars=max_chars)
    except ValueError as exc:
        msg = f"Invalid file path: {file_path}"
        raise ValueError(msg) from exc
    except FileNotFoundError as exc:
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg) from exc
    except IsADirectoryError as exc:
        msg = f"Path is a directory: {file_path}"
        raise IsADirectoryError(msg) from exc
    except UnicodeError as exc:
        msg = f"File is not UTF-8 text: {file_path}"
        raise UnicodeError(msg) from exc
    return text


@mcp.tool()
def write_file(repo_path: str, file_path: str, content: str) -> dict:
    """Write a UTF-8 file in a repository.

    Args:
        repo_path: Absolute path to the repository root.
        file_path: Path relative to the repo root.
        content: Full file contents to write.

    Returns:
        Dict with normalized path and byte length.
    """
    root = _repo_root(repo_path)
    try:
        written_path = fs_tools.write_text_file(root, file_path, content)
    except ValueError as exc:
        msg = f"Invalid file path: {file_path}"
        raise ValueError(msg) from exc
    return {"path": written_path, "bytes": len(content.encode("utf-8"))}


@mcp.tool()
def mkdir(repo_path: str, dir_path: str) -> dict:
    """Create a directory in a repository.

    Args:
        repo_path: Absolute path to the repository root.
        dir_path: Directory path relative to the repo root.

    Returns:
        Dict with normalized created path.
    """
    root = _repo_root(repo_path)
    try:
        created = fs_tools.mkdir_path(root, dir_path)
    except ValueError as exc:
        msg = f"Invalid directory path: {dir_path}"
        raise ValueError(msg) from exc
    return {"path": created}


@mcp.tool()
def path_exists(repo_path: str, path: str) -> bool:
    """Check whether a repo-relative path exists."""
    root = _repo_root(repo_path)
    return fs_tools.path_exists(root, path)


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
