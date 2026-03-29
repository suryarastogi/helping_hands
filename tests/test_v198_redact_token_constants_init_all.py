"""Guard the token redaction constants and root package __all__ contract.

_redact_token() is the security-sensitive function that masks GitHub tokens before
they are returned in API responses or logs. If _REDACT_TOKEN_PREFIX_LEN or
_REDACT_TOKEN_SUFFIX_LEN drift from 4, tokens either expose too much (security
risk) or become unrecognisable (UX regression). _REDACT_TOKEN_MIN_PARTIAL_LEN
controls the threshold below which the full token is replaced rather than partially
shown. The root package __all__ test prevents accidental removal of __version__
from the top-level namespace, which would break downstream `helping_hands.__version__`
version checks.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Root package __all__
# ---------------------------------------------------------------------------


class TestRootPackageAll:
    def test_all_declared(self) -> None:
        import helping_hands

        assert hasattr(helping_hands, "__all__")

    def test_all_contains_version(self) -> None:
        import helping_hands

        assert "__version__" in helping_hands.__all__

    def test_all_is_list(self) -> None:
        import helping_hands

        assert isinstance(helping_hands.__all__, list)

    def test_all_entries_are_strings(self) -> None:
        import helping_hands

        for entry in helping_hands.__all__:
            assert isinstance(entry, str)

    def test_all_entries_exist(self) -> None:
        import helping_hands

        for name in helping_hands.__all__:
            assert hasattr(helping_hands, name), f"{name!r} in __all__ but not defined"


# ---------------------------------------------------------------------------
# Redact token constants (requires fastapi)
# ---------------------------------------------------------------------------

fastapi = pytest.importorskip("fastapi")

from helping_hands.server.app import (  # noqa: E402
    _REDACT_TOKEN_MIN_PARTIAL_LEN,
    _REDACT_TOKEN_PREFIX_LEN,
    _REDACT_TOKEN_SUFFIX_LEN,
    _redact_token,
)


class TestRedactTokenConstants:
    """Verify constant types, values, and relationships."""

    def test_prefix_len_type(self) -> None:
        assert isinstance(_REDACT_TOKEN_PREFIX_LEN, int)

    def test_suffix_len_type(self) -> None:
        assert isinstance(_REDACT_TOKEN_SUFFIX_LEN, int)

    def test_min_partial_len_type(self) -> None:
        assert isinstance(_REDACT_TOKEN_MIN_PARTIAL_LEN, int)

    def test_prefix_len_value(self) -> None:
        assert _REDACT_TOKEN_PREFIX_LEN == 4

    def test_suffix_len_value(self) -> None:
        assert _REDACT_TOKEN_SUFFIX_LEN == 4

    def test_min_partial_len_value(self) -> None:
        assert _REDACT_TOKEN_MIN_PARTIAL_LEN == 12

    def test_min_partial_len_greater_than_visible(self) -> None:
        assert (
            _REDACT_TOKEN_MIN_PARTIAL_LEN
            > _REDACT_TOKEN_PREFIX_LEN + _REDACT_TOKEN_SUFFIX_LEN
        )

    def test_prefix_len_positive(self) -> None:
        assert _REDACT_TOKEN_PREFIX_LEN > 0

    def test_suffix_len_positive(self) -> None:
        assert _REDACT_TOKEN_SUFFIX_LEN > 0


class TestRedactTokenUsesConstants:
    """Verify _redact_token behaviour is consistent with named constants."""

    def test_none_returns_none(self) -> None:
        assert _redact_token(None) is None

    def test_empty_returns_none(self) -> None:
        assert _redact_token("") is None

    def test_at_min_partial_len_fully_masked(self) -> None:
        short = "a" * _REDACT_TOKEN_MIN_PARTIAL_LEN
        assert _redact_token(short) == "***"

    def test_shorter_than_min_fully_masked(self) -> None:
        assert _redact_token("abc") == "***"

    def test_exactly_min_plus_one_shows_prefix_suffix(self) -> None:
        token = "a" * (_REDACT_TOKEN_MIN_PARTIAL_LEN + 1)
        result = _redact_token(token)
        assert result is not None
        assert result.startswith("a" * _REDACT_TOKEN_PREFIX_LEN)
        assert result.endswith("a" * _REDACT_TOKEN_SUFFIX_LEN)
        assert "***" in result

    def test_long_token_prefix_suffix(self) -> None:
        token = "ghp_" + "x" * 30 + "abcd"
        result = _redact_token(token)
        assert result is not None
        assert result.startswith("ghp_")
        assert result.endswith("abcd")
        assert "***" in result
        # Original token must not appear
        assert token not in result

    def test_redacted_length_shorter_than_original(self) -> None:
        token = "a" * 50
        result = _redact_token(token)
        assert result is not None
        assert len(result) < len(token)


# ---------------------------------------------------------------------------
# ci_check_wait_minutes getattr fallback uses constant
# ---------------------------------------------------------------------------


class TestScheduleResponseCiWaitFallback:
    """Verify the getattr fallback for ci_check_wait_minutes uses the constant."""

    def test_fallback_value_matches_constant(self) -> None:
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES
        from tests.test_server_app_schedule_response import _FakeScheduledTask

        task = _FakeScheduledTask(enabled=False)
        delattr(task, "ci_check_wait_minutes")

        from helping_hands.server.app import _schedule_to_response

        resp = _schedule_to_response(task)
        assert resp.ci_check_wait_minutes == DEFAULT_CI_WAIT_MINUTES
