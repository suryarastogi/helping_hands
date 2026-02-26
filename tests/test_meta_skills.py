"""Tests for helping_hands.lib.meta.skills."""

from __future__ import annotations

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
