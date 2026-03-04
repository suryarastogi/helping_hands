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


class TestParseStrList:
    """Edge cases for _parse_str_list validator."""

    def test_missing_key_returns_empty(self) -> None:
        result = tool_registry._parse_str_list({}, key="items")
        assert result == []

    def test_none_value_returns_empty(self) -> None:
        result = tool_registry._parse_str_list({"items": None}, key="items")
        assert result == []

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a list"):
            tool_registry._parse_str_list({"items": "not-a-list"}, key="items")

    def test_non_string_element_raises(self) -> None:
        with pytest.raises(ValueError, match="must contain only strings"):
            tool_registry._parse_str_list({"items": ["ok", 123]}, key="items")

    def test_valid_list(self) -> None:
        result = tool_registry._parse_str_list({"items": ["a", "b"]}, key="items")
        assert result == ["a", "b"]


class TestParsePositiveInt:
    """Edge cases for _parse_positive_int validator."""

    def test_missing_key_uses_default(self) -> None:
        result = tool_registry._parse_positive_int({}, key="count", default=5)
        assert result == 5

    def test_boolean_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            tool_registry._parse_positive_int({"count": True}, key="count", default=5)

    def test_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            tool_registry._parse_positive_int({"count": "10"}, key="count", default=5)

    def test_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            tool_registry._parse_positive_int({"count": 0}, key="count", default=5)

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            tool_registry._parse_positive_int({"count": -1}, key="count", default=5)

    def test_valid_int(self) -> None:
        result = tool_registry._parse_positive_int(
            {"count": 42}, key="count", default=5
        )
        assert result == 42


class TestParseOptionalStr:
    """Edge cases for _parse_optional_str validator."""

    def test_missing_key_returns_none(self) -> None:
        result = tool_registry._parse_optional_str({}, key="name")
        assert result is None

    def test_none_value_returns_none(self) -> None:
        result = tool_registry._parse_optional_str({"name": None}, key="name")
        assert result is None

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            tool_registry._parse_optional_str({"name": 123}, key="name")

    def test_whitespace_only_returns_none(self) -> None:
        result = tool_registry._parse_optional_str({"name": "   "}, key="name")
        assert result is None

    def test_strips_whitespace(self) -> None:
        result = tool_registry._parse_optional_str({"name": "  hello  "}, key="name")
        assert result == "hello"


class TestNormalizeToolSelectionEdgeCases:
    """Additional edge cases for normalize_tool_selection."""

    def test_empty_string(self) -> None:
        assert tool_registry.normalize_tool_selection("") == ()

    def test_whitespace_only_string(self) -> None:
        assert tool_registry.normalize_tool_selection("  ,  ,  ") == ()

    def test_underscores_converted_to_hyphens(self) -> None:
        result = tool_registry.normalize_tool_selection("my_tool")
        assert result == ("my-tool",)

    def test_case_insensitive(self) -> None:
        result = tool_registry.normalize_tool_selection("EXECUTION, Web")
        assert result == ("execution", "web")

    def test_tuple_input(self) -> None:
        result = tool_registry.normalize_tool_selection(("execution", "web"))
        assert result == ("execution", "web")

    def test_non_string_in_list_raises(self) -> None:
        with pytest.raises(ValueError, match="tools must contain only strings"):
            tool_registry.normalize_tool_selection([123])  # type: ignore[list-item]


class TestValidateToolCategoryEdgeCases:
    """Additional edge cases for validate_tool_category_names."""

    def test_empty_tuple_passes(self) -> None:
        # Should not raise
        tool_registry.validate_tool_category_names(())

    def test_multiple_unknown_listed(self) -> None:
        with pytest.raises(ValueError, match="alpha, zeta"):
            tool_registry.validate_tool_category_names(("zeta", "alpha"))

    def test_valid_names_pass(self) -> None:
        # Should not raise
        tool_registry.validate_tool_category_names(("execution", "web"))


class TestMergeLegacyFlagsEdgeCases:
    """Additional edge cases for merge_with_legacy_tool_flags."""

    def test_both_flags_false_preserves_input(self) -> None:
        result = tool_registry.merge_with_legacy_tool_flags(
            ("web",), enable_execution=False, enable_web=False
        )
        assert result == ("web",)

    def test_both_flags_true(self) -> None:
        result = tool_registry.merge_with_legacy_tool_flags(
            (), enable_execution=True, enable_web=True
        )
        assert result == ("execution", "web")

    def test_deduplication_with_flags(self) -> None:
        result = tool_registry.merge_with_legacy_tool_flags(
            ("execution", "web"), enable_execution=True, enable_web=True
        )
        assert result == ("execution", "web")
