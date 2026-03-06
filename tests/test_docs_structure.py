"""Tests that documentation indexes stay in sync with actual files.

These tests catch common drift: a new design doc is added but not listed in
the index, or a completed plan is missing from PLANS.md.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Repo root is two levels up from tests/
REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"


class TestDesignDocsIndex:
    """Every .md file in docs/design-docs/ must be listed in the index."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "index.md").read_text()

    @pytest.fixture()
    def design_doc_files(self) -> list[str]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f.name for f in dd.glob("*.md") if f.name != "index.md")

    def test_all_design_docs_listed_in_index(
        self, index_text: str, design_doc_files: list[str]
    ) -> None:
        for filename in design_doc_files:
            assert filename in index_text, (
                f"Design doc '{filename}' exists in docs/design-docs/ "
                f"but is not referenced in design-docs/index.md"
            )

    def test_index_has_no_stale_links(
        self, index_text: str, design_doc_files: list[str]
    ) -> None:
        """Every .md link in the index must point to an actual file."""
        linked = re.findall(r"\(([^)]+\.md)\)", index_text)
        for link in linked:
            assert link in design_doc_files, (
                f"design-docs/index.md references '{link}' but no such file exists"
            )


class TestPlansTracking:
    """Every file in exec-plans/completed/ must be referenced in PLANS.md."""

    @pytest.fixture()
    def plans_text(self) -> str:
        return (DOCS_DIR / "PLANS.md").read_text()

    @pytest.fixture()
    def completed_plan_files(self) -> list[str]:
        completed = DOCS_DIR / "exec-plans" / "completed"
        if not completed.exists():
            return []
        return sorted(f.name for f in completed.glob("*.md"))

    def test_all_completed_plans_referenced(
        self, plans_text: str, completed_plan_files: list[str]
    ) -> None:
        for filename in completed_plan_files:
            assert filename in plans_text, (
                f"Completed plan '{filename}' exists in exec-plans/completed/ "
                f"but is not referenced in PLANS.md"
            )


class TestDocsIndexCompleteness:
    """docs/index.md should reference all top-level docs/*.md files."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    @pytest.fixture()
    def top_level_doc_files(self) -> list[str]:
        return sorted(f.name for f in DOCS_DIR.glob("*.md") if f.name != "index.md")

    def test_all_top_level_docs_referenced(
        self, index_text: str, top_level_doc_files: list[str]
    ) -> None:
        for filename in top_level_doc_files:
            assert filename in index_text, (
                f"Top-level doc '{filename}' exists in docs/ "
                f"but is not referenced in docs/index.md"
            )


class TestProductSpecsIndex:
    """Every .md file in docs/product-specs/ must be listed in the index."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "product-specs" / "index.md").read_text()

    @pytest.fixture()
    def spec_files(self) -> list[str]:
        ps = DOCS_DIR / "product-specs"
        return sorted(f.name for f in ps.glob("*.md") if f.name != "index.md")

    def test_all_specs_listed_in_index(
        self, index_text: str, spec_files: list[str]
    ) -> None:
        for filename in spec_files:
            assert filename in index_text, (
                f"Product spec '{filename}' exists in docs/product-specs/ "
                f"but is not referenced in product-specs/index.md"
            )

    def test_index_has_no_stale_links(
        self, index_text: str, spec_files: list[str]
    ) -> None:
        """Every .md link in the index must point to an actual file."""
        linked = re.findall(r"\(([^)]+\.md)\)", index_text)
        for link in linked:
            assert link in spec_files, (
                f"product-specs/index.md references '{link}' but no such file exists"
            )


class TestRootLevelDocsExist:
    """Key root-level docs must exist."""

    @pytest.mark.parametrize(
        "filename",
        ["ARCHITECTURE.md", "AGENTS.md", "CLAUDE.md", "README.md"],
    )
    def test_root_doc_exists(self, filename: str) -> None:
        path = REPO_ROOT / filename
        assert path.is_file(), f"Expected root-level doc '{filename}' to exist"


class TestReferenceFilesNonEmpty:
    """Every file in docs/references/ should have content."""

    @pytest.fixture()
    def reference_files(self) -> list[Path]:
        refs = DOCS_DIR / "references"
        if not refs.exists():
            return []
        return sorted(refs.iterdir())

    def test_all_reference_files_non_empty(self, reference_files: list[Path]) -> None:
        assert len(reference_files) > 0, "docs/references/ should have files"
        for ref_file in reference_files:
            content = ref_file.read_text()
            assert len(content.strip()) > 0, (
                f"Reference file '{ref_file.name}' is empty"
            )


class TestTechDebtTrackerModuleRefs:
    """Active tech debt items should reference modules that exist in source."""

    @pytest.fixture()
    def active_items(self) -> list[str]:
        tracker = DOCS_DIR / "exec-plans" / "tech-debt-tracker.md"
        text = tracker.read_text()
        # Parse rows between "## Active items" and "## Resolved items"
        in_active = False
        rows: list[str] = []
        for line in text.splitlines():
            if line.startswith("## Active items"):
                in_active = True
                continue
            if line.startswith("## Resolved items"):
                break
            if in_active and line.startswith("|") and "---" not in line:
                rows.append(line)
        # Skip header row
        return rows[1:] if rows else []

    def test_active_items_reference_real_modules(self, active_items: list[str]) -> None:
        """Each active item with a backticked module name should map to a real file."""
        src_root = REPO_ROOT / "src" / "helping_hands"
        for row in active_items:
            # Extract backticked module references like `cli/claude.py`
            modules = re.findall(r"`([^`]+\.py)`", row)
            for mod in modules:
                # Resolve relative module paths
                candidates = list(src_root.rglob(mod))
                assert len(candidates) > 0, (
                    f"Tech debt tracker references `{mod}` but no matching "
                    f"file found under src/helping_hands/"
                )
