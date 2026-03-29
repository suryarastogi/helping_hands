"""Tests for v219 finalization precondition extraction and status dispatch tables.

_validate_finalization_preconditions() is the gatekeeper before any git/GitHub
operations run. If it stops raising early on bad state (disabled flag, no git
repo, no staged changes, no remote) those operations will fail with confusing
errors deep in the stack rather than a clear early message.

The dispatch tables (_PR_STATUS_TEMPLATES, _CI_FIX_TEMPLATES) map status codes
to human-readable message templates. If a key is missing or a template is
mangled, the status line shown in the PR body will be blank or broken, making
it impossible to diagnose what happened during a run.
"""

from __future__ import annotations

from inspect import getsource
from unittest.mock import MagicMock, patch

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.base import (
    _META_PR_STATUS,
    _PR_STATUS_CREATED,
    _PR_STATUS_DISABLED,
    _PR_STATUS_NO_CHANGES,
    _PR_STATUS_UPDATED,
    PRStatus,
)
from helping_hands.lib.hands.v1.hand.cli.base import (
    _CI_FIX_TEMPLATES,
    _META_CI_FIX_ATTEMPTS,
    _META_CI_FIX_ERROR,
    _META_CI_FIX_STATUS,
    _META_PR_URL,
    _PR_STATUS_TEMPLATES,
    CIFixStatus,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Stub implementations
# ---------------------------------------------------------------------------


class _StubHand(Hand):
    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


# ---------------------------------------------------------------------------
# _validate_finalization_preconditions
# ---------------------------------------------------------------------------


class TestValidateFinalizationPreconditions:
    """Tests for Hand._validate_finalization_preconditions()."""

    def test_disabled_when_auto_pr_false(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = False
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        result = hand._validate_finalization_preconditions(metadata)
        assert result is None
        assert metadata[_META_PR_STATUS] == _PR_STATUS_DISABLED

    def test_no_repo_when_dir_missing(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = True
        # Point to a non-existent directory
        hand.repo_index = MagicMock()
        hand.repo_index.root.resolve.return_value = MagicMock()
        hand.repo_index.root.resolve.return_value.is_dir.return_value = False
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        result = hand._validate_finalization_preconditions(metadata)
        assert result is None
        assert metadata[_META_PR_STATUS] == PRStatus.NO_REPO

    def test_not_git_repo(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = True
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        with patch.object(hand, "_run_git_read", return_value="false"):
            result = hand._validate_finalization_preconditions(metadata)
        assert result is None
        assert metadata[_META_PR_STATUS] == PRStatus.NOT_GIT_REPO

    def test_no_changes(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = True
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        with patch.object(hand, "_run_git_read", side_effect=["true", ""]):
            result = hand._validate_finalization_preconditions(metadata)
        assert result is None
        assert metadata[_META_PR_STATUS] == _PR_STATUS_NO_CHANGES

    def test_no_github_origin(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = True
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        with (
            patch.object(hand, "_run_git_read", side_effect=["true", "M file.py"]),
            patch.object(hand, "_github_repo_from_origin", return_value=""),
        ):
            result = hand._validate_finalization_preconditions(metadata)
        assert result is None
        assert metadata[_META_PR_STATUS] == PRStatus.NO_GITHUB_ORIGIN

    def test_precommit_failure(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = True
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        with (
            patch.object(hand, "_run_git_read", side_effect=["true", "M file.py"]),
            patch.object(hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(hand, "_should_run_precommit_before_pr", return_value=True),
            patch.object(
                hand,
                "_run_precommit_checks_and_fixes",
                side_effect=RuntimeError("hook failed"),
            ),
        ):
            result = hand._validate_finalization_preconditions(metadata)
        assert result is None
        assert metadata[_META_PR_STATUS] == PRStatus.PRECOMMIT_FAILED
        assert metadata["pr_error"] == "hook failed"

    def test_precommit_cleans_all_changes(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = True
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        with (
            patch.object(
                hand,
                "_run_git_read",
                side_effect=["true", "M file.py", ""],
            ),
            patch.object(hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(hand, "_should_run_precommit_before_pr", return_value=True),
            patch.object(hand, "_run_precommit_checks_and_fixes"),
        ):
            result = hand._validate_finalization_preconditions(metadata)
        assert result is None
        assert metadata[_META_PR_STATUS] == _PR_STATUS_NO_CHANGES

    def test_success_returns_repo_dir_and_name(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="m")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = True
        metadata: dict[str, str] = {_META_PR_STATUS: ""}
        with (
            patch.object(hand, "_run_git_read", side_effect=["true", "M file.py"]),
            patch.object(hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(hand, "_should_run_precommit_before_pr", return_value=False),
        ):
            result = hand._validate_finalization_preconditions(metadata)
        assert result is not None
        repo_dir, repo_name = result
        assert repo_dir == repo_index.root.resolve()
        assert repo_name == "owner/repo"

    def test_finalize_repo_pr_delegates_to_validate(
        self, repo_index: RepoIndex
    ) -> None:
        """_finalize_repo_pr calls _validate_finalization_preconditions."""
        src = getsource(Hand._finalize_repo_pr)
        assert "_validate_finalization_preconditions" in src


# ---------------------------------------------------------------------------
# _PR_STATUS_TEMPLATES dispatch table
# ---------------------------------------------------------------------------


class TestPrStatusTemplates:
    """Tests for _PR_STATUS_TEMPLATES and _format_pr_status_message dispatch."""

    def test_contains_all_known_statuses(self) -> None:
        expected = {
            _PR_STATUS_CREATED,
            _PR_STATUS_UPDATED,
            _PR_STATUS_DISABLED,
            _PR_STATUS_NO_CHANGES,
            "interrupted",
        }
        assert set(_PR_STATUS_TEMPLATES.keys()) == expected

    def test_templates_are_non_empty_strings(self) -> None:
        for status, template in _PR_STATUS_TEMPLATES.items():
            assert isinstance(template, str), f"template for {status} not str"
            assert len(template) > 0, f"template for {status} is empty"

    def test_url_templates_contain_pr_url_placeholder(self) -> None:
        for status in (_PR_STATUS_CREATED, _PR_STATUS_UPDATED):
            assert "{pr_url}" in _PR_STATUS_TEMPLATES[status]

    def test_non_url_templates_are_static(self) -> None:
        for status in (_PR_STATUS_DISABLED, _PR_STATUS_NO_CHANGES, "interrupted"):
            assert "{pr_url}" not in _PR_STATUS_TEMPLATES[status]


# ---------------------------------------------------------------------------
# _CI_FIX_TEMPLATES dispatch table
# ---------------------------------------------------------------------------


class TestCiFixTemplates:
    """Tests for _CI_FIX_TEMPLATES and _format_ci_fix_message dispatch."""

    def test_contains_expected_statuses(self) -> None:
        expected = {
            CIFixStatus.SUCCESS,
            CIFixStatus.EXHAUSTED,
            CIFixStatus.PENDING_TIMEOUT,
            CIFixStatus.ERROR,
        }
        assert set(_CI_FIX_TEMPLATES.keys()) == expected

    def test_templates_are_non_empty_strings(self) -> None:
        for status, template in _CI_FIX_TEMPLATES.items():
            assert isinstance(template, str), f"template for {status} not str"
            assert len(template) > 0, f"template for {status} is empty"

    def test_exhausted_template_has_attempts_placeholder(self) -> None:
        assert "{attempts}" in _CI_FIX_TEMPLATES[CIFixStatus.EXHAUSTED]

    def test_error_template_has_error_placeholder(self) -> None:
        assert "{error}" in _CI_FIX_TEMPLATES[CIFixStatus.ERROR]

    def test_checking_status_not_in_templates(self) -> None:
        """CHECKING is a transient state, not a final message."""
        assert CIFixStatus.CHECKING not in _CI_FIX_TEMPLATES

    def test_no_checks_status_not_in_templates(self) -> None:
        """NO_CHECKS is not surfaced as a user message."""
        assert CIFixStatus.NO_CHECKS not in _CI_FIX_TEMPLATES


# ---------------------------------------------------------------------------
# _format_pr_status_message integration with dispatch table
# ---------------------------------------------------------------------------


class _StubCLIHand(_TwoPhaseCLIHand):
    _CLI_LABEL = "test"
    _BACKEND_NAME = "test-backend"
    _COMMAND_NAME = "test"

    async def _invoke_cli_with_cmd(self, *a: object, **kw: object) -> str:
        return ""

    def _normalize_args(self, *a: object, **kw: object) -> list[str]:
        return []

    def _resolve_cli_model(self, *a: object, **kw: object) -> str:
        return "m"


class TestFormatPrStatusMessageDispatch:
    """_format_pr_status_message uses _PR_STATUS_TEMPLATES."""

    def _make_hand(self, repo_index: RepoIndex) -> _StubCLIHand:
        config = Config(repo=str(repo_index.root), model="m")
        return _StubCLIHand(config, repo_index)

    def test_created_includes_url(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: _PR_STATUS_CREATED, _META_PR_URL: "https://pr/1"}
        msg = hand._format_pr_status_message(md)
        assert msg == "[test] PR created: https://pr/1"

    def test_updated_includes_url(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: _PR_STATUS_UPDATED, _META_PR_URL: "https://pr/2"}
        msg = hand._format_pr_status_message(md)
        assert msg == "[test] PR updated: https://pr/2"

    def test_disabled(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: _PR_STATUS_DISABLED}
        msg = hand._format_pr_status_message(md)
        assert msg == "[test] PR disabled (--no-pr)."

    def test_no_changes(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: _PR_STATUS_NO_CHANGES}
        msg = hand._format_pr_status_message(md)
        assert msg == "[test] PR skipped: no file changes detected."

    def test_interrupted(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: "interrupted"}
        msg = hand._format_pr_status_message(md)
        assert msg == "[test] Interrupted."

    def test_unknown_status_with_error(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: "git_error", "pr_error": "push failed"}
        msg = hand._format_pr_status_message(md)
        assert msg == "[test] PR status: git_error (push failed)"

    def test_unknown_status_without_error(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: "error"}
        msg = hand._format_pr_status_message(md)
        assert msg == "[test] PR status: error"

    def test_empty_status_returns_none(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_PR_STATUS: ""}
        assert hand._format_pr_status_message(md) is None


# ---------------------------------------------------------------------------
# _format_ci_fix_message integration with dispatch table
# ---------------------------------------------------------------------------


class TestFormatCiFixMessageDispatch:
    """_format_ci_fix_message uses _CI_FIX_TEMPLATES."""

    def _make_hand(self, repo_index: RepoIndex) -> _StubCLIHand:
        config = Config(repo=str(repo_index.root), model="m")
        return _StubCLIHand(config, repo_index)

    def test_success(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_CI_FIX_STATUS: CIFixStatus.SUCCESS}
        msg = hand._format_ci_fix_message(md)
        assert msg == "[test] CI checks passed."

    def test_exhausted_with_attempts(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {
            _META_CI_FIX_STATUS: CIFixStatus.EXHAUSTED,
            _META_CI_FIX_ATTEMPTS: "3",
        }
        msg = hand._format_ci_fix_message(md)
        assert msg == "[test] CI fix failed after 3 attempt(s)."

    def test_pending_timeout(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_CI_FIX_STATUS: CIFixStatus.PENDING_TIMEOUT}
        msg = hand._format_ci_fix_message(md)
        assert msg == "[test] CI checks still pending after max wait time."

    def test_error_with_message(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {
            _META_CI_FIX_STATUS: CIFixStatus.ERROR,
            _META_CI_FIX_ERROR: "API down",
        }
        msg = hand._format_ci_fix_message(md)
        assert msg == "[test] CI fix error: API down"

    def test_empty_status_returns_none(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md: dict[str, str] = {}
        assert hand._format_ci_fix_message(md) is None

    def test_unknown_status_returns_none(self, repo_index: RepoIndex) -> None:
        hand = self._make_hand(repo_index)
        md = {_META_CI_FIX_STATUS: "unknown_value"}
        assert hand._format_ci_fix_message(md) is None


# ---------------------------------------------------------------------------
# Source-level consistency checks
# ---------------------------------------------------------------------------


class TestSourceConsistency:
    """Verify dispatch tables are used in the method implementations."""

    def test_format_pr_status_uses_dispatch_table(self) -> None:
        src = getsource(_TwoPhaseCLIHand._format_pr_status_message)
        assert "_PR_STATUS_TEMPLATES" in src

    def test_format_ci_fix_uses_dispatch_table(self) -> None:
        src = getsource(_TwoPhaseCLIHand._format_ci_fix_message)
        assert "_CI_FIX_TEMPLATES" in src

    def test_validate_preconditions_is_separate_method(self) -> None:
        src = getsource(Hand._validate_finalization_preconditions)
        assert "_should_run_precommit_before_pr" in src
        assert "_github_repo_from_origin" in src
