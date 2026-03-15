"""Repository ingestion: clone, walk, and index a git repo."""

from __future__ import annotations

__all__ = ["RepoIndex"]

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RepoIndex:
    """Structural map of a repository.

    Attributes:
        root: Absolute path to the repository root directory.
        files: Sorted list of relative file paths (excludes ``.git``).
        reference_repos: Read-only reference repos as ``(name, local_path)`` pairs.
    """

    root: Path
    files: list[str] = field(default_factory=list)
    reference_repos: list[tuple[str, Path]] = field(default_factory=list)

    @classmethod
    def from_path(cls, path: Path) -> RepoIndex:
        """Walk a local repo and build an index of its files."""
        if not path.is_dir():
            msg = f"Not a directory: {path}"
            raise FileNotFoundError(msg)

        files: list[str] = []
        try:
            files = sorted(
                str(p.relative_to(path))
                for p in path.rglob("*")
                if p.is_file() and ".git" not in p.parts
            )
        except PermissionError:
            logger.warning(
                "Permission denied during file traversal of %s; "
                "returning partial index",
                path,
            )
        return cls(root=path, files=files)
