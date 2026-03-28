"""Guard CI conclusion enums, boilerplate detection, and the LangChain stream event constant.

CIConclusion values are compared against GitHub API check-suite conclusion strings.
If a member value drifts from the GitHub API's casing (e.g. "SUCCESS" instead of
"success"), the CI fix loop would never detect that checks passed and would loop
indefinitely. CI_CONCLUSIONS_IN_PROGRESS drives the polling loop — wrong membership
could cause the hand to stop polling prematurely or never stop. _BOILERPLATE_PREFIXES_LOWER
is the pre-lowercased cache of commit message boilerplate patterns; if it falls out
of sync with _BOILERPLATE_PREFIXES, the PR description extraction would regress on
case-insensitive matching. _LANGCHAIN_STREAM_EVENT must match the LangChain SDK's
actual event name or the streaming loop never receives text chunks.
"""

from __future__ import annotations

from helping_hands.lib.github import (
    _CI_RUN_FAILURE_CONCLUSIONS,
    CI_CONCLUSIONS_IN_PROGRESS,
    CIConclusion,
)
from helping_hands.lib.hands.v1.hand.cli.base import CIFixStatus
from helping_hands.lib.hands.v1.hand.langgraph import _LANGCHAIN_STREAM_EVENT
from helping_hands.lib.hands.v1.hand.pr_description import (
    _BOILERPLATE_PREFIXES,
    _BOILERPLATE_PREFIXES_LOWER,
    _is_boilerplate_line,
)

# ---------------------------------------------------------------------------
# CIConclusion enum — membership and string values
# ---------------------------------------------------------------------------


class TestCIConclusionEnum:
    """Verify CIConclusion is a StrEnum with correct values."""

    def test_is_str_subclass(self) -> None:
        assert isinstance(CIConclusion.SUCCESS, str)

    def test_no_checks_equals_string(self) -> None:
        assert CIConclusion.NO_CHECKS == "no_checks"

    def test_pending_equals_string(self) -> None:
        assert CIConclusion.PENDING == "pending"

    def test_success_equals_string(self) -> None:
        assert CIConclusion.SUCCESS == "success"

    def test_failure_equals_string(self) -> None:
        assert CIConclusion.FAILURE == "failure"

    def test_mixed_equals_string(self) -> None:
        assert CIConclusion.MIXED == "mixed"

    def test_member_count(self) -> None:
        assert len(CIConclusion) == 5

    def test_in_progress_frozenset_contains_pending(self) -> None:
        assert CIConclusion.PENDING in CI_CONCLUSIONS_IN_PROGRESS

    def test_in_progress_frozenset_contains_no_checks(self) -> None:
        assert CIConclusion.NO_CHECKS in CI_CONCLUSIONS_IN_PROGRESS

    def test_in_progress_frozenset_excludes_success(self) -> None:
        assert CIConclusion.SUCCESS not in CI_CONCLUSIONS_IN_PROGRESS

    def test_in_progress_frozenset_excludes_failure(self) -> None:
        assert CIConclusion.FAILURE not in CI_CONCLUSIONS_IN_PROGRESS

    def test_in_progress_frozenset_size(self) -> None:
        assert len(CI_CONCLUSIONS_IN_PROGRESS) == 2


# ---------------------------------------------------------------------------
# _CI_RUN_FAILURE_CONCLUSIONS frozenset
# ---------------------------------------------------------------------------


class TestCIRunFailureConclusions:
    """Verify the individual check-run failure conclusion set."""

    def test_contains_failure(self) -> None:
        assert "failure" in _CI_RUN_FAILURE_CONCLUSIONS

    def test_contains_cancelled(self) -> None:
        assert "cancelled" in _CI_RUN_FAILURE_CONCLUSIONS

    def test_contains_timed_out(self) -> None:
        assert "timed_out" in _CI_RUN_FAILURE_CONCLUSIONS

    def test_excludes_success(self) -> None:
        assert "success" not in _CI_RUN_FAILURE_CONCLUSIONS

    def test_size(self) -> None:
        assert len(_CI_RUN_FAILURE_CONCLUSIONS) == 3


# ---------------------------------------------------------------------------
# CIFixStatus enum — membership and string values
# ---------------------------------------------------------------------------


class TestCIFixStatusEnum:
    """Verify CIFixStatus is a StrEnum with correct values."""

    def test_is_str_subclass(self) -> None:
        assert isinstance(CIFixStatus.CHECKING, str)

    def test_checking_equals_string(self) -> None:
        assert CIFixStatus.CHECKING == "checking"

    def test_success_equals_string(self) -> None:
        assert CIFixStatus.SUCCESS == "success"

    def test_no_checks_equals_string(self) -> None:
        assert CIFixStatus.NO_CHECKS == "no_checks"

    def test_pending_timeout_equals_string(self) -> None:
        assert CIFixStatus.PENDING_TIMEOUT == "pending_timeout"

    def test_interrupted_equals_string(self) -> None:
        assert CIFixStatus.INTERRUPTED == "interrupted"

    def test_exhausted_equals_string(self) -> None:
        assert CIFixStatus.EXHAUSTED == "exhausted"

    def test_error_equals_string(self) -> None:
        assert CIFixStatus.ERROR == "error"

    def test_member_count(self) -> None:
        assert len(CIFixStatus) == 7

    def test_metadata_dict_round_trip(self) -> None:
        """StrEnum values survive dict serialization as plain strings."""
        meta: dict[str, str] = {"ci_fix_status": CIFixStatus.SUCCESS}
        assert meta["ci_fix_status"] == "success"


# ---------------------------------------------------------------------------
# _BOILERPLATE_PREFIXES_LOWER — pre-lowercased tuple
# ---------------------------------------------------------------------------


class TestBoilerplatePrefixesLower:
    """Verify the pre-lowercased boilerplate prefix tuple."""

    def test_same_length_as_original(self) -> None:
        assert len(_BOILERPLATE_PREFIXES_LOWER) == len(_BOILERPLATE_PREFIXES)

    def test_all_lowercase(self) -> None:
        for prefix in _BOILERPLATE_PREFIXES_LOWER:
            assert prefix == prefix.lower(), f"Not lowercase: {prefix!r}"

    def test_matches_original_lowered(self) -> None:
        for original, lowered in zip(
            _BOILERPLATE_PREFIXES, _BOILERPLATE_PREFIXES_LOWER, strict=True
        ):
            assert lowered == original.lower()

    def test_is_tuple(self) -> None:
        assert isinstance(_BOILERPLATE_PREFIXES_LOWER, tuple)

    def test_boilerplate_detection_still_works(self) -> None:
        """Ensure the optimization doesn't break case-insensitive matching."""
        assert _is_boilerplate_line("Initialization Phase: something")
        assert _is_boilerplate_line("EXECUTION CONTEXT: test")
        assert _is_boilerplate_line("repository context learned from init")

    def test_non_boilerplate_still_rejected(self) -> None:
        assert not _is_boilerplate_line("This is a normal line")
        assert not _is_boilerplate_line("Fixed the bug in module X")


# ---------------------------------------------------------------------------
# _LANGCHAIN_STREAM_EVENT — constant and cross-module sync
# ---------------------------------------------------------------------------


class TestLangchainStreamEvent:
    """Verify the LangChain stream event constant."""

    def test_value(self) -> None:
        assert _LANGCHAIN_STREAM_EVENT == "on_chat_model_stream"

    def test_is_string(self) -> None:
        assert isinstance(_LANGCHAIN_STREAM_EVENT, str)

    def test_iterative_imports_same_constant(self) -> None:
        """Verify iterative.py imports the same constant (no drift)."""
        from helping_hands.lib.hands.v1.hand import iterative

        assert iterative._LANGCHAIN_STREAM_EVENT is _LANGCHAIN_STREAM_EVENT
