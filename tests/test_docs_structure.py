"""Tests that documentation indexes stay in sync with actual files.

These tests catch common drift: a new design doc is added but not listed in
the index, or a completed plan is missing from PLANS.md.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

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


class TestApiDocsReferencesExist:
    """API doc links in docs/index.md must point to existing files."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    def test_api_reference_links_resolve(self, index_text: str) -> None:
        """Every (api/...) link in the API Reference section must exist."""
        api_links = re.findall(r"\(api/([^)]+\.md)\)", index_text)
        assert len(api_links) > 0, "docs/index.md should have API reference links"
        for link in api_links:
            path = DOCS_DIR / "api" / link
            assert path.is_file(), (
                f"docs/index.md references api/{link} but the file does not exist"
            )

    def test_api_docs_are_non_empty(self) -> None:
        """Every .md file under docs/api/ should have content."""
        api_dir = DOCS_DIR / "api"
        api_files = sorted(api_dir.rglob("*.md"))
        assert len(api_files) > 0, "docs/api/ should have files"
        for api_file in api_files:
            content = api_file.read_text()
            assert len(content.strip()) > 0, (
                f"API doc '{api_file.relative_to(DOCS_DIR)}' is empty"
            )


class TestCompletedPlanStructure:
    """Completed exec plans should have required sections."""

    @pytest.fixture()
    def completed_plan_paths(self) -> list[Path]:
        completed = DOCS_DIR / "exec-plans" / "completed"
        if not completed.exists():
            return []
        return sorted(completed.glob("*.md"))

    def test_completed_plans_exist(self, completed_plan_paths: list[Path]) -> None:
        assert len(completed_plan_paths) > 0, (
            "exec-plans/completed/ should have at least one plan"
        )

    def test_versioned_plans_have_status(
        self, completed_plan_paths: list[Path]
    ) -> None:
        """Versioned plans (not date-consolidated) must have a Status field."""
        for plan_path in completed_plan_paths:
            # Date-consolidated files (2026-03-04.md) are summaries, skip them
            if re.match(r"\d{4}-\d{2}-\d{2}\.md$", plan_path.name):
                continue
            content = plan_path.read_text()
            assert "**Status:**" in content, (
                f"Completed plan '{plan_path.name}' is missing **Status:** field"
            )

    def test_versioned_plans_have_tasks_section(
        self, completed_plan_paths: list[Path]
    ) -> None:
        """Versioned plans must have a Tasks section."""
        for plan_path in completed_plan_paths:
            if re.match(r"\d{4}-\d{2}-\d{2}\.md$", plan_path.name):
                continue
            content = plan_path.read_text()
            assert "## Tasks" in content, (
                f"Completed plan '{plan_path.name}' is missing ## Tasks section"
            )

    def test_consolidated_plans_have_version_entries(
        self, completed_plan_paths: list[Path]
    ) -> None:
        """Date-consolidated plans should contain at least one version heading."""
        for plan_path in completed_plan_paths:
            if not re.match(r"\d{4}-\d{2}-\d{2}\.md$", plan_path.name):
                continue
            content = plan_path.read_text()
            # Match headings like "## v32 - ..." or "## Docs and Testing v2"
            version_headings = re.findall(r"^## .*v\d+", content, re.MULTILINE)
            assert len(version_headings) > 0, (
                f"Consolidated plan '{plan_path.name}' has no version entries"
            )


class TestDesignDocsIndexCount:
    """design-docs/index.md link count should match actual file count."""

    def test_link_count_matches_file_count(self) -> None:
        dd = DOCS_DIR / "design-docs"
        doc_files = [f for f in dd.glob("*.md") if f.name != "index.md"]
        index_text = (dd / "index.md").read_text()
        linked = re.findall(r"\(([^)]+\.md)\)", index_text)
        assert len(linked) == len(doc_files), (
            f"design-docs/index.md has {len(linked)} links "
            f"but {len(doc_files)} .md files exist (excluding index.md)"
        )


class TestArchitectureMdKeyPaths:
    """ARCHITECTURE.md key file paths should point to existing source files."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_key_file_paths_exist(self, arch_text: str) -> None:
        """Every path in the Key file paths table must resolve to a real file."""
        # Extract paths like `src/helping_hands/lib/config.py`
        paths = re.findall(r"`(src/helping_hands/[^`]+\.py)`", arch_text)
        assert len(paths) > 0, "ARCHITECTURE.md should list key file paths"
        for rel_path in paths:
            full = REPO_ROOT / rel_path
            assert full.is_file(), (
                f"ARCHITECTURE.md references '{rel_path}' but the file does not exist"
            )

    def test_hand_backend_table_modules_exist(self, arch_text: str) -> None:
        """Every module in the Hand backends table must exist."""
        # Extract the Hand backends table section
        in_table = False
        hand_modules: list[str] = []
        for line in arch_text.splitlines():
            if "## Hand backends" in line or "### 3. Hand backends" in line:
                in_table = True
                continue
            if in_table and line.startswith("###") and "Hand" not in line:
                break
            if in_table and line.startswith("|") and "---" not in line:
                # Extract backticked module names like `e2e.py`, `cli/codex.py`
                mods = re.findall(r"`((?:cli/)?[a-z_]+\.py)`", line)
                hand_modules.extend(mods)
        hand_dir = REPO_ROOT / "src" / "helping_hands" / "lib" / "hands" / "v1" / "hand"
        assert len(hand_modules) > 0, (
            "ARCHITECTURE.md hand backends table should have module references"
        )
        for mod in hand_modules:
            full = hand_dir / mod
            assert full.is_file(), (
                f"ARCHITECTURE.md hand table references '{mod}' "
                f"but no file at {full.relative_to(REPO_ROOT)}"
            )


class TestAgentsMdSections:
    """AGENTS.md must have required structural sections."""

    @pytest.fixture()
    def agents_text(self) -> str:
        return (REPO_ROOT / "AGENTS.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## Agent types",
            "## Coordination rules",
            "## Sandbox isolation",
            "## Scheduled agents",
            "## Communication between agents",
        ],
    )
    def test_required_section_exists(self, agents_text: str, section: str) -> None:
        assert section in agents_text, (
            f"AGENTS.md is missing required section '{section}'"
        )

    def test_agent_type_table_has_entries(self, agents_text: str) -> None:
        """The Agent types section should have a table with at least 3 rows."""
        # Find table rows (lines starting with |, excluding header separator)
        in_types = False
        rows = 0
        for line in agents_text.splitlines():
            if "## Agent types" in line:
                in_types = True
                continue
            if in_types and line.startswith("##"):
                break
            if in_types and line.startswith("|") and "---" not in line:
                rows += 1
        # Subtract header row
        data_rows = rows - 1 if rows > 0 else 0
        assert data_rows >= 3, (
            f"AGENTS.md Agent types table has {data_rows} data rows, expected >= 3"
        )


class TestDocsIndexLinkResolution:
    """docs/index.md documentation map links must resolve to actual files."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    def test_documentation_map_links_resolve(self, index_text: str) -> None:
        """Every relative link in the documentation map table must exist."""
        # Match links like (DESIGN.md), (../ARCHITECTURE.md), (design-docs/index.md)
        links = re.findall(r"\((\.\./[^)]+|[^)]+\.md)\)", index_text)
        assert len(links) > 0, "docs/index.md should have links in documentation map"
        for link in links:
            # Resolve relative to docs/
            target = REPO_ROOT / link[3:] if link.startswith("../") else DOCS_DIR / link
            assert target.exists(), (
                f"docs/index.md references '{link}' but the target does not exist"
            )

    def test_documentation_map_has_minimum_entries(self, index_text: str) -> None:
        """The documentation map table should have at least 8 entries."""
        # Count table data rows in the Documentation map section
        in_map = False
        rows = 0
        for line in index_text.splitlines():
            if "## Documentation map" in line:
                in_map = True
                continue
            if in_map and line.startswith("##"):
                break
            if in_map and line.startswith("|") and "---" not in line:
                rows += 1
        data_rows = rows - 1 if rows > 0 else 0
        assert data_rows >= 8, (
            f"docs/index.md documentation map has {data_rows} rows, expected >= 8"
        )


class TestClaudeMdSections:
    """CLAUDE.md must have required structural sections."""

    @pytest.fixture()
    def claude_text(self) -> str:
        return (REPO_ROOT / "CLAUDE.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## Build & Development Commands",
            "## Architecture",
            "## Code Conventions",
            "## Key Architectural Decisions",
            "## CI",
        ],
    )
    def test_required_section_exists(self, claude_text: str, section: str) -> None:
        assert section in claude_text, (
            f"CLAUDE.md is missing required section '{section}'"
        )

    def test_has_install_command(self, claude_text: str) -> None:
        """CLAUDE.md should document the uv sync install command."""
        assert "uv sync" in claude_text, (
            "CLAUDE.md should contain 'uv sync' install command"
        )

    def test_has_test_command(self, claude_text: str) -> None:
        """CLAUDE.md should document the pytest test command."""
        assert "uv run pytest" in claude_text, (
            "CLAUDE.md should contain 'uv run pytest' test command"
        )


class TestDesignMdSections:
    """DESIGN.md must have required structural sections."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## Guiding principles",
            "## Patterns",
            "## Anti-patterns to avoid",
        ],
    )
    def test_required_section_exists(self, design_text: str, section: str) -> None:
        assert section in design_text, (
            f"DESIGN.md is missing required section '{section}'"
        )


class TestSecurityMdSections:
    """SECURITY.md must have required structural sections."""

    @pytest.fixture()
    def security_text(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## Path traversal prevention",
            "## Token authentication",
            "## Subprocess execution",
        ],
    )
    def test_required_section_exists(self, security_text: str, section: str) -> None:
        assert section in security_text, (
            f"SECURITY.md is missing required section '{section}'"
        )


class TestReliabilityMdSections:
    """RELIABILITY.md must have required structural sections."""

    @pytest.fixture()
    def reliability_text(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## Error handling patterns",
            "## Heartbeat monitoring",
            "## Idempotency",
        ],
    )
    def test_required_section_exists(self, reliability_text: str, section: str) -> None:
        assert section in reliability_text, (
            f"RELIABILITY.md is missing required section '{section}'"
        )


class TestReadmeMdSections:
    """README.md must have required structural sections."""

    @pytest.fixture()
    def readme_text(self) -> str:
        return (REPO_ROOT / "README.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## Quick start",
            "## Project structure",
            "## Configuration",
            "## Development",
        ],
    )
    def test_required_section_exists(self, readme_text: str, section: str) -> None:
        assert section in readme_text, (
            f"README.md is missing required section '{section}'"
        )


class TestQualityScoreMdStructure:
    """QUALITY_SCORE.md must have required sections and tables."""

    @pytest.fixture()
    def quality_text(self) -> str:
        return (DOCS_DIR / "QUALITY_SCORE.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "### CI pipeline",
            "## Testing conventions",
            "## Coverage targets",
        ],
    )
    def test_required_section_exists(self, quality_text: str, section: str) -> None:
        assert section in quality_text, (
            f"QUALITY_SCORE.md is missing required section '{section}'"
        )

    def test_ci_pipeline_table_has_entries(self, quality_text: str) -> None:
        """CI pipeline table should have at least 4 check entries."""
        in_ci = False
        rows = 0
        for line in quality_text.splitlines():
            if "### CI pipeline" in line:
                in_ci = True
                continue
            if in_ci and line.startswith("##"):
                break
            if in_ci and line.startswith("|") and "---" not in line:
                rows += 1
        data_rows = rows - 1 if rows > 0 else 0
        assert data_rows >= 4, (
            f"QUALITY_SCORE.md CI pipeline table has {data_rows} rows, expected >= 4"
        )

    def test_per_module_coverage_table_has_entries(self, quality_text: str) -> None:
        """Per-module coverage table should have at least 10 entries."""
        in_module = False
        rows = 0
        for line in quality_text.splitlines():
            if "## Per-module coverage targets" in line:
                in_module = True
                continue
            if in_module and line.startswith("##"):
                break
            if in_module and line.startswith("|") and "---" not in line:
                rows += 1
        data_rows = rows - 1 if rows > 0 else 0
        assert data_rows >= 10, (
            f"QUALITY_SCORE.md per-module table has {data_rows} rows, expected >= 10"
        )

    def test_remaining_gaps_table_has_entries(self, quality_text: str) -> None:
        """Remaining coverage gaps table should have at least 1 entry."""
        in_gaps = False
        rows = 0
        for line in quality_text.splitlines():
            if "## Remaining coverage gaps" in line:
                in_gaps = True
                continue
            if in_gaps and line.startswith("##"):
                break
            if in_gaps and line.startswith("|") and "---" not in line:
                rows += 1
        data_rows = rows - 1 if rows > 0 else 0
        assert data_rows >= 1, (
            f"QUALITY_SCORE.md remaining gaps table has {data_rows} rows, expected >= 1"
        )


class TestFrontendMdSections:
    """FRONTEND.md must have required structural sections."""

    @pytest.fixture()
    def frontend_text(self) -> str:
        return (DOCS_DIR / "FRONTEND.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## 1. Inline HTML UI",
            "## 2. React frontend",
            "### Component structure",
        ],
    )
    def test_required_section_exists(self, frontend_text: str, section: str) -> None:
        assert section in frontend_text, (
            f"FRONTEND.md is missing required section '{section}'"
        )

    def test_mentions_vite(self, frontend_text: str) -> None:
        """FRONTEND.md should mention Vite as the build tool."""
        assert "Vite" in frontend_text, (
            "FRONTEND.md should mention Vite as the build tool"
        )


class TestProductSenseMdSections:
    """PRODUCT_SENSE.md must have required structural sections."""

    @pytest.fixture()
    def product_text(self) -> str:
        return (DOCS_DIR / "PRODUCT_SENSE.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "## What helping_hands is",
            "## Target users",
            "## Key value propositions",
            "## Product priorities",
        ],
    )
    def test_required_section_exists(self, product_text: str, section: str) -> None:
        assert section in product_text, (
            f"PRODUCT_SENSE.md is missing required section '{section}'"
        )

    def test_has_target_user_entries(self, product_text: str) -> None:
        """Target users section should list at least 2 user types."""
        in_section = False
        entries = 0
        for line in product_text.splitlines():
            if "## Target users" in line:
                in_section = True
                continue
            if in_section and line.startswith("##"):
                break
            if in_section and line.strip().startswith(("1.", "2.", "3.", "-")):
                entries += 1
        assert entries >= 2, (
            f"PRODUCT_SENSE.md Target users has {entries} entries, expected >= 2"
        )


class TestSecurityMdSandboxingSections:
    """SECURITY.md must have sandboxing subsections."""

    @pytest.fixture()
    def security_text(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "### Codex CLI sandbox modes",
            "### Claude Code permissions",
            "### Container isolation for CLI hands",
            "### Docker Desktop sandbox isolation",
            "### Gemini CLI approval mode",
        ],
    )
    def test_sandboxing_subsection_exists(
        self, security_text: str, section: str
    ) -> None:
        assert section in security_text, (
            f"SECURITY.md is missing sandboxing subsection '{section}'"
        )


class TestDesignDocsMinimumContent:
    """Each design doc should have substantive content."""

    @pytest.fixture()
    def design_doc_paths(self) -> list[Path]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f for f in dd.glob("*.md") if f.name != "index.md")

    def test_design_docs_have_minimum_length(
        self, design_doc_paths: list[Path]
    ) -> None:
        """Each design doc should have at least 500 characters of content."""
        for doc_path in design_doc_paths:
            content = doc_path.read_text()
            assert len(content) >= 500, (
                f"Design doc '{doc_path.name}' has only {len(content)} chars, "
                f"expected >= 500"
            )

    def test_design_docs_have_context_section(
        self, design_doc_paths: list[Path]
    ) -> None:
        """Design docs (except core-beliefs and testing-methodology) should have a Context section."""
        exempt = {"core-beliefs.md", "testing-methodology.md", "two-phase-cli-hands.md"}
        for doc_path in design_doc_paths:
            if doc_path.name in exempt:
                continue
            content = doc_path.read_text()
            assert "## Context" in content, (
                f"Design doc '{doc_path.name}' is missing ## Context section"
            )

    def test_design_docs_have_heading(self, design_doc_paths: list[Path]) -> None:
        """Each design doc should start with a level-1 heading."""
        for doc_path in design_doc_paths:
            content = doc_path.read_text().strip()
            assert content.startswith("# "), (
                f"Design doc '{doc_path.name}' should start with a # heading"
            )


class TestArchitectureMdSectionCount:
    """ARCHITECTURE.md should have a minimum number of sections."""

    def test_minimum_section_count(self) -> None:
        arch_text = (REPO_ROOT / "ARCHITECTURE.md").read_text()
        sections = re.findall(r"^##\s", arch_text, re.MULTILINE)
        assert len(sections) >= 5, (
            f"ARCHITECTURE.md has {len(sections)} level-2 sections, expected >= 5"
        )


class TestPlansLinkResolution:
    """PLANS.md completed plan links must resolve to actual files."""

    @pytest.fixture()
    def plans_text(self) -> str:
        return (DOCS_DIR / "PLANS.md").read_text()

    def test_completed_plan_links_resolve(self, plans_text: str) -> None:
        """Every (exec-plans/...) link in PLANS.md must point to an existing file."""
        links = re.findall(r"\((exec-plans/[^)]+\.md)\)", plans_text)
        assert len(links) > 0, "PLANS.md should have exec-plan links"
        for link in links:
            path = DOCS_DIR / link
            assert path.is_file(), (
                f"PLANS.md references '{link}' but the file does not exist"
            )

    def test_no_active_plans_stale(self, plans_text: str) -> None:
        """If 'No active plans' is declared, the active directory should be empty."""
        if "_No active plans._" not in plans_text:
            return  # active plans exist, skip this check
        active_dir = DOCS_DIR / "exec-plans" / "active"
        if not active_dir.exists():
            return
        active_plans = list(active_dir.glob("*.md"))
        assert len(active_plans) == 0, (
            f"PLANS.md says no active plans but {len(active_plans)} files "
            f"exist in exec-plans/active/"
        )


class TestDocsIndexDesignDocsList:
    """docs/index.md design-docs parenthetical list should match actual files."""

    def test_design_doc_count_in_parenthetical(self) -> None:
        """The comma-separated list in docs/index.md should cover all design docs."""
        index_text = (DOCS_DIR / "index.md").read_text()
        dd = DOCS_DIR / "design-docs"
        actual_files = [f for f in dd.glob("*.md") if f.name != "index.md"]

        # Extract parenthetical after "Design documents"
        match = re.search(r"Design documents \(([^)]+)\)", index_text)
        assert match is not None, (
            "docs/index.md should have a 'Design documents (...)' parenthetical"
        )
        items = [item.strip() for item in match.group(1).split(",")]
        assert len(items) == len(actual_files), (
            f"docs/index.md lists {len(items)} design docs in parenthetical "
            f"but {len(actual_files)} .md files exist in design-docs/"
        )


class TestTechDebtTrackerStructure:
    """Tech debt tracker should have valid table structure."""

    @pytest.fixture()
    def tracker_text(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

    def test_has_required_sections(self, tracker_text: str) -> None:
        assert "## Active items" in tracker_text
        assert "## Resolved items" in tracker_text

    def test_has_table_header(self, tracker_text: str) -> None:
        """Active items table should have Item, Priority, Module, Notes columns."""
        assert "| Item | Priority | Module | Notes |" in tracker_text

    def test_active_items_have_valid_priorities(self, tracker_text: str) -> None:
        """Each active item should have a recognized priority value."""
        valid_priorities = {"High", "Medium", "Low", "None"}
        in_active = False
        rows: list[str] = []
        for line in tracker_text.splitlines():
            if line.startswith("## Active items"):
                in_active = True
                continue
            if line.startswith("## Resolved items"):
                break
            if in_active and line.startswith("|") and "---" not in line:
                rows.append(line)
        # Skip header row
        for row in rows[1:]:
            cols = [c.strip() for c in row.split("|")]
            # cols[0] is empty (before first |), cols[1]=Item, cols[2]=Priority
            if len(cols) >= 3:
                priority = cols[2]
                assert priority in valid_priorities, (
                    f"Tech debt tracker has unknown priority '{priority}' "
                    f"(expected one of {valid_priorities})"
                )


class TestTodoMdStructure:
    """TODO.md should exist and have list items."""

    @pytest.fixture()
    def todo_text(self) -> str:
        return (REPO_ROOT / "TODO.md").read_text()

    def test_todo_exists(self) -> None:
        assert (REPO_ROOT / "TODO.md").is_file(), "TODO.md should exist"

    def test_has_list_items(self, todo_text: str) -> None:
        """TODO.md should have at least one checkbox item."""
        items = re.findall(r"^- \[[ x]\]", todo_text, re.MULTILINE)
        assert len(items) > 0, "TODO.md should have at least one checkbox item"

    def test_has_heading(self, todo_text: str) -> None:
        assert todo_text.strip().startswith("# "), (
            "TODO.md should start with a level-1 heading"
        )


class TestCompletedPlansMinimumContent:
    """Completed plans should have substantive content."""

    @pytest.fixture()
    def completed_plan_paths(self) -> list[Path]:
        completed = DOCS_DIR / "exec-plans" / "completed"
        if not completed.exists():
            return []
        return sorted(completed.glob("*.md"))

    def test_completed_plans_non_trivial(
        self, completed_plan_paths: list[Path]
    ) -> None:
        """Each completed plan should have at least 200 characters."""
        for plan_path in completed_plan_paths:
            content = plan_path.read_text()
            assert len(content) >= 200, (
                f"Completed plan '{plan_path.name}' has only {len(content)} chars, "
                f"expected >= 200"
            )


class TestDesignDocsSourceReferences:
    """Design docs that reference source files should point to real paths."""

    @pytest.fixture()
    def design_doc_paths(self) -> list[Path]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f for f in dd.glob("*.md") if f.name != "index.md")

    def test_source_file_references_exist(self, design_doc_paths: list[Path]) -> None:
        """Every `src/helping_hands/...` path in design docs must exist."""
        for doc_path in design_doc_paths:
            content = doc_path.read_text()
            paths = re.findall(r"`(src/helping_hands/[^`]+\.py)`", content)
            for rel_path in paths:
                full = REPO_ROOT / rel_path
                assert full.is_file(), (
                    f"Design doc '{doc_path.name}' references '{rel_path}' "
                    f"but the file does not exist"
                )

    def test_design_docs_reference_other_docs_correctly(
        self, design_doc_paths: list[Path]
    ) -> None:
        """Design docs mentioning other design doc filenames should reference real files."""
        dd = DOCS_DIR / "design-docs"
        existing = {f.name for f in dd.glob("*.md")}
        for doc_path in design_doc_paths:
            content = doc_path.read_text()
            # Match references like "see [Foo](bar.md)" or "in `bar.md`"
            refs = re.findall(r"\(([a-z_-]+\.md)\)", content)
            for ref in refs:
                # Only check if it looks like a design doc reference (no path separators)
                if "/" not in ref:
                    assert ref in existing, (
                        f"Design doc '{doc_path.name}' links to '{ref}' "
                        f"but no such file in design-docs/"
                    )


class TestApiDocsCountMatchesIndex:
    """docs/index.md API reference links should cover all docs/api/ files."""

    def test_api_links_are_subset_of_files(self) -> None:
        """Every API link in docs/index.md should point to an existing file."""
        index_text = (DOCS_DIR / "index.md").read_text()
        api_links = re.findall(r"\(api/([^)]+\.md)\)", index_text)
        api_dir = DOCS_DIR / "api"
        file_set = {str(f.relative_to(api_dir)) for f in api_dir.rglob("*.md")}
        assert len(api_links) > 0, "docs/index.md should have API reference links"
        for link in api_links:
            assert link in file_set, (
                f"docs/index.md references api/{link} but no such file in docs/api/"
            )

    def test_api_doc_files_minimum_count(self) -> None:
        """docs/api/ should have at least 10 API doc files."""
        api_dir = DOCS_DIR / "api"
        api_files = sorted(api_dir.rglob("*.md"))
        assert len(api_files) >= 10, (
            f"docs/api/ has {len(api_files)} files, expected >= 10"
        )


class TestPlansMdStructure:
    """PLANS.md must have required structural elements."""

    @pytest.fixture()
    def plans_text(self) -> str:
        return (DOCS_DIR / "PLANS.md").read_text()

    def test_has_how_plans_work_section(self, plans_text: str) -> None:
        assert "## How plans work" in plans_text, (
            "PLANS.md is missing '## How plans work' section"
        )

    def test_has_active_plans_section(self, plans_text: str) -> None:
        assert "## Active plans" in plans_text, (
            "PLANS.md is missing '## Active plans' section"
        )

    def test_has_completed_plans_section(self, plans_text: str) -> None:
        assert "## Completed plans" in plans_text, (
            "PLANS.md is missing '## Completed plans' section"
        )

    def test_completed_plans_have_test_counts(self, plans_text: str) -> None:
        """Each completed plan entry (possibly multi-line) should mention a test count."""
        in_completed = False
        section_lines: list[str] = []
        for line in plans_text.splitlines():
            if "## Completed plans" in line:
                in_completed = True
                continue
            if in_completed and line.startswith("##"):
                break
            if in_completed:
                section_lines.append(line)
        # Split into entries starting with "- ["
        section = "\n".join(section_lines)
        entries = re.split(r"\n(?=- \[)", section)
        entries_without_count = []
        for entry in entries:
            entry = entry.strip()
            if not entry.startswith("- ["):
                continue
            if not re.search(r"\d+ tests", entry):
                entries_without_count.append(entry.splitlines()[0][:80])
        assert len(entries_without_count) == 0, (
            f"PLANS.md completed entries missing test counts: {entries_without_count}"
        )


class TestActivePlansNotCompleted:
    """Active plans directory should not contain completed plans."""

    def test_no_completed_plans_in_active(self) -> None:
        active_dir = DOCS_DIR / "exec-plans" / "active"
        if not active_dir.exists():
            return
        for plan_path in active_dir.glob("*.md"):
            content = plan_path.read_text()
            assert "**Status:** Completed" not in content, (
                f"Active plan '{plan_path.name}' has Status: Completed "
                f"— it should be moved to exec-plans/completed/"
            )


class TestDesignDocsIndexDescriptions:
    """Each entry in design-docs/index.md should have a non-empty description."""

    def test_index_entries_have_descriptions(self) -> None:
        index_text = (DOCS_DIR / "design-docs" / "index.md").read_text()
        # Match lines like "- [Title](file.md) — Description"
        entries = re.findall(
            r"^- \[.+?\]\(.+?\.md\)\s*(?:—|--)\s*(.*)$", index_text, re.MULTILINE
        )
        assert len(entries) > 0, "design-docs/index.md should have list entries"
        for desc in entries:
            assert len(desc.strip()) > 0, (
                "design-docs/index.md has an entry with an empty description"
            )

    def test_index_has_adding_section(self) -> None:
        """Index should have the 'Adding a design doc' section."""
        index_text = (DOCS_DIR / "design-docs" / "index.md").read_text()
        assert "## Adding a design doc" in index_text, (
            "design-docs/index.md is missing '## Adding a design doc' section"
        )


class TestGeneratedDocsContent:
    """Generated docs should have minimum content."""

    @pytest.fixture()
    def generated_paths(self) -> list[Path]:
        gen = DOCS_DIR / "generated"
        if not gen.exists():
            return []
        return sorted(gen.glob("*.md"))

    def test_generated_docs_exist(self, generated_paths: list[Path]) -> None:
        assert len(generated_paths) >= 1, "docs/generated/ should have at least 1 file"

    def test_generated_docs_have_minimum_length(
        self, generated_paths: list[Path]
    ) -> None:
        """Each generated doc should have at least 200 characters."""
        for doc_path in generated_paths:
            content = doc_path.read_text()
            assert len(content) >= 200, (
                f"Generated doc '{doc_path.name}' has only {len(content)} chars, "
                f"expected >= 200"
            )

    def test_generated_docs_have_heading(self, generated_paths: list[Path]) -> None:
        """Each generated doc should start with a heading."""
        for doc_path in generated_paths:
            content = doc_path.read_text().strip()
            assert content.startswith("# "), (
                f"Generated doc '{doc_path.name}' should start with a # heading"
            )


class TestProductSpecsContent:
    """Product spec files should have substantive content."""

    @pytest.fixture()
    def spec_paths(self) -> list[Path]:
        ps = DOCS_DIR / "product-specs"
        return sorted(f for f in ps.glob("*.md") if f.name != "index.md")

    def test_spec_files_have_minimum_length(self, spec_paths: list[Path]) -> None:
        """Each product spec should have at least 300 characters."""
        for spec_path in spec_paths:
            content = spec_path.read_text()
            assert len(content) >= 300, (
                f"Product spec '{spec_path.name}' has only {len(content)} chars, "
                f"expected >= 300"
            )

    def test_spec_files_have_heading(self, spec_paths: list[Path]) -> None:
        """Each product spec should start with a heading."""
        for spec_path in spec_paths:
            content = spec_path.read_text().strip()
            assert content.startswith("# "), (
                f"Product spec '{spec_path.name}' should start with a # heading"
            )


class TestArchitectureMdModuleBoundaries:
    """ARCHITECTURE.md module boundary paths should reference real directories."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_core_library_modules_exist(self, arch_text: str) -> None:
        """Module names mentioned in the Core library section should map to real paths."""
        src_lib = REPO_ROOT / "src" / "helping_hands" / "lib"
        expected_modules = ["config", "repo", "github", "ai_providers", "meta"]
        for mod in expected_modules:
            candidates = list(src_lib.glob(f"{mod}*"))
            assert len(candidates) > 0, (
                f"ARCHITECTURE.md references lib module '{mod}' "
                f"but nothing matching exists under src/helping_hands/lib/"
            )

    def test_entry_point_files_exist(self, arch_text: str) -> None:
        """Entry point files mentioned in ARCHITECTURE.md should exist."""
        src = REPO_ROOT / "src" / "helping_hands"
        entry_points = {
            "cli/main.py": src / "cli" / "main.py",
            "server/app.py": src / "server" / "app.py",
            "server/mcp_server.py": src / "server" / "mcp_server.py",
        }
        for name, path in entry_points.items():
            assert path.is_file(), (
                f"ARCHITECTURE.md references entry point '{name}' "
                f"but {path.relative_to(REPO_ROOT)} does not exist"
            )


class TestDocsIndexRuntimeFlowSection:
    """docs/index.md should have a Runtime flow section."""

    def test_runtime_flow_section_exists(self) -> None:
        index_text = (DOCS_DIR / "index.md").read_text()
        assert "## Runtime flow" in index_text, (
            "docs/index.md is missing '## Runtime flow' section"
        )


class TestQualityScoreAreasForImprovement:
    """QUALITY_SCORE.md should have an areas for improvement section."""

    def test_areas_for_improvement_exists(self) -> None:
        quality_text = (DOCS_DIR / "QUALITY_SCORE.md").read_text()
        assert "## Areas for improvement" in quality_text, (
            "QUALITY_SCORE.md is missing '## Areas for improvement' section"
        )

    def test_areas_for_improvement_has_items(self) -> None:
        quality_text = (DOCS_DIR / "QUALITY_SCORE.md").read_text()
        in_section = False
        items = 0
        for line in quality_text.splitlines():
            if "## Areas for improvement" in line:
                in_section = True
                continue
            if in_section and line.startswith("##"):
                break
            if in_section and line.strip().startswith("- ["):
                items += 1
        assert items >= 1, (
            f"QUALITY_SCORE.md Areas for improvement has {items} items, expected >= 1"
        )


class TestDesignDocsHaveKeySourceFiles:
    """Design docs with a 'Key source files' section should list real files."""

    @pytest.fixture()
    def design_doc_paths(self) -> list[Path]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f for f in dd.glob("*.md") if f.name != "index.md")

    def test_key_source_files_section_paths_exist(
        self, design_doc_paths: list[Path]
    ) -> None:
        """Files listed in 'Key source files' sections must exist."""
        for doc_path in design_doc_paths:
            content = doc_path.read_text()
            if "## Key source files" not in content:
                continue
            # Extract everything after "## Key source files"
            section = content.split("## Key source files", 1)[1]
            # Stop at next heading
            if "\n## " in section:
                section = section.split("\n## ", 1)[0]
            paths = re.findall(r"`(src/helping_hands/[^`]+\.py)`", section)
            for rel_path in paths:
                full = REPO_ROOT / rel_path
                assert full.is_file(), (
                    f"Design doc '{doc_path.name}' Key source files lists "
                    f"'{rel_path}' but the file does not exist"
                )


class TestReliabilitySubsections:
    """RELIABILITY.md must have key subsections for error handling patterns."""

    @pytest.fixture()
    def reliability_text(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    @pytest.mark.parametrize(
        "heading",
        [
            "## Error handling patterns",
            "### CLI hand subprocess failures",
            "### Iterative hand failures",
            "### Finalization failures",
            "### Docker sandbox failures",
            "### Async compatibility fallbacks",
            "## Heartbeat monitoring",
            "## Idempotency",
        ],
    )
    def test_subsection_exists(self, reliability_text: str, heading: str) -> None:
        assert heading in reliability_text, (
            f"RELIABILITY.md is missing expected heading '{heading}'"
        )

    def test_error_handling_has_numbered_items(self, reliability_text: str) -> None:
        """CLI hand subprocess failures should list specific failure modes."""
        section = reliability_text.split("### CLI hand subprocess failures", 1)[1]
        section = section.split("\n### ", 1)[0]
        numbered = [ln for ln in section.splitlines() if re.match(r"\d+\.", ln.strip())]
        assert len(numbered) >= 3, (
            f"CLI hand subprocess failures has {len(numbered)} numbered items, "
            f"expected >= 3"
        )


class TestDesignDocSubsections:
    """DESIGN.md must have key subsections covering core patterns."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.mark.parametrize(
        "heading",
        [
            "## Guiding principles",
            "## Patterns",
            "### Hand abstraction",
            "### Provider resolution",
            "### Two-phase CLI hands",
            "### Meta tools layer",
            "### Finalization",
            "### Error recovery patterns",
            "### Testing patterns",
        ],
    )
    def test_subsection_exists(self, design_text: str, heading: str) -> None:
        assert heading in design_text, (
            f"DESIGN.md is missing expected heading '{heading}'"
        )

    def test_guiding_principles_count(self, design_text: str) -> None:
        """Guiding principles section should list multiple principles."""
        section = design_text.split("## Guiding principles", 1)[1]
        section = section.split("\n## ", 1)[0]
        numbered = [ln for ln in section.splitlines() if re.match(r"\d+\.", ln.strip())]
        assert len(numbered) >= 4, (
            f"DESIGN.md Guiding principles has {len(numbered)} items, expected >= 4"
        )

    def test_error_recovery_table_has_rows(self, design_text: str) -> None:
        """Error recovery patterns section should have a table with rows."""
        section = design_text.split("### Error recovery patterns", 1)[1]
        section = section.split("\n### ", 1)[0]
        table_rows = [
            ln
            for ln in section.splitlines()
            if ln.strip().startswith("|") and "---" not in ln and "Pattern" not in ln
        ]
        assert len(table_rows) >= 5, (
            f"DESIGN.md error recovery table has {len(table_rows)} data rows, "
            f"expected >= 5"
        )


class TestDesignDocsMinimumContentLength:
    """Design docs should not be stubs -- each should have substantial content."""

    @pytest.fixture()
    def design_doc_paths(self) -> list[Path]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f for f in dd.glob("*.md") if f.name != "index.md")

    def test_minimum_content_length(self, design_doc_paths: list[Path]) -> None:
        min_chars = 500
        for doc_path in design_doc_paths:
            content = doc_path.read_text()
            assert len(content) >= min_chars, (
                f"Design doc '{doc_path.name}' has {len(content)} chars, "
                f"expected >= {min_chars}"
            )


class TestDesignDocsHaveStructuredHeadings:
    """Design docs should have either ## Context or ## Design headings."""

    @pytest.fixture()
    def design_doc_paths(self) -> list[Path]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f for f in dd.glob("*.md") if f.name != "index.md")

    def test_has_structured_headings(self, design_doc_paths: list[Path]) -> None:
        """Each design doc should have at least two ## headings."""
        for doc_path in design_doc_paths:
            content = doc_path.read_text()
            headings = re.findall(r"^## .+", content, re.MULTILINE)
            assert len(headings) >= 2, (
                f"Design doc '{doc_path.name}' has {len(headings)} '##' headings, "
                f"expected >= 2"
            )


class TestArchitectureHandTypes:
    """ARCHITECTURE.md should reference the main hand implementation types."""

    def test_hand_types_mentioned(self) -> None:
        arch_text = (REPO_ROOT / "ARCHITECTURE.md").read_text()
        expected_types = [
            "E2EHand",
            "BasicLangGraphHand",
            "BasicAtomicHand",
        ]
        for hand_type in expected_types:
            assert hand_type in arch_text, (
                f"ARCHITECTURE.md does not mention hand type '{hand_type}'"
            )


class TestConftestFixturesUsed:
    """Shared conftest fixtures should be referenced in at least one test file."""

    @pytest.fixture()
    def conftest_fixture_names(self) -> list[str]:
        conftest = REPO_ROOT / "tests" / "conftest.py"
        content = conftest.read_text()
        return re.findall(r"^def (\w+)\(", content, re.MULTILINE)

    @pytest.fixture()
    def test_file_contents(self) -> dict[str, str]:
        tests_dir = REPO_ROOT / "tests"
        return {f.name: f.read_text() for f in tests_dir.glob("test_*.py")}

    def test_each_fixture_is_used(
        self,
        conftest_fixture_names: list[str],
        test_file_contents: dict[str, str],
    ) -> None:
        all_test_content = "\n".join(test_file_contents.values())
        for fixture_name in conftest_fixture_names:
            # Skip private factory helpers (the outer function is the fixture)
            if fixture_name.startswith("_"):
                continue
            assert fixture_name in all_test_content, (
                f"conftest fixture '{fixture_name}' is not referenced in any test file"
            )


class TestTestingMethodologyDocReferences:
    """Testing methodology design doc should reference key patterns."""

    def test_coverage_targets_section(self) -> None:
        content = (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()
        assert "## Coverage targets" in content

    def test_key_patterns_section(self) -> None:
        content = (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()
        assert "## Key patterns" in content

    def test_anti_patterns_section(self) -> None:
        content = (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()
        assert "## Anti-patterns" in content

    def test_references_monkeypatch(self) -> None:
        content = (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()
        assert "monkeypatch" in content

    def test_references_importorskip(self) -> None:
        content = (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()
        assert "importorskip" in content


class TestDockerSandboxDesignDoc:
    """Docker sandbox design doc should cover key concepts."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "docker-sandbox.md").read_text()

    def test_has_context_section(self, content: str) -> None:
        assert "## Context" in content

    def test_has_inheritance_chain_section(self, content: str) -> None:
        assert "## Inheritance chain" in content

    def test_has_sandbox_lifecycle_section(self, content: str) -> None:
        assert "## Sandbox lifecycle" in content

    def test_has_command_wrapping_subsection(self, content: str) -> None:
        assert "### Command wrapping" in content

    def test_has_cleanup_subsection(self, content: str) -> None:
        assert "### Cleanup" in content

    def test_has_environment_variables_section(self, content: str) -> None:
        assert "## Environment variables" in content

    def test_has_failure_handling_section(self, content: str) -> None:
        assert "## Failure handling" in content

    def test_references_docker_sandbox_hand(self, content: str) -> None:
        assert "DockerSandboxClaudeCodeHand" in content

    def test_references_claude_code_hand(self, content: str) -> None:
        assert "ClaudeCodeHand" in content

    def test_references_two_phase(self, content: str) -> None:
        assert "_TwoPhaseCLIHand" in content

    def test_references_source_file(self, content: str) -> None:
        assert "docker_sandbox_claude.py" in content

    def test_has_disabled_features_section(self, content: str) -> None:
        assert "## Disabled features" in content

    def test_env_var_sandbox_name(self, content: str) -> None:
        assert "HELPING_HANDS_DOCKER_SANDBOX_NAME" in content

    def test_env_var_sandbox_cleanup(self, content: str) -> None:
        assert "HELPING_HANDS_DOCKER_SANDBOX_CLEANUP" in content

    def test_env_var_sandbox_template(self, content: str) -> None:
        assert "HELPING_HANDS_DOCKER_SANDBOX_TEMPLATE" in content


class TestConsolidatedPlanCoverage:
    """Consolidated 2026-03-06.md should cover all versions from that date."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "exec-plans" / "completed" / "2026-03-06.md").read_text()

    def test_covers_v32_through_v79(self, content: str) -> None:
        """Consolidated plan should reference v32-v79 in header."""
        assert "v32-v79" in content

    def test_has_v69_entry(self, content: str) -> None:
        assert "## v69" in content

    def test_has_v79_entry(self, content: str) -> None:
        assert "## v79" in content

    def test_v69_through_v79_all_present(self, content: str) -> None:
        for v in range(69, 80):
            assert f"## v{v}" in content, (
                f"Consolidated 2026-03-06.md is missing ## v{v} entry"
            )


class TestArchitectureDockerSandboxRef:
    """ARCHITECTURE.md should reference DockerSandboxClaudeCodeHand."""

    def test_references_docker_sandbox_hand(self) -> None:
        content = (REPO_ROOT / "ARCHITECTURE.md").read_text()
        assert "DockerSandboxClaudeCodeHand" in content or "docker-sandbox" in content


class TestSecurityDockerSandboxRef:
    """SECURITY.md should document Docker sandbox isolation."""

    def test_has_docker_sandbox_section(self) -> None:
        content = (DOCS_DIR / "SECURITY.md").read_text()
        assert "DockerSandboxClaudeCodeHand" in content

    def test_references_microvm(self) -> None:
        content = (DOCS_DIR / "SECURITY.md").read_text()
        assert "microVM" in content or "microvm" in content.lower()

    def test_references_sandbox_cleanup_env(self) -> None:
        content = (DOCS_DIR / "SECURITY.md").read_text()
        assert "HELPING_HANDS_DOCKER_SANDBOX_CLEANUP" in content


class TestCommandExecutionDesignDoc:
    """Command execution design doc should cover key concepts."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "command-execution.md").read_text()

    def test_has_context_section(self, content: str) -> None:
        assert "## Context" in content

    def test_has_command_result_section(self, content: str) -> None:
        assert "## CommandResult dataclass" in content

    def test_has_path_confined_section(self, content: str) -> None:
        assert "## Path-confined execution" in content

    def test_has_runners_section(self, content: str) -> None:
        assert "## Python and Bash runners" in content

    def test_has_registry_section(self, content: str) -> None:
        assert "## Tool registry" in content

    def test_has_payload_validation_section(self, content: str) -> None:
        assert "## Payload validation" in content

    def test_references_command_result(self, content: str) -> None:
        assert "CommandResult" in content

    def test_references_tool_spec(self, content: str) -> None:
        assert "ToolSpec" in content

    def test_references_tool_category(self, content: str) -> None:
        assert "ToolCategory" in content

    def test_references_resolve_repo_target(self, content: str) -> None:
        assert "resolve_repo_target" in content

    def test_references_source_files(self, content: str) -> None:
        assert "command.py" in content
        assert "registry.py" in content

    def test_references_cli_guidance(self, content: str) -> None:
        assert "format_tool_instructions_for_cli" in content


class TestConsolidated20260307:
    """Consolidated 2026-03-07 plan should cover completed plans."""

    @pytest.fixture()
    def content(self) -> str:
        path = DOCS_DIR / "exec-plans" / "completed" / "2026-03-07.md"
        if not path.exists():
            pytest.skip("2026-03-07.md not yet created")
        return path.read_text()

    def test_covers_v80(self, content: str) -> None:
        assert "v80" in content

    def test_has_date_header(self, content: str) -> None:
        assert "2026-03-07" in content


# ---------------------------------------------------------------------------
# v82: Design-docs index categorization
# ---------------------------------------------------------------------------

SRC_ROOT = REPO_ROOT / "src" / "helping_hands"


class TestDesignDocsIndexCategories:
    """design-docs/index.md should be organized by topic categories."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "index.md").read_text()

    @pytest.mark.parametrize(
        "category",
        [
            "## Core",
            "## Hands",
            "## Providers and Models",
            "## Tools and Skills",
            "## Infrastructure",
            "## Quality",
        ],
    )
    def test_has_category_heading(self, index_text: str, category: str) -> None:
        assert category in index_text, (
            f"design-docs/index.md should have a '{category}' category heading"
        )

    def test_core_beliefs_in_core_section(self, index_text: str) -> None:
        core_start = index_text.index("## Core")
        hands_start = index_text.index("## Hands")
        core_section = index_text[core_start:hands_start]
        assert "core-beliefs.md" in core_section

    def test_hand_abstraction_in_hands_section(self, index_text: str) -> None:
        hands_start = index_text.index("## Hands")
        providers_start = index_text.index("## Providers and Models")
        hands_section = index_text[hands_start:providers_start]
        assert "hand-abstraction.md" in hands_section

    def test_provider_abstraction_in_providers_section(self, index_text: str) -> None:
        providers_start = index_text.index("## Providers and Models")
        tools_start = index_text.index("## Tools and Skills")
        providers_section = index_text[providers_start:tools_start]
        assert "provider-abstraction.md" in providers_section

    def test_filesystem_security_in_tools_section(self, index_text: str) -> None:
        tools_start = index_text.index("## Tools and Skills")
        infra_start = index_text.index("## Infrastructure")
        tools_section = index_text[tools_start:infra_start]
        assert "filesystem-security.md" in tools_section

    def test_deployment_modes_in_infrastructure_section(self, index_text: str) -> None:
        infra_start = index_text.index("## Infrastructure")
        quality_start = index_text.index("## Quality")
        infra_section = index_text[infra_start:quality_start]
        assert "deployment-modes.md" in infra_section

    def test_testing_methodology_in_quality_section(self, index_text: str) -> None:
        quality_start = index_text.index("## Quality")
        quality_section = index_text[quality_start:]
        assert "testing-methodology.md" in quality_section


class TestDesignDocsIndexAllDocsListed:
    """Every design doc must appear in exactly one category in the index."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "index.md").read_text()

    @pytest.fixture()
    def design_doc_files(self) -> list[str]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f.name for f in dd.glob("*.md") if f.name != "index.md")

    def test_each_doc_listed_exactly_once(
        self, index_text: str, design_doc_files: list[str]
    ) -> None:
        linked = re.findall(r"\(([^)]+\.md)\)", index_text)
        for doc in design_doc_files:
            count = linked.count(doc)
            assert count == 1, (
                f"'{doc}' appears {count} time(s) in design-docs/index.md "
                f"(expected exactly 1)"
            )


# ---------------------------------------------------------------------------
# v82: ARCHITECTURE.md cross-references to design docs
# ---------------------------------------------------------------------------


class TestArchitectureDesignDocCrossRefs:
    """ARCHITECTURE.md should reference key design docs via docs/ links."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_references_design_md(self, arch_text: str) -> None:
        assert "DESIGN.md" in arch_text

    def test_references_agent_md(self, arch_text: str) -> None:
        assert "AGENT.md" in arch_text

    def test_has_hand_backends_table(self, arch_text: str) -> None:
        assert "E2EHand" in arch_text
        assert "BasicLangGraphHand" in arch_text
        assert "ClaudeCodeHand" in arch_text

    def test_lists_all_cli_hand_modules(self, arch_text: str) -> None:
        cli_dir = SRC_ROOT / "lib" / "hands" / "v1" / "hand" / "cli"
        cli_modules = sorted(
            f.stem
            for f in cli_dir.glob("*.py")
            if f.name not in ("__init__.py", "base.py")
        )
        for mod in cli_modules:
            assert mod in arch_text, (
                f"CLI hand module '{mod}.py' exists in source but is not "
                f"referenced in ARCHITECTURE.md"
            )

    def test_key_file_paths_match_source(self, arch_text: str) -> None:
        """Key paths listed in ARCHITECTURE.md should exist on disk."""
        paths = re.findall(r"`(src/helping_hands/[^`]+\.py)`", arch_text)
        assert len(paths) >= 10, "ARCHITECTURE.md should list at least 10 key paths"
        for rel in paths:
            full = REPO_ROOT / rel
            assert full.exists(), f"ARCHITECTURE.md lists '{rel}' but it does not exist"


# ---------------------------------------------------------------------------
# v82: AGENTS.md hand types consistency with source
# ---------------------------------------------------------------------------


class TestAgentsMdHandTypes:
    """AGENTS.md agent types table should match actual Hand subclasses."""

    @pytest.fixture()
    def agents_text(self) -> str:
        return (REPO_ROOT / "AGENTS.md").read_text()

    def test_mentions_cli_hand(self, agents_text: str) -> None:
        assert "CLI hand" in agents_text

    def test_mentions_worker_hand(self, agents_text: str) -> None:
        assert "Worker hand" in agents_text

    def test_mentions_mcp_agent(self, agents_text: str) -> None:
        assert "MCP agent" in agents_text

    def test_mentions_docker_sandbox(self, agents_text: str) -> None:
        assert "Docker Sandbox" in agents_text or "docker-sandbox" in agents_text

    def test_mentions_scheduled_hand(self, agents_text: str) -> None:
        assert "Scheduled hand" in agents_text or "RedBeat" in agents_text

    def test_coordination_rules_count(self, agents_text: str) -> None:
        """Should have at least 5 numbered coordination rules."""
        rules = re.findall(r"^\d+\.\s+\*\*", agents_text, re.MULTILINE)
        assert len(rules) >= 5, (
            f"AGENTS.md has {len(rules)} coordination rules, expected >= 5"
        )

    def test_file_ownership_table_has_key_paths(self, agents_text: str) -> None:
        for path_fragment in ["AGENT.md", "README.md", "src/helping_hands", "tests/"]:
            assert path_fragment in agents_text, (
                f"AGENTS.md file ownership table should mention '{path_fragment}'"
            )

    def test_sandbox_section_references_source_class(self, agents_text: str) -> None:
        assert "DockerSandboxClaudeCodeHand" in agents_text


class TestAgentsMdSchedulingSection:
    """AGENTS.md scheduling section should reference key components."""

    @pytest.fixture()
    def agents_text(self) -> str:
        return (REPO_ROOT / "AGENTS.md").read_text()

    def test_mentions_schedule_manager(self, agents_text: str) -> None:
        assert "ScheduleManager" in agents_text

    def test_mentions_trigger_now(self, agents_text: str) -> None:
        assert "trigger_now" in agents_text

    def test_mentions_redis_key_pattern(self, agents_text: str) -> None:
        assert "helping_hands:schedule:" in agents_text


# ---------------------------------------------------------------------------
# v82: Design doc structural quality
# ---------------------------------------------------------------------------

_FORMAL_DESIGN_DOCS = [
    "hand-abstraction.md",
    "two-phase-cli-hands.md",
    "provider-abstraction.md",
    "error-handling.md",
    "mcp-architecture.md",
    "config-loading.md",
    "repo-indexing.md",
    "scheduling-system.md",
    "deployment-modes.md",
    "ci-pipeline.md",
    "skills-system.md",
    "github-client.md",
    "pr-description.md",
    "default-prompts.md",
    "filesystem-security.md",
    "model-resolution.md",
    "e2e-hand-workflow.md",
    "task-lifecycle.md",
    "web-tools.md",
    "docker-sandbox.md",
    "command-execution.md",
]


class TestDesignDocsHaveContextOrOverview:
    """Formal design docs should have a Context or Overview section."""

    @pytest.mark.parametrize("doc_name", _FORMAL_DESIGN_DOCS)
    def test_has_context_or_overview(self, doc_name: str) -> None:
        path = DOCS_DIR / "design-docs" / doc_name
        if not path.exists():
            pytest.skip(f"{doc_name} not found")
        content = path.read_text()
        assert "## Context" in content or "## Overview" in content, (
            f"Design doc '{doc_name}' should have a '## Context' or "
            f"'## Overview' section"
        )


class TestDesignDocsHaveSubstantiveSection:
    """Formal design docs should have a Decision, Design, or domain section."""

    @pytest.mark.parametrize("doc_name", _FORMAL_DESIGN_DOCS)
    def test_has_substantive_section(self, doc_name: str) -> None:
        path = DOCS_DIR / "design-docs" / doc_name
        if not path.exists():
            pytest.skip(f"{doc_name} not found")
        content = path.read_text()
        headings = re.findall(r"^## .+", content, re.MULTILINE)
        # Must have at least 2 h2 headings (context/overview + substance)
        assert len(headings) >= 2, (
            f"Design doc '{doc_name}' should have at least 2 ## sections, "
            f"found {len(headings)}: {headings}"
        )


class TestDesignDocsCrossRefEachOther:
    """Key design docs should cross-reference related docs."""

    def test_hand_abstraction_refs_two_phase(self) -> None:
        content = (DOCS_DIR / "design-docs" / "hand-abstraction.md").read_text()
        assert "two-phase" in content.lower() or "cli" in content.lower()

    def test_provider_refs_model_resolution(self) -> None:
        content = (DOCS_DIR / "design-docs" / "provider-abstraction.md").read_text()
        assert "model" in content.lower()

    def test_filesystem_security_refs_tools(self) -> None:
        content = (DOCS_DIR / "design-docs" / "filesystem-security.md").read_text()
        assert "resolve_repo_target" in content

    def test_docker_sandbox_refs_claude(self) -> None:
        content = (DOCS_DIR / "design-docs" / "docker-sandbox.md").read_text()
        assert "claude" in content.lower() or "Claude" in content


class TestDocsIndexDesignDocsCategories:
    """docs/index.md design-docs listing should mention categorized topics."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    def test_mentions_design_docs_with_topics(self, index_text: str) -> None:
        assert "design-docs" in index_text.lower()
        for topic in ["core beliefs", "hand abstraction", "testing methodology"]:
            assert topic in index_text.lower(), (
                f"docs/index.md should mention design doc topic '{topic}'"
            )


class TestActivePlanConsistency:
    """Active plans directory should be in sync with PLANS.md."""

    @pytest.fixture()
    def plans_text(self) -> str:
        return (DOCS_DIR / "PLANS.md").read_text()

    @pytest.fixture()
    def active_plan_files(self) -> list[str]:
        active_dir = DOCS_DIR / "exec-plans" / "active"
        if not active_dir.exists():
            return []
        return sorted(f.name for f in active_dir.glob("*.md"))

    def test_active_plans_referenced_or_empty(
        self, plans_text: str, active_plan_files: list[str]
    ) -> None:
        if not active_plan_files:
            assert "No active plans" in plans_text or "no active" in plans_text.lower()
        else:
            for filename in active_plan_files:
                stem = filename.replace(".md", "")
                found = filename in plans_text or stem in plans_text
                assert found, (
                    f"Active plan '{filename}' exists in exec-plans/active/ "
                    f"but is not referenced in PLANS.md"
                )


class TestSourceToTestMapping:
    """Every non-trivial source module should have a corresponding test file."""

    @pytest.fixture()
    def source_modules(self) -> list[str]:
        """Collect Python source module basenames (excluding __init__.py and trivial files)."""
        src = REPO_ROOT / "src" / "helping_hands"
        modules: list[str] = []
        for py_file in sorted(src.rglob("*.py")):
            if py_file.name == "__init__.py":
                continue
            if py_file.name.startswith("_"):
                continue
            modules.append(py_file.name)
        return modules

    @pytest.fixture()
    def test_files(self) -> set[str]:
        """Collect all test file names."""
        tests_dir = REPO_ROOT / "tests"
        return {f.name for f in tests_dir.glob("test_*.py")}

    # Modules tested under broader test files, exempt from direct stem matching
    _EXEMPT_MODULES: ClassVar[set[str]] = {
        "main.py",  # CLI entry point — tested via test_cli.py
        "placeholders.py",  # backward compat shim — tested via test_placeholders.py
        "anthropic.py",  # tested via test_ai_providers.py and test_provider_build_inner.py
        "litellm.py",  # tested via test_ai_providers.py and test_provider_build_inner.py
        "types.py",  # tested via test_ai_providers.py (AIProvider base, normalize_messages)
    }

    def test_each_source_module_has_test_file(
        self, source_modules: list[str], test_files: set[str]
    ) -> None:
        """Each source module should map to at least one test_*.py file."""
        missing: list[str] = []
        for mod in source_modules:
            if mod in self._EXEMPT_MODULES:
                continue
            stem = mod.replace(".py", "")
            # Look for test files that contain the module stem
            # e.g. config.py -> test_config.py, claude.py -> test_cli_hand_claude.py
            has_test = any(stem in tf for tf in test_files)
            if not has_test:
                missing.append(mod)
        assert len(missing) == 0, (
            f"Source modules without matching test files: {missing}"
        )


class TestQualityScoreModuleTableAccuracy:
    """QUALITY_SCORE.md per-module table should reference real source modules."""

    @pytest.fixture()
    def quality_text(self) -> str:
        return (DOCS_DIR / "QUALITY_SCORE.md").read_text()

    def test_backticked_modules_exist(self, quality_text: str) -> None:
        """Every backticked module path in QUALITY_SCORE.md should exist."""
        src = REPO_ROOT / "src" / "helping_hands"
        # Extract paths like `lib/config.py` or `server/app.py`
        mod_paths = re.findall(r"`((?:lib|server|cli)/[^`]+\.py)`", quality_text)
        assert len(mod_paths) > 0, (
            "QUALITY_SCORE.md should reference module paths in backticks"
        )
        for mod_path in mod_paths:
            full = src / mod_path
            if full.is_file():
                continue
            # Some paths are abbreviated (e.g. `cli/base.py` for hands CLI base)
            # — check if the basename exists somewhere under src/
            basename = Path(mod_path).name
            candidates = list(src.rglob(basename))
            assert len(candidates) > 0, (
                f"QUALITY_SCORE.md references `{mod_path}` "
                f"but no matching file found under src/helping_hands/"
            )

    def test_coverage_states_are_valid(self, quality_text: str) -> None:
        """Current state values should be recognized categories."""
        valid_states = {"Excellent", "Good", "Fair", "Poor"}
        in_table = False
        rows: list[str] = []
        for line in quality_text.splitlines():
            if "## Per-module coverage targets" in line:
                in_table = True
                continue
            if in_table and line.startswith("##"):
                break
            if in_table and line.startswith("|") and "---" not in line:
                rows.append(line)
        # Skip header row
        for row in rows[1:]:
            cols = [c.strip() for c in row.split("|")]
            if len(cols) >= 4:
                state = cols[2]
                # State should start with one of the valid categories
                state_word = state.split("(")[0].split()[0] if state else ""
                assert state_word in valid_states, (
                    f"QUALITY_SCORE.md has unrecognized state '{state}' "
                    f"(expected to start with one of {valid_states})"
                )


class TestDocTimestampsNotStale:
    """Key documents should have timestamps from the current week."""

    @pytest.mark.parametrize(
        "doc_path",
        [
            REPO_ROOT / "ARCHITECTURE.md",
            REPO_ROOT / "AGENTS.md",
        ],
    )
    def test_last_updated_present(self, doc_path: Path) -> None:
        """Key docs should have a 'Last updated' footer."""
        content = doc_path.read_text()
        assert "Last updated:" in content, (
            f"{doc_path.name} is missing a 'Last updated:' timestamp"
        )

    @pytest.mark.parametrize(
        "doc_path",
        [
            REPO_ROOT / "ARCHITECTURE.md",
            REPO_ROOT / "AGENTS.md",
        ],
    )
    def test_last_updated_has_date_format(self, doc_path: Path) -> None:
        """Last updated timestamp should contain a date in YYYY-MM-DD format."""
        content = doc_path.read_text()
        match = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", content)
        assert match is not None, (
            f"{doc_path.name} 'Last updated' should contain a YYYY-MM-DD date"
        )


class TestArchitectureDataFlowSections:
    """ARCHITECTURE.md should have data flow diagrams for all entry points."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "### CLI task execution",
            "### Server task execution",
            "### MCP server flow",
        ],
    )
    def test_data_flow_section_exists(self, arch_text: str, section: str) -> None:
        assert section in arch_text, (
            f"ARCHITECTURE.md is missing data flow section '{section}'"
        )

    def test_external_integrations_section(self, arch_text: str) -> None:
        assert "## External integrations" in arch_text, (
            "ARCHITECTURE.md is missing '## External integrations' section"
        )

    def test_design_principles_section(self, arch_text: str) -> None:
        assert "## Design principles" in arch_text, (
            "ARCHITECTURE.md is missing '## Design principles' section"
        )


class TestTechDebtTrackerPriorityValues:
    """Active tech-debt items should have recognized priority values."""

    _VALID_PRIORITIES: ClassVar[set[str]] = {
        "None",
        "Low",
        "Medium",
        "High",
        "Critical",
    }

    @pytest.fixture()
    def tracker_text(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

    def test_active_items_have_valid_priority(self, tracker_text: str) -> None:
        """Each row in the Active items table must use a known priority."""
        in_table = False
        rows: list[str] = []
        for line in tracker_text.splitlines():
            if "## Active items" in line:
                in_table = True
                continue
            if in_table and line.startswith("## "):
                break
            if in_table and line.startswith("|") and "---" not in line:
                rows.append(line)
        # Skip the header row
        for row in rows[1:]:
            cols = [c.strip() for c in row.split("|")]
            if len(cols) >= 4:
                priority = cols[2]
                assert priority in self._VALID_PRIORITIES, (
                    f"Tech-debt-tracker has unrecognized priority '{priority}' "
                    f"(expected one of {self._VALID_PRIORITIES})"
                )

    def test_active_items_table_not_empty(self, tracker_text: str) -> None:
        """The active items table should have at least one entry."""
        assert "| " in tracker_text.split("## Active items")[1].split("## ")[0], (
            "Tech-debt-tracker active items table appears empty"
        )


class TestReliabilityMdErrorHandlingSubsections:
    """RELIABILITY.md should have subsections for each failure domain."""

    @pytest.fixture()
    def reliability_text(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    @pytest.mark.parametrize(
        "subsection",
        [
            "### CLI hand subprocess failures",
            "### Iterative hand failures",
            "### Finalization failures",
            "### Docker sandbox failures",
            "### Async compatibility fallbacks",
        ],
    )
    def test_error_handling_subsection_exists(
        self, reliability_text: str, subsection: str
    ) -> None:
        assert subsection in reliability_text, (
            f"RELIABILITY.md is missing error handling subsection '{subsection}'"
        )

    def test_heartbeat_monitoring_section(self, reliability_text: str) -> None:
        assert "## Heartbeat monitoring" in reliability_text, (
            "RELIABILITY.md is missing '## Heartbeat monitoring' section"
        )

    def test_idempotency_section(self, reliability_text: str) -> None:
        assert "## Idempotency" in reliability_text, (
            "RELIABILITY.md is missing '## Idempotency' section"
        )


class TestArchitectureHandTableCompleteness:
    """ARCHITECTURE.md hand table should list all hand modules."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    @pytest.fixture()
    def hand_modules(self) -> list[str]:
        """Discover all .py files in the hand directory (excluding __init__)."""
        hand_dir = REPO_ROOT / "src" / "helping_hands" / "lib" / "hands" / "v1" / "hand"
        modules = []
        for f in hand_dir.glob("*.py"):
            if f.name != "__init__.py":
                modules.append(f.stem)
        cli_dir = hand_dir / "cli"
        for f in cli_dir.glob("*.py"):
            if f.name not in ("__init__.py", "base.py"):
                modules.append(f.stem)
        return sorted(modules)

    def test_hand_table_references_all_modules(
        self, arch_text: str, hand_modules: list[str]
    ) -> None:
        """Each hand module should be referenced in ARCHITECTURE.md."""
        for mod in hand_modules:
            # Module filenames like docker_sandbox_claude.py -> docker_sandbox_claude
            assert (
                f"{mod}.py" in arch_text or mod.replace("_", "") in arch_text.lower()
            ), f"ARCHITECTURE.md hand table is missing reference to '{mod}.py'"


class TestTestingMethodologyPatternReferences:
    """testing-methodology.md should reference actual test patterns used."""

    @pytest.fixture()
    def methodology_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()

    def test_references_monkeypatch(self, methodology_text: str) -> None:
        assert "monkeypatch" in methodology_text, (
            "testing-methodology.md should reference monkeypatch isolation pattern"
        )

    def test_references_importorskip(self, methodology_text: str) -> None:
        assert "importorskip" in methodology_text, (
            "testing-methodology.md should reference importorskip pattern"
        )

    def test_references_dead_code_documentation(self, methodology_text: str) -> None:
        assert "tech-debt-tracker" in methodology_text, (
            "testing-methodology.md should reference tech-debt-tracker for dead code"
        )

    def test_coverage_targets_table_exists(self, methodology_text: str) -> None:
        assert "## Coverage targets" in methodology_text, (
            "testing-methodology.md should have a Coverage targets section"
        )

    def test_anti_patterns_section_exists(self, methodology_text: str) -> None:
        assert "## Anti-patterns" in methodology_text, (
            "testing-methodology.md should have an Anti-patterns section"
        )


class TestFrontendMdStructure:
    """FRONTEND.md should document both UI surfaces and sync requirements."""

    @pytest.fixture()
    def frontend_text(self) -> str:
        return (DOCS_DIR / "FRONTEND.md").read_text()

    def test_inline_html_section(self, frontend_text: str) -> None:
        assert "Inline HTML" in frontend_text, (
            "FRONTEND.md should document the inline HTML UI"
        )

    def test_react_frontend_section(self, frontend_text: str) -> None:
        assert "React frontend" in frontend_text, (
            "FRONTEND.md should document the React frontend"
        )

    def test_sync_requirements_section(self, frontend_text: str) -> None:
        assert "## Sync requirements" in frontend_text, (
            "FRONTEND.md should have a 'Sync requirements' section"
        )

    def test_testing_strategy_section(self, frontend_text: str) -> None:
        assert "## Testing strategy" in frontend_text, (
            "FRONTEND.md should have a 'Testing strategy' section"
        )

    def test_api_endpoints_table(self, frontend_text: str) -> None:
        assert "## API endpoints" in frontend_text, (
            "FRONTEND.md should have an API endpoints section"
        )

    def test_component_structure_section(self, frontend_text: str) -> None:
        assert "### Component structure" in frontend_text, (
            "FRONTEND.md should have a component structure section"
        )


class TestDocsIndexDocumentationMap:
    """docs/index.md documentation map should list all top-level docs."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    @pytest.mark.parametrize(
        "doc_name",
        [
            "ARCHITECTURE.md",
            "AGENTS.md",
            "DESIGN.md",
            "FRONTEND.md",
            "SECURITY.md",
            "RELIABILITY.md",
            "PRODUCT_SENSE.md",
            "QUALITY_SCORE.md",
            "PLANS.md",
        ],
    )
    def test_top_level_doc_listed(self, index_text: str, doc_name: str) -> None:
        assert doc_name in index_text, (
            f"docs/index.md documentation map is missing reference to {doc_name}"
        )

    def test_design_docs_link(self, index_text: str) -> None:
        assert "design-docs/index.md" in index_text, (
            "docs/index.md should link to design-docs/index.md"
        )

    def test_product_specs_link(self, index_text: str) -> None:
        assert "product-specs/index.md" in index_text, (
            "docs/index.md should link to product-specs/index.md"
        )


class TestCompletedPlanTestCountFormat:
    """Completed plan summaries in PLANS.md should mention test counts."""

    @pytest.fixture()
    def plans_text(self) -> str:
        return (DOCS_DIR / "PLANS.md").read_text()

    def test_completed_plans_mention_test_counts(self, plans_text: str) -> None:
        """Each completed plan summary should include a test count reference."""
        completed_section = plans_text.split("## Completed plans")[1]
        if "## " in completed_section:
            completed_section = completed_section.split("## ")[0]
        # Gather multi-line plan entries (start with "- [", continuation indented)
        entries: list[str] = []
        current: list[str] = []
        for line in completed_section.splitlines():
            if line.strip().startswith("- ["):
                if current:
                    entries.append(" ".join(current))
                current = [line.strip()]
            elif current and line.strip() and not line.strip().startswith("- "):
                current.append(line.strip())
        if current:
            entries.append(" ".join(current))
        assert len(entries) > 0, "PLANS.md should have completed plan entries"
        for entry in entries:
            assert "tests" in entry.lower(), (
                f"Completed plan entry should mention test counts: {entry[:80]}..."
            )

    def test_completed_plans_have_date_links(self, plans_text: str) -> None:
        """Each completed plan should link to a date-stamped file."""
        completed_section = plans_text.split("## Completed plans")[1]
        plan_lines = [
            line
            for line in completed_section.splitlines()
            if line.strip().startswith("- [")
        ]
        for line in plan_lines:
            assert re.search(r"\d{4}-\d{2}-\d{2}", line), (
                f"Completed plan entry should have a YYYY-MM-DD date: {line[:80]}..."
            )


class TestCompletedPlanChronologicalOrder:
    """Completed plan files should have dates in chronological order."""

    @pytest.fixture()
    def completed_dates(self) -> list[str]:
        completed = DOCS_DIR / "exec-plans" / "completed"
        if not completed.exists():
            return []
        files = sorted(f.stem for f in completed.glob("*.md"))
        return [f for f in files if re.match(r"\d{4}-\d{2}-\d{2}", f)]

    def test_dates_are_chronological(self, completed_dates: list[str]) -> None:
        """Completed plan dates should be in ascending order."""
        assert completed_dates == sorted(completed_dates), (
            "Completed plan dates are not in chronological order"
        )

    def test_no_duplicate_dates(self, completed_dates: list[str]) -> None:
        """Each date should appear at most once in completed plans."""
        assert len(completed_dates) == len(set(completed_dates)), (
            "Completed plans contain duplicate dates"
        )

    def test_dates_are_valid_format(self, completed_dates: list[str]) -> None:
        """All completed plan filenames should be valid YYYY-MM-DD dates."""
        for date_str in completed_dates:
            parts = date_str.split("-")
            assert len(parts) == 3, f"Invalid date format: {date_str}"
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            assert 2024 <= year <= 2030, f"Year out of range: {date_str}"
            assert 1 <= month <= 12, f"Month out of range: {date_str}"
            assert 1 <= day <= 31, f"Day out of range: {date_str}"


class TestProductSenseMdContent:
    """PRODUCT_SENSE.md should have all expected sections and content."""

    @pytest.fixture()
    def product_text(self) -> str:
        return (DOCS_DIR / "PRODUCT_SENSE.md").read_text()

    _EXPECTED_SECTIONS: ClassVar[list[str]] = [
        "What helping_hands is",
        "Target users",
        "Key value propositions",
        "Product priorities",
        "Implemented capabilities",
        "Future directions",
    ]

    def test_has_all_sections(self, product_text: str) -> None:
        for section in self._EXPECTED_SECTIONS:
            assert section.lower() in product_text.lower(), (
                f"PRODUCT_SENSE.md missing expected section: {section}"
            )

    def test_target_users_lists_three_personas(self, product_text: str) -> None:
        """Should list at least 3 target user types."""
        users_section = product_text.split("## Target users")[1].split("##")[0]
        numbered = re.findall(r"^\d+\.", users_section, re.MULTILINE)
        assert len(numbered) >= 3, (
            f"Expected at least 3 target user personas, found {len(numbered)}"
        )

    def test_mentions_all_backends(self, product_text: str) -> None:
        """Product doc should mention key backend names."""
        backends = ["LangGraph", "Atomic", "Codex", "Claude", "Goose", "Gemini"]
        for backend in backends:
            assert backend.lower() in product_text.lower(), (
                f"PRODUCT_SENSE.md should mention backend: {backend}"
            )

    def test_implemented_capabilities_has_items(self, product_text: str) -> None:
        """Implemented capabilities section should have bullet items."""
        caps_section = product_text.split("## Implemented capabilities")[1].split("##")[
            0
        ]
        bullets = [
            line for line in caps_section.splitlines() if line.strip().startswith("- ")
        ]
        assert len(bullets) >= 2, "Expected at least 2 implemented capabilities"


class TestQualityScoreRemainingGapsMatchTechDebt:
    """QUALITY_SCORE remaining gaps table should reference modules from tech-debt."""

    @pytest.fixture()
    def quality_text(self) -> str:
        return (REPO_ROOT / "docs" / "QUALITY_SCORE.md").read_text()

    @pytest.fixture()
    def tracker_text(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

    def test_remaining_gaps_reference_documented_dead_code(
        self, quality_text: str
    ) -> None:
        """Remaining gaps table should state they are documented dead code."""
        gaps_section = quality_text.split("## Remaining coverage gaps")[1]
        assert (
            "dead code" in gaps_section.lower() or "untestable" in gaps_section.lower()
        ), "Remaining gaps section should explain gaps as dead code or untestable"

    def test_remaining_gaps_modules_exist_in_tech_debt(
        self, quality_text: str, tracker_text: str
    ) -> None:
        """Modules listed in remaining gaps should also appear in tech-debt-tracker."""
        gaps_section = quality_text.split("## Remaining coverage gaps")[1]
        # Extract module names from backticked references in the gaps table
        gap_modules = re.findall(r"`([^`]+\.py)`", gaps_section)
        for mod in gap_modules:
            base = mod.split("/")[-1]
            assert base in tracker_text, (
                f"Module '{mod}' in QUALITY_SCORE remaining gaps "
                f"not found in tech-debt-tracker.md"
            )


class TestReferencesDirectoryContent:
    """docs/references/ should contain non-empty reference files."""

    @pytest.fixture()
    def reference_files(self) -> list[Path]:
        refs_dir = DOCS_DIR / "references"
        if not refs_dir.exists():
            return []
        return sorted(refs_dir.iterdir())

    def test_references_directory_not_empty(self, reference_files: list[Path]) -> None:
        assert len(reference_files) >= 1, "docs/references/ should have files"

    def test_reference_files_are_non_empty(self, reference_files: list[Path]) -> None:
        for f in reference_files:
            assert f.stat().st_size > 0, f"Reference file '{f.name}' is empty"

    def test_reference_files_have_expected_extensions(
        self, reference_files: list[Path]
    ) -> None:
        """Reference files should be text-based (.txt, .md)."""
        allowed = {".txt", ".md", ".json", ".yaml", ".yml"}
        for f in reference_files:
            assert f.suffix in allowed, f"Unexpected file type in references/: {f.name}"


class TestAgentsMdCoordinationCompleteness:
    """AGENTS.md coordination rules should cover all key concerns."""

    @pytest.fixture()
    def agents_text(self) -> str:
        return (REPO_ROOT / "AGENTS.md").read_text()

    _COORDINATION_TOPICS: ClassVar[list[str]] = [
        "branch",
        "PR ownership",
        "workspace",
        "config",
        "AGENT.md",
    ]

    def test_coordination_rules_cover_key_topics(self, agents_text: str) -> None:
        rules_section = agents_text.split("## Coordination rules")[1].split("##")[0]
        for topic in self._COORDINATION_TOPICS:
            assert topic.lower() in rules_section.lower(), (
                f"AGENTS.md coordination rules missing topic: {topic}"
            )

    def test_communication_section_exists(self, agents_text: str) -> None:
        """Should document how agents communicate (or don't)."""
        assert "communication" in agents_text.lower(), (
            "AGENTS.md should have a communication section"
        )

    def test_sandbox_isolation_section_exists(self, agents_text: str) -> None:
        """Should document sandbox isolation for Docker agents."""
        assert "sandbox isolation" in agents_text.lower(), (
            "AGENTS.md should have a sandbox isolation section"
        )

    def test_file_ownership_table_has_entries(self, agents_text: str) -> None:
        """File ownership table should list path patterns."""
        ownership_section = agents_text.split("## File ownership")[1].split("##")[0]
        rows = [
            line
            for line in ownership_section.splitlines()
            if line.strip().startswith("|")
            and "---" not in line
            and "Path pattern" not in line
        ]
        assert len(rows) >= 3, (
            f"File ownership table should have at least 3 entries, found {len(rows)}"
        )


class TestActivePlanStructure:
    """Active plans should have required sections."""

    @pytest.fixture()
    def active_plans(self) -> list[Path]:
        active_dir = DOCS_DIR / "exec-plans" / "active"
        if not active_dir.exists():
            return []
        return sorted(active_dir.glob("*.md"))

    def test_active_plans_have_status(self, active_plans: list[Path]) -> None:
        for plan in active_plans:
            text = plan.read_text()
            assert "status" in text.lower(), (
                f"Active plan '{plan.name}' missing Status field"
            )

    def test_active_plans_have_tasks(self, active_plans: list[Path]) -> None:
        for plan in active_plans:
            text = plan.read_text()
            assert "## Tasks" in text or "## Objective" in text, (
                f"Active plan '{plan.name}' missing Tasks or Objective section"
            )

    def test_active_plans_have_completion_criteria(
        self, active_plans: list[Path]
    ) -> None:
        for plan in active_plans:
            text = plan.read_text()
            assert "completion" in text.lower() or "criteria" in text.lower(), (
                f"Active plan '{plan.name}' missing completion criteria"
            )


class TestSecurityMdIterativeHandSecurity:
    """SECURITY.md must document iterative hand security boundaries."""

    @pytest.fixture()
    def security_text(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    def test_iterative_hand_security_section_exists(self, security_text: str) -> None:
        assert "## Iterative hand security boundaries" in security_text, (
            "SECURITY.md is missing '## Iterative hand security boundaries' section"
        )

    @pytest.mark.parametrize(
        "subsection",
        [
            "### BasicLangGraphHand",
            "No subprocess sandboxing",
            "Tool dispatch",
            "Network access",
            "Context window",
        ],
    )
    def test_iterative_security_subsections(
        self, security_text: str, subsection: str
    ) -> None:
        section = security_text.split("## Iterative hand security boundaries")[1]
        assert subsection in section, (
            f"SECURITY.md iterative hand section missing '{subsection}'"
        )

    def test_mitigation_recommendation(self, security_text: str) -> None:
        """Should recommend running iterative hands inside Docker."""
        section = security_text.split("## Iterative hand security boundaries")[1]
        assert "docker" in section.lower(), (
            "SECURITY.md iterative section should recommend Docker isolation"
        )


class TestReliabilityMdTestPatterns:
    """RELIABILITY.md should document test-level error handling patterns."""

    @pytest.fixture()
    def reliability_text(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    def test_test_level_section_exists(self, reliability_text: str) -> None:
        assert "## Test-level error handling patterns" in reliability_text, (
            "RELIABILITY.md is missing '## Test-level error handling patterns'"
        )

    @pytest.mark.parametrize(
        "subsection",
        [
            "### Testing pure helpers in isolation",
            "### Dataclass invariants",
            "### Subprocess mocking",
            "### Security boundary tests",
        ],
    )
    def test_test_pattern_subsections(
        self, reliability_text: str, subsection: str
    ) -> None:
        assert subsection in reliability_text, (
            f"RELIABILITY.md is missing test pattern subsection '{subsection}'"
        )

    def test_mentions_mocking(self, reliability_text: str) -> None:
        """Test patterns section should mention mocking as an isolation technique."""
        section = reliability_text.split("## Test-level error handling patterns")[1]
        assert "mock" in section.lower(), (
            "RELIABILITY.md test patterns should mention mocking"
        )


class TestDesignMdAntiPatterns:
    """DESIGN.md anti-patterns section should cover key concerns."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_anti_patterns_section_exists(self, design_text: str) -> None:
        assert "## Anti-patterns to avoid" in design_text, (
            "DESIGN.md is missing '## Anti-patterns to avoid' section"
        )

    @pytest.mark.parametrize(
        "keyword",
        ["Global state", "Cross-layer imports", "Monolithic", "Implicit auth"],
    )
    def test_anti_pattern_keywords(self, design_text: str, keyword: str) -> None:
        section = design_text.split("## Anti-patterns to avoid")[1]
        assert keyword.lower() in section.lower(), (
            f"DESIGN.md anti-patterns section missing keyword '{keyword}'"
        )

    def test_anti_patterns_have_list_items(self, design_text: str) -> None:
        """Anti-patterns section should list at least 3 items."""
        section = design_text.split("## Anti-patterns to avoid")[1]
        items = [ln for ln in section.splitlines() if ln.strip().startswith("- **")]
        assert len(items) >= 3, (
            f"DESIGN.md anti-patterns has {len(items)} items, expected >= 3"
        )


class TestTestingMethodologyCoverageTable:
    """testing-methodology.md coverage table should have valid data."""

    @pytest.fixture()
    def methodology_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()

    def test_coverage_table_exists(self, methodology_text: str) -> None:
        assert "## Coverage targets" in methodology_text, (
            "testing-methodology.md is missing '## Coverage targets' section"
        )

    def test_coverage_table_has_backend_entry(self, methodology_text: str) -> None:
        """Should have a Backend (overall) row with test count."""
        assert re.search(r"Backend.*\d+ tests", methodology_text), (
            "testing-methodology.md coverage table missing Backend test count"
        )

    def test_coverage_table_has_frontend_entry(self, methodology_text: str) -> None:
        """Should have a Frontend row with percentage."""
        assert re.search(r"Frontend.*\d+(\.\d+)?%", methodology_text), (
            "testing-methodology.md coverage table missing Frontend percentage"
        )

    def test_anti_patterns_section_exists(self, methodology_text: str) -> None:
        assert "## Anti-patterns" in methodology_text, (
            "testing-methodology.md is missing '## Anti-patterns' section"
        )

    def test_anti_patterns_has_items(self, methodology_text: str) -> None:
        """Anti-patterns section should list at least 3 items."""
        section = methodology_text.split("## Anti-patterns")[1]
        items = [ln for ln in section.splitlines() if ln.strip().startswith("- **")]
        assert len(items) >= 3, (
            f"testing-methodology.md anti-patterns has {len(items)} items, expected >= 3"
        )


class TestClaudeMdArchitectureSubsections:
    """CLAUDE.md Architecture section should reference key concepts."""

    @pytest.fixture()
    def claude_text(self) -> str:
        return (REPO_ROOT / "CLAUDE.md").read_text()

    def test_architecture_mentions_hand_abstraction(self, claude_text: str) -> None:
        arch_section = claude_text.split("## Architecture")[1].split("## Code")[0]
        assert "hand" in arch_section.lower(), (
            "CLAUDE.md Architecture section should mention the Hand abstraction"
        )

    def test_architecture_mentions_providers(self, claude_text: str) -> None:
        arch_section = claude_text.split("## Architecture")[1].split("## Code")[0]
        assert "provider" in arch_section.lower(), (
            "CLAUDE.md Architecture section should mention providers"
        )

    def test_architecture_mentions_module_boundaries(self, claude_text: str) -> None:
        arch_section = claude_text.split("## Architecture")[1].split("## Code")[0]
        assert (
            "module boundaries" in arch_section.lower() or "### Module" in arch_section
        ), "CLAUDE.md Architecture should discuss module boundaries"

    def test_architecture_mentions_filesystem_tools(self, claude_text: str) -> None:
        arch_section = claude_text.split("## Architecture")[1].split("## Code")[0]
        assert "filesystem" in arch_section.lower(), (
            "CLAUDE.md Architecture should mention filesystem tool isolation"
        )


class TestDocsIndexCliExamples:
    """docs/index.md should have CLI examples covering key backends."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    def test_cli_examples_section_exists(self, index_text: str) -> None:
        assert "## CLI examples" in index_text, (
            "docs/index.md is missing '## CLI examples' section"
        )

    @pytest.mark.parametrize(
        "backend",
        [
            "basic-langgraph",
            "codexcli",
            "claudecodecli",
            "goose",
            "geminicli",
            "e2e",
        ],
    )
    def test_cli_example_covers_backend(self, index_text: str, backend: str) -> None:
        section = index_text.split("## CLI examples")[1]
        # Stop at next h2
        if "\n## " in section:
            section = section.split("\n## ")[0]
        assert backend in section, (
            f"docs/index.md CLI examples missing backend '{backend}'"
        )


class TestDesignMdPatternSubsections:
    """DESIGN.md Patterns section should cover all major subsystems."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.mark.parametrize(
        "heading",
        [
            "### Skill catalog",
            "### PR description",
            "### Scheduled task management",
            "### Health checks",
            "### GitHub client abstraction",
        ],
    )
    def test_pattern_subsection_exists(self, design_text: str, heading: str) -> None:
        assert heading in design_text, (
            f"DESIGN.md is missing pattern subsection '{heading}'"
        )
