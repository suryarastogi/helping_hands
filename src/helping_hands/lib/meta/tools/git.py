"""Git tools for repo-aware version control operations.

These helpers provide safe, read-oriented git operations inside a repository
root.  Inspired by the ecosystem patterns in awesome-claude-code — many
effective AI coding workflows rely on git context (status, diff, log, grep)
to ground changes in the current state of the codebase.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "GitResult",
    "git_diff",
    "git_grep",
    "git_log",
    "git_status",
]


@dataclass(frozen=True)
class GitResult:
    """Captured result of a git operation."""

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        """Return whether the git command completed successfully."""
        return self.exit_code == 0


def _run_git(
    repo_root: Path,
    args: list[str],
    *,
    timeout_s: int = 30,
) -> GitResult:
    """Run a git command confined to *repo_root*."""
    root = repo_root.resolve()
    if not root.is_dir():
        raise ValueError("repo_root must be an existing directory")

    command = ["git", "-C", str(root), *args]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return GitResult(
            command=command,
            exit_code=124,
            stdout=stdout,
            stderr=f"{stderr}\ngit command timed out after {timeout_s}s".strip(),
        )
    except FileNotFoundError:
        return GitResult(
            command=command,
            exit_code=127,
            stdout="",
            stderr="git is not installed or not on PATH",
        )

    return GitResult(
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def git_status(
    repo_root: Path,
    *,
    timeout_s: int = 30,
) -> GitResult:
    """Return ``git status --short`` for the repo."""
    return _run_git(repo_root, ["status", "--short"], timeout_s=timeout_s)


def git_diff(
    repo_root: Path,
    *,
    ref: str | None = None,
    staged: bool = False,
    name_only: bool = False,
    timeout_s: int = 30,
) -> GitResult:
    """Return ``git diff`` output, optionally against a ref or staged changes."""
    args = ["diff"]
    if staged:
        args.append("--cached")
    if name_only:
        args.append("--name-only")
    if ref:
        args.append(ref)
    return _run_git(repo_root, args, timeout_s=timeout_s)


def git_log(
    repo_root: Path,
    *,
    max_count: int = 20,
    oneline: bool = True,
    timeout_s: int = 30,
) -> GitResult:
    """Return recent git log entries."""
    args = ["log", f"--max-count={max_count}"]
    if oneline:
        args.append("--oneline")
    return _run_git(repo_root, args, timeout_s=timeout_s)


def git_grep(
    repo_root: Path,
    *,
    pattern: str,
    paths: list[str] | None = None,
    max_count: int = 50,
    ignore_case: bool = False,
    timeout_s: int = 30,
) -> GitResult:
    """Search tracked files for a pattern using ``git grep``."""
    if not pattern.strip():
        raise ValueError("pattern must be non-empty")
    args = ["grep", "-n", f"--max-count={max_count}"]
    if ignore_case:
        args.append("-i")
    args.append(pattern)
    if paths:
        args.append("--")
        args.extend(paths)
    return _run_git(repo_root, args, timeout_s=timeout_s)
