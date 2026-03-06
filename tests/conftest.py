"""Shared pytest fixtures for the helping_hands test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.repo import RepoIndex


@pytest.fixture()
def repo_index(tmp_path: Path) -> RepoIndex:
    """A minimal RepoIndex backed by tmp_path with two stub files."""
    (tmp_path / "main.py").write_text("")
    (tmp_path / "utils.py").write_text("")
    return RepoIndex.from_path(tmp_path)


@pytest.fixture()
def fake_config(tmp_path: Path) -> Config:
    """A Config pointing at tmp_path with a test model."""
    return Config(repo=str(tmp_path), model="test-model")
