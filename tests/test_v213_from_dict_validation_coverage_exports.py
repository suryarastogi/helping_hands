"""Guard ScheduledTask.from_dict input validation and the validate_cron_expression helper.

ScheduledTask.from_dict is the deserialisation path for schedule records stored in
Redis. If required fields (schedule_id, name, cron_expression, repo_path, prompt)
accept empty or whitespace-only strings, a corrupted or manually-crafted Redis entry
could create a ScheduledTask with blank identifiers that would silently fail at
trigger time without a useful error. These tests confirm that all five required
fields are rejected when empty or whitespace-only. The validate_cron_expression
whitespace-stripping test ensures that expressions copied with surrounding spaces
(common from user input) are normalised before croniter validation, preventing false
parse errors.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import ClassVar

import pytest

pytest.importorskip("celery", reason="celery extra not installed")

from helping_hands.server.schedules import (
    ScheduledTask,
    validate_cron_expression,
)

# ---------------------------------------------------------------------------
# ScheduledTask.from_dict — empty/whitespace required-field rejection
# ---------------------------------------------------------------------------


class TestFromDictEmptyFieldRejection:
    """from_dict must reject empty or whitespace-only required fields."""

    _VALID_BASE: ClassVar[dict] = {
        "schedule_id": "sched_abc",
        "name": "Valid",
        "cron_expression": "0 0 * * *",
        "repo_path": "owner/repo",
        "prompt": "do it",
    }

    def test_empty_schedule_id_raises(self) -> None:
        data = {**self._VALID_BASE, "schedule_id": ""}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_whitespace_schedule_id_raises(self) -> None:
        data = {**self._VALID_BASE, "schedule_id": "   "}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_empty_name_raises(self) -> None:
        data = {**self._VALID_BASE, "name": ""}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_whitespace_name_raises(self) -> None:
        data = {**self._VALID_BASE, "name": "  \t  "}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_empty_cron_expression_raises(self) -> None:
        data = {**self._VALID_BASE, "cron_expression": ""}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_empty_repo_path_raises(self) -> None:
        data = {**self._VALID_BASE, "repo_path": ""}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_empty_prompt_raises(self) -> None:
        data = {**self._VALID_BASE, "prompt": ""}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_whitespace_prompt_raises(self) -> None:
        data = {**self._VALID_BASE, "prompt": "\n  \n"}
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduledTask.from_dict(data)

    def test_multiple_empty_fields_reports_all(self) -> None:
        data = {**self._VALID_BASE, "schedule_id": "", "name": " ", "prompt": ""}
        with pytest.raises(ValueError, match="schedule_id") as exc_info:
            ScheduledTask.from_dict(data)
        msg = str(exc_info.value)
        assert "name" in msg
        assert "prompt" in msg

    def test_valid_data_still_works(self) -> None:
        task = ScheduledTask.from_dict(self._VALID_BASE)
        assert task.schedule_id == "sched_abc"
        assert task.name == "Valid"

    def test_missing_field_error_takes_precedence(self) -> None:
        """Missing key check runs before empty check."""
        data = {"schedule_id": "x"}  # missing all other required fields
        with pytest.raises(ValueError, match="Missing required fields"):
            ScheduledTask.from_dict(data)


# ---------------------------------------------------------------------------
# validate_cron_expression — whitespace stripping
# ---------------------------------------------------------------------------


class TestValidateCronExpressionStripping:
    """validate_cron_expression should strip leading/trailing whitespace."""

    def test_leading_whitespace(self) -> None:
        result = validate_cron_expression("  0 0 * * *")
        assert result == "0 0 * * *"

    def test_trailing_whitespace(self) -> None:
        result = validate_cron_expression("0 0 * * *  ")
        assert result == "0 0 * * *"

    def test_both_whitespace(self) -> None:
        result = validate_cron_expression("  0 * * * *  ")
        assert result == "0 * * * *"

    def test_preset_with_whitespace(self) -> None:
        result = validate_cron_expression("  daily  ")
        assert result == "0 0 * * *"

    def test_newline_whitespace(self) -> None:
        result = validate_cron_expression("\n0 0 * * *\n")
        assert result == "0 0 * * *"

    def test_tab_whitespace(self) -> None:
        result = validate_cron_expression("\t*/5 * * * *\t")
        assert result == "*/5 * * * *"


# ---------------------------------------------------------------------------
# Package-level __all__ exports
# ---------------------------------------------------------------------------


class TestPackageAllExports:
    """Package-level __init__.py files should declare non-empty __all__."""

    def test_lib_all_non_empty(self) -> None:
        import helping_hands.lib

        assert hasattr(helping_hands.lib, "__all__")
        assert len(helping_hands.lib.__all__) > 0

    def test_lib_all_contains_key_modules(self) -> None:
        import helping_hands.lib

        for name in ("config", "repo", "hands", "ai_providers", "meta", "validation"):
            assert name in helping_hands.lib.__all__, f"{name} missing from lib.__all__"

    def test_server_all_non_empty(self) -> None:
        import helping_hands.server

        assert hasattr(helping_hands.server, "__all__")
        assert len(helping_hands.server.__all__) > 0

    def test_server_all_contains_key_modules(self) -> None:
        import helping_hands.server

        for name in ("constants", "schedules", "task_result", "mcp_server"):
            assert name in helping_hands.server.__all__, (
                f"{name} missing from server.__all__"
            )

    def test_cli_all_non_empty(self) -> None:
        import helping_hands.cli

        assert hasattr(helping_hands.cli, "__all__")
        assert len(helping_hands.cli.__all__) > 0

    def test_cli_all_contains_main(self) -> None:
        import helping_hands.cli

        assert "main" in helping_hands.cli.__all__

    def test_lib_all_entries_are_strings(self) -> None:
        import helping_hands.lib

        assert all(isinstance(e, str) for e in helping_hands.lib.__all__)

    def test_server_all_entries_are_strings(self) -> None:
        import helping_hands.server

        assert all(isinstance(e, str) for e in helping_hands.server.__all__)

    def test_cli_all_entries_are_strings(self) -> None:
        import helping_hands.cli

        assert all(isinstance(e, str) for e in helping_hands.cli.__all__)

    def test_lib_all_entries_are_importable(self) -> None:
        """Each entry in lib.__all__ should be an importable sub-module."""
        import helping_hands.lib

        for name in helping_hands.lib.__all__:
            mod = importlib.import_module(f"helping_hands.lib.{name}")
            assert mod is not None

    def test_cli_all_entries_are_importable(self) -> None:
        import helping_hands.cli

        for name in helping_hands.cli.__all__:
            mod = importlib.import_module(f"helping_hands.cli.{name}")
            assert mod is not None


# ---------------------------------------------------------------------------
# Coverage fail_under threshold
# ---------------------------------------------------------------------------


class TestCoverageThreshold:
    """pyproject.toml should enforce a coverage floor."""

    def test_fail_under_configured(self) -> None:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "fail_under" in content

    def test_fail_under_value_is_75(self) -> None:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "fail_under = 75" in content
