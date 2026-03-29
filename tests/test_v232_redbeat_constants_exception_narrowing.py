"""Tests for v232: RedBeat prefix constants, task name constants, exception narrowing.

RedBeat uses string key prefixes to namespace its Redis entries; if celery_app.py
and schedules.py use different prefix literals, the scheduler and the worker see
different Redis keys and scheduled jobs either never run or create duplicates.

Centralising task name constants in server/constants.py means that renaming a
Celery task only requires one change; the AST checks ensure no module still
references the old bare string.

ensure_usage_schedule must catch only KeyError (a known RedBeat data race)
rather than bare Exception, so programming errors in the scheduler surface
immediately instead of being silently swallowed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _src_root() -> Path:
    """Return the path to src/helping_hands/server/."""
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands" / "server"


def _get_string_literals(source: str) -> list[str]:
    """Extract all string literals from Python source."""
    tree = ast.parse(source)
    literals: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
    return literals


# ---------------------------------------------------------------------------
# server/constants — RedBeat constant values
# ---------------------------------------------------------------------------


class TestRedBeatConstants:
    """Verify RedBeat-related constants in server/constants."""

    def test_redbeat_key_prefix_value(self) -> None:
        from helping_hands.server.constants import REDBEAT_KEY_PREFIX

        assert REDBEAT_KEY_PREFIX == "redbeat:"

    def test_redbeat_key_prefix_is_str(self) -> None:
        from helping_hands.server.constants import REDBEAT_KEY_PREFIX

        assert isinstance(REDBEAT_KEY_PREFIX, str)

    def test_redbeat_schedule_entry_prefix_value(self) -> None:
        from helping_hands.server.constants import REDBEAT_SCHEDULE_ENTRY_PREFIX

        assert REDBEAT_SCHEDULE_ENTRY_PREFIX == "helping_hands:scheduled:"

    def test_redbeat_schedule_entry_prefix_is_str(self) -> None:
        from helping_hands.server.constants import REDBEAT_SCHEDULE_ENTRY_PREFIX

        assert isinstance(REDBEAT_SCHEDULE_ENTRY_PREFIX, str)

    def test_redbeat_usage_entry_name_value(self) -> None:
        from helping_hands.server.constants import REDBEAT_USAGE_ENTRY_NAME

        assert REDBEAT_USAGE_ENTRY_NAME == "helping_hands:usage-logger"

    def test_redbeat_usage_entry_name_is_str(self) -> None:
        from helping_hands.server.constants import REDBEAT_USAGE_ENTRY_NAME

        assert isinstance(REDBEAT_USAGE_ENTRY_NAME, str)


# ---------------------------------------------------------------------------
# server/constants — Celery task name constants
# ---------------------------------------------------------------------------


class TestCeleryTaskNameConstants:
    """Verify Celery task name constants in server/constants."""

    def test_task_name_scheduled_build_value(self) -> None:
        from helping_hands.server.constants import TASK_NAME_SCHEDULED_BUILD

        assert TASK_NAME_SCHEDULED_BUILD == "helping_hands.scheduled_build"

    def test_task_name_log_usage_value(self) -> None:
        from helping_hands.server.constants import TASK_NAME_LOG_USAGE

        assert TASK_NAME_LOG_USAGE == "helping_hands.log_claude_usage"

    def test_task_names_are_strings(self) -> None:
        from helping_hands.server.constants import (
            TASK_NAME_LOG_USAGE,
            TASK_NAME_SCHEDULED_BUILD,
        )

        assert isinstance(TASK_NAME_SCHEDULED_BUILD, str)
        assert isinstance(TASK_NAME_LOG_USAGE, str)

    def test_task_names_are_distinct(self) -> None:
        from helping_hands.server.constants import (
            TASK_NAME_LOG_USAGE,
            TASK_NAME_SCHEDULED_BUILD,
        )

        assert TASK_NAME_SCHEDULED_BUILD != TASK_NAME_LOG_USAGE


# ---------------------------------------------------------------------------
# server/constants — __all__ includes new constants
# ---------------------------------------------------------------------------


class TestServerConstantsAllUpdated:
    """Verify __all__ includes new RedBeat and task name constants."""

    def test_all_exports_updated(self) -> None:
        from helping_hands.server import constants

        expected = {
            "ANTHROPIC_BETA_HEADER",
            "ANTHROPIC_USAGE_URL",
            "DEFAULT_BACKEND",
            "DEFAULT_CI_WAIT_MINUTES",
            "DEFAULT_MAX_ITERATIONS",
            "JWT_TOKEN_PREFIX",
            "KEYCHAIN_ACCESS_TOKEN_KEY",
            "KEYCHAIN_OAUTH_KEY",
            "KEYCHAIN_SERVICE_NAME",
            "KEYCHAIN_TIMEOUT_S",
            "MAX_CI_WAIT_MINUTES",
            "MAX_GITHUB_TOKEN_LENGTH",
            "MAX_ITERATIONS_UPPER_BOUND",
            "MAX_MODEL_LENGTH",
            "MAX_PROMPT_LENGTH",
            "MAX_REFERENCE_REPOS",
            "MAX_REPO_PATH_LENGTH",
            "MIN_CI_WAIT_MINUTES",
            "REDBEAT_KEY_PREFIX",
            "REDBEAT_SCHEDULE_ENTRY_PREFIX",
            "REDBEAT_USAGE_ENTRY_NAME",
            "TASK_NAME_LOG_USAGE",
            "TASK_NAME_SCHEDULED_BUILD",
            "USAGE_API_TIMEOUT_S",
            "USAGE_CACHE_TTL_S",
            "USAGE_USER_AGENT",
        }
        assert expected.issubset(set(constants.__all__))

    def test_all_symbols_importable(self) -> None:
        from helping_hands.server import constants

        for name in constants.__all__:
            assert hasattr(constants, name), (
                f"{name} declared in __all__ but not importable"
            )


# ---------------------------------------------------------------------------
# celery_app — uses shared RedBeat prefix constant in conf
# ---------------------------------------------------------------------------


class TestCeleryAppUsesRedBeatPrefix:
    """Verify celery_app uses shared constants for RedBeat configuration."""

    def test_redbeat_key_prefix_in_conf(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import celery_app
        from helping_hands.server.constants import REDBEAT_KEY_PREFIX

        assert celery_app.conf.redbeat_key_prefix == REDBEAT_KEY_PREFIX


# ---------------------------------------------------------------------------
# AST-based source consistency — no bare string literals for prefixes
# (uses file reading instead of module import to avoid celery dependency)
# ---------------------------------------------------------------------------


class TestSourceConsistencyRedBeatPrefixes:
    """AST checks that RedBeat string literals are not hardcoded in source."""

    def test_schedules_no_hardcoded_redbeat_prefix(self) -> None:
        """schedules.py should not contain bare 'redbeat:' string."""
        source = (_src_root() / "schedules.py").read_text()
        literals = _get_string_literals(source)
        bare = [s for s in literals if s == "redbeat:"]
        assert bare == [], "schedules.py still contains bare 'redbeat:' literal"

    def test_schedules_no_hardcoded_schedule_entry_prefix(self) -> None:
        """schedules.py should not contain bare 'helping_hands:scheduled:' string."""
        source = (_src_root() / "schedules.py").read_text()
        literals = _get_string_literals(source)
        bare = [s for s in literals if s == "helping_hands:scheduled:"]
        assert bare == [], (
            "schedules.py still contains bare 'helping_hands:scheduled:' literal"
        )

    def test_celery_app_no_hardcoded_task_name_scheduled_build(self) -> None:
        """celery_app.py should not contain bare 'helping_hands.scheduled_build'."""
        source = (_src_root() / "celery_app.py").read_text()
        literals = _get_string_literals(source)
        bare = [s for s in literals if s == "helping_hands.scheduled_build"]
        assert bare == [], (
            "celery_app.py still contains bare 'helping_hands.scheduled_build' literal"
        )

    def test_celery_app_no_hardcoded_task_name_log_usage(self) -> None:
        """celery_app.py should not contain bare 'helping_hands.log_claude_usage'."""
        source = (_src_root() / "celery_app.py").read_text()
        literals = _get_string_literals(source)
        bare = [s for s in literals if s == "helping_hands.log_claude_usage"]
        assert bare == [], (
            "celery_app.py still contains bare 'helping_hands.log_claude_usage' literal"
        )

    def test_schedules_no_hardcoded_task_name(self) -> None:
        """schedules.py should not contain bare 'helping_hands.scheduled_build'."""
        source = (_src_root() / "schedules.py").read_text()
        literals = _get_string_literals(source)
        bare = [s for s in literals if s == "helping_hands.scheduled_build"]
        assert bare == [], (
            "schedules.py still contains bare 'helping_hands.scheduled_build' literal"
        )

    def test_celery_app_no_hardcoded_redbeat_prefix(self) -> None:
        """celery_app.py should not contain bare 'redbeat:' string."""
        source = (_src_root() / "celery_app.py").read_text()
        literals = _get_string_literals(source)
        bare = [s for s in literals if s == "redbeat:"]
        assert bare == [], "celery_app.py still contains bare 'redbeat:' literal"

    def test_celery_app_no_hardcoded_usage_entry_name(self) -> None:
        """celery_app.py should not contain bare 'helping_hands:usage-logger'."""
        source = (_src_root() / "celery_app.py").read_text()
        literals = _get_string_literals(source)
        bare = [s for s in literals if s == "helping_hands:usage-logger"]
        assert bare == [], (
            "celery_app.py still contains bare 'helping_hands:usage-logger' literal"
        )


# ---------------------------------------------------------------------------
# ensure_usage_schedule — KeyError narrowing (AST check on source file)
# ---------------------------------------------------------------------------


class TestEnsureUsageScheduleExceptionNarrowing:
    """Verify ensure_usage_schedule catches KeyError, not bare Exception."""

    def test_inner_except_is_key_error(self) -> None:
        """The inner except in ensure_usage_schedule must be KeyError."""
        source = (_src_root() / "celery_app.py").read_text()
        tree = ast.parse(source)

        # Find the ensure_usage_schedule function definition
        func_node = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "ensure_usage_schedule"
            ):
                func_node = node
                break

        assert func_node is not None, "ensure_usage_schedule not found in celery_app.py"

        # Find the outer and inner Try nodes.
        # The outer Try wraps the entire function body (after the docstring).
        try_nodes: list[ast.Try] = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Try):
                try_nodes.append(node)

        assert len(try_nodes) >= 2, (
            f"Expected at least 2 Try nodes, found {len(try_nodes)}"
        )

        # Find the try node whose handler catches KeyError (the inner
        # from_key lookup).  After v234 the function has 3 try blocks:
        # ImportError, OSError, and KeyError — so we search by handler type
        # instead of relying on positional index.
        key_error_try = None
        for try_node in try_nodes:
            for handler in try_node.handlers:
                if isinstance(handler.type, ast.Name) and handler.type.id == "KeyError":
                    key_error_try = try_node
                    break

        assert key_error_try is not None, (
            "No try/except KeyError found in ensure_usage_schedule"
        )
