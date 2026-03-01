"""Repository ingestion: clone, walk, and index a git repo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["RepoIndex"]


@dataclass
class RepoIndex:
    """Structural map of a repository."""

    root: Path
    files: list[str] = field(default_factory=list)

    @classmethod
    def from_path(cls, path: Path) -> RepoIndex:
        """Walk a local repo and build an index of its files."""
        if not path.is_dir():
            msg = f"Not a directory: {path}"
            raise FileNotFoundError(msg)

        files = sorted(
            str(p.relative_to(path))
            for p in path.rglob("*")
            if p.is_file() and ".git" not in p.parts
        )
        return cls(root=path, files=files)
