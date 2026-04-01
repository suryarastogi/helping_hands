"""Pins streaming-preview and failure-tail truncation constants.

CLI streaming truncates tool results and text blocks to named constants so
live output stays readable; without these limits, multi-kilobyte blobs per
tool call flood the terminal.  The key behavioral test is
test_detect_auth_failure_uses_tail_length, which verifies _detect_auth_failure
actually slices output to _FAILURE_OUTPUT_TAIL_LENGTH rather than ignoring it.

PR description constants (_PR_SUMMARY_TRUNCATION_LENGTH, etc.) bound the text
sent to the description-generation LLM, preventing token-limit blowouts.

# TODO: CLEANUP CANDIDATE -- individual positive/is_int assertions per constant
# add no failure signal beyond the value tests; collapse to a single
# parametrized positive-and-typed check.
"""

# ---------------------------------------------------------------------------
# Claude CLI preview constants (claude.py)
# ---------------------------------------------------------------------------


class TestClaudeCLIPreviewConstants:
    """Tests for preview truncation constants in claude.py."""

    def test_text_preview_max_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _TEXT_PREVIEW_MAX_LENGTH,
        )

        assert _TEXT_PREVIEW_MAX_LENGTH == 200

    def test_text_preview_max_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _TEXT_PREVIEW_MAX_LENGTH,
        )

        assert _TEXT_PREVIEW_MAX_LENGTH > 0

    def test_text_preview_max_length_is_int(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _TEXT_PREVIEW_MAX_LENGTH,
        )

        assert isinstance(_TEXT_PREVIEW_MAX_LENGTH, int)

    def test_tool_result_preview_max_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _TOOL_RESULT_PREVIEW_MAX_LENGTH,
        )

        assert _TOOL_RESULT_PREVIEW_MAX_LENGTH == 150

    def test_tool_result_preview_max_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _TOOL_RESULT_PREVIEW_MAX_LENGTH,
        )

        assert _TOOL_RESULT_PREVIEW_MAX_LENGTH > 0

    def test_command_preview_max_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _COMMAND_PREVIEW_MAX_LENGTH,
        )

        assert _COMMAND_PREVIEW_MAX_LENGTH == 80

    def test_command_preview_max_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _COMMAND_PREVIEW_MAX_LENGTH,
        )

        assert _COMMAND_PREVIEW_MAX_LENGTH > 0


# ---------------------------------------------------------------------------
# Failure output tail constants (claude.py, codex.py, gemini.py, opencode.py)
# ---------------------------------------------------------------------------


class TestFailureOutputTailConstants:
    """Tests for _FAILURE_OUTPUT_TAIL_LENGTH in cli/base.py.

    Since v203, subclasses no longer directly import this constant —
    it is consumed internally by ``_detect_auth_failure`` in base.py.
    """

    def test_base_failure_tail_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FAILURE_OUTPUT_TAIL_LENGTH,
        )

        assert _FAILURE_OUTPUT_TAIL_LENGTH == 2000

    def test_base_failure_tail_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FAILURE_OUTPUT_TAIL_LENGTH,
        )

        assert _FAILURE_OUTPUT_TAIL_LENGTH > 0

    def test_detect_auth_failure_uses_tail_length(self) -> None:
        """_detect_auth_failure respects _FAILURE_OUTPUT_TAIL_LENGTH."""
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FAILURE_OUTPUT_TAIL_LENGTH,
            _detect_auth_failure,
        )

        long_prefix = "x" * (_FAILURE_OUTPUT_TAIL_LENGTH + 500)
        _, tail = _detect_auth_failure(long_prefix + "end")
        assert len(tail) <= _FAILURE_OUTPUT_TAIL_LENGTH


# ---------------------------------------------------------------------------
# PR description constants (pr_description.py)
# ---------------------------------------------------------------------------


class TestPRDescriptionConstants:
    """Tests for truncation constants in pr_description.py."""

    def test_pr_summary_truncation_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _PR_SUMMARY_TRUNCATION_LENGTH,
        )

        assert _PR_SUMMARY_TRUNCATION_LENGTH == 2000

    def test_pr_summary_truncation_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _PR_SUMMARY_TRUNCATION_LENGTH,
        )

        assert _PR_SUMMARY_TRUNCATION_LENGTH > 0

    def test_commit_summary_truncation_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_SUMMARY_TRUNCATION_LENGTH,
        )

        assert _COMMIT_SUMMARY_TRUNCATION_LENGTH == 1000

    def test_commit_summary_truncation_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_SUMMARY_TRUNCATION_LENGTH,
        )

        assert _COMMIT_SUMMARY_TRUNCATION_LENGTH > 0

    def test_commit_summary_shorter_than_pr_summary(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_SUMMARY_TRUNCATION_LENGTH,
            _PR_SUMMARY_TRUNCATION_LENGTH,
        )

        assert _COMMIT_SUMMARY_TRUNCATION_LENGTH < _PR_SUMMARY_TRUNCATION_LENGTH

    def test_prompt_context_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _PROMPT_CONTEXT_LENGTH,
        )

        assert _PROMPT_CONTEXT_LENGTH == 500

    def test_prompt_context_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _PROMPT_CONTEXT_LENGTH,
        )

        assert _PROMPT_CONTEXT_LENGTH > 0

    def test_pr_error_tail_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _PR_ERROR_TAIL_LENGTH,
        )

        assert _PR_ERROR_TAIL_LENGTH == 500

    def test_pr_error_tail_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _PR_ERROR_TAIL_LENGTH,
        )

        assert _PR_ERROR_TAIL_LENGTH > 0

    def test_commit_error_tail_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_ERROR_TAIL_LENGTH,
        )

        assert _COMMIT_ERROR_TAIL_LENGTH == 300

    def test_commit_error_tail_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_ERROR_TAIL_LENGTH,
        )

        assert _COMMIT_ERROR_TAIL_LENGTH > 0

    def test_commit_msg_max_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_MSG_MAX_LENGTH,
        )

        assert _COMMIT_MSG_MAX_LENGTH == 72

    def test_commit_msg_max_length_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_MSG_MAX_LENGTH,
        )

        assert _COMMIT_MSG_MAX_LENGTH > 0

    def test_commit_msg_max_length_is_int(self) -> None:  # TODO: CLEANUP CANDIDATE
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _COMMIT_MSG_MAX_LENGTH,
        )

        assert isinstance(_COMMIT_MSG_MAX_LENGTH, int)


# ---------------------------------------------------------------------------
# CLI base file list constant import (cli/base.py)
# ---------------------------------------------------------------------------


class TestCLIBaseFileListConstant:
    """Tests that cli/base.py uses _FILE_LIST_PREVIEW_LIMIT from base.py."""

    def test_file_list_preview_limit_importable_from_cli_base(self) -> None:
        """The constant should be importable via cli/base.py (re-imported from base)."""
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FILE_LIST_PREVIEW_LIMIT,
        )

        assert _FILE_LIST_PREVIEW_LIMIT == 200

    def test_file_list_preview_limit_same_as_base(self) -> None:
        """cli/base.py should import the exact same object from base.py."""
        from helping_hands.lib.hands.v1.hand.base import (
            _FILE_LIST_PREVIEW_LIMIT as _BASE_LIMIT,
        )
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _FILE_LIST_PREVIEW_LIMIT as _CLI_LIMIT,
        )

        assert _CLI_LIMIT is _BASE_LIMIT
