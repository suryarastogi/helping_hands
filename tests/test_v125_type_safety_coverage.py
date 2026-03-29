"""Tests for v125: git timeout upper bound and PR description boilerplate filtering.

_git_timeout() must cap values at _MAX_GIT_TIMEOUT (3600 s) to prevent operator
misconfiguration from setting an absurdly long timeout that would tie up workers
for hours.  Exceeding the cap should emit a WARNING so operators notice.

_is_boilerplate_line protects PR description quality: lines from the AI's
iteration-prompt scaffolding (banners, numbered steps, known prefixes) are filtered
before writing the PR body.  Regressions here mean internal prompt boilerplate leaks
into public pull-request descriptions, making the project look amateurish and
revealing internal system-prompt structure to contributors.
"""

from __future__ import annotations

import logging

import pytest

from helping_hands.lib.github import (
    _MAX_GIT_TIMEOUT,
    _git_timeout,
)
from helping_hands.lib.hands.v1.hand.pr_description import (
    _BOILERPLATE_PREFIXES,
    _is_boilerplate_line,
)

# ---------------------------------------------------------------------------
# _git_timeout upper bound
# ---------------------------------------------------------------------------


class TestGitTimeoutUpperBound:
    """Tests for the _MAX_GIT_TIMEOUT cap added in v125."""

    def test_max_constant_value(self) -> None:
        assert _MAX_GIT_TIMEOUT == 3600

    def test_over_max_is_capped(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "7200")
        with caplog.at_level(logging.WARNING):
            result = _git_timeout()
        assert result == _MAX_GIT_TIMEOUT
        assert "exceeds max" in caplog.text

    def test_at_max_is_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", str(_MAX_GIT_TIMEOUT))
        assert _git_timeout() == _MAX_GIT_TIMEOUT

    def test_just_above_max_is_capped(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", str(_MAX_GIT_TIMEOUT + 1))
        with caplog.at_level(logging.WARNING):
            result = _git_timeout()
        assert result == _MAX_GIT_TIMEOUT
        assert "exceeds max" in caplog.text

    def test_just_below_max_is_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", str(_MAX_GIT_TIMEOUT - 1))
        assert _git_timeout() == _MAX_GIT_TIMEOUT - 1

    def test_very_large_value_is_capped(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "999999")
        with caplog.at_level(logging.WARNING):
            result = _git_timeout()
        assert result == _MAX_GIT_TIMEOUT


# ---------------------------------------------------------------------------
# _get_schedule_manager return type
# ---------------------------------------------------------------------------


class TestGetScheduleManagerReturnType:
    """Tests for the ScheduleManager return type annotation added in v125."""

    def test_return_annotation_present(self) -> None:
        """_get_schedule_manager should have a return type annotation."""
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _get_schedule_manager

        annotations = _get_schedule_manager.__annotations__
        assert "return" in annotations
        assert "ScheduleManager" in str(annotations["return"])

    def test_schedule_manager_type_checking_import(self) -> None:
        """ScheduleManager should be importable from schedules module."""
        pytest.importorskip("fastapi")
        from helping_hands.server.schedules import ScheduleManager

        assert ScheduleManager is not None

    def test_module_level_variable_annotation(self) -> None:
        """_schedule_manager module variable should allow ScheduleManager | None."""
        pytest.importorskip("fastapi")
        import helping_hands.server.app as app_mod

        # The variable exists and starts as None
        assert hasattr(app_mod, "_schedule_manager")


# ---------------------------------------------------------------------------
# _is_boilerplate_line — direct tests
# ---------------------------------------------------------------------------


class TestIsBoilerplateLine:
    """Direct tests for _is_boilerplate_line in pr_description.py."""

    # --- Bracket banners ---

    def test_bracket_banner(self) -> None:
        assert _is_boilerplate_line("[INFO] Starting build") is True

    def test_bracket_banner_with_key_value(self) -> None:
        assert _is_boilerplate_line("[model] gpt-5.2 backend=basic") is True

    def test_bracket_no_space_after(self) -> None:
        """No space after bracket = not a banner."""
        assert _is_boilerplate_line("[nospacer]text") is False

    def test_bracket_empty_label(self) -> None:
        """Empty brackets are not matched by the regex .+?"""
        assert _is_boilerplate_line("[] something") is False

    # --- Numbered list items ---

    def test_numbered_list_item(self) -> None:
        assert _is_boilerplate_line("1. Read README.md") is True

    def test_numbered_multi_digit(self) -> None:
        assert _is_boilerplate_line("42. Apply changes") is True

    def test_number_without_dot(self) -> None:
        assert _is_boilerplate_line("1 something else") is False

    def test_number_dot_no_space(self) -> None:
        """'1.something' without space is not a numbered list."""
        assert _is_boilerplate_line("1.something") is False

    # --- Bullet items ---

    def test_bullet_item(self) -> None:
        assert _is_boilerplate_line("- Install dependencies") is True

    def test_bullet_nested(self) -> None:
        assert _is_boilerplate_line("- Nested item") is True

    def test_dash_not_bullet(self) -> None:
        """A line starting with dash but no space is not a bullet."""
        assert _is_boilerplate_line("-not a bullet") is False

    # --- Known boilerplate prefixes ---

    def test_initialization_phase(self) -> None:
        assert _is_boilerplate_line("Initialization phase: loading config") is True

    def test_execution_context(self) -> None:
        assert _is_boilerplate_line("Execution context: this hand is running") is True

    def test_repository_root(self) -> None:
        assert _is_boilerplate_line("Repository root: /tmp/repo") is True

    def test_task_execution_phase(self) -> None:
        assert _is_boilerplate_line("Task execution phase.") is True

    def test_user_task_request(self) -> None:
        assert _is_boilerplate_line("User task request:") is True

    def test_goals(self) -> None:
        assert _is_boilerplate_line("Goals: implement feature X") is True

    def test_do_not_ask(self) -> None:
        assert _is_boilerplate_line("Do not ask the user for approvals") is True

    def test_use_only_tools(self) -> None:
        assert _is_boilerplate_line("Use only tools that are available") is True

    def test_implement_the_task(self) -> None:
        assert _is_boilerplate_line("Implement the task directly") is True

    def test_skill_knowledge_catalog(self) -> None:
        assert _is_boilerplate_line("Skill knowledge catalog: prd, ralph") is True

    # --- Case insensitivity ---

    def test_prefix_case_insensitive(self) -> None:
        assert _is_boilerplate_line("INITIALIZATION PHASE: stuff") is True

    def test_prefix_mixed_case(self) -> None:
        assert _is_boilerplate_line("execution Context: test") is True

    # --- Non-boilerplate lines ---

    def test_normal_text(self) -> None:
        assert _is_boilerplate_line("Added a new feature to the codebase") is False

    def test_empty_string(self) -> None:
        assert _is_boilerplate_line("") is False

    def test_plain_sentence(self) -> None:
        assert _is_boilerplate_line("Fixed the login bug in auth module") is False

    def test_code_line(self) -> None:
        assert _is_boilerplate_line("def my_function():") is False

    # --- All prefixes are represented ---

    def test_all_prefixes_recognized(self) -> None:
        """Every entry in _BOILERPLATE_PREFIXES should be matched."""
        for prefix in _BOILERPLATE_PREFIXES:
            line = f"{prefix} some trailing text"
            assert _is_boilerplate_line(line) is True, f"Prefix not matched: {prefix!r}"

    def test_boilerplate_prefixes_count(self) -> None:
        """Verify the constant has the expected number of prefixes."""
        assert len(_BOILERPLATE_PREFIXES) == 18
