"""Agent orchestration: the 'hand' that interacts with the AI."""

from __future__ import annotations

from dataclasses import dataclass

from helping_hands.lib.config import Config
from helping_hands.lib.repo import RepoIndex


@dataclass
class Agent:
    """AI agent that operates on a repo with a given config."""

    config: Config
    repo_index: RepoIndex

    def greet(self) -> str:
        """Return a short greeting summarising the loaded repo."""
        n = len(self.repo_index.files)
        s = "s" if n != 1 else ""
        return f"Ready. Indexed {n} file{s} in {self.repo_index.root}."
