"""v168 — Docstring presence tests for langgraph.py, app.py validators,
and cli/base.py configuration/utility methods."""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand
from helping_hands.lib.hands.v1.hand.langgraph import LangGraphHand

# ---------------------------------------------------------------------------
# LangGraph hand docstrings
# ---------------------------------------------------------------------------

_LANGGRAPH_METHODS = [
    "__init__",
    "_build_agent",
    "run",
]


class TestLangGraphHandDocstrings:
    """Verify LangGraphHand methods have Google-style docstrings."""

    @pytest.mark.parametrize("method_name", _LANGGRAPH_METHODS)
    def test_method_has_docstring(self, method_name):
        method = getattr(LangGraphHand, method_name)
        doc = inspect.getdoc(method)
        assert doc and len(doc.strip()) >= 10, (
            f"LangGraphHand.{method_name} is missing a docstring"
        )

    def test_init_docstring_has_args(self):
        doc = inspect.getdoc(LangGraphHand.__init__)
        assert "Args:" in doc

    def test_build_agent_docstring_has_returns(self):
        doc = inspect.getdoc(LangGraphHand._build_agent)
        assert "Returns:" in doc

    def test_run_docstring_has_args(self):
        doc = inspect.getdoc(LangGraphHand.run)
        assert "Args:" in doc

    def test_run_docstring_has_returns(self):
        doc = inspect.getdoc(LangGraphHand.run)
        assert "Returns:" in doc


# ---------------------------------------------------------------------------
# app.py _ToolSkillValidatorMixin docstrings
# ---------------------------------------------------------------------------

_APP_VALIDATOR_METHODS = [
    "_coerce_tools",
    "_validate_tools",
    "_coerce_skills",
    "_validate_skills",
]


class TestAppValidatorDocstrings:
    """Verify _ToolSkillValidatorMixin validator methods have docstrings."""

    @pytest.fixture()
    def mixin_cls(self):
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _ToolSkillValidatorMixin

        return _ToolSkillValidatorMixin

    @pytest.mark.parametrize("method_name", _APP_VALIDATOR_METHODS)
    def test_method_has_docstring(self, mixin_cls, method_name):
        method = getattr(mixin_cls, method_name)
        doc = inspect.getdoc(method)
        assert doc and len(doc.strip()) >= 10, (
            f"_ToolSkillValidatorMixin.{method_name} is missing a docstring"
        )

    @pytest.mark.parametrize("method_name", _APP_VALIDATOR_METHODS)
    def test_method_docstring_has_args(self, mixin_cls, method_name):
        method = getattr(mixin_cls, method_name)
        doc = inspect.getdoc(method)
        assert "Args:" in doc, (
            f"_ToolSkillValidatorMixin.{method_name} docstring missing Args"
        )

    @pytest.mark.parametrize("method_name", _APP_VALIDATOR_METHODS)
    def test_method_docstring_has_returns(self, mixin_cls, method_name):
        method = getattr(mixin_cls, method_name)
        doc = inspect.getdoc(method)
        assert "Returns:" in doc, (
            f"_ToolSkillValidatorMixin.{method_name} docstring missing Returns"
        )

    @pytest.mark.parametrize("method_name", ["_validate_tools", "_validate_skills"])
    def test_validate_method_docstring_has_raises(self, mixin_cls, method_name):
        method = getattr(mixin_cls, method_name)
        doc = inspect.getdoc(method)
        assert "Raises:" in doc, (
            f"_ToolSkillValidatorMixin.{method_name} docstring missing Raises"
        )


# ---------------------------------------------------------------------------
# cli/base.py _TwoPhaseCLIHand docstrings (v168 batch)
# ---------------------------------------------------------------------------

_CLI_BASE_METHODS_WITH_DOCSTRINGS = [
    "__init__",
    "_truncate_summary",
    "_normalize_base_command",
    "_base_command",
    "_resolve_cli_model",
    "_apply_backend_defaults",
    "_render_command",
    "_container_enabled",
    "_container_image",
    "_container_env_names",
    "_use_native_cli_auth",
    "_native_cli_auth_env_names",
    "_effective_container_env_names",
    "_execution_mode",
    "_float_env",
    "_io_poll_seconds",
    "_heartbeat_seconds",
    "_idle_timeout_seconds",
    "_build_subprocess_env",
    "_build_failure_message",
    "_build_init_prompt",
    "_build_task_prompt",
    "_repo_has_changes",
    "_looks_like_edit_request",
    "_should_retry_without_changes",
    "_build_apply_changes_prompt",
    "_interrupted_pr_metadata",
    "_finalize_after_run",
    "_format_pr_status_message",
    "_format_ci_fix_message",
]


class TestCLIBaseDocstringsV168:
    """Verify v168 cli/base.py methods have Google-style docstrings."""

    @pytest.mark.parametrize("method_name", _CLI_BASE_METHODS_WITH_DOCSTRINGS)
    def test_method_has_docstring(self, method_name):
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = inspect.getdoc(method)
        assert doc and len(doc.strip()) >= 10, (
            f"_TwoPhaseCLIHand.{method_name} is missing a docstring"
        )


_CLI_BASE_METHODS_WITH_ARGS = [
    "__init__",
    "_truncate_summary",
    "_normalize_base_command",
    "_apply_backend_defaults",
    "_render_command",
    "_float_env",
    "_build_failure_message",
    "_build_task_prompt",
    "_looks_like_edit_request",
    "_should_retry_without_changes",
    "_build_apply_changes_prompt",
    "_finalize_after_run",
    "_format_pr_status_message",
    "_format_ci_fix_message",
]


class TestCLIBaseDocstringsArgsReturns:
    """Verify Args/Returns sections in cli/base.py docstrings."""

    @pytest.mark.parametrize("method_name", _CLI_BASE_METHODS_WITH_ARGS)
    def test_docstring_has_args(self, method_name):
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = inspect.getdoc(method)
        assert "Args:" in doc, f"_TwoPhaseCLIHand.{method_name} docstring missing Args"

    @pytest.mark.parametrize(
        "method_name",
        [
            "_truncate_summary",
            "_normalize_base_command",
            "_base_command",
            "_resolve_cli_model",
            "_apply_backend_defaults",
            "_render_command",
            "_container_enabled",
            "_container_image",
            "_container_env_names",
            "_use_native_cli_auth",
            "_native_cli_auth_env_names",
            "_effective_container_env_names",
            "_execution_mode",
            "_float_env",
            "_io_poll_seconds",
            "_heartbeat_seconds",
            "_idle_timeout_seconds",
            "_build_subprocess_env",
            "_build_failure_message",
            "_build_init_prompt",
            "_build_task_prompt",
            "_repo_has_changes",
            "_looks_like_edit_request",
            "_should_retry_without_changes",
            "_build_apply_changes_prompt",
            "_interrupted_pr_metadata",
            "_finalize_after_run",
            "_format_pr_status_message",
            "_format_ci_fix_message",
        ],
    )
    def test_docstring_has_returns(self, method_name):
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = inspect.getdoc(method)
        assert "Returns:" in doc or "Return" in doc, (
            f"_TwoPhaseCLIHand.{method_name} docstring missing Returns"
        )

    def test_truncate_summary_docstring_has_raises(self):
        doc = inspect.getdoc(_TwoPhaseCLIHand._truncate_summary)
        assert "Raises:" in doc

    def test_base_command_docstring_has_raises(self):
        doc = inspect.getdoc(_TwoPhaseCLIHand._base_command)
        assert "Raises:" in doc

    def test_container_image_docstring_has_raises(self):
        doc = inspect.getdoc(_TwoPhaseCLIHand._container_image)
        assert "Raises:" in doc
