"""Tests for v204: DRY form defaults, truthy values, inline import, tool dispatch.

Covers:
- Form default mismatch fix: enqueue_build_form uses _DEFAULT_BACKEND, not "codexcli"
- _is_running_in_docker uses _TRUTHY_VALUES from config
- Top-level import time (no inline import)
- _build_form_redirect_query uses _DEFAULT_CI_WAIT_MINUTES constant
- _TOOL_SUMMARY_KEY_MAP / _TOOL_SUMMARY_STATIC dispatch tables in claude.py
- _StreamJsonEmitter._summarize_tool correctness with dispatch tables
"""

from __future__ import annotations

import ast
import inspect

import pytest

# ---------------------------------------------------------------------------
# Form default alignment with constants
# ---------------------------------------------------------------------------


class TestFormDefaultAlignment:
    """enqueue_build_form defaults must match server constants."""

    @classmethod
    def setup_class(cls) -> None:
        pytest.importorskip("fastapi")

    def test_form_backend_default_matches_constant(self) -> None:
        """Form backend default is _DEFAULT_BACKEND, not a hardcoded string."""

        # Read source to confirm Form() default references the constant
        from helping_hands.server import app as app_mod

        src = inspect.getsource(app_mod.enqueue_build_form)
        assert "codexcli" not in src, (
            "Form backend default should use _DEFAULT_BACKEND constant"
        )
        assert "_DEFAULT_BACKEND" in src

    def test_form_max_iterations_default_matches_constant(self) -> None:
        from helping_hands.server import app as app_mod

        src = inspect.getsource(app_mod.enqueue_build_form)
        assert "_DEFAULT_MAX_ITERATIONS" in src

    def test_form_ci_wait_default_matches_constant(self) -> None:
        from helping_hands.server import app as app_mod

        src = inspect.getsource(app_mod.enqueue_build_form)
        assert "_DEFAULT_CI_WAIT_MINUTES" in src
        # No hardcoded 3.0 in Form() default
        assert "Form(3.0)" not in src


class TestBuildFormRedirectQuery:
    """_build_form_redirect_query uses constant for CI wait comparison."""

    @classmethod
    def setup_class(cls) -> None:
        pytest.importorskip("fastapi")

    def test_no_hardcoded_ci_wait_literal(self) -> None:
        from helping_hands.server import app as app_mod

        src = inspect.getsource(app_mod._build_form_redirect_query)
        assert "!= 3.0" not in src, (
            "Should use _DEFAULT_CI_WAIT_MINUTES instead of hardcoded 3.0"
        )
        assert "_DEFAULT_CI_WAIT_MINUTES" in src

    def test_default_ci_wait_omitted_from_query(self) -> None:
        from helping_hands.server.app import _build_form_redirect_query
        from helping_hands.server.constants import DEFAULT_CI_WAIT_MINUTES

        query = _build_form_redirect_query(
            repo_path="/tmp/r",
            prompt="test",
            backend="claudecodecli",
            max_iterations=6,
            error="err",
            ci_check_wait_minutes=DEFAULT_CI_WAIT_MINUTES,
        )
        assert "ci_check_wait_minutes" not in query

    def test_non_default_ci_wait_included_in_query(self) -> None:
        from helping_hands.server.app import _build_form_redirect_query

        query = _build_form_redirect_query(
            repo_path="/tmp/r",
            prompt="test",
            backend="claudecodecli",
            max_iterations=6,
            error="err",
            ci_check_wait_minutes=5.0,
        )
        assert query["ci_check_wait_minutes"] == "5.0"


# ---------------------------------------------------------------------------
# _is_running_in_docker uses _TRUTHY_VALUES
# ---------------------------------------------------------------------------


class TestIsRunningInDockerTruthy:
    """_is_running_in_docker delegates to _TRUTHY_VALUES from config."""

    @classmethod
    def setup_class(cls) -> None:
        pytest.importorskip("fastapi")

    def test_source_references_truthy_values(self) -> None:
        from helping_hands.server import app as app_mod

        src = inspect.getsource(app_mod._is_running_in_docker)
        assert "_TRUTHY_VALUES" in src, (
            "Should use _TRUTHY_VALUES instead of inline set"
        )
        # No inline set literal
        assert '{"1", "true", "yes"}' not in src

    def test_truthy_env_detected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "yes")
        assert _is_running_in_docker() is True

    def test_falsy_env_not_detected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "no")
        assert _is_running_in_docker() is False

    def test_empty_env_not_detected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        # Also ensure /.dockerenv doesn't exist in test env
        import pathlib

        if not pathlib.Path("/.dockerenv").exists():
            assert _is_running_in_docker() is False


# ---------------------------------------------------------------------------
# Top-level import time (no inline import)
# ---------------------------------------------------------------------------


class TestTopLevelTimeImport:
    """time module is imported at module level, not inline."""

    @classmethod
    def setup_class(cls) -> None:
        pytest.importorskip("fastapi")

    def test_no_inline_time_import(self) -> None:
        from helping_hands.server import app as app_mod

        src = inspect.getsource(app_mod._fetch_claude_usage)
        assert "import time" not in src, (
            "time should be imported at module level, not inside function"
        )

    def test_module_has_time_import(self) -> None:
        """Verify time is available as a top-level module attribute."""
        from helping_hands.server import app as app_mod

        # Parse the module source to check for top-level import time
        mod_src = inspect.getsource(app_mod)
        tree = ast.parse(mod_src)
        top_imports = [
            node
            for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.Import)
            and any(alias.name == "time" for alias in node.names)
        ]
        assert len(top_imports) >= 1, "time should be imported at module level"


# ---------------------------------------------------------------------------
# _TOOL_SUMMARY_KEY_MAP and _TOOL_SUMMARY_STATIC
# ---------------------------------------------------------------------------


class TestToolSummaryDispatchTables:
    """Verify the dispatch table constants exist and contain expected entries."""

    def test_key_map_contains_read(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_KEY_MAP

        assert "Read" in _TOOL_SUMMARY_KEY_MAP
        assert _TOOL_SUMMARY_KEY_MAP["Read"] == "file_path"

    def test_key_map_contains_edit(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_KEY_MAP

        assert "Edit" in _TOOL_SUMMARY_KEY_MAP
        assert _TOOL_SUMMARY_KEY_MAP["Edit"] == "file_path"

    def test_key_map_contains_write(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_KEY_MAP

        assert "Write" in _TOOL_SUMMARY_KEY_MAP
        assert _TOOL_SUMMARY_KEY_MAP["Write"] == "file_path"

    def test_key_map_contains_glob(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_KEY_MAP

        assert "Glob" in _TOOL_SUMMARY_KEY_MAP
        assert _TOOL_SUMMARY_KEY_MAP["Glob"] == "pattern"

    def test_key_map_contains_notebook_edit(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_KEY_MAP

        assert "NotebookEdit" in _TOOL_SUMMARY_KEY_MAP
        assert _TOOL_SUMMARY_KEY_MAP["NotebookEdit"] == "notebook_path"

    def test_key_map_is_dict(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_KEY_MAP

        assert isinstance(_TOOL_SUMMARY_KEY_MAP, dict)

    def test_static_contains_todo_write(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_STATIC

        assert "TodoWrite" in _TOOL_SUMMARY_STATIC

    def test_static_contains_cron_list(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_STATIC

        assert "CronList" in _TOOL_SUMMARY_STATIC

    def test_static_is_frozenset(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _TOOL_SUMMARY_STATIC

        assert isinstance(_TOOL_SUMMARY_STATIC, frozenset)

    def test_key_map_and_static_disjoint(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            _TOOL_SUMMARY_KEY_MAP,
            _TOOL_SUMMARY_STATIC,
        )

        overlap = set(_TOOL_SUMMARY_KEY_MAP) & _TOOL_SUMMARY_STATIC
        assert not overlap, f"Overlap between key map and static: {overlap}"


# ---------------------------------------------------------------------------
# _summarize_tool correctness (via dispatch tables)
# ---------------------------------------------------------------------------


class TestSummarizeToolDispatch:
    """_summarize_tool produces correct summaries using dispatch tables."""

    @pytest.fixture()
    def summarize(self):
        from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter

        return _StreamJsonEmitter._summarize_tool

    # --- Key-map tools (simple pattern) ---

    def test_read(self, summarize) -> None:
        assert summarize("Read", {"file_path": "/a/b.py"}) == "Read /a/b.py"

    def test_edit(self, summarize) -> None:
        assert summarize("Edit", {"file_path": "/x.py"}) == "Edit /x.py"

    def test_write(self, summarize) -> None:
        assert summarize("Write", {"file_path": "/w.py"}) == "Write /w.py"

    def test_glob(self, summarize) -> None:
        assert summarize("Glob", {"pattern": "**/*.py"}) == "Glob **/*.py"

    def test_notebook_edit(self, summarize) -> None:
        assert (
            summarize("NotebookEdit", {"notebook_path": "nb.ipynb"})
            == "NotebookEdit nb.ipynb"
        )

    def test_key_map_missing_key(self, summarize) -> None:
        """If the input key is missing, should return 'ToolName '."""
        assert summarize("Read", {}) == "Read "

    # --- Static tools ---

    def test_todo_write(self, summarize) -> None:
        assert summarize("TodoWrite", {}) == "TodoWrite"

    def test_cron_list(self, summarize) -> None:
        assert summarize("CronList", {}) == "CronList"

    # --- Custom-format tools ---

    def test_bash(self, summarize) -> None:
        result = summarize("Bash", {"command": "ls -la"})
        assert result.startswith("$ ")
        assert "ls -la" in result

    def test_grep(self, summarize) -> None:
        assert summarize("Grep", {"pattern": "TODO"}) == "Grep /TODO/"

    def test_web_fetch(self, summarize) -> None:
        assert (
            summarize("WebFetch", {"url": "https://example.com"})
            == "WebFetch https://example.com"
        )

    def test_web_search_with_query(self, summarize) -> None:
        result = summarize("WebSearch", {"query": "python"})
        assert "python" in result

    def test_web_search_empty(self, summarize) -> None:
        assert summarize("WebSearch", {"query": ""}) == "WebSearch"

    def test_agent_with_desc(self, summarize) -> None:
        assert summarize("Agent", {"description": "search"}) == "Agent: search"

    def test_agent_empty(self, summarize) -> None:
        assert summarize("Agent", {"description": ""}) == "Agent"

    def test_multi_tool(self, summarize) -> None:
        assert summarize("MultiTool", {"tool_uses": [1, 2, 3]}) == "MultiTool (3 tools)"

    def test_multi_tool_non_list(self, summarize) -> None:
        assert (
            summarize("MultiTool", {"tool_uses": "not-a-list"}) == "MultiTool (0 tools)"
        )

    def test_skill_with_name(self, summarize) -> None:
        assert summarize("Skill", {"skill": "commit"}) == "Skill: commit"

    def test_skill_empty(self, summarize) -> None:
        assert summarize("Skill", {"skill": ""}) == "Skill"

    def test_cron_create_with_prompt(self, summarize) -> None:
        result = summarize("CronCreate", {"prompt": "check logs"})
        assert "CronCreate" in result
        assert "check logs" in result

    def test_cron_create_empty(self, summarize) -> None:
        assert summarize("CronCreate", {"prompt": ""}) == "CronCreate"

    def test_cron_delete_with_id(self, summarize) -> None:
        assert summarize("CronDelete", {"id": "abc123"}) == "CronDelete abc123"

    def test_cron_delete_empty(self, summarize) -> None:
        assert summarize("CronDelete", {"id": ""}) == "CronDelete"

    def test_enter_worktree(self, summarize) -> None:
        assert summarize("EnterWorktree", {"name": "feat-x"}) == "EnterWorktree feat-x"

    def test_enter_worktree_empty(self, summarize) -> None:
        assert summarize("EnterWorktree", {"name": ""}) == "EnterWorktree"

    def test_exit_worktree(self, summarize) -> None:
        assert summarize("ExitWorktree", {"action": "merge"}) == "ExitWorktree merge"

    def test_exit_worktree_empty(self, summarize) -> None:
        assert summarize("ExitWorktree", {"action": ""}) == "ExitWorktree"

    def test_unknown_tool(self, summarize) -> None:
        assert summarize("FutureTool", {"x": 1}) == "tool: FutureTool"


# ---------------------------------------------------------------------------
# __all__ exports
# ---------------------------------------------------------------------------


class TestAllExports:
    """New constants are in __all__."""

    def test_claude_exports_key_map(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import claude

        assert "_TOOL_SUMMARY_KEY_MAP" in claude.__all__

    def test_claude_exports_static(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import claude

        assert "_TOOL_SUMMARY_STATIC" in claude.__all__
