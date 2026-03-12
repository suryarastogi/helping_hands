"""Tests for v136: extracted constants in base.py/cli/base.py and _truncate_summary validation."""

from __future__ import annotations

import pytest


class TestHandBaseConstants:
    """Tests for _MAX_FILE_LIST_DISPLAY, _ERROR_PREVIEW_CHARS, _PRECOMMIT_OUTPUT_LIMIT."""

    def test_max_file_list_display_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _MAX_FILE_LIST_DISPLAY

        assert _MAX_FILE_LIST_DISPLAY == 200

    def test_error_preview_chars_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _ERROR_PREVIEW_CHARS

        assert _ERROR_PREVIEW_CHARS == 200

    def test_precommit_output_limit_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PRECOMMIT_OUTPUT_LIMIT

        assert _PRECOMMIT_OUTPUT_LIMIT == 4000

    def test_constants_are_positive_integers(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _ERROR_PREVIEW_CHARS,
            _MAX_FILE_LIST_DISPLAY,
            _PRECOMMIT_OUTPUT_LIMIT,
        )

        for const in (
            _MAX_FILE_LIST_DISPLAY,
            _ERROR_PREVIEW_CHARS,
            _PRECOMMIT_OUTPUT_LIMIT,
        ):
            assert isinstance(const, int)
            assert const > 0


class TestCliBaseConstants:
    """Tests for _APPLY_CHANGES_SUMMARY_LIMIT."""

    def test_apply_changes_summary_limit_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _APPLY_CHANGES_SUMMARY_LIMIT,
        )

        assert _APPLY_CHANGES_SUMMARY_LIMIT == 2000

    def test_apply_changes_summary_limit_is_positive_int(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _APPLY_CHANGES_SUMMARY_LIMIT,
        )

        assert isinstance(_APPLY_CHANGES_SUMMARY_LIMIT, int)
        assert _APPLY_CHANGES_SUMMARY_LIMIT > 0


class TestTruncateSummaryLimitValidation:
    """Tests for _truncate_summary limit <= 0 guard."""

    def test_zero_limit_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        with pytest.raises(ValueError, match="limit must be positive"):
            _TwoPhaseCLIHand._truncate_summary("hello", limit=0)

    def test_negative_limit_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        with pytest.raises(ValueError, match="limit must be positive"):
            _TwoPhaseCLIHand._truncate_summary("hello", limit=-1)

    def test_positive_limit_works(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        result = _TwoPhaseCLIHand._truncate_summary("hello", limit=10)
        assert result == "hello"

    def test_limit_of_one_works(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        result = _TwoPhaseCLIHand._truncate_summary("hello world", limit=1)
        assert result.startswith("h")
        assert result.endswith("...[truncated]")
