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
  - run_python_code: Execute inline Python code (default ``_DEFAULT_PYTHON_VERSION``).
  - run_python_script: Execute a repo-relative Python script.
  - run_bash_script: Execute a repo-relative or inline bash script.
  - web_search: Search the web (DuckDuckGo endpoint wrapper).
  - web_browse: Browse and extract text from a URL.

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
from helping_hands.lib.hands.v1.hand.factory import BACKEND_CODEXCLI
from helping_hands.lib.meta import skills as meta_skills
from helping_hands.lib.meta.tools import (
    command as exec_tools,
    filesystem as fs_tools,
    registry as meta_tools,
    web as web_tools,
)
from helping_hands.lib.meta.tools.command import _DEFAULT_PYTHON_VERSION
from helping_hands.lib.repo import RepoIndex
from helping_hands.lib.validation import require_non_empty_string
from helping_hands.server.task_result import normalize_task_result

__all__ = ["main", "mcp"]

mcp = FastMCP(
    "helping_hands",
    instructions=(
        "helping_hands MCP server. Use index_repo to load a repository, "
        "then build_feature to request AI-driven changes."
    ),
)

_indexed_repos: dict[str, RepoIndex] = {}

_DEFAULT_EXEC_TIMEOUT_S = 60
"""Default timeout in seconds for code/script execution MCP tools."""

_DEFAULT_BROWSE_MAX_CHARS = web_tools.DEFAULT_BROWSE_MAX_CHARS
"""Default maximum characters returned by the web_browse MCP tool."""

_INDEX_FILES_LIMIT = 200
"""Maximum number of file paths returned by the index_repo MCP tool."""


def _repo_root(repo_path: str) -> Path:
    """Resolve and validate a repository root path."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        msg = f"Repository path not found: {repo_path}"
        raise FileNotFoundError(msg)
    return root


def _command_result_to_dict(result: exec_tools.CommandResult) -> dict:
    """Convert command result dataclass into JSON-safe dict."""
    return {
        "success": result.success,
        "command": result.command,
        "cwd": result.cwd,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@mcp.tool()
def index_repo(repo_path: str) -> dict:
    """Index a local git repository and return its file listing.

    Args:
        repo_path: Absolute path to the repository on disk.

    Returns:
        Dict with root path, file count, and first ``_INDEX_FILES_LIMIT`` file paths.
    """
    path = Path(repo_path).resolve()
    idx = RepoIndex.from_path(path)
    _indexed_repos[str(path)] = idx
    return {
        "root": str(idx.root),
        "file_count": len(idx.files),
        "files": idx.files[:_INDEX_FILES_LIMIT],
    }


@mcp.tool()
def build_feature(
    repo_path: str,
    prompt: str,
    pr_number: int | None = None,
    backend: str = BACKEND_CODEXCLI,
    model: str | None = None,
    max_iterations: int = 6,
    no_pr: bool = False,
    enable_execution: bool = False,
    enable_web: bool = False,
    tools: list[str] | None = None,
    skills: list[str] | None = None,
) -> dict:
    """Enqueue a hand task via Celery and return the task ID.

    Args:
        repo_path: Local path or GitHub repo reference in `owner/repo` format.
        prompt: Description of the feature or change to build.
        pr_number: Optional existing PR number to resume/update.
        backend: One of e2e/basic-langgraph/basic-atomic/basic-agent/
            codexcli/claudecodecli/goose/geminicli.
        model: Optional model override.
        max_iterations: Iteration cap for basic backends.
        no_pr: Disable final PR push/create side effects.
        enable_execution: Enable python/bash execution tools.
        enable_web: Enable web.search/web.browse tools.
        tools: Optional tool categories to enable (e.g. execution, web).
        skills: Optional skill knowledge files to inject.

    Returns:
        Dict with task_id and status.
    """
    require_non_empty_string(repo_path, "repo_path")
    require_non_empty_string(prompt, "prompt")

    from helping_hands.server.celery_app import (
        build_feature as celery_build,
    )

    selected_tools = meta_tools.normalize_tool_selection(tools)
    meta_tools.validate_tool_category_names(selected_tools)
    selected_skills = meta_skills.normalize_skill_selection(skills)
    meta_skills.validate_skill_names(selected_skills)

    task = celery_build.delay(
        repo_path=repo_path,
        prompt=prompt,
        pr_number=pr_number,
        backend=backend,
        model=model,
        max_iterations=max_iterations,
        no_pr=no_pr,
        enable_execution=enable_execution,
        enable_web=enable_web,
        tools=list(selected_tools),
        skills=list(selected_skills),
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
    require_non_empty_string(task_id, "task_id")

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
    except FileNotFoundError as exc:
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg) from exc
    except IsADirectoryError as exc:
        msg = f"Path is a directory: {file_path}"
        raise IsADirectoryError(msg) from exc
    except UnicodeError as exc:
        # UnicodeError is a subclass of ValueError; catch it before ValueError.
        msg = f"File is not UTF-8 text: {file_path}"
        raise UnicodeError(msg) from exc
    except ValueError as exc:
        msg = f"Invalid file path: {file_path}"
        raise ValueError(msg) from exc
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
    """Check whether a repo-relative path exists.

    Args:
        repo_path: Absolute path to the repository root.
        path: Path relative to the repo root.

    Returns:
        ``True`` if the path exists, ``False`` otherwise.

    Raises:
        ValueError: If *path* is empty or whitespace-only.
    """
    require_non_empty_string(path, "path")
    root = _repo_root(repo_path)
    return fs_tools.path_exists(root, path)


@mcp.tool()
def run_python_code(
    repo_path: str,
    code: str,
    python_version: str = _DEFAULT_PYTHON_VERSION,
    args: list[str] | None = None,
    timeout_s: int = _DEFAULT_EXEC_TIMEOUT_S,
    cwd: str | None = None,
) -> dict:
    """Execute inline Python code from a repository context."""
    root = _repo_root(repo_path)
    result = exec_tools.run_python_code(
        root,
        code=code,
        python_version=python_version,
        args=args,
        timeout_s=timeout_s,
        cwd=cwd,
    )
    return _command_result_to_dict(result)


@mcp.tool()
def run_python_script(
    repo_path: str,
    script_path: str,
    python_version: str = _DEFAULT_PYTHON_VERSION,
    args: list[str] | None = None,
    timeout_s: int = _DEFAULT_EXEC_TIMEOUT_S,
    cwd: str | None = None,
) -> dict:
    """Execute a repo-relative Python script from a repository context."""
    root = _repo_root(repo_path)
    result = exec_tools.run_python_script(
        root,
        script_path=script_path,
        python_version=python_version,
        args=args,
        timeout_s=timeout_s,
        cwd=cwd,
    )
    return _command_result_to_dict(result)


@mcp.tool()
def run_bash_script(
    repo_path: str,
    script_path: str | None = None,
    inline_script: str | None = None,
    args: list[str] | None = None,
    timeout_s: int = _DEFAULT_EXEC_TIMEOUT_S,
    cwd: str | None = None,
) -> dict:
    """Execute a repo-relative or inline bash script from repo context.

    Args:
        repo_path: Absolute path to the repository root.
        script_path: Path to a bash script relative to the repo root.
        inline_script: Inline bash code to execute.
        args: Optional arguments passed to the script.
        timeout_s: Execution timeout in seconds.
        cwd: Optional working directory relative to the repo root.

    Returns:
        Dict with success, command, cwd, exit_code, timed_out, stdout, stderr.

    Raises:
        ValueError: If neither *script_path* nor *inline_script* is provided,
            or if both are provided simultaneously.
    """
    if not script_path and not inline_script:
        raise ValueError("Either script_path or inline_script must be provided")
    if script_path and inline_script:
        raise ValueError("Cannot provide both script_path and inline_script")
    root = _repo_root(repo_path)
    result = exec_tools.run_bash_script(
        root,
        script_path=script_path,
        inline_script=inline_script,
        args=args,
        timeout_s=timeout_s,
        cwd=cwd,
    )
    return _command_result_to_dict(result)


@mcp.tool()
def web_search(
    query: str,
    max_results: int = 5,
    timeout_s: int = 20,
) -> dict:
    """Search the web and return lightweight result entries."""
    require_non_empty_string(query, "query")
    result = web_tools.search_web(query, max_results=max_results, timeout_s=timeout_s)
    return {
        "query": result.query,
        "results": [
            {
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
            }
            for item in result.results
        ],
    }


@mcp.tool()
def web_browse(
    url: str,
    max_chars: int = _DEFAULT_BROWSE_MAX_CHARS,
    timeout_s: int = 20,
) -> dict:
    """Browse a URL and return extracted text content."""
    require_non_empty_string(url, "url")
    result = web_tools.browse_url(url, max_chars=max_chars, timeout_s=timeout_s)
    return {
        "url": result.url,
        "final_url": result.final_url,
        "status_code": result.status_code,
        "truncated": result.truncated,
        "content": result.content,
    }


@mcp.tool()
def get_config() -> dict:
    """Return the current helping_hands configuration (from env vars)."""
    cfg = Config.from_env()
    return {
        "model": cfg.model,
        "verbose": cfg.verbose,
        "enable_execution": cfg.enable_execution,
        "enable_web": cfg.enable_web,
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
