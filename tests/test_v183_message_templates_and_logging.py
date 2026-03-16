"""Tests for v183: commit/PR message template constants, silent exception logging.

Validates extracted ``_DEFAULT_COMMIT_MSG_TEMPLATE`` and
``_DEFAULT_PR_TITLE_TEMPLATE`` in base.py and debug logging added to
silent exception handlers in server/app.py.
"""

from __future__ import annotations

import importlib
import re
from inspect import getsource

import pytest

from helping_hands.lib.hands.v1.hand.base import (
    _DEFAULT_COMMIT_MSG_TEMPLATE,
    _DEFAULT_PR_TITLE_TEMPLATE,
)

_has_fastapi = importlib.util.find_spec("fastapi") is not None


# ---------------------------------------------------------------------------
# _DEFAULT_COMMIT_MSG_TEMPLATE constant
# ---------------------------------------------------------------------------


class TestDefaultCommitMsgTemplate:
    """Verify _DEFAULT_COMMIT_MSG_TEMPLATE value, type, and usage."""

    def test_is_string(self) -> None:
        assert isinstance(_DEFAULT_COMMIT_MSG_TEMPLATE, str)

    def test_not_empty(self) -> None:
        assert _DEFAULT_COMMIT_MSG_TEMPLATE.strip()

    def test_contains_backend_placeholder(self) -> None:
        assert "{backend}" in _DEFAULT_COMMIT_MSG_TEMPLATE

    def test_format_produces_expected_value(self) -> None:
        result = _DEFAULT_COMMIT_MSG_TEMPLATE.format(backend="test-be")
        assert result == "feat(test-be): apply hand updates"

    def test_starts_with_conventional_prefix(self) -> None:
        assert _DEFAULT_COMMIT_MSG_TEMPLATE.startswith("feat(")

    def test_used_in_push_to_existing_pr(self) -> None:
        """Constant is referenced in _push_to_existing_pr."""
        from helping_hands.lib.hands.v1.hand.base import Hand

        src = getsource(Hand._push_to_existing_pr)
        assert "_DEFAULT_COMMIT_MSG_TEMPLATE" in src

    def test_used_in_create_new_pr(self) -> None:
        """Constant is referenced in _create_new_pr (extracted from _finalize_repo_pr)."""
        from helping_hands.lib.hands.v1.hand.base import Hand

        src = getsource(Hand._create_new_pr)
        assert "_DEFAULT_COMMIT_MSG_TEMPLATE" in src

    def test_no_inline_duplicates(self) -> None:
        """No remaining inline f-string duplicates of this template."""
        from helping_hands.lib.hands.v1.hand import base

        src = getsource(base)
        # Should not find the old inline f-string pattern
        matches = re.findall(
            r'f"feat\(\{backend\}\): apply hand updates"',
            src,
        )
        assert len(matches) == 0, f"found {len(matches)} inline duplicate(s)"


# ---------------------------------------------------------------------------
# _DEFAULT_PR_TITLE_TEMPLATE constant
# ---------------------------------------------------------------------------


class TestDefaultPrTitleTemplate:
    """Verify _DEFAULT_PR_TITLE_TEMPLATE value, type, and usage."""

    def test_is_string(self) -> None:
        assert isinstance(_DEFAULT_PR_TITLE_TEMPLATE, str)

    def test_not_empty(self) -> None:
        assert _DEFAULT_PR_TITLE_TEMPLATE.strip()

    def test_contains_backend_placeholder(self) -> None:
        assert "{backend}" in _DEFAULT_PR_TITLE_TEMPLATE

    def test_format_produces_expected_value(self) -> None:
        result = _DEFAULT_PR_TITLE_TEMPLATE.format(backend="my-hand")
        assert result == "feat(my-hand): automated hand update"

    def test_starts_with_conventional_prefix(self) -> None:
        assert _DEFAULT_PR_TITLE_TEMPLATE.startswith("feat(")

    def test_differs_from_commit_template(self) -> None:
        """PR title and commit message templates are distinct."""
        assert _DEFAULT_COMMIT_MSG_TEMPLATE != _DEFAULT_PR_TITLE_TEMPLATE

    def test_used_in_generate_pr_title_and_body(self) -> None:
        """Constant is referenced in _generate_pr_title_and_body (extracted from _finalize_repo_pr)."""
        from helping_hands.lib.hands.v1.hand.base import Hand

        src = getsource(Hand._generate_pr_title_and_body)
        assert "_DEFAULT_PR_TITLE_TEMPLATE" in src

    def test_no_inline_duplicates(self) -> None:
        """No remaining inline f-string duplicates of this template."""
        from helping_hands.lib.hands.v1.hand import base

        src = getsource(base)
        matches = re.findall(
            r'f"feat\(\{backend\}\): automated hand update"',
            src,
        )
        assert len(matches) == 0, f"found {len(matches)} inline duplicate(s)"


# ---------------------------------------------------------------------------
# server/app.py: debug logging in silent exception handlers
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")
class TestSilentExceptionLogging:
    """Verify debug logging was added to previously-silent exception handlers."""

    def test_safe_inspect_call_has_logger_debug(self) -> None:
        """_safe_inspect_call exception handler includes logger.debug."""
        from helping_hands.server.app import _safe_inspect_call

        src = getsource(_safe_inspect_call)
        assert "logger.debug" in src

    def test_safe_inspect_call_has_exc_info(self) -> None:
        """_safe_inspect_call exception handler passes exc_info."""
        from helping_hands.server.app import _safe_inspect_call

        src = getsource(_safe_inspect_call)
        assert "exc_info=True" in src

    def test_safe_inspect_call_logs_method_name(self) -> None:
        """_safe_inspect_call log message references method_name."""
        from helping_hands.server.app import _safe_inspect_call

        src = getsource(_safe_inspect_call)
        assert "method_name" in src

    def test_collect_celery_current_tasks_has_logger_debug(self) -> None:
        """_collect_celery_current_tasks exception handler includes logging."""
        from helping_hands.server.app import _collect_celery_current_tasks

        src = getsource(_collect_celery_current_tasks)
        assert "logger.debug" in src

    def test_collect_celery_current_tasks_has_exc_info(self) -> None:
        """_collect_celery_current_tasks exception handler passes exc_info."""
        from helping_hands.server.app import _collect_celery_current_tasks

        src = getsource(_collect_celery_current_tasks)
        assert "exc_info=True" in src
