"""Tests for v138: Hand base and CLI base constants extracted from inline literals.

Extracting magic numbers to named constants (_DEFAULT_BASE_BRANCH, _BRANCH_PREFIX,
_UUID_HEX_LENGTH, etc.) allows a single-point change to propagate to every place
that uses git branch naming, bot identity, and CI retry logic.  If _BRANCH_PREFIX
loses its trailing slash, branch names like "helping-handsmain" are created instead
of "helping-hands/main", silently breaking GitHub branch-protection rules.

_DEFAULT_GIT_USER_EMAIL must contain "@" to be accepted by git config; a regression
to a plain string would cause every commit authored by the bot to fail git's author
validation.

# TODO: CLEANUP CANDIDATE — tests that only assert is_str/is_positive duplicate
# the value-equality tests immediately above them without adding new failure paths.
"""

# ---------------------------------------------------------------------------
# Hand base constants (base.py)
# ---------------------------------------------------------------------------


class TestHandBaseConstants:
    """Tests for constants extracted to base.py module level."""

    def test_default_base_branch_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_BASE_BRANCH

        assert _DEFAULT_BASE_BRANCH == "main"

    def test_default_base_branch_is_str(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_BASE_BRANCH

        assert isinstance(_DEFAULT_BASE_BRANCH, str)

    def test_default_git_user_name_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_GIT_USER_NAME

        assert _DEFAULT_GIT_USER_NAME == "helping-hands[bot]"

    def test_default_git_user_email_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_GIT_USER_EMAIL

        assert _DEFAULT_GIT_USER_EMAIL == "helping-hands-bot@users.noreply.github.com"

    def test_default_git_user_email_is_valid(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_GIT_USER_EMAIL

        assert "@" in _DEFAULT_GIT_USER_EMAIL

    def test_default_ci_wait_minutes_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_CI_WAIT_MINUTES

        assert _DEFAULT_CI_WAIT_MINUTES == 3.0

    def test_default_ci_wait_minutes_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_CI_WAIT_MINUTES

        assert _DEFAULT_CI_WAIT_MINUTES > 0

    def test_default_ci_max_retries_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_CI_MAX_RETRIES

        assert _DEFAULT_CI_MAX_RETRIES == 3

    def test_default_ci_max_retries_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_CI_MAX_RETRIES

        assert _DEFAULT_CI_MAX_RETRIES > 0

    def test_branch_prefix_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _BRANCH_PREFIX

        assert _BRANCH_PREFIX == "helping-hands/"

    def test_branch_prefix_ends_with_slash(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _BRANCH_PREFIX

        assert _BRANCH_PREFIX.endswith("/")

    def test_uuid_hex_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _UUID_HEX_LENGTH

        assert _UUID_HEX_LENGTH == 8

    def test_uuid_hex_length_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _UUID_HEX_LENGTH

        assert _UUID_HEX_LENGTH > 0

    def test_max_output_display_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _MAX_OUTPUT_DISPLAY_LENGTH

        assert _MAX_OUTPUT_DISPLAY_LENGTH == 4000

    def test_max_output_display_length_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _MAX_OUTPUT_DISPLAY_LENGTH

        assert _MAX_OUTPUT_DISPLAY_LENGTH > 0

    def test_file_list_preview_limit_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _FILE_LIST_PREVIEW_LIMIT

        assert _FILE_LIST_PREVIEW_LIMIT == 200

    def test_file_list_preview_limit_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _FILE_LIST_PREVIEW_LIMIT

        assert _FILE_LIST_PREVIEW_LIMIT > 0

    def test_log_truncation_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _LOG_TRUNCATION_LENGTH

        assert _LOG_TRUNCATION_LENGTH == 200

    def test_log_truncation_length_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _LOG_TRUNCATION_LENGTH

        assert _LOG_TRUNCATION_LENGTH > 0


# ---------------------------------------------------------------------------
# CLI hand base constants (cli/base.py)
# ---------------------------------------------------------------------------


class TestCLIHandBaseConstants:
    """Tests for constants extracted to cli/base.py module level."""

    def test_process_terminate_timeout_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _PROCESS_TERMINATE_TIMEOUT_S,
        )

        assert _PROCESS_TERMINATE_TIMEOUT_S == 5

    def test_process_terminate_timeout_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _PROCESS_TERMINATE_TIMEOUT_S,
        )

        assert _PROCESS_TERMINATE_TIMEOUT_S > 0

    def test_ci_poll_interval_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_POLL_INTERVAL_S

        assert _CI_POLL_INTERVAL_S == 30.0

    def test_ci_poll_interval_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _CI_POLL_INTERVAL_S

        assert _CI_POLL_INTERVAL_S > 0

    def test_pr_description_timeout_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _PR_DESCRIPTION_TIMEOUT_S

        assert _PR_DESCRIPTION_TIMEOUT_S == 300

    def test_pr_description_timeout_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _PR_DESCRIPTION_TIMEOUT_S

        assert _PR_DESCRIPTION_TIMEOUT_S > 0

    def test_pr_description_timeout_is_int(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _PR_DESCRIPTION_TIMEOUT_S

        assert isinstance(_PR_DESCRIPTION_TIMEOUT_S, int)


# ---------------------------------------------------------------------------
# CLI main constants (cli/main.py)
# ---------------------------------------------------------------------------


class TestCLIMainConstants:
    """Tests for constants extracted to cli/main.py module level."""

    def test_default_clone_depth_value(self) -> None:
        """Default depth parameter of run_git_clone is 1 (shallow clone)."""
        import inspect

        from helping_hands.lib.github_url import run_git_clone

        sig = inspect.signature(run_git_clone)
        assert sig.parameters["depth"].default == 1

    def test_default_clone_depth_positive(self) -> None:
        """Default depth parameter of run_git_clone is positive."""
        import inspect

        from helping_hands.lib.github_url import run_git_clone

        sig = inspect.signature(run_git_clone)
        assert sig.parameters["depth"].default > 0

    def test_temp_clone_prefix_value(self) -> None:
        from helping_hands.cli.main import _TEMP_CLONE_PREFIX

        assert _TEMP_CLONE_PREFIX == "helping_hands_repo_"

    def test_temp_clone_prefix_is_str(self) -> None:
        from helping_hands.cli.main import _TEMP_CLONE_PREFIX

        assert isinstance(_TEMP_CLONE_PREFIX, str)

    def test_temp_clone_prefix_not_empty(self) -> None:
        from helping_hands.cli.main import _TEMP_CLONE_PREFIX

        assert len(_TEMP_CLONE_PREFIX) > 0
