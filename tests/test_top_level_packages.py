"""Tests for top-level package imports, docstrings, and conftest fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock

import helping_hands
import helping_hands.cli
import helping_hands.lib
import helping_hands.lib.hands
import helping_hands.server


class TestRootPackage:
    """Tests for the helping_hands root package."""

    def test_version_is_string(self) -> None:
        assert isinstance(helping_hands.__version__, str)

    def test_version_is_semver_like(self) -> None:
        parts = helping_hands.__version__.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts)

    def test_docstring_present(self) -> None:
        assert helping_hands.__doc__
        assert "repo builder" in helping_hands.__doc__.lower()


class TestLibPackage:
    """Tests for helping_hands.lib package."""

    def test_importable(self) -> None:
        assert helping_hands.lib is not None

    def test_docstring_present(self) -> None:
        assert helping_hands.lib.__doc__
        assert "library" in helping_hands.lib.__doc__.lower()

    def test_submodules_accessible(self) -> None:
        from helping_hands.lib import config, repo

        assert config is not None
        assert repo is not None


class TestCLIPackage:
    """Tests for helping_hands.cli package."""

    def test_importable(self) -> None:
        assert helping_hands.cli is not None

    def test_docstring_present(self) -> None:
        assert helping_hands.cli.__doc__
        assert "cli" in helping_hands.cli.__doc__.lower()


class TestServerPackage:
    """Tests for helping_hands.server package."""

    def test_importable(self) -> None:
        assert helping_hands.server is not None

    def test_docstring_present(self) -> None:
        assert helping_hands.server.__doc__
        assert "server" in helping_hands.server.__doc__.lower()


class TestHandsPackage:
    """Tests for helping_hands.lib.hands package."""

    def test_importable(self) -> None:
        assert helping_hands.lib.hands is not None

    def test_docstring_present(self) -> None:
        assert helping_hands.lib.hands.__doc__
        assert "hands" in helping_hands.lib.hands.__doc__.lower()


class TestMockGitHubClientFixture:
    """Tests for the mock_github_client conftest fixture."""

    def test_fixture_returns_magic_mock(self, mock_github_client: MagicMock) -> None:
        assert isinstance(mock_github_client, MagicMock)

    def test_context_manager_protocol(self, mock_github_client: MagicMock) -> None:
        with mock_github_client as gh:
            assert gh is mock_github_client

    def test_default_branch(self, mock_github_client: MagicMock) -> None:
        assert mock_github_client.default_branch() == "main"

    def test_add_and_commit(self, mock_github_client: MagicMock) -> None:
        result = mock_github_client.add_and_commit()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_create_pr_defaults(self, mock_github_client: MagicMock) -> None:
        pr = mock_github_client.create_pr()
        assert pr.number == 42
        assert "pull/42" in pr.url

    def test_whoami(self, mock_github_client: MagicMock) -> None:
        assert mock_github_client.whoami()["login"] == "bot-user"

    def test_token_present(self, mock_github_client: MagicMock) -> None:
        assert mock_github_client.token == "ghp_test"

    def test_get_check_runs(self, mock_github_client: MagicMock) -> None:
        result = mock_github_client.get_check_runs()
        assert result["conclusion"] == "success"

    def test_overridable(self, mock_github_client: MagicMock) -> None:
        """Callers can override defaults for specific test scenarios."""
        mock_github_client.default_branch.return_value = "develop"
        assert mock_github_client.default_branch() == "develop"
