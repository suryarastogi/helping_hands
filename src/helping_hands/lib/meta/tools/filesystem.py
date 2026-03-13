"""Filesystem tools for repo-aware execution.

These helpers provide a narrow, reusable interface for safe path handling and
file operations inside a repository root. They are consumed by hand modules
and MCP tools so read/write behavior is centralized and path-confined.
"""

from __future__ import annotations

from pathlib import Path


def normalize_relative_path(rel_path: str) -> str:
    """Normalize a repo-relative path to a safe forward-slash form."""
    if not isinstance(rel_path, str):
        raise TypeError("rel_path must be a string")
    normalized = rel_path.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def resolve_repo_target(repo_root: Path, rel_path: str) -> Path:
    """Resolve a relative path inside ``repo_root`` or raise ``ValueError``."""
    root = repo_root.resolve()
    if not root.is_dir():
        raise ValueError("repo_root must be an existing directory")
    normalized = normalize_relative_path(rel_path)
    if not normalized or normalized.startswith("/"):
        raise ValueError("path must be a non-empty relative path")

    target = (root / normalized).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes repository root") from exc
    return target


_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def read_text_file(
    repo_root: Path,
    rel_path: str,
    *,
    max_chars: int | None = None,
    max_file_size: int = _MAX_FILE_SIZE_BYTES,
) -> tuple[str, bool, str]:
    """Read a text file and return ``(content, truncated, display_path)``.

    Args:
        repo_root: Repository root directory.
        rel_path: Relative path within the repository.
        max_chars: Optional character limit for returned content.
        max_file_size: Maximum file size in bytes (default 10 MB).
            Files exceeding this limit raise ``ValueError``.
    """
    if max_file_size <= 0:
        raise ValueError(f"max_file_size must be positive, got {max_file_size}")
    if max_chars is not None and max_chars <= 0:
        raise ValueError(f"max_chars must be positive, got {max_chars}")

    root = repo_root.resolve()
    target = resolve_repo_target(root, rel_path)

    if not target.exists():
        raise FileNotFoundError("file not found")
    if target.is_dir():
        raise IsADirectoryError("path is a directory")

    file_size = target.stat().st_size
    if file_size > max_file_size:
        mb = file_size / (1024 * 1024)
        limit_mb = max_file_size / (1024 * 1024)
        raise ValueError(f"file is too large ({mb:.1f} MB, limit {limit_mb:.1f} MB)")

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
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        display = target.relative_to(root).as_posix()
        raise RuntimeError(f"cannot write file {display}: {exc}") from exc
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
