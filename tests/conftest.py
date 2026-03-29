"""Shared pytest fixtures that enforce test isolation boundaries.

Every test that touches a Hand, Config, or GitHubClient must use these
fixtures rather than constructing production objects directly.  This
prevents tests from accidentally reaching the real filesystem, invoking
real AI providers, or authenticating against live GitHub endpoints.
The mock_github_client fixture pre-wires the context-manager protocol
and sensible return values so that tests exercising finalize/PR paths
stay deterministic without per-test boilerplate.  The make_fake_module
factory keeps AI-provider tests from importing real SDKs (openai,
anthropic, etc.) that may not be installed in all CI matrix entries.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

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


@pytest.fixture()
def make_cli_hand(tmp_path: Path) -> Callable[..., Any]:
    """Factory fixture for CLI hand instances backed by tmp_path.

    Usage::

        def test_something(make_cli_hand):
            hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
    """

    def _factory(hand_cls: type, model: str = "test-model") -> Any:
        (tmp_path / "main.py").write_text("")
        config = Config(repo=str(tmp_path), model=model)
        ri = RepoIndex.from_path(tmp_path)
        return hand_cls(config=config, repo_index=ri)

    return _factory


@pytest.fixture()
def mock_github_client() -> MagicMock:
    """A MagicMock satisfying the GitHubClient context-manager interface.

    Pre-configured with sensible defaults for common operations
    (default_branch, add_and_commit, create_pr, get_pr, whoami).
    Tests can override individual return values as needed.

    Usage::

        def test_push(mock_github_client):
            mock_github_client.push.side_effect = RuntimeError("rejected")
    """
    gh = MagicMock()
    gh.__enter__ = MagicMock(return_value=gh)
    gh.__exit__ = MagicMock(return_value=False)
    gh.token = "ghp_test"
    gh.default_branch.return_value = "main"
    gh.current_branch.return_value = "main"
    gh.clone.return_value = Path("/tmp/cloned")
    gh.add_and_commit.return_value = "abc123deadbeef"
    gh.whoami.return_value = {"login": "bot-user"}
    pr_mock = MagicMock()
    pr_mock.number = 42
    pr_mock.url = "https://github.com/owner/repo/pull/42"
    pr_mock.html_url = "https://github.com/owner/repo/pull/42"
    pr_mock.title = "test PR"
    pr_mock.head = "helping-hands/test-branch"
    pr_mock.base = "main"
    gh.create_pr.return_value = pr_mock
    gh.get_pr.return_value = {
        "base": "main",
        "head": "existing-branch",
        "url": "https://github.com/owner/repo/pull/99",
    }
    gh.get_check_runs.return_value = {"conclusion": "success"}
    return gh


@pytest.fixture()
def make_fake_module() -> Callable[..., ModuleType]:
    """Factory fixture for creating fake SDK modules with MagicMock attributes.

    Reduces boilerplate in AI provider tests that mock ``openai``, ``anthropic``,
    ``google.genai``, ``litellm``, etc.  Returns a ``ModuleType`` with arbitrary
    attributes set from keyword arguments.

    Usage::

        def test_openai_build_inner(make_fake_module):
            mod = make_fake_module("openai", OpenAI=MagicMock())
            with patch.dict(sys.modules, {"openai": mod}):
                ...
    """

    def _factory(name: str, **attrs: Any) -> ModuleType:
        mod = ModuleType(name)
        for attr_name, attr_value in attrs.items():
            setattr(mod, attr_name, attr_value)
        return mod

    return _factory
