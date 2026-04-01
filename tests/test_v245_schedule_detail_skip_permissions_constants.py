"""Protect the Claude skip-permissions flag lifecycle and the schedule-not-found HTTP detail contract.

_SKIP_PERMISSIONS_FLAG must equal "--dangerously-skip-permissions" exactly;
if the string drifts, the Claude binary silently ignores it and every
automated run stalls waiting for interactive approval. The insert/remove
symmetry between _apply_backend_defaults and _retry_command_after_failure
is critical: broken insert double-adds the flag; broken remove prevents
recovery from "root required" errors.

_SCHEDULE_NOT_FOUND_DETAIL is an API contract: external clients match on
this 404 detail string, so any change silently breaks client error handling.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.cli.claude import (
    _SKIP_PERMISSIONS_FLAG,
    ClaudeCodeHand,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _src_root() -> Path:
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands"


# ===========================================================================
# _SKIP_PERMISSIONS_FLAG
# ===========================================================================


class TestSkipPermissionsFlag:
    """Tests for the _SKIP_PERMISSIONS_FLAG constant."""

    def test_is_string(self) -> None:  # TODO: CLEANUP CANDIDATE — subsumed by test_value
        assert isinstance(_SKIP_PERMISSIONS_FLAG, str)

    def test_non_empty(self) -> None:  # TODO: CLEANUP CANDIDATE — subsumed by test_value
        assert len(_SKIP_PERMISSIONS_FLAG) > 0

    def test_value(self) -> None:
        assert _SKIP_PERMISSIONS_FLAG == "--dangerously-skip-permissions"

    def test_starts_with_double_dash(self) -> None:  # TODO: CLEANUP CANDIDATE — subsumed by test_value
        assert _SKIP_PERMISSIONS_FLAG.startswith("--")


class TestSkipPermissionsFlagSourceConsistency:
    """Ensure claude.py has no remaining bare '--dangerously-skip-permissions'
    string literals — they should all reference the constant instead."""

    def test_no_bare_skip_permissions_in_methods(self) -> None:
        claude_path = (
            _src_root() / "lib" / "hands" / "v1" / "hand" / "cli" / "claude.py"
        )
        tree = ast.parse(claude_path.read_text(), filename=str(claude_path))
        bare_occurrences: list[int] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and node.value == "--dangerously-skip-permissions"
            ):
                bare_occurrences.append(node.lineno)
        # The only allowed occurrence is the constant definition itself.
        assert len(bare_occurrences) <= 1, (
            f"Found bare '--dangerously-skip-permissions' string literals at "
            f"lines {bare_occurrences} in claude.py — "
            f"use _SKIP_PERMISSIONS_FLAG instead"
        )

    def test_constant_referenced_in_methods(self) -> None:
        """Verify that _SKIP_PERMISSIONS_FLAG is used in method bodies."""
        claude_path = (
            _src_root() / "lib" / "hands" / "v1" / "hand" / "cli" / "claude.py"
        )
        source = claude_path.read_text()
        # Expect at least 5 references (1 definition + 4 usages in methods)
        count = source.count("_SKIP_PERMISSIONS_FLAG")
        assert count >= 5, (
            f"Expected _SKIP_PERMISSIONS_FLAG to appear at least 5 times "
            f"in claude.py, found {count}"
        )


class TestSkipPermissionsFlagBehavior:
    """Test that the constant is correctly used in _apply_backend_defaults
    and _retry_command_after_failure."""

    def test_apply_backend_defaults_inserts_flag(self) -> None:
        """_apply_backend_defaults should insert _SKIP_PERMISSIONS_FLAG."""
        hand = ClaudeCodeHand.__new__(ClaudeCodeHand)
        hand._config = type("C", (), {"enable_execution": False})()
        hand._skip_permissions_value = "1"
        cmd = ["claude", "-p", "hello"]
        result = hand._apply_backend_defaults(cmd)
        assert _SKIP_PERMISSIONS_FLAG in result
        assert result[0] == "claude"
        assert result[1] == _SKIP_PERMISSIONS_FLAG

    def test_apply_backend_defaults_skips_when_already_present(self) -> None:
        hand = ClaudeCodeHand.__new__(ClaudeCodeHand)
        hand._config = type("C", (), {"enable_execution": False})()
        hand._skip_permissions_value = "1"
        cmd = ["claude", _SKIP_PERMISSIONS_FLAG, "-p", "hello"]
        result = hand._apply_backend_defaults(cmd)
        assert result == cmd

    def test_retry_command_removes_flag_on_root_error(self) -> None:
        """_retry_command_after_failure should strip _SKIP_PERMISSIONS_FLAG."""
        hand = ClaudeCodeHand.__new__(ClaudeCodeHand)
        cmd = ["claude", _SKIP_PERMISSIONS_FLAG, "-p", "hello"]
        output = hand._ROOT_PERMISSION_ERROR
        result = hand._retry_command_after_failure(cmd, output=output, return_code=1)
        assert result is not None
        assert _SKIP_PERMISSIONS_FLAG not in result

    def test_retry_command_returns_none_without_flag(self) -> None:
        hand = ClaudeCodeHand.__new__(ClaudeCodeHand)
        cmd = ["claude", "-p", "hello"]
        result = hand._retry_command_after_failure(
            cmd, output="some error", return_code=1
        )
        assert result is None

    def test_retry_command_returns_none_on_success(self) -> None:
        hand = ClaudeCodeHand.__new__(ClaudeCodeHand)
        cmd = ["claude", _SKIP_PERMISSIONS_FLAG, "-p", "hello"]
        result = hand._retry_command_after_failure(cmd, output="", return_code=0)
        assert result is None

    def test_retry_command_returns_none_on_unrelated_error(self) -> None:
        hand = ClaudeCodeHand.__new__(ClaudeCodeHand)
        cmd = ["claude", _SKIP_PERMISSIONS_FLAG, "-p", "hello"]
        result = hand._retry_command_after_failure(
            cmd, output="some unrelated error", return_code=1
        )
        assert result is None


class TestSkipPermissionsFlagInAllExports:
    """Verify the constant is listed in __all__."""

    def test_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import claude

        assert "_SKIP_PERMISSIONS_FLAG" in claude.__all__


# ===========================================================================
# _SCHEDULE_NOT_FOUND_DETAIL (source consistency — AST-only, no fastapi needed)
# ===========================================================================


class TestScheduleNotFoundDetailSourceConsistency:
    """Ensure app.py defines _SCHEDULE_NOT_FOUND_DETAIL and has no remaining
    bare 'Schedule not found' string literals in HTTPException detail args."""

    def test_constant_defined_in_app(self) -> None:
        """Verify that _SCHEDULE_NOT_FOUND_DETAIL is defined in app.py."""
        app_path = _src_root() / "server" / "app.py"
        tree = ast.parse(app_path.read_text(), filename=str(app_path))
        assignments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "_SCHEDULE_NOT_FOUND_DETAIL"
                for t in node.targets
            )
        ]
        assert len(assignments) == 1

    def test_constant_value_is_schedule_not_found(self) -> None:
        """Verify the constant value via AST inspection."""
        app_path = _src_root() / "server" / "app.py"
        tree = ast.parse(app_path.read_text(), filename=str(app_path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "_SCHEDULE_NOT_FOUND_DETAIL"
                    for t in node.targets
                )
                and isinstance(node.value, ast.Constant)
            ):
                assert node.value.value == "Schedule not found"
                return
        pytest.fail("_SCHEDULE_NOT_FOUND_DETAIL assignment not found")

    def test_no_bare_schedule_not_found_in_http_exceptions(self) -> None:
        app_path = _src_root() / "server" / "app.py"
        tree = ast.parse(app_path.read_text(), filename=str(app_path))
        bare_literals: list[int] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg != "detail":
                    continue
                if (
                    isinstance(kw.value, ast.Constant)
                    and kw.value.value == "Schedule not found"
                ):
                    bare_literals.append(kw.value.lineno)
        assert bare_literals == [], (
            f"Found bare 'Schedule not found' string literals at lines "
            f"{bare_literals} in app.py — use _SCHEDULE_NOT_FOUND_DETAIL instead"
        )

    def test_constant_referenced_in_schedule_endpoints(self) -> None:
        """Verify that _SCHEDULE_NOT_FOUND_DETAIL is referenced in app.py."""
        app_path = _src_root() / "server" / "app.py"
        source = app_path.read_text()
        # At least the definition + 5 usages in schedule endpoints
        count = source.count("_SCHEDULE_NOT_FOUND_DETAIL")
        assert count >= 6, (
            f"Expected _SCHEDULE_NOT_FOUND_DETAIL to appear at least 6 times "
            f"in app.py, found {count}"
        )


# TODO: CLEANUP CANDIDATE — these runtime tests duplicate the AST-based value
# checks above (TestScheduleNotFoundDetailSourceConsistency already verifies
# the constant equals "Schedule not found" and is referenced consistently).
class TestScheduleNotFoundDetailRuntime:
    """Runtime tests for _SCHEDULE_NOT_FOUND_DETAIL (requires fastapi)."""

    @pytest.fixture(autouse=True)
    def _require_fastapi(self) -> None:
        pytest.importorskip("fastapi", reason="fastapi not installed")

    def test_is_string(self) -> None:
        from helping_hands.server.app import _SCHEDULE_NOT_FOUND_DETAIL

        assert isinstance(_SCHEDULE_NOT_FOUND_DETAIL, str)

    def test_value(self) -> None:
        from helping_hands.server.app import _SCHEDULE_NOT_FOUND_DETAIL

        assert _SCHEDULE_NOT_FOUND_DETAIL == "Schedule not found"

    def test_non_empty(self) -> None:
        from helping_hands.server.app import _SCHEDULE_NOT_FOUND_DETAIL

        assert len(_SCHEDULE_NOT_FOUND_DETAIL) > 0
