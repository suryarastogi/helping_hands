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

    @property
    def file_count(self) -> int:
        """Return the total number of indexed files."""
        return len(self.files)

    def has_file(self, relative_path: str) -> bool:
        """Check whether *relative_path* exists in the index.

        Uses the pre-sorted ``files`` list for an O(log n) binary search.

        Args:
            relative_path: Forward-slash separated path relative to repo root
                (e.g. ``"src/main.py"``).

        Returns:
            ``True`` if the path is present in the index.
        """
        import bisect

        i = bisect.bisect_left(self.files, relative_path)
        return i < len(self.files) and self.files[i] == relative_path

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
