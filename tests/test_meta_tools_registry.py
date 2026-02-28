"""Tests for helping_hands.lib.meta.tools.registry."""

from __future__ import annotations

import pytest

from helping_hands.lib.meta.tools import registry as tool_registry


class TestToolRegistry:
    def test_available_tool_categories(self) -> None:
        assert tool_registry.available_tool_category_names() == (
            "execution",
            "web",
        )

    def test_normalize_tool_selection(self) -> None:
        assert tool_registry.normalize_tool_selection("execution, web,execution") == (
            "execution",
            "web",
        )
        assert tool_registry.normalize_tool_selection(["execution", "web"]) == (
            "execution",
            "web",
        )
        assert tool_registry.normalize_tool_selection(None) == ()

    def test_validate_rejects_unknown(self) -> None:
        with pytest.raises(ValueError, match="unknown tool"):
            tool_registry.validate_tool_category_names(("unknown",))

    def test_merge_with_legacy_tool_flags(self) -> None:
        merged = tool_registry.merge_with_legacy_tool_flags(
            ("web",),
            enable_execution=True,
            enable_web=False,
        )
        assert merged == ("execution", "web")

    def test_resolve_and_build_runner_map(self) -> None:
        resolved = tool_registry.resolve_tool_categories(("execution", "web"))
        names = [cat.name for cat in resolved]
        assert names == ["execution", "web"]

        mapping = tool_registry.build_tool_runner_map(resolved)
        assert set(mapping.keys()) == {
            "python.run_code",
            "python.run_script",
            "bash.run_script",
            "web.search",
            "web.browse",
        }

    def test_category_name_for_tool(self) -> None:
        assert tool_registry.category_name_for_tool("python.run_code") == "execution"
        assert tool_registry.category_name_for_tool("web.search") == "web"
        assert tool_registry.category_name_for_tool("unknown.tool") is None

    def test_format_tool_instructions(self) -> None:
        resolved = tool_registry.resolve_tool_categories(("execution",))
        formatted = tool_registry.format_tool_instructions(resolved)
        assert "Tool category enabled: execution" in formatted
        assert "@@TOOL: python.run_code" in formatted

    def test_format_tool_instructions_empty(self) -> None:
        formatted = tool_registry.format_tool_instructions(())
        assert "No dynamic tools enabled" in formatted

    def test_format_tool_instructions_for_cli(self) -> None:
        resolved = tool_registry.resolve_tool_categories(("execution",))
        formatted = tool_registry.format_tool_instructions_for_cli(resolved)
        assert "Tool category enabled: execution" in formatted
        assert "python.run_code" in formatted
        assert "@@TOOL" not in formatted

    def test_format_tool_instructions_for_cli_empty(self) -> None:
        assert tool_registry.format_tool_instructions_for_cli(()) == ""
