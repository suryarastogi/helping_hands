"""Tests for registry public API: selection, validation, resolution, and formatting.

Protects the tool selection pipeline that both iterative hands and CLI hands
rely on to configure runtime tools. These pure functions normalize user input,
validate category names, resolve categories to specs, merge legacy boolean
flags, and produce prompt-ready instructions. A regression here would silently
break tool dispatch for all hand types — e.g. ``normalize_tool_selection``
dropping a valid category would disable tools without any error, or
``validate_tool_category_names`` failing to reject unknown names would cause
a KeyError deep in the hand execution loop.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.meta.tools.registry import (
    ToolCategory,
    ToolSpec,
    _normalize_and_deduplicate,
    available_tool_category_names,
    build_tool_runner_map,
    category_name_for_tool,
    format_tool_instructions,
    format_tool_instructions_for_cli,
    merge_with_legacy_tool_flags,
    normalize_tool_selection,
    resolve_tool_categories,
    validate_tool_category_names,
)

# ---------------------------------------------------------------------------
# available_tool_category_names
# ---------------------------------------------------------------------------


class TestAvailableToolCategoryNames:
    def test_returns_tuple(self) -> None:
        result = available_tool_category_names()
        assert isinstance(result, tuple)

    def test_contains_execution_and_web(self) -> None:
        names = available_tool_category_names()
        assert "execution" in names
        assert "web" in names

    def test_no_empty_names(self) -> None:
        for name in available_tool_category_names():
            assert name.strip()


# ---------------------------------------------------------------------------
# normalize_tool_selection
# ---------------------------------------------------------------------------


class TestNormalizeToolSelection:
    def test_none_returns_empty(self) -> None:
        assert normalize_tool_selection(None) == ()

    def test_comma_separated_string(self) -> None:
        result = normalize_tool_selection("execution,web")
        assert result == ("execution", "web")

    def test_list_input(self) -> None:
        result = normalize_tool_selection(["execution", "web"])
        assert result == ("execution", "web")

    def test_tuple_input(self) -> None:
        result = normalize_tool_selection(("web", "execution"))
        assert result == ("web", "execution")

    def test_deduplication_preserves_order(self) -> None:
        result = normalize_tool_selection("web,execution,web")
        assert result == ("web", "execution")

    def test_case_normalization(self) -> None:
        result = normalize_tool_selection("EXECUTION,Web")
        assert result == ("execution", "web")

    def test_underscore_to_hyphen(self) -> None:
        result = normalize_tool_selection("my_tool")
        assert result == ("my-tool",)

    def test_whitespace_stripping(self) -> None:
        result = normalize_tool_selection("  execution , web  ")
        assert result == ("execution", "web")

    def test_empty_string_returns_empty(self) -> None:
        assert normalize_tool_selection("") == ()

    def test_empty_list_returns_empty(self) -> None:
        assert normalize_tool_selection([]) == ()

    def test_comma_only_string(self) -> None:
        assert normalize_tool_selection(",,,") == ()


# ---------------------------------------------------------------------------
# _normalize_and_deduplicate
# ---------------------------------------------------------------------------


class TestNormalizeAndDeduplicate:
    def test_rejects_int(self) -> None:
        with pytest.raises(TypeError, match="must be a string, list, or tuple"):
            _normalize_and_deduplicate(42, label="tools")  # type: ignore[arg-type]

    def test_rejects_dict(self) -> None:
        with pytest.raises(TypeError, match="must be a string, list, or tuple"):
            _normalize_and_deduplicate({"a": 1}, label="tools")  # type: ignore[arg-type]

    def test_rejects_non_string_in_list(self) -> None:
        with pytest.raises(ValueError, match="must contain only strings"):
            _normalize_and_deduplicate([123], label="tools")  # type: ignore[list-item]

    def test_label_appears_in_error(self) -> None:
        with pytest.raises(TypeError, match="backends"):
            _normalize_and_deduplicate(42, label="backends")  # type: ignore[arg-type]

    def test_list_with_commas_inside_elements(self) -> None:
        """Elements containing commas are split further."""
        result = _normalize_and_deduplicate(["a,b", "c"], label="tools")
        assert result == ("a", "b", "c")


# ---------------------------------------------------------------------------
# validate_tool_category_names
# ---------------------------------------------------------------------------


class TestValidateToolCategoryNames:
    def test_valid_names_pass(self) -> None:
        validate_tool_category_names(("execution", "web"))

    def test_empty_tuple_passes(self) -> None:
        validate_tool_category_names(())

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(ValueError, match=r"unknown tool.*nonexistent"):
            validate_tool_category_names(("nonexistent",))

    def test_mixed_valid_and_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match=r"unknown tool.*bad"):
            validate_tool_category_names(("execution", "bad"))

    def test_error_lists_available(self) -> None:
        with pytest.raises(ValueError, match="available:"):
            validate_tool_category_names(("nope",))


# ---------------------------------------------------------------------------
# resolve_tool_categories
# ---------------------------------------------------------------------------


class TestResolveToolCategories:
    def test_resolves_execution(self) -> None:
        cats = resolve_tool_categories(("execution",))
        assert len(cats) == 1
        assert isinstance(cats[0], ToolCategory)
        assert cats[0].name == "execution"

    def test_resolves_multiple(self) -> None:
        cats = resolve_tool_categories(("execution", "web"))
        assert len(cats) == 2
        names = [c.name for c in cats]
        assert names == ["execution", "web"]

    def test_empty_returns_empty(self) -> None:
        assert resolve_tool_categories(()) == ()

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown tool"):
            resolve_tool_categories(("nope",))

    def test_categories_have_tools(self) -> None:
        cats = resolve_tool_categories(("execution",))
        assert len(cats[0].tools) > 0
        assert all(isinstance(t, ToolSpec) for t in cats[0].tools)


# ---------------------------------------------------------------------------
# merge_with_legacy_tool_flags
# ---------------------------------------------------------------------------


class TestMergeWithLegacyToolFlags:
    def test_no_flags_passthrough(self) -> None:
        result = merge_with_legacy_tool_flags(
            ("web",), enable_execution=False, enable_web=False
        )
        assert result == ("web",)

    def test_execution_flag_prepends(self) -> None:
        result = merge_with_legacy_tool_flags(
            ("web",), enable_execution=True, enable_web=False
        )
        assert result[0] == "execution"
        assert "web" in result

    def test_web_flag_appends(self) -> None:
        result = merge_with_legacy_tool_flags(
            ("execution",), enable_execution=False, enable_web=True
        )
        assert "web" in result
        assert "execution" in result

    def test_both_flags_dedup(self) -> None:
        result = merge_with_legacy_tool_flags(
            ("execution", "web"), enable_execution=True, enable_web=True
        )
        assert result == ("execution", "web")

    def test_empty_with_both_flags(self) -> None:
        result = merge_with_legacy_tool_flags(
            (), enable_execution=True, enable_web=True
        )
        assert "execution" in result
        assert "web" in result


# ---------------------------------------------------------------------------
# build_tool_runner_map
# ---------------------------------------------------------------------------


class TestBuildToolRunnerMap:
    def test_empty_categories(self) -> None:
        assert build_tool_runner_map(()) == {}

    def test_execution_tools_present(self) -> None:
        cats = resolve_tool_categories(("execution",))
        mapping = build_tool_runner_map(cats)
        assert "python.run_code" in mapping
        assert "python.run_script" in mapping
        assert "bash.run_script" in mapping
        assert callable(mapping["python.run_code"])

    def test_web_tools_present(self) -> None:
        cats = resolve_tool_categories(("web",))
        mapping = build_tool_runner_map(cats)
        assert "web.search" in mapping
        assert "web.browse" in mapping

    def test_all_categories(self) -> None:
        cats = resolve_tool_categories(("execution", "web"))
        mapping = build_tool_runner_map(cats)
        assert len(mapping) == 5  # 3 execution + 2 web


# ---------------------------------------------------------------------------
# category_name_for_tool
# ---------------------------------------------------------------------------


class TestCategoryNameForTool:
    def test_known_execution_tool(self) -> None:
        assert category_name_for_tool("python.run_code") == "execution"

    def test_known_web_tool(self) -> None:
        assert category_name_for_tool("web.search") == "web"

    def test_unknown_returns_none(self) -> None:
        assert category_name_for_tool("nonexistent.tool") is None

    def test_empty_string_returns_none(self) -> None:
        assert category_name_for_tool("") is None


# ---------------------------------------------------------------------------
# format_tool_instructions
# ---------------------------------------------------------------------------


class TestFormatToolInstructions:
    def test_empty_categories(self) -> None:
        result = format_tool_instructions(())
        assert result == "No dynamic tools enabled for this run."

    def test_execution_category_has_tool_blocks(self) -> None:
        cats = resolve_tool_categories(("execution",))
        result = format_tool_instructions(cats)
        assert "@@TOOL: python.run_code" in result
        assert "@@TOOL: python.run_script" in result
        assert "@@TOOL: bash.run_script" in result
        assert "```json" in result

    def test_web_category_has_tool_blocks(self) -> None:
        cats = resolve_tool_categories(("web",))
        result = format_tool_instructions(cats)
        assert "@@TOOL: web.search" in result
        assert "@@TOOL: web.browse" in result

    def test_execution_guidance_text(self) -> None:
        cats = resolve_tool_categories(("execution",))
        result = format_tool_instructions(cats)
        assert "deterministic local validation" in result

    def test_web_guidance_text(self) -> None:
        cats = resolve_tool_categories(("web",))
        result = format_tool_instructions(cats)
        assert "targeted research" in result

    def test_mixed_categories(self) -> None:
        cats = resolve_tool_categories(("execution", "web"))
        result = format_tool_instructions(cats)
        assert "python.run_code" in result
        assert "web.search" in result


# ---------------------------------------------------------------------------
# format_tool_instructions_for_cli
# ---------------------------------------------------------------------------


class TestFormatToolInstructionsForCli:
    def test_empty_categories(self) -> None:
        assert format_tool_instructions_for_cli(()) == ""

    def test_execution_guidance(self) -> None:
        cats = resolve_tool_categories(("execution",))
        result = format_tool_instructions_for_cli(cats)
        assert "python.run_code" in result
        assert "bash.run_script" in result
        # CLI variant should NOT have @@TOOL blocks
        assert "@@TOOL" not in result

    def test_web_guidance(self) -> None:
        cats = resolve_tool_categories(("web",))
        result = format_tool_instructions_for_cli(cats)
        assert "web.search" in result
        assert "web.browse" in result

    def test_includes_category_header(self) -> None:
        cats = resolve_tool_categories(("execution",))
        result = format_tool_instructions_for_cli(cats)
        assert "Tool category enabled: execution" in result
