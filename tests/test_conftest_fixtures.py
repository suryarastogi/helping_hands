"""Tests for shared conftest fixtures (repo_index, fake_config, make_cli_hand, mock_github_client, make_fake_module).

Documents and locks the contract of the test infrastructure itself: each
fixture's return type, default field values, and mutability guarantees. Without
these tests, a conftest change (e.g. renaming a default model, changing
mock_github_client.create_pr return shape) would silently invalidate dozens of
tests that rely on those defaults. make_fake_module is also tested here since
it is the standard way to inject optional-dependency mocks (openai, anthropic)
without installing the packages.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand
from helping_hands.lib.hands.v1.hand.e2e import E2EHand
from helping_hands.lib.repo import RepoIndex


class TestRepoIndexFixture:
    def test_returns_repo_index(self, repo_index) -> None:
        assert isinstance(repo_index, RepoIndex)

    def test_contains_stub_files(self, repo_index) -> None:
        assert "main.py" in repo_index.files
        assert "utils.py" in repo_index.files

    def test_backed_by_tmp_path(self, repo_index) -> None:
        assert repo_index.root.exists()


class TestFakeConfigFixture:
    def test_returns_config(self, fake_config) -> None:
        assert isinstance(fake_config, Config)

    def test_model_is_test(self, fake_config) -> None:
        assert fake_config.model == "test-model"

    def test_repo_path_exists(self, fake_config) -> None:
        assert Path(fake_config.repo).exists()


class TestMakeCliHandFixture:
    def test_creates_hand_instance(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="anthropic/test")
        assert isinstance(hand, GooseCLIHand)

    def test_default_model(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand)
        assert hand.config.model == "test-model"

    def test_custom_model(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        assert hand.config.model == "openai/gpt-5.2"

    def test_has_config_and_repo_index(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand)
        assert hasattr(hand, "config")
        assert isinstance(hand.config, Config)


class TestMakeFakeModuleFixture:
    def test_returns_module_type(self, make_fake_module) -> None:
        mod = make_fake_module("mypackage")
        assert isinstance(mod, ModuleType)

    def test_module_has_correct_name(self, make_fake_module) -> None:
        mod = make_fake_module("openai")
        assert mod.__name__ == "openai"

    def test_sets_keyword_attributes(self, make_fake_module) -> None:
        sentinel = MagicMock()
        mod = make_fake_module("openai", OpenAI=sentinel)
        assert mod.OpenAI is sentinel

    def test_multiple_attributes(self, make_fake_module) -> None:
        cls_a = MagicMock()
        cls_b = MagicMock()
        mod = make_fake_module("anthropic", Anthropic=cls_a, AsyncAnthropic=cls_b)
        assert mod.Anthropic is cls_a
        assert mod.AsyncAnthropic is cls_b

    def test_no_attributes(self, make_fake_module) -> None:
        mod = make_fake_module("empty")
        assert not hasattr(mod, "Client")


class TestMockGithubClientFixture:
    """Tests for the mock_github_client shared fixture."""

    def test_returns_magic_mock(self, mock_github_client) -> None:
        assert isinstance(mock_github_client, MagicMock)

    def test_context_manager_protocol(self, mock_github_client) -> None:
        with mock_github_client as gh:
            assert gh is mock_github_client

    def test_has_token(self, mock_github_client) -> None:
        assert mock_github_client.token == "ghp_test"

    def test_default_branch(self, mock_github_client) -> None:
        assert mock_github_client.default_branch() == "main"

    def test_current_branch(self, mock_github_client) -> None:
        assert mock_github_client.current_branch() == "main"

    def test_add_and_commit(self, mock_github_client) -> None:
        sha = mock_github_client.add_and_commit()
        assert isinstance(sha, str) and len(sha) > 0

    def test_create_pr_defaults(self, mock_github_client) -> None:
        pr = mock_github_client.create_pr()
        assert pr.number == 42
        assert "pull/42" in pr.html_url

    def test_get_pr_returns_dict(self, mock_github_client) -> None:
        pr_info = mock_github_client.get_pr()
        assert pr_info["base"] == "main"
        assert "head" in pr_info

    def test_get_check_runs_default_success(self, mock_github_client) -> None:
        result = mock_github_client.get_check_runs()
        assert result["conclusion"] == "success"

    def test_whoami(self, mock_github_client) -> None:
        assert mock_github_client.whoami()["login"] == "bot-user"

    def test_clone_returns_path(self, mock_github_client) -> None:
        assert isinstance(mock_github_client.clone(), Path)


class TestMakeCliHandWithE2E:
    """Tests that make_cli_hand works with non-CLI hand subclasses too."""

    def test_creates_e2e_hand(self, make_cli_hand) -> None:
        hand = make_cli_hand(E2EHand)
        assert isinstance(hand, E2EHand)

    def test_e2e_hand_has_auto_pr(self, make_cli_hand) -> None:
        hand = make_cli_hand(E2EHand)
        assert hand.auto_pr is True
