"""Tests for v198 — Request validation hardening and DRY form defaults.

Validates:
- ``BuildRequest.pr_number`` rejects zero/negative values via ``ge=1``
- ``ScheduleRequest.pr_number`` rejects zero/negative values via ``ge=1``
- ``BuildRequest.github_token`` whitespace-only → None normalization
- ``ScheduleRequest.github_token`` whitespace-only → None normalization
- ``BuildRequest.reference_repos`` rejects empty/whitespace-only items
- ``ScheduleRequest.reference_repos`` rejects empty/whitespace-only items
- ``_build_form_redirect_query`` uses ``_DEFAULT_CI_WAIT_MINUTES`` constant
- ``search_web`` rejects queries exceeding ``MAX_SEARCH_QUERY_LENGTH``
- ``MAX_SEARCH_QUERY_LENGTH`` constant in ``web.__all__``
"""

from __future__ import annotations

import inspect
import sys

import pytest

_has_fastapi = "fastapi" in sys.modules or bool(
    __import__("importlib").util.find_spec("fastapi")
)
_skip_no_fastapi = pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")


# ---------------------------------------------------------------------------
# BuildRequest.pr_number — ge=1 validation
# ---------------------------------------------------------------------------


@_skip_no_fastapi
class TestBuildRequestPrNumber:
    """Verify BuildRequest.pr_number rejects invalid values."""

    def test_pr_number_none_accepted(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix")
        assert req.pr_number is None

    def test_pr_number_positive_accepted(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix", pr_number=42)
        assert req.pr_number == 42

    def test_pr_number_one_accepted(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix", pr_number=1)
        assert req.pr_number == 1

    def test_pr_number_zero_rejected(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="pr_number"):
            BuildRequest(repo_path="/tmp/r", prompt="fix", pr_number=0)

    def test_pr_number_negative_rejected(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="pr_number"):
            BuildRequest(repo_path="/tmp/r", prompt="fix", pr_number=-5)


# ---------------------------------------------------------------------------
# ScheduleRequest.pr_number — ge=1 validation
# ---------------------------------------------------------------------------


@_skip_no_fastapi
class TestScheduleRequestPrNumber:
    """Verify ScheduleRequest.pr_number rejects invalid values."""

    def test_pr_number_none_accepted(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="test",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="fix",
        )
        assert req.pr_number is None

    def test_pr_number_positive_accepted(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="test",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="fix",
            pr_number=7,
        )
        assert req.pr_number == 7

    def test_pr_number_zero_rejected(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="pr_number"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="/tmp/r",
                prompt="fix",
                pr_number=0,
            )

    def test_pr_number_negative_rejected(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="pr_number"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="/tmp/r",
                prompt="fix",
                pr_number=-1,
            )


# ---------------------------------------------------------------------------
# BuildRequest.github_token — whitespace normalization
# ---------------------------------------------------------------------------


@_skip_no_fastapi
class TestBuildRequestGithubToken:
    """Verify BuildRequest.github_token whitespace-to-None normalization."""

    def test_none_stays_none(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix")
        assert req.github_token is None

    def test_valid_token_preserved(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix", github_token="ghp_abc123")
        assert req.github_token == "ghp_abc123"

    def test_empty_string_becomes_none(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix", github_token="")
        assert req.github_token is None

    def test_whitespace_only_becomes_none(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix", github_token="   ")
        assert req.github_token is None

    def test_tabs_only_becomes_none(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix", github_token="\t\n  ")
        assert req.github_token is None


# ---------------------------------------------------------------------------
# ScheduleRequest.github_token — whitespace normalization
# ---------------------------------------------------------------------------


@_skip_no_fastapi
class TestScheduleRequestGithubToken:
    """Verify ScheduleRequest.github_token whitespace-to-None normalization."""

    def test_whitespace_only_becomes_none(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="test",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="fix",
            github_token="   ",
        )
        assert req.github_token is None

    def test_valid_token_preserved(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="test",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="fix",
            github_token="ghp_xyz",
        )
        assert req.github_token == "ghp_xyz"


# ---------------------------------------------------------------------------
# BuildRequest.reference_repos — item validation
# ---------------------------------------------------------------------------


@_skip_no_fastapi
class TestBuildRequestReferenceRepos:
    """Verify BuildRequest.reference_repos rejects empty/whitespace items."""

    def test_valid_repos_accepted(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(
            repo_path="/tmp/r",
            prompt="fix",
            reference_repos=["owner/repo1", "owner/repo2"],
        )
        assert req.reference_repos == ["owner/repo1", "owner/repo2"]

    def test_empty_list_accepted(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="fix", reference_repos=[])
        assert req.reference_repos == []

    def test_empty_string_rejected(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="reference_repos"):
            BuildRequest(
                repo_path="/tmp/r",
                prompt="fix",
                reference_repos=["owner/repo", ""],
            )

    def test_whitespace_only_rejected(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="reference_repos"):
            BuildRequest(
                repo_path="/tmp/r",
                prompt="fix",
                reference_repos=["   "],
            )

    def test_error_includes_index(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="reference_repos\\[1\\]"):
            BuildRequest(
                repo_path="/tmp/r",
                prompt="fix",
                reference_repos=["owner/ok", "  "],
            )


# ---------------------------------------------------------------------------
# ScheduleRequest.reference_repos — item validation
# ---------------------------------------------------------------------------


@_skip_no_fastapi
class TestScheduleRequestReferenceRepos:
    """Verify ScheduleRequest.reference_repos rejects empty/whitespace items."""

    def test_empty_string_rejected(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="reference_repos"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="/tmp/r",
                prompt="fix",
                reference_repos=[""],
            )

    def test_valid_repos_accepted(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="test",
            cron_expression="0 0 * * *",
            repo_path="/tmp/r",
            prompt="fix",
            reference_repos=["owner/repo"],
        )
        assert req.reference_repos == ["owner/repo"]


# ---------------------------------------------------------------------------
# _build_form_redirect_query — DRY CI wait default
# ---------------------------------------------------------------------------


@_skip_no_fastapi
class TestBuildFormRedirectQueryCiDefault:
    """Verify _build_form_redirect_query uses the shared constant."""

    def test_default_param_uses_constant(self) -> None:
        from helping_hands.server.app import _build_form_redirect_query
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES

        sig = inspect.signature(_build_form_redirect_query)
        default = sig.parameters["ci_check_wait_minutes"].default
        assert default == DEFAULT_CI_WAIT_MINUTES

    def test_default_ci_wait_omitted_from_query(self) -> None:
        from helping_hands.server.app import _build_form_redirect_query
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES

        result = _build_form_redirect_query(
            repo_path="/r",
            prompt="p",
            backend="codexcli",
            max_iterations=6,
            error="oops",
            ci_check_wait_minutes=DEFAULT_CI_WAIT_MINUTES,
        )
        assert "ci_check_wait_minutes" not in result

    def test_non_default_ci_wait_included_in_query(self) -> None:
        from helping_hands.server.app import _build_form_redirect_query

        result = _build_form_redirect_query(
            repo_path="/r",
            prompt="p",
            backend="codexcli",
            max_iterations=6,
            error="oops",
            ci_check_wait_minutes=5.0,
        )
        assert result["ci_check_wait_minutes"] == "5.0"


# ---------------------------------------------------------------------------
# search_web — query length validation
# ---------------------------------------------------------------------------


class TestSearchWebQueryLength:
    """Verify search_web rejects overly long queries."""

    def test_max_search_query_length_constant_value(self) -> None:
        from helping_hands.lib.meta.tools.web import MAX_SEARCH_QUERY_LENGTH

        assert MAX_SEARCH_QUERY_LENGTH == 500

    def test_max_search_query_length_in_all(self) -> None:
        from helping_hands.lib.meta.tools import web

        assert "MAX_SEARCH_QUERY_LENGTH" in web.__all__

    def test_query_at_max_length_accepted(self) -> None:
        """Query exactly at the limit should not raise ValueError."""
        from unittest.mock import patch

        from helping_hands.lib.meta.tools.web import (
            MAX_SEARCH_QUERY_LENGTH,
            search_web,
        )

        query = "a" * MAX_SEARCH_QUERY_LENGTH
        with (
            patch(
                "helping_hands.lib.meta.tools.web.urlopen",
                side_effect=RuntimeError("blocked"),
            ),
            pytest.raises(RuntimeError, match="blocked"),
        ):
            search_web(query)

    def test_query_exceeding_max_length_rejected(self) -> None:
        from helping_hands.lib.meta.tools.web import (
            MAX_SEARCH_QUERY_LENGTH,
            search_web,
        )

        query = "a" * (MAX_SEARCH_QUERY_LENGTH + 1)
        with pytest.raises(ValueError, match=r"query length.*exceeds maximum"):
            search_web(query)

    def test_query_with_leading_whitespace_measured_after_strip(self) -> None:
        """Whitespace is stripped before length check."""
        from unittest.mock import patch

        from helping_hands.lib.meta.tools.web import (
            MAX_SEARCH_QUERY_LENGTH,
            search_web,
        )

        # Content exactly at limit, but with leading/trailing whitespace
        query = "  " + "a" * MAX_SEARCH_QUERY_LENGTH + "  "
        with (
            patch(
                "helping_hands.lib.meta.tools.web.urlopen",
                side_effect=RuntimeError("blocked"),
            ),
            pytest.raises(RuntimeError, match="blocked"),
        ):
            search_web(query)
