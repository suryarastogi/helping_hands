"""Tests for helping_hands.lib.agent."""

from __future__ import annotations

from pathlib import Path

from helping_hands.lib.agent import Agent
from helping_hands.lib.config import Config
from helping_hands.lib.repo import RepoIndex


class TestAgent:
    def test_greet_with_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        idx = RepoIndex.from_path(tmp_path)
        agent = Agent(config=Config(), repo_index=idx)

        msg = agent.greet()
        assert "2 files" in msg

    def test_greet_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "only.py").write_text("")
        idx = RepoIndex.from_path(tmp_path)
        agent = Agent(config=Config(), repo_index=idx)

        msg = agent.greet()
        assert "1 file" in msg
        assert "1 files" not in msg
