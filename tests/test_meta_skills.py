"""Tests for helping_hands.lib.meta.skills."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from helping_hands.lib.meta import skills as meta_skills


class TestMetaSkills:
    def test_available_skills_are_stable(self) -> None:
        assert meta_skills.available_skill_names() == (
            "execution",
            "prd",
            "ralph",
            "web",
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

    def test_resolve_skills(self) -> None:
        resolved = meta_skills.resolve_skills(("execution", "prd"))
        names = [skill.name for skill in resolved]
        assert names == ["execution", "prd"]

    def test_skill_spec_has_content(self) -> None:
        resolved = meta_skills.resolve_skills(("prd",))
        assert len(resolved) == 1
        assert "clarifying questions" in resolved[0].content

    def test_format_skill_knowledge(self) -> None:
        resolved = meta_skills.resolve_skills(("prd",))
        formatted = meta_skills.format_skill_knowledge(resolved)
        assert "Skill enabled: prd" in formatted
        assert "clarifying questions" in formatted

    def test_format_skill_knowledge_empty(self) -> None:
        assert meta_skills.format_skill_knowledge(()) == ""

    def test_stage_skill_catalog(self) -> None:
        resolved = meta_skills.resolve_skills(("prd", "ralph"))
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "skills"
            meta_skills.stage_skill_catalog(resolved, target)
            assert (target / "prd.md").is_file()
            assert (target / "ralph.md").is_file()
            assert "clarifying questions" in (target / "prd.md").read_text()

    def test_format_skill_catalog_instructions(self) -> None:
        resolved = meta_skills.resolve_skills(("prd",))
        catalog_dir = Path("/tmp/skills")
        formatted = meta_skills.format_skill_catalog_instructions(resolved, catalog_dir)
        assert "prd" in formatted
        assert str(catalog_dir / "prd.md") in formatted

    def test_format_skill_catalog_instructions_no_dir(self) -> None:
        resolved = meta_skills.resolve_skills(("prd",))
        formatted = meta_skills.format_skill_catalog_instructions(resolved, None)
        assert "prd" in formatted

    def test_format_skill_catalog_instructions_empty(self) -> None:
        assert meta_skills.format_skill_catalog_instructions((), None) == ""
