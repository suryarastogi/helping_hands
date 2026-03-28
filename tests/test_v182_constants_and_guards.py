"""Guard the pre-commit and git error message constants used in Hand finalization.

_PRECOMMIT_UV_MISSING_MSG and _DEFAULT_GIT_ERROR_MSG are the user-visible strings
surfaced when `uv` is missing during pre-commit checks or when a git command fails
without a specific message. If these constants are removed or inlined the error
messages lose their consistent wording, making it harder for users to diagnose
environment problems. The function-level tests verify that FileNotFoundError in
both the first and second pre-commit passes produces a RuntimeError containing
"uv is not available" — ensuring the constant is actually reached in the hot path,
not just defined.
"""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.base import (
    _DEFAULT_GIT_ERROR_MSG,
    _PRECOMMIT_UV_MISSING_MSG,
    Hand,
)

_has_fastapi = importlib.util.find_spec("fastapi") is not None


# ---------------------------------------------------------------------------
# _PRECOMMIT_UV_MISSING_MSG constant
# ---------------------------------------------------------------------------


class TestPrecommitUvMissingMsg:
    """Verify _PRECOMMIT_UV_MISSING_MSG constant value, type, and usage."""

    def test_is_string(self) -> None:
        assert isinstance(_PRECOMMIT_UV_MISSING_MSG, str)

    def test_not_empty(self) -> None:
        assert _PRECOMMIT_UV_MISSING_MSG.strip()

    def test_contains_uv(self) -> None:
        assert "uv" in _PRECOMMIT_UV_MISSING_MSG

    def test_contains_pre_commit(self) -> None:
        assert "pre-commit" in _PRECOMMIT_UV_MISSING_MSG

    def test_contains_finalization(self) -> None:
        assert "finalization" in _PRECOMMIT_UV_MISSING_MSG

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_first_pass_file_not_found_uses_constant(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """First-pass FileNotFoundError raises RuntimeError with the constant."""
        mock_run.side_effect = FileNotFoundError("uv not found")
        with pytest.raises(RuntimeError, match="uv is not available"):
            Hand._run_precommit_checks_and_fixes(tmp_path)

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_second_pass_file_not_found_uses_constant(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Second-pass FileNotFoundError raises RuntimeError with the constant."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="reformatted", stderr=""
            ),
            FileNotFoundError("uv gone"),
        ]
        with pytest.raises(RuntimeError, match="uv is not available"):
            Hand._run_precommit_checks_and_fixes(tmp_path)


# ---------------------------------------------------------------------------
# _DEFAULT_GIT_ERROR_MSG constant
# ---------------------------------------------------------------------------


class TestDefaultGitErrorMsg:
    """Verify _DEFAULT_GIT_ERROR_MSG constant value, type, and usage."""

    def test_is_string(self) -> None:
        assert isinstance(_DEFAULT_GIT_ERROR_MSG, str)

    def test_not_empty(self) -> None:
        assert _DEFAULT_GIT_ERROR_MSG.strip()

    def test_value(self) -> None:
        assert _DEFAULT_GIT_ERROR_MSG == "unknown git error"

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_used_in_configure_push_remote_fallback(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """When git returns non-zero with empty stderr, the constant is used."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="   "
        )
        with pytest.raises(RuntimeError, match=_DEFAULT_GIT_ERROR_MSG):
            Hand._configure_authenticated_push_remote(tmp_path, "owner/repo", "tok")


# ---------------------------------------------------------------------------
# Task state set guards (server/app.py)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")
class TestTaskStateSetGuards:
    """Verify module-level assertions on task state sets in server/app.py."""

    def test_terminal_and_current_states_are_disjoint(self) -> None:
        from helping_hands.server.app import (
            _CURRENT_TASK_STATES,
            _TERMINAL_TASK_STATES,
        )

        assert _TERMINAL_TASK_STATES.isdisjoint(_CURRENT_TASK_STATES)

    def test_state_priority_keys_subset_of_current(self) -> None:
        from helping_hands.server.app import (
            _CURRENT_TASK_STATES,
            _TASK_STATE_PRIORITY,
        )

        assert set(_TASK_STATE_PRIORITY.keys()) <= _CURRENT_TASK_STATES

    def test_terminal_states_is_set(self) -> None:
        from helping_hands.server.app import _TERMINAL_TASK_STATES

        assert isinstance(_TERMINAL_TASK_STATES, set)

    def test_current_states_is_set(self) -> None:
        from helping_hands.server.app import _CURRENT_TASK_STATES

        assert isinstance(_CURRENT_TASK_STATES, set)

    def test_terminal_states_contains_expected(self) -> None:
        from helping_hands.server.app import _TERMINAL_TASK_STATES

        assert "SUCCESS" in _TERMINAL_TASK_STATES
        assert "FAILURE" in _TERMINAL_TASK_STATES
        assert "REVOKED" in _TERMINAL_TASK_STATES

    def test_current_states_contains_started(self) -> None:
        from helping_hands.server.app import _CURRENT_TASK_STATES

        assert "STARTED" in _CURRENT_TASK_STATES

    def test_priority_dict_is_dict(self) -> None:
        from helping_hands.server.app import _TASK_STATE_PRIORITY

        assert isinstance(_TASK_STATE_PRIORITY, dict)

    def test_priority_values_are_ints(self) -> None:
        from helping_hands.server.app import _TASK_STATE_PRIORITY

        for key, val in _TASK_STATE_PRIORITY.items():
            assert isinstance(val, int), f"Priority for {key} is not int: {val}"
