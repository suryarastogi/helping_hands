"""Filesystem tools for repo-aware execution.

These helpers provide a narrow, reusable interface for safe path handling and
file operations inside a repository root. They are consumed by hand modules
and MCP tools so read/write behavior is centralized and path-confined.
"""

from __future__ import annotations

__all__ = [
    "mkdir_path",
    "normalize_relative_path",
    "path_exists",
    "read_text_file",
    "resolve_repo_target",
    "write_text_file",
]

from pathlib import Path


def normalize_relative_path(rel_path: str) -> str:
    """Normalize a repo-relative path to a safe forward-slash form."""
    normalized = rel_path.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def resolve_repo_target(repo_root: Path, rel_path: str) -> Path:
    """Resolve a relative path inside ``repo_root`` or raise ``ValueError``."""
    root = repo_root.resolve()
    normalized = normalize_relative_path(rel_path)
    if not normalized or normalized.startswith("/"):
        raise ValueError("invalid path")

    target = (root / normalized).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("invalid path") from exc
    return target


def read_text_file(
    repo_root: Path,
    rel_path: str,
    *,
    max_chars: int | None = None,
) -> tuple[str, bool, str]:
    """Read a text file and return ``(content, truncated, display_path)``."""
    root = repo_root.resolve()
    target = resolve_repo_target(root, rel_path)

    if not target.exists():
        raise FileNotFoundError("file not found")
    if target.is_dir():
        raise IsADirectoryError("path is a directory")

    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UnicodeError("file is not UTF-8 text") from exc

    truncated = False
    if max_chars is not None and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    display_path = target.relative_to(root).as_posix()
    return text, truncated, display_path


def write_text_file(repo_root: Path, rel_path: str, content: str) -> str:
    """Write UTF-8 text to a repo-relative file and return normalized path."""
    root = repo_root.resolve()
    target = resolve_repo_target(root, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target.relative_to(root).as_posix()


def mkdir_path(repo_root: Path, rel_path: str) -> str:
    """Create a repo-relative directory and return normalized path."""
    root = repo_root.resolve()
    target = resolve_repo_target(root, rel_path)
    target.mkdir(parents=True, exist_ok=True)
    return target.relative_to(root).as_posix()


def path_exists(repo_root: Path, rel_path: str) -> bool:
    """Return whether a repo-relative path exists."""
    try:
        target = resolve_repo_target(repo_root, rel_path)
    except ValueError:
        return False
    return target.exists()
