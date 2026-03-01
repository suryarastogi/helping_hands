"""Unit tests for E2EHand private helper methods.

These tests exercise the static/class helpers on ``E2EHand`` without
needing GitHub credentials or network access.
"""

import os

from helping_hands.lib.hands.v1.hand.e2e import E2EHand


class TestSafeRepoDir:
    def test_simple_owner_repo(self) -> None:
        assert E2EHand._safe_repo_dir("owner/repo") == "owner_repo"

    def test_strips_leading_trailing_slashes(self) -> None:
        assert E2EHand._safe_repo_dir("/owner/repo/") == "owner_repo"

    def test_preserves_dots_and_hyphens(self) -> None:
        assert E2EHand._safe_repo_dir("my-org/my.repo") == "my-org_my.repo"

    def test_replaces_spaces(self) -> None:
        assert E2EHand._safe_repo_dir("owner/repo name") == "owner_repo_name"

    def test_replaces_special_chars(self) -> None:
        assert E2EHand._safe_repo_dir("owner/repo@v2!") == "owner_repo_v2_"

    def test_empty_string(self) -> None:
        assert E2EHand._safe_repo_dir("") == ""


class TestWorkBase:
    def test_default_is_cwd(self, monkeypatch: object) -> None:
        os.environ.pop("HELPING_HANDS_WORK_ROOT", None)
        result = E2EHand._work_base()
        assert str(result) == "."

    def test_env_override(self, monkeypatch: object) -> None:
        os.environ["HELPING_HANDS_WORK_ROOT"] = "/tmp/test-work"
        try:
            result = E2EHand._work_base()
            assert str(result) == "/tmp/test-work"
        finally:
            os.environ.pop("HELPING_HANDS_WORK_ROOT", None)


class TestConfiguredBaseBranch:
    def test_default_empty(self) -> None:
        os.environ.pop("HELPING_HANDS_BASE_BRANCH", None)
        assert E2EHand._configured_base_branch() == ""

    def test_env_override(self) -> None:
        os.environ["HELPING_HANDS_BASE_BRANCH"] = "  develop  "
        try:
            assert E2EHand._configured_base_branch() == "develop"
        finally:
            os.environ.pop("HELPING_HANDS_BASE_BRANCH", None)


class TestDraftPrEnabled:
    def test_default_false(self) -> None:
        os.environ.pop("HELPING_HANDS_DRAFT_PR", None)
        assert E2EHand._draft_pr_enabled() is False

    def test_enabled_with_1(self) -> None:
        os.environ["HELPING_HANDS_DRAFT_PR"] = "1"
        try:
            assert E2EHand._draft_pr_enabled() is True
        finally:
            os.environ.pop("HELPING_HANDS_DRAFT_PR", None)

    def test_enabled_with_true(self) -> None:
        os.environ["HELPING_HANDS_DRAFT_PR"] = "true"
        try:
            assert E2EHand._draft_pr_enabled() is True
        finally:
            os.environ.pop("HELPING_HANDS_DRAFT_PR", None)

    def test_disabled_with_random_value(self) -> None:
        os.environ["HELPING_HANDS_DRAFT_PR"] = "no"
        try:
            assert E2EHand._draft_pr_enabled() is False
        finally:
            os.environ.pop("HELPING_HANDS_DRAFT_PR", None)


class TestBuildE2EPrBody:
    def test_contains_all_fields(self) -> None:
        body = E2EHand._build_e2e_pr_body(
            hand_uuid="abc-123",
            prompt="test prompt",
            stamp_utc="2026-03-01T00:00:00+00:00",
            commit_sha="deadbeef",
        )
        assert "abc-123" in body
        assert "test prompt" in body
        assert "2026-03-01T00:00:00+00:00" in body
        assert "deadbeef" in body
        assert "Automated E2E" in body


class TestBuildE2EPrComment:
    def test_contains_all_fields(self) -> None:
        comment = E2EHand._build_e2e_pr_comment(
            hand_uuid="abc-123",
            prompt="test prompt",
            stamp_utc="2026-03-01T00:00:00+00:00",
            commit_sha="deadbeef",
        )
        assert "abc-123" in comment
        assert "test prompt" in comment
        assert "2026-03-01T00:00:00+00:00" in comment
        assert "deadbeef" in comment
        assert "E2E update" in comment
