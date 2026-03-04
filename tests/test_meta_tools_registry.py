"""Tests for helping_hands.lib.meta.tools.registry."""

from __future__ import annotations

import pytest

from helping_hands.lib.meta.tools import registry as tool_registry
from helping_hands.lib.meta.tools.registry import (
    _parse_optional_str,
    _parse_positive_int,
    _parse_str_list,
)


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


# ---------------------------------------------------------------------------
# Payload parser edge-case tests (TD-002)
# ---------------------------------------------------------------------------


class TestParseStrList:
    """Edge cases for _parse_str_list."""

    def test_missing_key_returns_empty(self) -> None:
        assert _parse_str_list({}, key="items") == []

    def test_none_value_returns_empty(self) -> None:
        assert _parse_str_list({"items": None}, key="items") == []

    def test_valid_list(self) -> None:
        assert _parse_str_list({"items": ["a", "b"]}, key="items") == ["a", "b"]

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a list"):
            _parse_str_list({"items": "not-a-list"}, key="items")

    def test_non_string_item_raises(self) -> None:
        with pytest.raises(ValueError, match="must contain only strings"):
            _parse_str_list({"items": ["ok", 123]}, key="items")

    def test_empty_list(self) -> None:
        assert _parse_str_list({"items": []}, key="items") == []


class TestParsePositiveInt:
    """Edge cases for _parse_positive_int."""

    def test_missing_key_uses_default(self) -> None:
        assert _parse_positive_int({}, key="n", default=42) == 42

    def test_valid_int(self) -> None:
        assert _parse_positive_int({"n": 5}, key="n", default=1) == 5

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            _parse_positive_int({"n": 0}, key="n", default=1)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            _parse_positive_int({"n": -3}, key="n", default=1)

    def test_bool_raises(self) -> None:
        """Booleans are subclasses of int but should be rejected."""
        with pytest.raises(ValueError, match="must be an integer"):
            _parse_positive_int({"n": True}, key="n", default=1)

    def test_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            _parse_positive_int({"n": "5"}, key="n", default=1)

    def test_float_raises(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            _parse_positive_int({"n": 3.14}, key="n", default=1)


class TestParseOptionalStr:
    """Edge cases for _parse_optional_str."""

    def test_missing_key_returns_none(self) -> None:
        assert _parse_optional_str({}, key="s") is None

    def test_none_value_returns_none(self) -> None:
        assert _parse_optional_str({"s": None}, key="s") is None

    def test_valid_string(self) -> None:
        assert _parse_optional_str({"s": "hello"}, key="s") == "hello"

    def test_whitespace_only_returns_none(self) -> None:
        assert _parse_optional_str({"s": "   "}, key="s") is None

    def test_string_is_stripped(self) -> None:
        assert _parse_optional_str({"s": "  hi  "}, key="s") == "hi"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            _parse_optional_str({"s": 123}, key="s")

    def test_empty_string_returns_none(self) -> None:
        assert _parse_optional_str({"s": ""}, key="s") is None


class TestNormalizeToolSelectionEdgeCases:
    """Additional edge cases for normalize_tool_selection."""

    def test_tuple_input(self) -> None:
        result = tool_registry.normalize_tool_selection(("execution", "web"))
        assert result == ("execution", "web")

    def test_underscores_normalized_to_hyphens(self) -> None:
        result = tool_registry.normalize_tool_selection("some_tool")
        assert result == ("some-tool",)

    def test_mixed_case_normalized(self) -> None:
        result = tool_registry.normalize_tool_selection("Execution")
        assert result == ("execution",)

    def test_empty_string_returns_empty(self) -> None:
        result = tool_registry.normalize_tool_selection("")
        assert result == ()

    def test_commas_only_returns_empty(self) -> None:
        result = tool_registry.normalize_tool_selection(",,,")
        assert result == ()

    def test_non_string_item_in_list_raises(self) -> None:
        with pytest.raises(ValueError, match="must contain only strings"):
            tool_registry.normalize_tool_selection([123])  # type: ignore[list-item]


class TestRunnerValidation:
    """Tests for runner wrapper input validation."""

    def test_run_python_code_empty_code_raises(self) -> None:
        from pathlib import Path

        from helping_hands.lib.meta.tools.registry import _run_python_code

        with pytest.raises(ValueError, match="code must be a non-empty string"):
            _run_python_code(Path("/tmp"), {"code": ""})

    def test_run_python_code_missing_code_raises(self) -> None:
        from pathlib import Path

        from helping_hands.lib.meta.tools.registry import _run_python_code

        with pytest.raises(ValueError, match="code must be a non-empty string"):
            _run_python_code(Path("/tmp"), {})

    def test_run_python_script_empty_path_raises(self) -> None:
        from pathlib import Path

        from helping_hands.lib.meta.tools.registry import _run_python_script

        with pytest.raises(ValueError, match="script_path must be a non-empty"):
            _run_python_script(Path("/tmp"), {"script_path": "  "})

    def test_run_web_search_empty_query_raises(self) -> None:
        from pathlib import Path

        from helping_hands.lib.meta.tools.registry import _run_web_search

        with pytest.raises(ValueError, match="query must be a non-empty"):
            _run_web_search(Path("/tmp"), {"query": ""})

    def test_run_web_browse_missing_url_raises(self) -> None:
        from pathlib import Path

        from helping_hands.lib.meta.tools.registry import _run_web_browse

        with pytest.raises(ValueError, match="url must be a non-empty"):
            _run_web_browse(Path("/tmp"), {})

    def test_run_bash_script_non_string_path_raises(self) -> None:
        from pathlib import Path

        from helping_hands.lib.meta.tools.registry import _run_bash_script

        with pytest.raises(ValueError, match="script_path must be a string"):
            _run_bash_script(Path("/tmp"), {"script_path": 123})
