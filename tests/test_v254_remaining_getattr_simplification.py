"""Protect direct attribute access on typed objects, preventing getattr-with-default from hiding typos.

getattr(obj, "attr", default) on objects with well-defined schemas
(HTTPResponse, PyGitHub Repository, ScheduledTask dataclass, Celery
Task.request) silently returns the default when the attribute name is
misspelled, producing wrong values with no error. Direct access lets both
the type checker and runtime catch name mismatches immediately.

The AST checks ensure no regression to getattr patterns in browse_url,
finalize_pr, update_schedule, and run_hand.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parent.parent / "src" / "helping_hands"
_WEB_PY = _SRC / "lib" / "meta" / "tools" / "web.py"
_BASE_PY = _SRC / "lib" / "hands" / "v1" / "hand" / "base.py"
_APP_PY = _SRC / "server" / "app.py"
_CELERY_APP_PY = _SRC / "server" / "celery_app.py"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _find_getattr_calls_in_function(
    source_path: Path, function_name: str
) -> list[tuple[int, str]]:
    """Return (line, source_segment) for getattr() calls inside *function_name*."""
    tree = ast.parse(source_path.read_text())
    results: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "getattr"
            ):
                results.append((child.lineno, ast.dump(child)))
    return results


def _count_getattr_on_line(source_path: Path, lineno: int) -> int:
    """Count getattr() occurrences on a specific line (1-based)."""
    lines = source_path.read_text().splitlines()
    if lineno < 1 or lineno > len(lines):
        return 0
    return lines[lineno - 1].count("getattr")


# ---------------------------------------------------------------------------
# AST consistency: no getattr in target locations
# ---------------------------------------------------------------------------


class TestWebPyNoGetattr:
    """web.py browse_url should use response.status directly."""

    def test_no_getattr_in_browse_url(self) -> None:
        hits = _find_getattr_calls_in_function(_WEB_PY, "browse_url")
        assert hits == [], f"Unexpected getattr() in browse_url: {hits}"

    def test_response_status_direct_access(self) -> None:
        source = _WEB_PY.read_text()
        assert "response.status" in source
        assert 'getattr(response, "status"' not in source


class TestBasePyNoGetattr:
    """base.py finalize_pr should use repo_obj.default_branch directly."""

    def test_no_getattr_for_default_branch(self) -> None:
        source = _BASE_PY.read_text()
        assert 'getattr(repo_obj, "default_branch"' not in source

    def test_direct_default_branch_access(self) -> None:
        source = _BASE_PY.read_text()
        assert "repo_obj.default_branch" in source


class TestAppPyNoGetattr:
    """app.py update_schedule should use existing.github_token directly."""

    def test_no_getattr_for_github_token(self) -> None:
        source = _APP_PY.read_text()
        assert 'getattr(existing, "github_token"' not in source

    def test_direct_github_token_access(self) -> None:
        source = _APP_PY.read_text()
        assert "existing.github_token" in source


class TestCeleryAppNoNestedGetattr:
    """celery_app.py run_hand should use self.request.id directly."""

    def test_no_nested_getattr_for_task_id(self) -> None:
        source = _CELERY_APP_PY.read_text()
        assert 'getattr(self, "request"' not in source
        assert "getattr(getattr(self" not in source

    def test_direct_request_id_access(self) -> None:
        source = _CELERY_APP_PY.read_text()
        assert "self.request.id" in source


# ---------------------------------------------------------------------------
# ScheduledTask field guarantees
# ---------------------------------------------------------------------------


def _skip_without_server_extras():
    pytest.importorskip("celery", reason="celery extra not installed")
    pytest.importorskip("fastapi", reason="fastapi extra not installed")


class TestScheduledTaskGithubToken:
    """ScheduledTask.github_token has a default and is always accessible."""

    @pytest.fixture(autouse=True)
    def _require_extras(self):
        _skip_without_server_extras()

    def test_default_is_none(self) -> None:
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="test",
            name="test",
            cron_expression="* * * * *",
            repo_path="/tmp/test",
            prompt="test",
        )
        assert task.github_token is None

    def test_explicit_value(self) -> None:
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="test",
            name="test",
            cron_expression="* * * * *",
            repo_path="/tmp/test",
            prompt="test",
            github_token="ghp_test123",
        )
        assert task.github_token == "ghp_test123"
