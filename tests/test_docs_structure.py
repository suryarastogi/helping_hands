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
