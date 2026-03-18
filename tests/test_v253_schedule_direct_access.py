"""Tests for v253: Simplify schedule getattr() to direct attribute access.

Covers:
- AST source consistency: no getattr(schedule/task, ...) in target functions
- ScheduledTask dataclass guarantees: all fields have defaults
- Behavioral: schedule trigger and response conversion access attrs correctly
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parent.parent / "src" / "helping_hands"
_CELERY_APP = _SRC / "server" / "celery_app.py"
_APP = _SRC / "server" / "app.py"

# Fields that were previously accessed via getattr()
_SCHEDULE_DIRECT_FIELDS = (
    "tools",
    "fix_ci",
    "ci_check_wait_minutes",
    "reference_repos",
)
_RESPONSE_DIRECT_FIELDS = (
    "fix_ci",
    "ci_check_wait_minutes",
    "github_token",
    "reference_repos",
    "tools",
    "schedule_id",
)


# ===========================================================================
# AST helpers
# ===========================================================================


class _GetattrScheduleVisitor(ast.NodeVisitor):
    """Find getattr(name, ...) calls for schedule/task variables."""

    def __init__(self, var_names: tuple[str, ...] = ("schedule", "task")) -> None:
        self.var_names = var_names
        self.hits: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in self.var_names
        ):
            attr = ""
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                attr = str(node.args[1].value)
            self.hits.append((node.lineno, attr))
        self.generic_visit(node)


class _FunctionExtractor(ast.NodeVisitor):
    """Extract function AST nodes by name."""

    def __init__(self, func_names: set[str]) -> None:
        self.func_names = func_names
        self.functions: dict[str, ast.FunctionDef] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in self.func_names:
            self.functions[node.name] = node
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name in self.func_names:
            self.functions[node.name] = node  # type: ignore[assignment]
        self.generic_visit(node)


# ===========================================================================
# AST: No getattr(schedule/task, ...) in target functions
# ===========================================================================


class TestNoGetattrInCeleryRunScheduledBuild:
    """scheduled_build should not use getattr(schedule, ...)."""

    def test_no_getattr_schedule(self) -> None:
        source = _CELERY_APP.read_text()
        tree = ast.parse(source, filename=str(_CELERY_APP))
        extractor = _FunctionExtractor({"scheduled_build"})
        extractor.visit(tree)
        assert "scheduled_build" in extractor.functions

        visitor = _GetattrScheduleVisitor(var_names=("schedule",))
        visitor.visit(extractor.functions["scheduled_build"])
        assert visitor.hits == [], (
            f"scheduled_build still has getattr(schedule, ...) at: {visitor.hits}"
        )


class TestNoGetattrInAppScheduleToResponse:
    """_schedule_to_response should not use getattr(task, ...)."""

    def test_no_getattr_task(self) -> None:
        source = _APP.read_text()
        tree = ast.parse(source, filename=str(_APP))
        extractor = _FunctionExtractor({"_schedule_to_response"})
        extractor.visit(tree)
        assert "_schedule_to_response" in extractor.functions

        visitor = _GetattrScheduleVisitor(var_names=("task",))
        visitor.visit(extractor.functions["_schedule_to_response"])
        assert visitor.hits == [], (
            f"_schedule_to_response still has getattr(task, ...) at: {visitor.hits}"
        )


# ===========================================================================
# ScheduledTask dataclass field guarantees
# ===========================================================================


def _skip_without_server_extras():
    pytest.importorskip("celery", reason="celery extra not installed")
    pytest.importorskip("fastapi", reason="fastapi extra not installed")


class TestScheduledTaskFieldDefaults:
    """All previously-getattr'd fields exist on ScheduledTask with defaults."""

    @pytest.fixture(autouse=True)
    def _require_extras(self):
        _skip_without_server_extras()

    @pytest.fixture()
    def task(self):
        from helping_hands.server.schedules import ScheduledTask

        return ScheduledTask(
            schedule_id="sched_test123",
            name="test",
            cron_expression="0 * * * *",
            repo_path="/tmp/repo",
            prompt="fix bugs",
        )

    def test_tools_default_is_empty_list(self, task) -> None:
        assert task.tools == []
        assert isinstance(task.tools, list)

    def test_fix_ci_default_is_false(self, task) -> None:
        assert task.fix_ci is False

    def test_ci_check_wait_minutes_default(self, task) -> None:
        assert isinstance(task.ci_check_wait_minutes, float)
        assert task.ci_check_wait_minutes > 0

    def test_reference_repos_default_is_empty_list(self, task) -> None:
        assert task.reference_repos == []
        assert isinstance(task.reference_repos, list)

    def test_github_token_default_is_none(self, task) -> None:
        assert task.github_token is None

    def test_schedule_id_is_required(self, task) -> None:
        assert task.schedule_id == "sched_test123"

    def test_all_direct_fields_accessible(self, task) -> None:
        """Every field previously accessed via getattr is directly accessible."""
        all_fields = set(_SCHEDULE_DIRECT_FIELDS) | set(_RESPONSE_DIRECT_FIELDS)
        for name in all_fields:
            getattr(task, name)


class TestScheduledTaskWithValues:
    """Fields are correctly set when explicitly provided."""

    @pytest.fixture(autouse=True)
    def _require_extras(self):
        _skip_without_server_extras()

    @pytest.fixture()
    def task(self):
        from helping_hands.server.schedules import ScheduledTask

        return ScheduledTask(
            schedule_id="sched_abc",
            name="full",
            cron_expression="0 0 * * *",
            repo_path="/tmp/repo",
            prompt="test",
            tools=["filesystem", "web"],
            fix_ci=True,
            ci_check_wait_minutes=5.0,
            reference_repos=["owner/other-repo"],
            github_token="ghp_test123",
        )

    def test_tools_set(self, task) -> None:
        assert task.tools == ["filesystem", "web"]

    def test_fix_ci_set(self, task) -> None:
        assert task.fix_ci is True

    def test_ci_check_wait_minutes_set(self, task) -> None:
        assert task.ci_check_wait_minutes == 5.0

    def test_reference_repos_set(self, task) -> None:
        assert task.reference_repos == ["owner/other-repo"]

    def test_github_token_set(self, task) -> None:
        assert task.github_token == "ghp_test123"
