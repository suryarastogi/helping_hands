"""Tests for helping_hands.lib.meta.skills."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta import skills as meta_skills


class TestMetaSkills:
    def test_available_skills_are_stable(self) -> None:
        assert meta_skills.available_skill_names() == (
            "execution",
            "web",
            "prd",
            "ralph",
        )

    def test_normalize_skill_selection_deduplicates_and_normalizes(self) -> None:
        assert meta_skills.normalize_skill_selection("execution, web,execution") == (
            "execution",
            "web",
        )
        assert meta_skills.normalize_skill_selection(["execution", "web"]) == (
            "execution",
            "web",
        )
        assert meta_skills.normalize_skill_selection(("enable_execution",)) == (
            "enable-execution",
        )

    def test_validate_skill_names_rejects_unknown(self) -> None:
        with pytest.raises(ValueError, match="unknown skill"):
            meta_skills.validate_skill_names(("unknown",))

    def test_merge_with_legacy_tool_flags(self) -> None:
        merged = meta_skills.merge_with_legacy_tool_flags(
            ("web",),
            enable_execution=True,
            enable_web=False,
        )
        assert merged == ("execution", "web")

    def test_resolve_skills_and_build_tool_runner_map(self) -> None:
        resolved = meta_skills.resolve_skills(("execution", "web"))
        names = [skill.name for skill in resolved]
        assert names == ["execution", "web"]

        mapping = meta_skills.build_tool_runner_map(resolved)
        assert set(mapping.keys()) == {
            "python.run_code",
            "python.run_script",
            "bash.run_script",
            "web.search",
            "web.browse",
        }

    def test_skill_name_for_tool_and_instruction_format(self) -> None:
        assert meta_skills.skill_name_for_tool("python.run_code") == "execution"
        assert meta_skills.skill_name_for_tool("web.search") == "web"
        assert meta_skills.skill_name_for_tool("unknown.tool") is None

        formatted = meta_skills.format_skill_instructions(
            meta_skills.resolve_skills(("execution",))
        )
        assert "Skill enabled: execution" in formatted
        assert "@@TOOL: python.run_code" in formatted

    def test_non_tool_skill_instructions_are_included(self) -> None:
        formatted = meta_skills.format_skill_instructions(
            meta_skills.resolve_skills(("ralph",))
        )
        assert "Skill enabled: ralph" in formatted
        assert "prd.json" in formatted


# ---------------------------------------------------------------------------
# Payload runner validation tests
# ---------------------------------------------------------------------------

_DUMMY_ROOT = Path("/tmp/test_repo")


class TestRunPythonCodeValidation:
    """Tests for _run_python_code() payload validation."""

    def test_missing_code_raises(self) -> None:
        with pytest.raises(ValueError, match="code must be a non-empty string"):
            meta_skills._run_python_code(_DUMMY_ROOT, {})

    def test_non_string_code_raises(self) -> None:
        with pytest.raises(ValueError, match="code must be a non-empty string"):
            meta_skills._run_python_code(_DUMMY_ROOT, {"code": 42})

    def test_empty_code_raises(self) -> None:
        with pytest.raises(ValueError, match="code must be a non-empty string"):
            meta_skills._run_python_code(_DUMMY_ROOT, {"code": "   "})

    def test_valid_code_calls_runner(self) -> None:
        mock_result = MagicMock()
        with patch(
            "helping_hands.lib.meta.skills.command_tools.run_python_code",
            return_value=mock_result,
        ) as mock_run:
            result = meta_skills._run_python_code(_DUMMY_ROOT, {"code": "print('hi')"})
        assert result is mock_result
        mock_run.assert_called_once()

    def test_invalid_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="timeout_s must be an integer"):
            meta_skills._run_python_code(
                _DUMMY_ROOT, {"code": "x", "timeout_s": "fast"}
            )

    def test_negative_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="timeout_s must be > 0"):
            meta_skills._run_python_code(_DUMMY_ROOT, {"code": "x", "timeout_s": -1})

    def test_bool_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="timeout_s must be an integer"):
            meta_skills._run_python_code(_DUMMY_ROOT, {"code": "x", "timeout_s": True})


class TestRunPythonScriptValidation:
    """Tests for _run_python_script() payload validation."""

    def test_missing_script_path_raises(self) -> None:
        with pytest.raises(ValueError, match="script_path must be a non-empty string"):
            meta_skills._run_python_script(_DUMMY_ROOT, {})

    def test_non_string_script_path_raises(self) -> None:
        with pytest.raises(ValueError, match="script_path must be a non-empty string"):
            meta_skills._run_python_script(_DUMMY_ROOT, {"script_path": 123})

    def test_empty_script_path_raises(self) -> None:
        with pytest.raises(ValueError, match="script_path must be a non-empty string"):
            meta_skills._run_python_script(_DUMMY_ROOT, {"script_path": ""})

    def test_valid_script_path_calls_runner(self) -> None:
        mock_result = MagicMock()
        with patch(
            "helping_hands.lib.meta.skills.command_tools.run_python_script",
            return_value=mock_result,
        ) as mock_run:
            result = meta_skills._run_python_script(
                _DUMMY_ROOT, {"script_path": "test.py"}
            )
        assert result is mock_result
        mock_run.assert_called_once()


class TestRunBashScriptValidation:
    """Tests for _run_bash_script() payload validation."""

    def test_both_none_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one of"):
            meta_skills._run_bash_script(_DUMMY_ROOT, {})

    def test_both_empty_strings_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one of"):
            meta_skills._run_bash_script(
                _DUMMY_ROOT, {"script_path": "", "inline_script": "  "}
            )

    def test_non_string_script_path_raises(self) -> None:
        with pytest.raises(ValueError, match="script_path must be a string"):
            meta_skills._run_bash_script(_DUMMY_ROOT, {"script_path": 42})

    def test_non_string_inline_script_raises(self) -> None:
        with pytest.raises(ValueError, match="inline_script must be a string"):
            meta_skills._run_bash_script(_DUMMY_ROOT, {"inline_script": 42})

    def test_valid_script_path_calls_runner(self) -> None:
        mock_result = MagicMock()
        with patch(
            "helping_hands.lib.meta.skills.command_tools.run_bash_script",
            return_value=mock_result,
        ) as mock_run:
            result = meta_skills._run_bash_script(
                _DUMMY_ROOT, {"script_path": "run.sh"}
            )
        assert result is mock_result
        mock_run.assert_called_once()

    def test_valid_inline_script_calls_runner(self) -> None:
        mock_result = MagicMock()
        with patch(
            "helping_hands.lib.meta.skills.command_tools.run_bash_script",
            return_value=mock_result,
        ) as mock_run:
            result = meta_skills._run_bash_script(
                _DUMMY_ROOT, {"inline_script": "echo hi"}
            )
        assert result is mock_result
        mock_run.assert_called_once()


class TestRunWebSearchValidation:
    """Tests for _run_web_search() payload validation."""

    def test_missing_query_raises(self) -> None:
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            meta_skills._run_web_search(_DUMMY_ROOT, {})

    def test_non_string_query_raises(self) -> None:
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            meta_skills._run_web_search(_DUMMY_ROOT, {"query": 42})

    def test_empty_query_raises(self) -> None:
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            meta_skills._run_web_search(_DUMMY_ROOT, {"query": "   "})

    def test_valid_query_calls_runner(self) -> None:
        mock_result = MagicMock()
        with patch(
            "helping_hands.lib.meta.skills.web_tools.search_web",
            return_value=mock_result,
        ) as mock_search:
            result = meta_skills._run_web_search(_DUMMY_ROOT, {"query": "python docs"})
        assert result is mock_result
        mock_search.assert_called_once()


class TestRunWebBrowseValidation:
    """Tests for _run_web_browse() payload validation."""

    def test_missing_url_raises(self) -> None:
        with pytest.raises(ValueError, match="url must be a non-empty string"):
            meta_skills._run_web_browse(_DUMMY_ROOT, {})

    def test_non_string_url_raises(self) -> None:
        with pytest.raises(ValueError, match="url must be a non-empty string"):
            meta_skills._run_web_browse(_DUMMY_ROOT, {"url": 42})

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="url must be a non-empty string"):
            meta_skills._run_web_browse(_DUMMY_ROOT, {"url": ""})

    def test_valid_url_calls_runner(self) -> None:
        mock_result = MagicMock()
        with patch(
            "helping_hands.lib.meta.skills.web_tools.browse_url",
            return_value=mock_result,
        ) as mock_browse:
            result = meta_skills._run_web_browse(
                _DUMMY_ROOT, {"url": "https://example.com"}
            )
        assert result is mock_result
        mock_browse.assert_called_once()


class TestParseHelpers:
    """Tests for internal payload parsing helpers."""

    def test_parse_str_list_valid(self) -> None:
        assert meta_skills._parse_str_list({"args": ["a", "b"]}, key="args") == [
            "a",
            "b",
        ]

    def test_parse_str_list_none_returns_empty(self) -> None:
        assert meta_skills._parse_str_list({"args": None}, key="args") == []

    def test_parse_str_list_missing_returns_empty(self) -> None:
        assert meta_skills._parse_str_list({}, key="args") == []

    def test_parse_str_list_not_list_raises(self) -> None:
        with pytest.raises(ValueError, match="args must be a list"):
            meta_skills._parse_str_list({"args": "not-a-list"}, key="args")

    def test_parse_str_list_non_string_element_raises(self) -> None:
        with pytest.raises(ValueError, match="args must contain only strings"):
            meta_skills._parse_str_list({"args": [1, 2]}, key="args")

    def test_parse_positive_int_default(self) -> None:
        assert meta_skills._parse_positive_int({}, key="x", default=10) == 10

    def test_parse_positive_int_provided(self) -> None:
        assert meta_skills._parse_positive_int({"x": 5}, key="x", default=10) == 5

    def test_parse_positive_int_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="x must be > 0"):
            meta_skills._parse_positive_int({"x": 0}, key="x", default=10)

    def test_parse_positive_int_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="x must be an integer"):
            meta_skills._parse_positive_int({"x": True}, key="x", default=10)

    def test_parse_optional_str_present(self) -> None:
        assert meta_skills._parse_optional_str({"k": "val"}, key="k") == "val"

    def test_parse_optional_str_missing(self) -> None:
        assert meta_skills._parse_optional_str({}, key="k") is None

    def test_parse_optional_str_empty_returns_none(self) -> None:
        assert meta_skills._parse_optional_str({"k": "  "}, key="k") is None

    def test_parse_optional_str_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="k must be a string"):
            meta_skills._parse_optional_str({"k": 42}, key="k")
