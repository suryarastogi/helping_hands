"""v334 — Additional registry.py coverage tests.

Covers: _parse_required_str direct tests, _normalize_and_deduplicate edge cases
(TypeError, tuple input, underscore normalization), _run_bash_script both/neither
paths, merge_with_legacy_tool_flags variations, format_tool_instructions web
category, and validate_tool_category_names valid case.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta.tools.registry import (
    _normalize_and_deduplicate,
    _parse_required_str,
    _run_bash_script,
    build_tool_runner_map,
    format_tool_instructions,
    merge_with_legacy_tool_flags,
    resolve_tool_categories,
    validate_tool_category_names,
)

# ---------------------------------------------------------------------------
# _parse_required_str (direct unit tests)
# ---------------------------------------------------------------------------


class TestParseRequiredStr:
    def test_returns_non_empty_string(self) -> None:
        assert _parse_required_str({"k": "hello"}, key="k") == "hello"

    def test_rejects_missing_key(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _parse_required_str({}, key="k")

    def test_rejects_none_value(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _parse_required_str({"k": None}, key="k")

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _parse_required_str({"k": ""}, key="k")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _parse_required_str({"k": "   "}, key="k")

    def test_rejects_int_value(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _parse_required_str({"k": 42}, key="k")

    def test_preserves_whitespace_in_value(self) -> None:
        """_parse_required_str does NOT strip — caller decides."""
        assert _parse_required_str({"k": "  hello  "}, key="k") == "  hello  "


# ---------------------------------------------------------------------------
# _normalize_and_deduplicate
# ---------------------------------------------------------------------------


class TestNormalizeAndDeduplicate:
    def test_none_returns_empty(self) -> None:
        assert _normalize_and_deduplicate(None, label="t") == ()

    def test_string_input_splits_on_comma(self) -> None:
        result = _normalize_and_deduplicate("a,b,c", label="t")
        assert result == ("a", "b", "c")

    def test_list_input(self) -> None:
        result = _normalize_and_deduplicate(["alpha", "beta"], label="t")
        assert result == ("alpha", "beta")

    def test_tuple_input(self) -> None:
        result = _normalize_and_deduplicate(("alpha", "beta"), label="t")
        assert result == ("alpha", "beta")

    def test_deduplicates_preserving_order(self) -> None:
        result = _normalize_and_deduplicate("a,b,a,c,b", label="t")
        assert result == ("a", "b", "c")

    def test_lowercases_values(self) -> None:
        result = _normalize_and_deduplicate("FOO,Bar", label="t")
        assert result == ("foo", "bar")

    def test_replaces_underscores_with_hyphens(self) -> None:
        result = _normalize_and_deduplicate("my_tool", label="t")
        assert result == ("my-tool",)

    def test_rejects_int_type(self) -> None:
        with pytest.raises(TypeError, match="must be a string, list, or tuple"):
            _normalize_and_deduplicate(42, label="tools")  # type: ignore[arg-type]

    def test_rejects_dict_type(self) -> None:
        with pytest.raises(TypeError, match="must be a string, list, or tuple"):
            _normalize_and_deduplicate({"a": 1}, label="tools")  # type: ignore[arg-type]

    def test_rejects_non_string_in_list(self) -> None:
        with pytest.raises(ValueError, match="must contain only strings"):
            _normalize_and_deduplicate([123], label="tools")  # type: ignore[list-item]

    def test_list_with_comma_separated_values_splits(self) -> None:
        """List elements containing commas are split further."""
        result = _normalize_and_deduplicate(["a,b", "c"], label="t")
        assert result == ("a", "b", "c")

    def test_empty_tokens_after_split_skipped(self) -> None:
        result = _normalize_and_deduplicate("a,,b, ,c", label="t")
        assert result == ("a", "b", "c")


# ---------------------------------------------------------------------------
# _run_bash_script edge cases
# ---------------------------------------------------------------------------


class TestRunBashScriptEdgeCases:
    def test_rejects_both_script_path_and_inline(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            _run_bash_script(
                tmp_path,
                {"script_path": "run.sh", "inline_script": "echo hi"},
            )

    def test_rejects_neither_script_path_nor_inline(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            _run_bash_script(tmp_path, {})

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_bash_script")
    def test_inline_with_custom_args_and_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = MagicMock()
        _run_bash_script(
            tmp_path,
            {
                "inline_script": "ls -la",
                "args": ["-v"],
                "timeout_s": 120,
                "cwd": "subdir",
            },
        )
        mock_run.assert_called_once_with(
            tmp_path,
            script_path=None,
            inline_script="ls -la",
            args=["-v"],
            timeout_s=120,
            cwd="subdir",
        )


# ---------------------------------------------------------------------------
# merge_with_legacy_tool_flags variations
# ---------------------------------------------------------------------------


class TestMergeWithLegacyToolFlags:
    def test_both_flags_false_preserves_input(self) -> None:
        result = merge_with_legacy_tool_flags(
            ("execution",), enable_execution=False, enable_web=False
        )
        assert result == ("execution",)

    def test_only_web_flag(self) -> None:
        result = merge_with_legacy_tool_flags(
            (), enable_execution=False, enable_web=True
        )
        assert result == ("web",)

    def test_both_flags_true_deduplicates(self) -> None:
        result = merge_with_legacy_tool_flags(
            ("execution", "web"), enable_execution=True, enable_web=True
        )
        assert result == ("execution", "web")

    def test_empty_input_both_flags(self) -> None:
        result = merge_with_legacy_tool_flags(
            (), enable_execution=True, enable_web=True
        )
        assert result == ("execution", "web")


# ---------------------------------------------------------------------------
# validate_tool_category_names
# ---------------------------------------------------------------------------


class TestValidateToolCategoryNames:
    def test_valid_names_no_error(self) -> None:
        validate_tool_category_names(("execution", "web"))

    def test_empty_tuple_no_error(self) -> None:
        validate_tool_category_names(())

    def test_unknown_lists_available(self) -> None:
        with pytest.raises(ValueError, match="available: execution, web"):
            validate_tool_category_names(("nope",))

    def test_mixed_valid_and_unknown(self) -> None:
        with pytest.raises(ValueError, match=r"unknown tool.*nope"):
            validate_tool_category_names(("execution", "nope"))


# ---------------------------------------------------------------------------
# format_tool_instructions — web category branch
# ---------------------------------------------------------------------------


class TestFormatToolInstructionsWebCategory:
    def test_web_category_guidance(self) -> None:
        resolved = resolve_tool_categories(("web",))
        result = format_tool_instructions(resolved)
        assert "Tool category enabled: web" in result
        assert "@@TOOL: web.search" in result
        assert "@@TOOL: web.browse" in result
        assert "targeted research" in result

    def test_both_categories(self) -> None:
        resolved = resolve_tool_categories(("execution", "web"))
        result = format_tool_instructions(resolved)
        assert "execution" in result
        assert "web" in result
        assert "@@TOOL: python.run_code" in result
        assert "@@TOOL: web.search" in result


# ---------------------------------------------------------------------------
# resolve_tool_categories + build_tool_runner_map
# ---------------------------------------------------------------------------


class TestResolveAndBuild:
    def test_single_category(self) -> None:
        cats = resolve_tool_categories(("web",))
        assert len(cats) == 1
        assert cats[0].name == "web"
        runners = build_tool_runner_map(cats)
        assert set(runners.keys()) == {"web.search", "web.browse"}

    def test_empty_selection(self) -> None:
        cats = resolve_tool_categories(())
        assert cats == ()
        runners = build_tool_runner_map(cats)
        assert runners == {}
