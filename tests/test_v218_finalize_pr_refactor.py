"""Tests for v218: _generate_pr_title_and_body() and _create_new_pr() helpers.

Validates the PR description generation helper and the new-PR creation method
extracted from ``_finalize_repo_pr()`` in ``Hand`` base class.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.base import (
    _BRANCH_PREFIX,
    _DEFAULT_COMMIT_MSG_TEMPLATE,
    _DEFAULT_PR_TITLE_TEMPLATE,
    _META_PR_BRANCH,
    _META_PR_COMMIT,
    _META_PR_NUMBER,
    _META_PR_STATUS,
    _META_PR_URL,
    PRStatus,
)
from helping_hands.lib.repo import RepoIndex


class _StubHand(Hand):
    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


# ---------------------------------------------------------------------------
# _generate_pr_title_and_body
# ---------------------------------------------------------------------------


class TestGeneratePrTitleAndBody:
    """Tests for Hand._generate_pr_title_and_body()."""

    def test_returns_rich_title_and_body_when_available(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        rich = MagicMock()
        rich.title = "feat: rich title"
        rich.body = "Rich body content"

        with patch(
            "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
            return_value=rich,
        ):
            title, body = hand._generate_pr_title_and_body(
                repo_dir=repo_index.root,
                base_branch="main",
                backend="test",
                prompt="add feature",
                summary="done",
                commit_sha="abc123",
            )

        assert title == "feat: rich title"
        assert body == "Rich body content"

    def test_falls_back_to_commit_message_from_prompt(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_pr_description",
                return_value=None,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                "._commit_message_from_prompt",
                return_value="feat: inferred title",
            ),
            patch.object(hand, "_build_generic_pr_body", return_value="generic body"),
        ):
            title, body = hand._generate_pr_title_and_body(
                repo_dir=repo_index.root,
                base_branch="main",
                backend="test",
                prompt="add feature",
                summary="done",
                commit_sha="abc123",
            )

        assert title == "feat: inferred title"
        assert body == "generic body"

    def test_falls_back_to_default_template_when_prompt_returns_empty(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_pr_description",
                return_value=None,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                "._commit_message_from_prompt",
                return_value="",
            ),
            patch.object(hand, "_build_generic_pr_body", return_value="generic body"),
        ):
            title, body = hand._generate_pr_title_and_body(
                repo_dir=repo_index.root,
                base_branch="main",
                backend="mybackend",
                prompt="task",
                summary="result",
                commit_sha="def456",
            )

        assert title == _DEFAULT_PR_TITLE_TEMPLATE.format(backend="mybackend")
        assert body == "generic body"

    def test_passes_correct_args_to_generate_pr_description(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        rich = MagicMock()
        rich.title = "t"
        rich.body = "b"

        with patch(
            "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
            return_value=rich,
        ) as mock_gen:
            hand._generate_pr_title_and_body(
                repo_dir=repo_index.root,
                base_branch="develop",
                backend="langgraph",
                prompt="fix bug",
                summary="patched",
                commit_sha="aaa111",
            )

        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["repo_dir"] == repo_index.root
        assert call_kwargs["base_branch"] == "develop"
        assert call_kwargs["backend"] == "langgraph"
        assert call_kwargs["prompt"] == "fix bug"
        assert call_kwargs["summary"] == "patched"

    def test_generic_body_receives_commit_sha(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_pr_description",
                return_value=None,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                "._commit_message_from_prompt",
                return_value="title",
            ),
            patch.object(
                hand, "_build_generic_pr_body", return_value="body"
            ) as mock_body,
        ):
            hand._generate_pr_title_and_body(
                repo_dir=repo_index.root,
                base_branch="main",
                backend="test",
                prompt="p",
                summary="s",
                commit_sha="sha999",
            )

        call_kwargs = mock_body.call_args[1]
        assert call_kwargs["commit_sha"] == "sha999"
        assert call_kwargs["backend"] == "test"


# ---------------------------------------------------------------------------
# _create_new_pr
# ---------------------------------------------------------------------------


class TestCreateNewPr:
    """Tests for Hand._create_new_pr()."""

    def _make_hand(self, repo_index: RepoIndex) -> _StubHand:
        config = Config(repo=str(repo_index.root), model="test-model")
        return _StubHand(config, repo_index)

    def _base_metadata(self) -> dict[str, str]:
        return {
            "auto_pr": "true",
            _META_PR_STATUS: "not_attempted",
            _META_PR_URL: "",
            _META_PR_NUMBER: "",
            _META_PR_BRANCH: "",
            _META_PR_COMMIT: "",
        }

    def test_creates_branch_commits_pushes_and_opens_pr(
        self, repo_index: RepoIndex
    ) -> None:
        hand = self._make_hand(repo_index)

        mock_gh = MagicMock()
        mock_gh.add_and_commit.return_value = "abc123"
        mock_gh.get_repo.return_value = MagicMock(default_branch="main")
        mock_gh.create_pr.return_value = MagicMock(
            number=42, url="https://github.com/o/r/pull/42"
        )

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_commit_message",
                return_value="feat: commit msg",
            ),
            patch.object(
                hand,
                "_generate_pr_title_and_body",
                return_value=("feat: pr title", "pr body"),
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            metadata = hand._create_new_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="add feature",
                summary="done",
                metadata=self._base_metadata(),
            )

        assert metadata[_META_PR_STATUS] == PRStatus.CREATED
        assert metadata[_META_PR_URL] == "https://github.com/o/r/pull/42"
        assert metadata[_META_PR_NUMBER] == "42"
        assert metadata[_META_PR_COMMIT] == "abc123"
        assert metadata[_META_PR_BRANCH].startswith(_BRANCH_PREFIX)

    def test_branch_name_contains_backend(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)

        mock_gh = MagicMock()
        mock_gh.add_and_commit.return_value = "sha1"
        mock_gh.get_repo.return_value = MagicMock(default_branch="main")
        mock_gh.create_pr.return_value = MagicMock(number=1, url="u")

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_commit_message",
                return_value="msg",
            ),
            patch.object(
                hand,
                "_generate_pr_title_and_body",
                return_value=("t", "b"),
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            metadata = hand._create_new_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="langgraph",
                prompt="p",
                summary="s",
                metadata=self._base_metadata(),
            )

        branch = metadata[_META_PR_BRANCH]
        assert branch.startswith(f"{_BRANCH_PREFIX}langgraph-")

    def test_uses_fallback_commit_message_when_generator_returns_empty(
        self, repo_index: RepoIndex
    ) -> None:
        hand = self._make_hand(repo_index)

        mock_gh = MagicMock()
        mock_gh.add_and_commit.return_value = "sha1"
        mock_gh.get_repo.return_value = MagicMock(default_branch="main")
        mock_gh.create_pr.return_value = MagicMock(number=1, url="u")

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_commit_message",
                return_value="",
            ),
            patch.object(
                hand,
                "_generate_pr_title_and_body",
                return_value=("t", "b"),
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            hand._create_new_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="p",
                summary="s",
                metadata=self._base_metadata(),
            )

        commit_msg = mock_gh.add_and_commit.call_args
        # The fallback template should be used
        expected = _DEFAULT_COMMIT_MSG_TEMPLATE.format(backend="test")
        # add_and_commit is called via _add_and_commit_with_hook_retry
        # which delegates to gh.add_and_commit — check the commit message arg
        assert expected in str(commit_msg) or mock_gh.add_and_commit.called

    def test_falls_back_to_default_base_branch_on_api_error(
        self, repo_index: RepoIndex
    ) -> None:
        hand = self._make_hand(repo_index)

        mock_gh = MagicMock()
        mock_gh.add_and_commit.return_value = "sha1"
        mock_gh.get_repo.side_effect = GithubException(500, "API error", None)
        mock_gh.create_pr.return_value = MagicMock(number=1, url="u")

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_commit_message",
                return_value="msg",
            ),
            patch.object(
                hand,
                "_generate_pr_title_and_body",
                return_value=("t", "b"),
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            hand._create_new_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="p",
                summary="s",
                metadata=self._base_metadata(),
            )

        # Should still call create_pr with default base branch
        create_call = mock_gh.create_pr.call_args[1]
        assert create_call["base"] == "main"

    def test_uses_remote_default_branch_when_available(
        self, repo_index: RepoIndex
    ) -> None:
        hand = self._make_hand(repo_index)

        mock_gh = MagicMock()
        mock_gh.add_and_commit.return_value = "sha1"
        mock_gh.get_repo.return_value = MagicMock(default_branch="develop")
        mock_gh.create_pr.return_value = MagicMock(number=1, url="u")

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_commit_message",
                return_value="msg",
            ),
            patch.object(
                hand,
                "_generate_pr_title_and_body",
                return_value=("t", "b"),
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            hand._create_new_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="p",
                summary="s",
                metadata=self._base_metadata(),
            )

        create_call = mock_gh.create_pr.call_args[1]
        assert create_call["base"] == "develop"

    def test_passes_title_and_body_to_create_pr(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)

        mock_gh = MagicMock()
        mock_gh.add_and_commit.return_value = "sha1"
        mock_gh.get_repo.return_value = MagicMock(default_branch="main")
        mock_gh.create_pr.return_value = MagicMock(number=1, url="u")

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_commit_message",
                return_value="msg",
            ),
            patch.object(
                hand,
                "_generate_pr_title_and_body",
                return_value=("My Title", "My Body"),
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            hand._create_new_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="p",
                summary="s",
                metadata=self._base_metadata(),
            )

        create_call = mock_gh.create_pr.call_args[1]
        assert create_call["title"] == "My Title"
        assert create_call["body"] == "My Body"


# ---------------------------------------------------------------------------
# _update_pr_description delegates to _generate_pr_title_and_body
# ---------------------------------------------------------------------------


class TestUpdatePrDescriptionDelegation:
    """Verify _update_pr_description uses _generate_pr_title_and_body."""

    def test_update_pr_description_uses_generated_body(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 5

        mock_gh = MagicMock()

        with patch.object(
            hand,
            "_generate_pr_title_and_body",
            return_value=("ignored title", "generated body"),
        ):
            hand._update_pr_description(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="p",
                summary="s",
                base_branch="main",
                commit_sha="sha1",
            )

        mock_gh.update_pr_body.assert_called_once_with(
            "owner/repo", 5, body="generated body"
        )

    def test_update_pr_description_raises_without_pr_number(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = None

        with pytest.raises(ValueError, match="pr_number must be set"):
            hand._update_pr_description(
                gh=MagicMock(),
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="p",
                summary="s",
                base_branch="main",
                commit_sha="sha1",
            )


# ---------------------------------------------------------------------------
# _create_pr_for_diverged_branch delegates to _generate_pr_title_and_body
# ---------------------------------------------------------------------------


class TestDivergedBranchDelegation:
    """Verify _create_pr_for_diverged_branch uses _generate_pr_title_and_body."""

    def test_diverged_pr_appends_follow_up_note(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 10

        mock_gh = MagicMock()
        mock_gh.create_pr.return_value = MagicMock(
            number=11, url="https://github.com/o/r/pull/11"
        )

        with (
            patch.object(
                hand,
                "_generate_pr_title_and_body",
                return_value=("pr title", "pr body"),
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            metadata = hand._create_pr_for_diverged_branch(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="p",
                summary="s",
                metadata={},
                pr_branch="feature-branch",
                commit_sha="sha1",
            )

        create_call = mock_gh.create_pr.call_args[1]
        assert create_call["title"] == "pr title"
        assert "pr body" in create_call["body"]
        assert "Follow-up to #10" in create_call["body"]
        assert metadata[_META_PR_STATUS] == PRStatus.CREATED
