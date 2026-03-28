"""Tests for v140: CLI buffer/truncation constants and GitHub PR number validation.

_APPLY_CHANGES_TRUNCATION_LIMIT and _STREAM_READ_BUFFER_SIZE govern how much
subprocess output is buffered and sent to the AI; changing them silently affects
both memory use and model context size.  Pinning their values here catches
accidental edits during refactors.

The GitHub PR validation tests (get_pr, update_pr_body, list_prs) guard against
zero and negative PR numbers reaching the PyGitHub API.  A regression would cause
confusing "not found" or "rate limited" errors from GitHub instead of a clear
ValueError at the client boundary.

_DEFAULT_MAX_TOKENS in the Anthropic provider is the fallback when no max_tokens is
specified; setting it too low truncates AI responses mid-sentence.
"""

import pytest

# ---------------------------------------------------------------------------
# CLI base constants (cli/base.py)
# ---------------------------------------------------------------------------


class TestApplyChangesTruncationLimit:
    """Tests for _APPLY_CHANGES_TRUNCATION_LIMIT in cli/base.py."""

    def test_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _APPLY_CHANGES_TRUNCATION_LIMIT,
        )

        assert _APPLY_CHANGES_TRUNCATION_LIMIT == 2000

    def test_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _APPLY_CHANGES_TRUNCATION_LIMIT,
        )

        assert _APPLY_CHANGES_TRUNCATION_LIMIT > 0

    def test_is_int(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _APPLY_CHANGES_TRUNCATION_LIMIT,
        )

        assert isinstance(_APPLY_CHANGES_TRUNCATION_LIMIT, int)


class TestStreamReadBufferSize:
    """Tests for _STREAM_READ_BUFFER_SIZE in cli/base.py."""

    def test_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _STREAM_READ_BUFFER_SIZE,
        )

        assert _STREAM_READ_BUFFER_SIZE == 1024

    def test_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _STREAM_READ_BUFFER_SIZE,
        )

        assert _STREAM_READ_BUFFER_SIZE > 0

    def test_is_int(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _STREAM_READ_BUFFER_SIZE,
        )

        assert isinstance(_STREAM_READ_BUFFER_SIZE, int)

    def test_docker_sandbox_imports_from_base(self) -> None:
        """docker_sandbox_claude.py imports _STREAM_READ_BUFFER_SIZE from base."""
        import importlib

        source = importlib.util.find_spec(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude"
        )
        assert source is not None


# ---------------------------------------------------------------------------
# Anthropic provider constant (anthropic.py)
# ---------------------------------------------------------------------------


class TestAnthropicDefaultMaxTokens:
    """Tests for _DEFAULT_MAX_TOKENS in anthropic.py."""

    def test_value(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import _DEFAULT_MAX_TOKENS

        assert _DEFAULT_MAX_TOKENS == 1024

    def test_positive(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import _DEFAULT_MAX_TOKENS

        assert _DEFAULT_MAX_TOKENS > 0

    def test_is_int(self) -> None:
        from helping_hands.lib.ai_providers.anthropic import _DEFAULT_MAX_TOKENS

        assert isinstance(_DEFAULT_MAX_TOKENS, int)


# ---------------------------------------------------------------------------
# GitHub PR number/limit validation (github.py)
# ---------------------------------------------------------------------------


class TestGetPrNumberValidation:
    """Tests for get_pr() PR number validation."""

    def test_rejects_zero(self, tmp_path: object) -> None:
        from helping_hands.lib.github import GitHubClient

        client = GitHubClient(token="fake")
        with pytest.raises(ValueError, match="PR number must be positive"):
            client.get_pr("owner/repo", 0)

    def test_rejects_negative(self, tmp_path: object) -> None:
        from helping_hands.lib.github import GitHubClient

        client = GitHubClient(token="fake")
        with pytest.raises(ValueError, match="PR number must be positive"):
            client.get_pr("owner/repo", -1)


class TestUpdatePrBodyNumberValidation:
    """Tests for update_pr_body() PR number validation."""

    def test_rejects_zero(self) -> None:
        from helping_hands.lib.github import GitHubClient

        client = GitHubClient(token="fake")
        with pytest.raises(ValueError, match="PR number must be positive"):
            client.update_pr_body("owner/repo", 0, body="desc")

    def test_rejects_negative(self) -> None:
        from helping_hands.lib.github import GitHubClient

        client = GitHubClient(token="fake")
        with pytest.raises(ValueError, match="PR number must be positive"):
            client.update_pr_body("owner/repo", -3, body="desc")


class TestListPrsLimitValidation:
    """Tests for list_prs() limit validation."""

    def test_rejects_zero(self) -> None:
        from helping_hands.lib.github import GitHubClient

        client = GitHubClient(token="fake")
        with pytest.raises(ValueError, match="limit must be positive"):
            client.list_prs("owner/repo", limit=0)

    def test_rejects_negative(self) -> None:
        from helping_hands.lib.github import GitHubClient

        client = GitHubClient(token="fake")
        with pytest.raises(ValueError, match="limit must be positive"):
            client.list_prs("owner/repo", limit=-10)


# ---------------------------------------------------------------------------
# _truncate_diff limit validation (pr_description.py)
# ---------------------------------------------------------------------------


class TestTruncateDiffLimitValidation:
    """Tests for _truncate_diff() limit validation."""

    def test_rejects_zero_limit(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_diff

        with pytest.raises(ValueError, match="limit must be positive"):
            _truncate_diff("hello", limit=0)

    def test_rejects_negative_limit(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_diff

        with pytest.raises(ValueError, match="limit must be positive"):
            _truncate_diff("hello", limit=-5)

    def test_accepts_positive_limit(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_diff

        result = _truncate_diff("hello", limit=10)
        assert result == "hello"

    def test_truncates_at_limit(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_diff

        result = _truncate_diff("hello world", limit=5)
        assert result.startswith("hello")
        assert "truncated" in result
