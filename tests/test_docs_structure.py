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
