"""Search tools for repo-aware code exploration.

Provides glob-based file discovery and content search (grep) within a
repository root.  Inspired by the context-engineering patterns in the
awesome-claude-code ecosystem — effective AI agents need fast, bounded
code search to build working context before making changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from helping_hands.lib.meta.tools.filesystem import resolve_repo_target

__all__ = [
    "GlobResult",
    "GrepMatch",
    "GrepResult",
    "glob_files",
    "grep_content",
    "list_directory",
]


@dataclass(frozen=True)
class GlobResult:
    """Result of a glob file search."""

    pattern: str
    matches: tuple[str, ...]
    truncated: bool = False


@dataclass(frozen=True)
class GrepMatch:
    """A single grep match with file, line number, and content."""

    file: str
    line_number: int
    line: str


@dataclass(frozen=True)
class GrepResult:
    """Result of a content search."""

    pattern: str
    matches: tuple[GrepMatch, ...] = field(default_factory=tuple)
    truncated: bool = False


def glob_files(
    repo_root: Path,
    *,
    pattern: str,
    base_dir: str | None = None,
    max_results: int = 100,
) -> GlobResult:
    """Find files matching a glob pattern within the repo.

    Args:
        repo_root: Repository root directory.
        pattern: Glob pattern (e.g. ``**/*.py``, ``src/**/*.ts``).
        base_dir: Optional repo-relative subdirectory to search within.
        max_results: Maximum number of results to return.
    """
    if not pattern.strip():
        raise ValueError("pattern must be non-empty")
    if max_results <= 0:
        raise ValueError("max_results must be > 0")

    root = repo_root.resolve()
    if base_dir:
        search_root = resolve_repo_target(root, base_dir)
        if not search_root.is_dir():
            raise NotADirectoryError(f"base_dir is not a directory: {base_dir}")
    else:
        search_root = root

    matches: list[str] = []
    truncated = False
    for path in sorted(search_root.rglob(pattern)):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            matches.append(rel)
            if len(matches) >= max_results:
                truncated = True
                break

    return GlobResult(
        pattern=pattern,
        matches=tuple(matches),
        truncated=truncated,
    )


def grep_content(
    repo_root: Path,
    *,
    pattern: str,
    glob: str | None = None,
    base_dir: str | None = None,
    max_results: int = 50,
    ignore_case: bool = False,
) -> GrepResult:
    """Search file contents for a regex pattern within the repo.

    Args:
        repo_root: Repository root directory.
        pattern: Regex pattern to search for.
        glob: Optional file glob to filter which files are searched.
        base_dir: Optional repo-relative subdirectory to search within.
        max_results: Maximum number of matches to return.
        ignore_case: Whether to ignore case in pattern matching.
    """
    if not pattern.strip():
        raise ValueError("pattern must be non-empty")
    if max_results <= 0:
        raise ValueError("max_results must be > 0")

    root = repo_root.resolve()
    if base_dir:
        search_root = resolve_repo_target(root, base_dir)
        if not search_root.is_dir():
            raise NotADirectoryError(f"base_dir is not a directory: {base_dir}")
    else:
        search_root = root

    flags = re.IGNORECASE if ignore_case else 0
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"invalid regex pattern: {exc}") from exc

    # Collect candidate files.
    file_glob = glob or "**/*"
    candidates = sorted(search_root.rglob(file_glob))

    matches: list[GrepMatch] = []
    truncated = False

    _skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv"}

    for path in candidates:
        if not path.is_file():
            continue
        # Skip common non-text directories.
        parts = path.relative_to(root).parts
        if any(part in _skip_dirs for part in parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            if compiled.search(line):
                matches.append(
                    GrepMatch(file=rel, line_number=line_no, line=line.rstrip())
                )
                if len(matches) >= max_results:
                    truncated = True
                    break
        if truncated:
            break

    return GrepResult(
        pattern=pattern,
        matches=tuple(matches),
        truncated=truncated,
    )


def list_directory(
    repo_root: Path,
    *,
    rel_path: str = ".",
    max_entries: int = 200,
    include_hidden: bool = False,
) -> tuple[list[str], bool]:
    """List directory contents (files and subdirectories).

    Args:
        repo_root: Repository root directory.
        rel_path: Repo-relative directory to list (default: root).
        max_entries: Maximum entries to return.
        include_hidden: Whether to include dotfiles/dotdirs.

    Returns:
        Tuple of (entries, truncated) where entries are ``path/`` for dirs.
    """
    root = repo_root.resolve()
    target = root if rel_path == "." else resolve_repo_target(root, rel_path)
    if not target.is_dir():
        raise NotADirectoryError(f"not a directory: {rel_path}")

    entries: list[str] = []
    truncated = False
    for child in sorted(target.iterdir()):
        name = child.name
        if not include_hidden and name.startswith("."):
            continue
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{name}{suffix}")
        if len(entries) >= max_entries:
            truncated = True
            break

    return entries, truncated
