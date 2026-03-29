"""Guard PRStatus StrEnum values and the grouping frozensets that drive hand result logic.

PRStatus values appear in hand result dicts, Celery task state, and the frontend
status display. If any member's string value changes (e.g. "no_changes" → "no-changes"),
existing persisted task states in Redis would not match, causing the frontend to
show incorrect status badges. PR_STATUSES_SKIPPED and PR_STATUSES_WITH_URL control
whether the hand result includes a GitHub URL and whether finalization is skipped;
incorrect membership means PRs could be created when they should be skipped, or the
URL could be omitted from a successful result. The member-count test catches
accidental additions or removals to the enum.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.hands.v1.hand.base import (
    PR_STATUSES_SKIPPED,
    PR_STATUSES_WITH_URL,
    Hand,
    PRStatus,
)

# ---------------------------------------------------------------------------
# PRStatus enum — membership and string values
# ---------------------------------------------------------------------------


class TestPRStatusEnum:
    """Verify PRStatus is a StrEnum with correct values."""

    def test_is_str_subclass(self) -> None:
        assert isinstance(PRStatus.CREATED, str)

    def test_created_equals_string(self) -> None:
        assert PRStatus.CREATED == "created"

    def test_updated_equals_string(self) -> None:
        assert PRStatus.UPDATED == "updated"

    def test_no_changes_equals_string(self) -> None:
        assert PRStatus.NO_CHANGES == "no_changes"

    def test_disabled_equals_string(self) -> None:
        assert PRStatus.DISABLED == "disabled"

    def test_not_attempted_equals_string(self) -> None:
        assert PRStatus.NOT_ATTEMPTED == "not_attempted"

    def test_no_repo_equals_string(self) -> None:
        assert PRStatus.NO_REPO == "no_repo"

    def test_not_git_repo_equals_string(self) -> None:
        assert PRStatus.NOT_GIT_REPO == "not_git_repo"

    def test_no_github_origin_equals_string(self) -> None:
        assert PRStatus.NO_GITHUB_ORIGIN == "no_github_origin"

    def test_precommit_failed_equals_string(self) -> None:
        assert PRStatus.PRECOMMIT_FAILED == "precommit_failed"

    def test_missing_token_equals_string(self) -> None:
        assert PRStatus.MISSING_TOKEN == "missing_token"

    def test_git_error_equals_string(self) -> None:
        assert PRStatus.GIT_ERROR == "git_error"

    def test_error_equals_string(self) -> None:
        assert PRStatus.ERROR == "error"

    def test_all_members_are_unique(self) -> None:
        values = [m.value for m in PRStatus]
        assert len(values) == len(set(values))

    def test_member_count(self) -> None:
        assert len(PRStatus) == 12


# ---------------------------------------------------------------------------
# PRStatus grouping frozensets
# ---------------------------------------------------------------------------


class TestPRStatusGroupings:
    """Verify WITH_URL and SKIPPED frozensets."""

    def test_with_url_is_frozenset(self) -> None:
        assert isinstance(PR_STATUSES_WITH_URL, frozenset)

    def test_with_url_contains_created_and_updated(self) -> None:
        assert PRStatus.CREATED in PR_STATUSES_WITH_URL
        assert PRStatus.UPDATED in PR_STATUSES_WITH_URL

    def test_with_url_has_exactly_two_members(self) -> None:
        assert len(PR_STATUSES_WITH_URL) == 2

    def test_skipped_is_frozenset(self) -> None:
        assert isinstance(PR_STATUSES_SKIPPED, frozenset)

    def test_skipped_contains_no_changes_and_disabled(self) -> None:
        assert PRStatus.NO_CHANGES in PR_STATUSES_SKIPPED
        assert PRStatus.DISABLED in PR_STATUSES_SKIPPED

    def test_skipped_has_exactly_two_members(self) -> None:
        assert len(PR_STATUSES_SKIPPED) == 2

    def test_with_url_and_skipped_are_disjoint(self) -> None:
        assert PR_STATUSES_WITH_URL.isdisjoint(PR_STATUSES_SKIPPED)


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------


class TestBackwardCompatAliases:
    """Old _PR_STATUS_* names still importable and equal to enum members."""

    def test_created_alias(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_CREATED

        assert _PR_STATUS_CREATED is PRStatus.CREATED

    def test_updated_alias(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_UPDATED

        assert _PR_STATUS_UPDATED is PRStatus.UPDATED

    def test_no_changes_alias(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NO_CHANGES

        assert _PR_STATUS_NO_CHANGES is PRStatus.NO_CHANGES

    def test_disabled_alias(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_DISABLED

        assert _PR_STATUS_DISABLED is PRStatus.DISABLED

    def test_not_attempted_alias(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NOT_ATTEMPTED

        assert _PR_STATUS_NOT_ATTEMPTED is PRStatus.NOT_ATTEMPTED

    def test_statuses_with_url_alias(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUSES_WITH_URL

        assert _PR_STATUSES_WITH_URL is PR_STATUSES_WITH_URL

    def test_statuses_skipped_alias(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUSES_SKIPPED

        assert _PR_STATUSES_SKIPPED is PR_STATUSES_SKIPPED


# ---------------------------------------------------------------------------
# _build_generic_pr_body — validation uses require_non_empty_string
# ---------------------------------------------------------------------------


class TestBuildGenericPrBodyValidation:
    """Verify commit_sha and stamp_utc now use require_non_empty_string."""

    def test_empty_commit_sha_raises(self) -> None:
        with pytest.raises(ValueError, match="commit_sha"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do something",
                summary="",
                commit_sha="",
                stamp_utc="2026-01-01T00:00:00+00:00",
            )

    def test_whitespace_commit_sha_raises(self) -> None:
        with pytest.raises(ValueError, match="commit_sha"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do something",
                summary="",
                commit_sha="   ",
                stamp_utc="2026-01-01T00:00:00+00:00",
            )

    def test_empty_stamp_utc_raises(self) -> None:
        with pytest.raises(ValueError, match="stamp_utc"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do something",
                summary="",
                commit_sha="abc123",
                stamp_utc="",
            )

    def test_whitespace_stamp_utc_raises(self) -> None:
        with pytest.raises(ValueError, match="stamp_utc"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do something",
                summary="",
                commit_sha="abc123",
                stamp_utc="   ",
            )

    def test_valid_inputs_return_body(self) -> None:
        result = Hand._build_generic_pr_body(
            backend="test",
            prompt="do something",
            summary="changed stuff",
            commit_sha="abc123",
            stamp_utc="2026-01-01T00:00:00+00:00",
        )
        assert "abc123" in result
        assert "do something" in result
        assert "changed stuff" in result


# ---------------------------------------------------------------------------
# _pr_result_metadata — DRY helper
# ---------------------------------------------------------------------------


class TestPrResultMetadata:
    """Verify _pr_result_metadata updates the dict correctly."""

    def test_populates_all_fields(self) -> None:
        meta: dict[str, str] = {"auto_pr": "true"}
        result = Hand._pr_result_metadata(
            meta,
            status=PRStatus.CREATED,
            pr_url="https://github.com/o/r/pull/1",
            pr_number="1",
            pr_branch="helping-hands/test-abc123",
            pr_commit="deadbeef",
        )
        assert result is meta  # mutates in place
        assert result["pr_status"] == "created"
        assert result["pr_url"] == "https://github.com/o/r/pull/1"
        assert result["pr_number"] == "1"
        assert result["pr_branch"] == "helping-hands/test-abc123"
        assert result["pr_commit"] == "deadbeef"
        assert result["auto_pr"] == "true"  # existing key preserved

    def test_updated_status(self) -> None:
        meta: dict[str, str] = {}
        result = Hand._pr_result_metadata(
            meta,
            status=PRStatus.UPDATED,
            pr_url="url",
            pr_number="42",
            pr_branch="branch",
            pr_commit="sha",
        )
        assert result["pr_status"] == "updated"

    def test_returns_same_dict_object(self) -> None:
        meta: dict[str, str] = {"existing": "value"}
        result = Hand._pr_result_metadata(
            meta,
            status=PRStatus.CREATED,
            pr_url="https://github.com/o/r/pull/99",
            pr_number="99",
            pr_branch="helping-hands/test",
            pr_commit="abc1234",
        )
        assert result is meta
        assert "existing" in result


# ---------------------------------------------------------------------------
# PRStatus is exported in __all__
# ---------------------------------------------------------------------------


class TestPRStatusExport:
    """Verify PRStatus is in __all__."""

    def test_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand import base

        assert "PRStatus" in base.__all__
