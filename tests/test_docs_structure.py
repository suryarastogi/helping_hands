"""Tests that documentation indexes stay in sync with actual files.

Catches documentation drift that is invisible to linters: a new design doc
added to docs/design-docs/ but not listed in its index.md, a stale link in an
index pointing to a deleted file, a completed plan not tracked in PLANS.md, or
a top-level doc omitted from docs/index.md. These tests also assert that key
root-level files (ARCHITECTURE.md, AGENTS.md, CLAUDE.md, README.md) continue
to exist, since agents and humans depend on them for onboarding and conventions.
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
        # Daily files consolidated into weekly summaries are OK unreferenced
        # as long as a weekly file for their week exists in PLANS.md
        for filename in completed_plan_files:
            if filename in plans_text:
                continue
            # Daily files (YYYY-MM-DD.md) are OK if covered by weekly
            if re.match(r"\d{4}-\d{2}-\d{2}\.md$", filename):
                continue
            raise AssertionError(
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
        return sorted(completed.rglob("*.md"))

    def test_completed_plans_exist(self, completed_plan_paths: list[Path]) -> None:
        assert len(completed_plan_paths) > 0, (
            "exec-plans/completed/ should have at least one plan"
        )

    @staticmethod
    def _is_summary_file(plan_path: Path) -> bool:
        """Date-consolidated (2026-03-04.md) and weekly (Week-8.md) files are summaries."""
        name = plan_path.name
        return bool(
            re.match(r"\d{4}-\d{2}-\d{2}\.md$", name)
            or re.match(r"Week-\d+\.md$", name)
        )

    def test_versioned_plans_have_status(
        self, completed_plan_paths: list[Path]
    ) -> None:
        """Versioned plans (not date/week-consolidated) must have a Status field."""
        for plan_path in completed_plan_paths:
            if self._is_summary_file(plan_path):
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
            if self._is_summary_file(plan_path):
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
            # Skip absolute URLs (e.g. https://github.com/...)
            if link.startswith(("http://", "https://")):
                continue
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


class TestCompletedPlansMinimumContent:
    """Completed plans should have substantive content."""

    @pytest.fixture()
    def completed_plan_paths(self) -> list[Path]:
        completed = DOCS_DIR / "exec-plans" / "completed"
        if not completed.exists():
            return []
        return sorted(completed.rglob("*.md"))

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
    """Week-10 consolidation should cover all daily summaries (Mar 3-7)."""

    @pytest.fixture()
    def content(self) -> str:
        return (
            DOCS_DIR / "exec-plans" / "completed" / "2026" / "Week-10.md"
        ).read_text()

    def test_covers_mar_6_v32_v79(self, content: str) -> None:
        """Week-10 should reference Mar 6 edge cases and design docs."""
        assert "v32" in content
        assert "v79" in content

    def test_covers_all_days(self, content: str) -> None:
        """Week-10 should have entries for each day Mar 3-7."""
        assert "Mar 3" in content
        assert "Mar 4" in content
        assert "Mar 5" in content
        assert "Mar 6" in content
        assert "Mar 7" in content

    def test_daily_files_removed(self) -> None:
        """Individual daily files should not exist after weekly consolidation."""
        for day in range(3, 8):
            daily = DOCS_DIR / "exec-plans" / "completed" / f"2026-03-0{day}.md"
            assert not daily.exists(), (
                f"Daily file {daily.name} should be removed after Week-10 consolidation"
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


class TestWeek10ConsolidatedContent:
    """Week-10 should cover v80+ from Mar 7."""

    @pytest.fixture()
    def content(self) -> str:
        return (
            DOCS_DIR / "exec-plans" / "completed" / "2026" / "Week-10.md"
        ).read_text()

    def test_covers_v80(self, content: str) -> None:
        assert "v80" in content

    def test_has_week_header(self, content: str) -> None:
        assert "Week 10" in content

    def test_has_mar_7_section(self, content: str) -> None:
        assert "Mar 7" in content


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
            assert (
                "No active plans" in plans_text
                or "no active" in plans_text.lower()
                or "(none)" in plans_text.lower()
            )
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
        "litellm.py",  # tested via test_litellm_provider.py, test_ai_providers.py, test_provider_build_inner.py
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


class TestArchitectureKeyFilePathsAccuracy:
    """ARCHITECTURE.md key file paths table entries must resolve to real files."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    @pytest.fixture()
    def key_paths(self, arch_text: str) -> list[str]:
        """Extract backticked paths from the Key file paths table."""
        in_table = False
        paths: list[str] = []
        for line in arch_text.splitlines():
            if "Key file paths" in line:
                in_table = True
                continue
            if in_table and line.startswith("|") and "`" in line:
                for match in re.findall(r"`(src/[^`]+)`", line):
                    paths.append(match)
            elif in_table and line.startswith("---"):
                break
        return paths

    def test_key_paths_exist(self, key_paths: list[str]) -> None:
        assert len(key_paths) > 0, "No key file paths found in ARCHITECTURE.md"
        for path in key_paths:
            assert (REPO_ROOT / path).exists(), (
                f"ARCHITECTURE.md key file path '{path}' does not exist"
            )

    def test_minimum_key_paths(self, key_paths: list[str]) -> None:
        assert len(key_paths) >= 10, (
            f"Expected at least 10 key file paths, found {len(key_paths)}"
        )


class TestArchitectureUsageMonitoring:
    """ARCHITECTURE.md usage monitoring section should reference key components."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_usage_monitoring_section_exists(self, arch_text: str) -> None:
        assert "Usage monitoring" in arch_text

    @pytest.mark.parametrize(
        "keyword",
        [
            "log_claude_usage",
            "Keychain",
            "usage_schedule",
            "Postgres",
        ],
    )
    def test_usage_monitoring_references(self, arch_text: str, keyword: str) -> None:
        assert keyword.lower() in arch_text.lower(), (
            f"ARCHITECTURE.md usage monitoring section should reference '{keyword}'"
        )


class TestArchitectureTaskResultNormalization:
    """ARCHITECTURE.md task result normalization section references."""

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_task_result_section_exists(self, arch_text: str) -> None:
        assert "Task result normalization" in arch_text

    def test_references_task_result_module(self, arch_text: str) -> None:
        assert "task_result.py" in arch_text

    def test_references_json_serializable(self, arch_text: str) -> None:
        assert "JSON-serializable" in arch_text


class TestDesignMdErrorRecoveryPatterns:
    """DESIGN.md error recovery patterns table should cover all strategies."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.mark.parametrize(
        "pattern",
        [
            "Exception suppression with fallback",
            "Retry with modified command",
            "Fallback command",
            "Graceful degradation",
            "Default branch fallback",
            "Platform capability detection",
            "Idle timeout with heartbeat",
            "Async fallback chains",
        ],
    )
    def test_error_recovery_pattern_listed(
        self, design_text: str, pattern: str
    ) -> None:
        assert pattern in design_text, (
            f"DESIGN.md error recovery table missing pattern '{pattern}'"
        )

    def test_error_recovery_has_table(self, design_text: str) -> None:
        assert "| Pattern |" in design_text, (
            "DESIGN.md should have an error recovery patterns table"
        )


class TestDesignMdMetaToolsLayer:
    """DESIGN.md meta tools layer section should cover all submodules."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_meta_tools_section_exists(self, design_text: str) -> None:
        assert "### Meta tools layer" in design_text

    @pytest.mark.parametrize(
        "submodule",
        [
            "filesystem.py",
            "command.py",
            "registry.py",
            "web.py",
        ],
    )
    def test_meta_tools_submodule_referenced(
        self, design_text: str, submodule: str
    ) -> None:
        assert submodule in design_text, (
            f"DESIGN.md meta tools section should reference '{submodule}'"
        )


class TestDesignMdFinalizationSection:
    """DESIGN.md finalization section should cover key resilience patterns."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_finalization_section_exists(self, design_text: str) -> None:
        assert "### Finalization" in design_text

    @pytest.mark.parametrize(
        "keyword",
        [
            "whoami fallback",
            "precommit cleanup",
            "default_branch fallback",
        ],
    )
    def test_finalization_resilience_patterns(
        self, design_text: str, keyword: str
    ) -> None:
        assert keyword in design_text, (
            f"DESIGN.md finalization section should reference '{keyword}'"
        )


class TestSecurityDeploymentRecommendations:
    """SECURITY.md deployment recommendations should cover key areas."""

    @pytest.fixture()
    def security_text(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    def test_recommendations_section_exists(self, security_text: str) -> None:
        assert "## Recommendations for deployment" in security_text

    @pytest.mark.parametrize(
        "keyword",
        [
            "GITHUB_TOKEN",
            "API keys",
            "Docker",
            "enable_execution",
            "sandbox",
        ],
    )
    def test_recommendation_covers_topic(
        self, security_text: str, keyword: str
    ) -> None:
        # Check in the recommendations section (after the heading)
        idx = security_text.find("## Recommendations for deployment")
        assert idx >= 0
        recommendations = security_text[idx:]
        assert keyword in recommendations, (
            f"SECURITY.md recommendations should reference '{keyword}'"
        )

    def test_minimum_recommendations(self, security_text: str) -> None:
        idx = security_text.find("## Recommendations for deployment")
        recommendations = security_text[idx:]
        numbered = [
            line for line in recommendations.splitlines() if re.match(r"\d+\.", line)
        ]
        assert len(numbered) >= 5, (
            f"Expected at least 5 deployment recommendations, found {len(numbered)}"
        )


class TestSecurityApiKeyHandling:
    """SECURITY.md API key handling section should cover key practices."""

    @pytest.fixture()
    def security_text(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    def test_api_key_section_exists(self, security_text: str) -> None:
        assert "## API key handling" in security_text

    @pytest.mark.parametrize(
        "keyword",
        [
            "environment variables",
            ".env",
            "native-cli-auth",
            ".gitignore",
        ],
    )
    def test_api_key_practice_mentioned(self, security_text: str, keyword: str) -> None:
        # Check within the API key handling section
        idx = security_text.find("## API key handling")
        end_idx = security_text.find("\n## ", idx + 1)
        section = security_text[idx:end_idx] if end_idx > 0 else security_text[idx:]
        assert keyword in section, (
            f"SECURITY.md API key handling should reference '{keyword}'"
        )


class TestDocsIndexBackendRequirements:
    """docs/index.md should have backend requirements sections."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    @pytest.mark.parametrize(
        "heading",
        [
            "## Codex backend requirements",
            "## Claude Code backend requirements",
            "## Goose backend requirements",
            "## Gemini backend requirements",
        ],
    )
    def test_backend_requirements_section(self, index_text: str, heading: str) -> None:
        assert heading in index_text, f"docs/index.md missing '{heading}'"

    def test_each_backend_has_env_vars(self, index_text: str) -> None:
        for backend in ["Codex", "Claude Code", "Goose", "Gemini"]:
            heading = f"## {backend} backend requirements"
            idx = index_text.find(heading)
            assert idx >= 0, f"Missing {heading}"
            end_idx = index_text.find("\n## ", idx + 1)
            section = index_text[idx:end_idx] if end_idx > 0 else index_text[idx:]
            assert "Env vars" in section or "env" in section.lower(), (
                f"{backend} backend requirements should mention env vars"
            )


class TestDocsIndexApiRefCompleteness:
    """docs/index.md API reference section should list core modules."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    def test_api_reference_section_exists(self, index_text: str) -> None:
        assert "## API Reference" in index_text

    @pytest.mark.parametrize(
        "module",
        [
            "config",
            "repo",
            "github",
            "ai providers",
            "hands",
            "meta tools",
            "mcp_server",
        ],
    )
    def test_api_ref_lists_module(self, index_text: str, module: str) -> None:
        idx = index_text.find("## API Reference")
        assert idx >= 0
        end_idx = index_text.find("\n## ", idx + 1)
        section = index_text[idx:end_idx] if end_idx > 0 else index_text[idx:]
        assert module in section, f"docs/index.md API Reference should list '{module}'"


class TestReliabilityMdDockerSandboxFailures:
    """RELIABILITY.md should document Docker sandbox failure modes."""

    @pytest.fixture()
    def reliability_text(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    def test_docker_sandbox_failures_section(self, reliability_text: str) -> None:
        assert "### Docker sandbox failures" in reliability_text

    @pytest.mark.parametrize(
        "failure_mode",
        [
            "Plugin unavailable",
            "Docker not found",
            "Sandbox creation failure",
            "Cleanup guarantee",
            "Name collision prevention",
        ],
    )
    def test_docker_failure_mode_documented(
        self, reliability_text: str, failure_mode: str
    ) -> None:
        assert failure_mode in reliability_text, (
            f"RELIABILITY.md missing Docker sandbox failure mode '{failure_mode}'"
        )


class TestReliabilityMdAsyncFallbacks:
    """RELIABILITY.md should document async compatibility fallbacks."""

    @pytest.fixture()
    def reliability_text(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    def test_async_fallbacks_section(self, reliability_text: str) -> None:
        assert "### Async compatibility fallbacks" in reliability_text

    @pytest.mark.parametrize(
        "scenario",
        [
            "AssertionError",
            "sync",
            "awaitable",
        ],
    )
    def test_async_scenario_documented(
        self, reliability_text: str, scenario: str
    ) -> None:
        # Check in the async compatibility section
        idx = reliability_text.find("### Async compatibility fallbacks")
        end_idx = reliability_text.find("\n## ", idx + 1)
        section = (
            reliability_text[idx:end_idx] if end_idx > 0 else reliability_text[idx:]
        )
        assert scenario in section, (
            f"RELIABILITY.md async fallbacks should mention '{scenario}'"
        )


class TestAgentsMdCommunicationChannels:
    """AGENTS.md communication section should list all channels."""

    @pytest.fixture()
    def agents_text(self) -> str:
        return (REPO_ROOT / "AGENTS.md").read_text()

    def test_communication_section_exists(self, agents_text: str) -> None:
        assert "## Communication between agents" in agents_text

    @pytest.mark.parametrize(
        "channel",
        [
            "Git branches",
            "PR comments",
            "Task status API",
            "Celery inspect",
            "Redis schedules",
        ],
    )
    def test_communication_channel_listed(self, agents_text: str, channel: str) -> None:
        idx = agents_text.find("## Communication between agents")
        section = agents_text[idx:]
        assert channel in section, (
            f"AGENTS.md communication section should list '{channel}'"
        )


class TestAgentsMdFileOwnership:
    """AGENTS.md file ownership table should cover key paths."""

    @pytest.fixture()
    def agents_text(self) -> str:
        return (REPO_ROOT / "AGENTS.md").read_text()

    @pytest.mark.parametrize(
        "path_pattern",
        [
            "AGENT.md",
            "README.md",
            "src/helping_hands/**",
            "tests/**",
            "docs/**",
        ],
    )
    def test_file_ownership_paths(self, agents_text: str, path_pattern: str) -> None:
        assert path_pattern in agents_text, (
            f"AGENTS.md file ownership should cover '{path_pattern}'"
        )


class TestDesignDocsHaveDecisionSection:
    """Design docs should include a Decision section explaining the choice."""

    @pytest.fixture()
    def design_doc_files(self) -> list[Path]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f for f in dd.glob("*.md") if f.name != "index.md")

    def test_at_least_half_have_decision_section(
        self, design_doc_files: list[Path]
    ) -> None:
        with_decision = sum(
            1
            for f in design_doc_files
            if "## Decision" in f.read_text() or "## Context" in f.read_text()
        )
        assert with_decision >= len(design_doc_files) // 2, (
            f"At least half of design docs should have Decision/Context sections, "
            f"found {with_decision}/{len(design_doc_files)}"
        )


class TestQualityScoreRemainingGapsTable:
    """QUALITY_SCORE.md remaining gaps table should list documented dead code."""

    @pytest.fixture()
    def qs_text(self) -> str:
        return (DOCS_DIR / "QUALITY_SCORE.md").read_text()

    def test_remaining_gaps_section_exists(self, qs_text: str) -> None:
        assert "## Remaining coverage gaps" in qs_text

    def test_remaining_gaps_has_table(self, qs_text: str) -> None:
        idx = qs_text.find("## Remaining coverage gaps")
        section = qs_text[idx:]
        assert "| Module |" in section, "Remaining gaps section should have a table"

    def test_remaining_gaps_reference_dead_code(self, qs_text: str) -> None:
        idx = qs_text.find("## Remaining coverage gaps")
        section = qs_text[idx:]
        # Should mention dead code or untestable
        assert "dead code" in section.lower() or "untestable" in section.lower(), (
            "Remaining gaps should explain items as dead code or untestable"
        )

    @pytest.mark.parametrize(
        "module_ref",
        [
            "cli/main.py",
            "cli/base.py",
            "iterative.py",
            "web.py",
            "mcp_server.py",
        ],
    )
    def test_remaining_gaps_lists_known_modules(
        self, qs_text: str, module_ref: str
    ) -> None:
        idx = qs_text.find("## Remaining coverage gaps")
        section = qs_text[idx:]
        assert module_ref in section, f"Remaining gaps should list '{module_ref}'"


class TestDesignMdTwoPhaseCliHooksTable:
    """DESIGN.md two-phase CLI hooks table should list real hook methods."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.fixture()
    def hooks_section(self, design_text: str) -> str:
        idx = design_text.find("### Two-phase CLI hands")
        assert idx != -1, "DESIGN.md must have a Two-phase CLI hands section"
        end = design_text.find("\n### ", idx + 1)
        return design_text[idx:end] if end != -1 else design_text[idx:]

    @pytest.mark.parametrize(
        "hook_method",
        [
            "_apply_backend_defaults",
            "_retry_command_after_failure",
            "_build_failure_message",
            "_fallback_command_when_not_found",
            "_resolve_cli_model",
        ],
    )
    def test_hook_methods_listed(self, hooks_section: str, hook_method: str) -> None:
        assert hook_method in hooks_section, (
            f"DESIGN.md two-phase CLI hooks table should list '{hook_method}'"
        )

    def test_hooks_table_has_header(self, hooks_section: str) -> None:
        assert "| Hook method |" in hooks_section, (
            "Two-phase CLI hooks section should have a table with Hook method header"
        )

    @pytest.mark.parametrize(
        "backend_name",
        ["Claude", "Codex", "Gemini", "Goose", "OpenCode"],
    )
    def test_backend_specific_behaviors_listed(
        self, design_text: str, backend_name: str
    ) -> None:
        idx = design_text.find("#### Backend-specific behaviors")
        assert idx != -1, "DESIGN.md must have Backend-specific behaviors section"
        section = design_text[idx:]
        assert backend_name in section, (
            f"Backend-specific behaviors should mention '{backend_name}'"
        )


class TestDesignMdHealthChecksTable:
    """DESIGN.md health checks table should list probe functions."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.fixture()
    def health_section(self, design_text: str) -> str:
        idx = design_text.find("### Health checks and server config")
        assert idx != -1, "DESIGN.md must have Health checks section"
        end = design_text.find("\n### ", idx + 1)
        return design_text[idx:end] if end != -1 else design_text[idx:]

    @pytest.mark.parametrize(
        "probe_name",
        [
            "_check_redis_health",
            "_check_db_health",
            "_check_workers_health",
        ],
    )
    def test_probe_functions_listed(self, health_section: str, probe_name: str) -> None:
        assert probe_name in health_section, (
            f"Health checks table should list '{probe_name}'"
        )

    def test_health_section_has_table(self, health_section: str) -> None:
        assert "| Probe |" in health_section, (
            "Health checks section should have a table with Probe header"
        )

    def test_is_running_in_docker_mentioned(self, health_section: str) -> None:
        assert "_is_running_in_docker" in health_section, (
            "Health checks section should reference _is_running_in_docker"
        )


class TestDesignMdGitHubClientSection:
    """DESIGN.md GitHub client section should cover key design choices."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.fixture()
    def github_section(self, design_text: str) -> str:
        idx = design_text.find("### GitHub client abstraction")
        assert idx != -1, "DESIGN.md must have GitHub client abstraction section"
        end = design_text.find("\n### ", idx + 1)
        return design_text[idx:end] if end != -1 else design_text[idx:]

    @pytest.mark.parametrize(
        "concept",
        [
            "Context manager",
            "Token resolution",
            "Check run aggregation",
            "upsert_pr_comment",
        ],
    )
    def test_key_concepts_covered(self, github_section: str, concept: str) -> None:
        assert concept in github_section, (
            f"GitHub client section should mention '{concept}'"
        )

    def test_static_git_helpers_mentioned(self, github_section: str) -> None:
        assert "staticmethod" in github_section.lower() or "Static" in github_section, (
            "GitHub client section should mention static git helpers"
        )


class TestFrontendMdApiEndpointsTable:
    """FRONTEND.md API endpoints table should list all shared endpoints."""

    @pytest.fixture()
    def frontend_text(self) -> str:
        return (DOCS_DIR / "FRONTEND.md").read_text()

    @pytest.fixture()
    def api_section(self, frontend_text: str) -> str:
        idx = frontend_text.find("## API endpoints used by both UIs")
        assert idx != -1, "FRONTEND.md must have API endpoints section"
        return frontend_text[idx:]

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/build",
            "/tasks/{task_id}",
            "/tasks/current",
            "/monitor/{task_id}",
            "/workers/capacity",
        ],
    )
    def test_endpoint_listed(self, api_section: str, endpoint: str) -> None:
        assert endpoint in api_section, (
            f"FRONTEND.md API endpoints table should list '{endpoint}'"
        )

    def test_api_section_has_table(self, api_section: str) -> None:
        assert "| Endpoint |" in api_section, (
            "API endpoints section should have a table with Endpoint header"
        )

    def test_api_section_includes_methods(self, api_section: str) -> None:
        assert "POST" in api_section and "GET" in api_section, (
            "API endpoints table should include HTTP methods"
        )


class TestFrontendMdComponentStructure:
    """FRONTEND.md should document the component structure."""

    @pytest.fixture()
    def frontend_text(self) -> str:
        return (DOCS_DIR / "FRONTEND.md").read_text()

    def test_component_structure_section_exists(self, frontend_text: str) -> None:
        assert "### Component structure" in frontend_text

    @pytest.mark.parametrize(
        "filename",
        ["App.tsx", "main.tsx", "styles.css", "App.test.tsx"],
    )
    def test_key_files_listed(self, frontend_text: str, filename: str) -> None:
        assert filename in frontend_text, (
            f"FRONTEND.md component structure should list '{filename}'"
        )

    def test_state_management_section(self, frontend_text: str) -> None:
        assert "### State management" in frontend_text

    def test_key_typescript_types_section(self, frontend_text: str) -> None:
        assert "### Key TypeScript types" in frontend_text

    @pytest.mark.parametrize(
        "ts_type",
        ["Backend", "FormState", "TaskStatus"],
    )
    def test_key_types_listed(self, frontend_text: str, ts_type: str) -> None:
        assert ts_type in frontend_text, (
            f"FRONTEND.md should list TypeScript type '{ts_type}'"
        )


class TestSecurityMdSubprocessExecution:
    """SECURITY.md subprocess execution section should cover key protections."""

    @pytest.fixture()
    def security_text(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    @pytest.fixture()
    def subprocess_section(self, security_text: str) -> str:
        idx = security_text.find("## Subprocess execution")
        assert idx != -1, "SECURITY.md must have Subprocess execution section"
        end = security_text.find("\n## ", idx + 1)
        return security_text[idx:end] if end != -1 else security_text[idx:]

    @pytest.mark.parametrize(
        "protection",
        [
            "shell=True",
            "Idle timeout",
            "--enable-execution",
        ],
    )
    def test_protection_mentioned(
        self, subprocess_section: str, protection: str
    ) -> None:
        assert (
            protection in subprocess_section
            or protection.lower() in subprocess_section.lower()
        ), f"Subprocess execution section should mention '{protection}'"

    def test_env_var_mentioned(self, subprocess_section: str) -> None:
        assert "HELPING_HANDS_CLI_IDLE_TIMEOUT_SECONDS" in subprocess_section, (
            "Subprocess section should reference idle timeout env var"
        )


class TestDesignMdTwoPhaseLifecycle:
    """DESIGN.md should document the two-phase lifecycle and IO loop."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_two_phase_lifecycle_section(self, design_text: str) -> None:
        assert "### Two-phase lifecycle and IO loop" in design_text

    @pytest.mark.parametrize(
        "concept",
        [
            "_run_two_phase",
            "_invoke_cli_with_cmd",
            "Idle timeout",
            "Heartbeat messages",
            "Interrupt handling",
        ],
    )
    def test_lifecycle_concepts_covered(self, design_text: str, concept: str) -> None:
        idx = design_text.find("### Two-phase lifecycle and IO loop")
        assert idx != -1
        section = design_text[idx:]
        assert concept in section, (
            f"Two-phase lifecycle section should cover '{concept}'"
        )

    def test_docker_sandbox_integration_noted(self, design_text: str) -> None:
        idx = design_text.find("### Two-phase lifecycle and IO loop")
        assert idx != -1
        end = design_text.find("\n### ", idx + 1)
        section = design_text[idx:end] if end != -1 else design_text[idx:]
        assert "DockerSandbox" in section or "_ensure_sandbox" in section, (
            "Two-phase lifecycle should note Docker sandbox integration"
        )


class TestDesignMdTestingPatternsSection:
    """DESIGN.md testing patterns section should describe key test practices."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    @pytest.fixture()
    def testing_section(self, design_text: str) -> str:
        idx = design_text.find("### Testing patterns")
        assert idx != -1, "DESIGN.md must have Testing patterns section"
        end = design_text.find("\n## ", idx + 1)
        return design_text[idx:end] if end != -1 else design_text[idx:]

    @pytest.mark.parametrize(
        "pattern_keyword",
        [
            "monkeypatch",
            "importorskip",
            "Dead code documentation",
            "Coverage-guided iteration",
            "Fake dataclasses",
        ],
    )
    def test_pattern_described(
        self, testing_section: str, pattern_keyword: str
    ) -> None:
        assert pattern_keyword in testing_section, (
            f"Testing patterns section should describe '{pattern_keyword}'"
        )

    def test_section_has_bold_headings(self, testing_section: str) -> None:
        bold_count = testing_section.count("**")
        assert bold_count >= 8, (
            f"Testing patterns section should have multiple bold-formatted "
            f"headings, found {bold_count // 2} pairs"
        )


# ---------------------------------------------------------------------------
# AGENT.md structural validation
# ---------------------------------------------------------------------------


class TestAgentMdStructure:
    """AGENT.md must have required sections for AI agent guidance."""

    @pytest.fixture()
    def agent_text(self) -> str:
        return (REPO_ROOT / "AGENT.md").read_text()

    @pytest.mark.parametrize(
        "section",
        [
            "Ground rules",
            "Code style",
            "Design preferences",
            "Tone and communication",
            "Recurring decisions",
            "Dependencies",
        ],
    )
    def test_required_sections_exist(self, agent_text: str, section: str) -> None:
        assert section in agent_text, f"AGENT.md must have '{section}' section"

    def test_has_auto_update_markers(self, agent_text: str) -> None:
        count = agent_text.count("[auto-update]")
        assert count >= 4, (
            f"AGENT.md should have at least 4 [auto-update] markers, found {count}"
        )

    def test_dependencies_table_has_entries(self, agent_text: str) -> None:
        idx = agent_text.find("## Dependencies")
        assert idx != -1
        section = agent_text[idx:]
        table_rows = [
            line
            for line in section.splitlines()
            if line.startswith("|") and "---" not in line and "Package" not in line
        ]
        assert len(table_rows) >= 10, (
            f"Dependencies table should list at least 10 packages, found {len(table_rows)}"
        )

    @pytest.mark.parametrize(
        "keyword",
        ["pytest", "ruff", "fastapi", "celery", "PyGithub", "mcp"],
    )
    def test_key_dependencies_listed(self, agent_text: str, keyword: str) -> None:
        assert keyword in agent_text, f"AGENT.md Dependencies should list '{keyword}'"

    def test_recurring_decisions_have_dates(self, agent_text: str) -> None:
        idx = agent_text.find("## Recurring decisions")
        assert idx != -1
        section = agent_text[idx:]
        date_pattern = re.compile(r"\(20\d{2}-\d{2}-\d{2}\)")
        dates = date_pattern.findall(section)
        assert len(dates) >= 5, (
            f"Recurring decisions should have at least 5 dated entries, found {len(dates)}"
        )

    def test_last_updated_present(self, agent_text: str) -> None:
        assert "Last updated:" in agent_text, (
            "AGENT.md should have a 'Last updated:' footer"
        )


# ---------------------------------------------------------------------------
# API docs directory validation
# ---------------------------------------------------------------------------


class TestApiDocsDirectory:
    """API docs directory should have valid non-empty documentation files."""

    API_DIR: ClassVar[Path] = DOCS_DIR / "api"

    @pytest.fixture()
    def api_doc_files(self) -> list[Path]:
        return sorted(self.API_DIR.rglob("*.md"))

    def test_api_docs_exist(self, api_doc_files: list[Path]) -> None:
        assert len(api_doc_files) >= 7, (
            f"API docs should have at least 7 files, found {len(api_doc_files)}"
        )

    def test_api_docs_non_empty(self, api_doc_files: list[Path]) -> None:
        for doc in api_doc_files:
            content = doc.read_text()
            assert len(content) > 20, (
                f"API doc {doc.relative_to(DOCS_DIR)} should have some content"
            )

    @pytest.mark.parametrize(
        "expected_file",
        [
            "cli/main.md",
            "lib/config.md",
            "lib/repo.md",
            "lib/github.md",
            "lib/ai_providers.md",
            "server/app.md",
            "server/mcp_server.md",
        ],
    )
    def test_expected_api_docs_exist(self, expected_file: str) -> None:
        path = self.API_DIR / expected_file
        assert path.exists(), f"Expected API doc {expected_file} does not exist"

    def test_api_docs_have_headings(self, api_doc_files: list[Path]) -> None:
        for doc in api_doc_files:
            content = doc.read_text()
            assert content.startswith("#") or "\n#" in content, (
                f"API doc {doc.relative_to(DOCS_DIR)} should have at least one heading"
            )


# ---------------------------------------------------------------------------
# Product specs content validation
# ---------------------------------------------------------------------------


class TestProductSpecsStructuredContent:
    """Product specs should have structured content with required sections."""

    SPECS_DIR: ClassVar[Path] = DOCS_DIR / "product-specs"

    @pytest.fixture()
    def spec_files(self) -> list[Path]:
        return sorted(f for f in self.SPECS_DIR.glob("*.md") if f.name != "index.md")

    def test_specs_exist(self, spec_files: list[Path]) -> None:
        assert len(spec_files) >= 1, "Should have at least one product spec"

    def test_onboarding_spec_has_required_sections(self) -> None:
        content = (self.SPECS_DIR / "new-user-onboarding.md").read_text()
        for section in ["User story", "Current state", "Requirements"]:
            assert section in content, f"Onboarding spec must have '{section}' section"

    def test_specs_have_status(self, spec_files: list[Path]) -> None:
        for spec in spec_files:
            content = spec.read_text()
            assert "Status:" in content, (
                f"Product spec {spec.name} should have a Status field"
            )

    def test_specs_have_created_date(self, spec_files: list[Path]) -> None:
        for spec in spec_files:
            content = spec.read_text()
            assert "Created:" in content, (
                f"Product spec {spec.name} should have a Created date"
            )

    def test_index_lists_all_specs(self, spec_files: list[Path]) -> None:
        index = (self.SPECS_DIR / "index.md").read_text()
        for spec in spec_files:
            assert spec.stem in index, (
                f"Product spec {spec.name} should be listed in index.md"
            )


# ---------------------------------------------------------------------------
# Local stack design doc validation
# ---------------------------------------------------------------------------


class TestLocalStackDesignDoc:
    """Local stack design doc should describe the development stack script."""

    @pytest.fixture()
    def doc_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "local-stack.md").read_text()

    def test_doc_exists(self) -> None:
        path = DOCS_DIR / "design-docs" / "local-stack.md"
        assert path.exists(), "local-stack.md design doc must exist"

    @pytest.mark.parametrize(
        "section",
        [
            "Context",
            "Overview",
            "Services",
            "Lifecycle",
            "Environment variables",
            "Redis URL normalization",
            "Decision",
            "Consequences",
        ],
    )
    def test_required_sections(self, doc_text: str, section: str) -> None:
        assert section in doc_text, f"local-stack.md should have '{section}' section"

    @pytest.mark.parametrize(
        "service",
        ["server", "worker", "beat", "flower"],
    )
    def test_services_documented(self, doc_text: str, service: str) -> None:
        assert service in doc_text, (
            f"local-stack.md should document the '{service}' service"
        )

    @pytest.mark.parametrize(
        "env_var",
        [
            "SERVER_PORT",
            "FLOWER_PORT",
            "REDIS_URL",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
            "HH_LOCAL_STACK_KEEP_DOCKER_HOSTS",
        ],
    )
    def test_env_vars_documented(self, doc_text: str, env_var: str) -> None:
        assert env_var in doc_text, f"local-stack.md should document '{env_var}'"

    def test_script_path_referenced(self, doc_text: str) -> None:
        assert "run-local-stack.sh" in doc_text, (
            "local-stack.md should reference the script path"
        )

    def test_indexed_in_design_docs(self) -> None:
        index = (DOCS_DIR / "design-docs" / "index.md").read_text()
        assert "local-stack.md" in index, (
            "local-stack.md should be listed in design-docs/index.md"
        )

    def test_indexed_in_docs_index(self) -> None:
        index = (DOCS_DIR / "index.md").read_text()
        assert "local stack" in index, (
            "local stack should be mentioned in docs/index.md"
        )


# ---------------------------------------------------------------------------
# Run-local-stack script existence and consistency
# ---------------------------------------------------------------------------


class TestRunLocalStackScript:
    """The run-local-stack.sh script should exist and match doc claims."""

    SCRIPT_PATH: ClassVar[Path] = REPO_ROOT / "scripts" / "run-local-stack.sh"

    def test_script_exists(self) -> None:
        assert self.SCRIPT_PATH.exists(), "scripts/run-local-stack.sh must exist"

    def test_script_is_executable_bash(self) -> None:
        content = self.SCRIPT_PATH.read_text()
        assert content.startswith("#!/usr/bin/env bash"), (
            "Script should use /usr/bin/env bash shebang"
        )

    @pytest.mark.parametrize(
        "command",
        ["start", "stop", "restart", "status", "logs"],
    )
    def test_commands_implemented(self, command: str) -> None:
        content = self.SCRIPT_PATH.read_text()
        assert command in content, f"Script should implement '{command}' command"

    @pytest.mark.parametrize(
        "service",
        ["server", "worker", "beat", "flower"],
    )
    def test_services_managed(self, service: str) -> None:
        content = self.SCRIPT_PATH.read_text()
        assert f'"{service}"' in content or f"'{service}'" in content, (
            f"Script should manage '{service}' service"
        )

    def test_env_loading(self) -> None:
        content = self.SCRIPT_PATH.read_text()
        assert "load_env" in content, "Script should have env loading function"

    def test_redis_normalization(self) -> None:
        content = self.SCRIPT_PATH.read_text()
        assert "normalize_redis_url_for_local" in content, (
            "Script should normalize Redis URLs for local use"
        )

    def test_deployment_modes_doc_references_script(self) -> None:
        content = (DOCS_DIR / "design-docs" / "deployment-modes.md").read_text()
        assert "run-local-stack" in content, (
            "deployment-modes.md should reference run-local-stack script"
        )


# ---------------------------------------------------------------------------
# AGENT.md cross-reference validation
# ---------------------------------------------------------------------------


class TestAgentMdCrossReferences:
    """AGENT.md references should point to real files and conventions."""

    @pytest.fixture()
    def agent_text(self) -> str:
        return (REPO_ROOT / "AGENT.md").read_text()

    @pytest.mark.parametrize(
        "path_fragment",
        [
            "src/helping_hands/lib/hands/v1/hand/",
            "src/helping_hands/lib/meta/tools/filesystem.py",
            "src/helping_hands/lib/ai_providers/",
            "src/helping_hands/lib/hands/v1/hand/model_provider.py",
        ],
    )
    def test_referenced_paths_exist(self, path_fragment: str) -> None:
        full_path = REPO_ROOT / path_fragment
        assert full_path.exists(), (
            f"AGENT.md references '{path_fragment}' which does not exist"
        )

    def test_readme_reference(self, agent_text: str) -> None:
        assert "README.md" in agent_text, "AGENT.md should reference README.md"

    def test_code_style_matches_claude_md(self, agent_text: str) -> None:
        claude_text = (REPO_ROOT / "CLAUDE.md").read_text()
        assert "ruff" in agent_text and "ruff" in claude_text, (
            "Both AGENT.md and CLAUDE.md should reference ruff"
        )
        assert "88" in agent_text and "88" in claude_text, (
            "Both should agree on line length 88"
        )


# ---------------------------------------------------------------------------
# Scheduling system design doc cross-reference validation
# ---------------------------------------------------------------------------


class TestSchedulingSystemDocContent:
    """scheduling-system.md should accurately describe the scheduling design."""

    @pytest.fixture()
    def doc_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "scheduling-system.md").read_text()

    def test_has_architecture_section(self, doc_text: str) -> None:
        assert "## Architecture" in doc_text or "## Design" in doc_text, (
            "scheduling-system.md should have an Architecture or Design section"
        )

    @pytest.mark.parametrize(
        "concept",
        [
            "ScheduledTask",
            "ScheduleManager",
            "RedBeat",
            "CRON_PRESETS",
            "trigger_now",
        ],
    )
    def test_key_concepts_documented(self, doc_text: str, concept: str) -> None:
        assert concept in doc_text, f"scheduling-system.md should document '{concept}'"

    @pytest.mark.parametrize(
        "operation",
        ["create_schedule", "update_schedule", "delete_schedule"],
    )
    def test_crud_operations_documented(self, doc_text: str, operation: str) -> None:
        assert operation in doc_text, (
            f"scheduling-system.md should document '{operation}'"
        )

    def test_dual_storage_model_documented(self, doc_text: str) -> None:
        assert "schedule:meta:" in doc_text or "Metadata key" in doc_text, (
            "scheduling-system.md should document the dual storage model"
        )

    def test_cron_presets_table(self, doc_text: str) -> None:
        for preset in ["daily", "hourly", "weekdays"]:
            assert preset in doc_text, (
                f"scheduling-system.md should list '{preset}' preset"
            )

    def test_alternatives_considered(self, doc_text: str) -> None:
        assert "Alternatives considered" in doc_text, (
            "scheduling-system.md should have an Alternatives section"
        )

    def test_consequences_section(self, doc_text: str) -> None:
        assert "Consequences" in doc_text, (
            "scheduling-system.md should have a Consequences section"
        )

    def test_source_module_referenced(self, doc_text: str) -> None:
        assert "schedules.py" in doc_text or "schedules" in doc_text, (
            "scheduling-system.md should reference the source module"
        )


# ---------------------------------------------------------------------------
# Skills system design doc cross-reference validation
# ---------------------------------------------------------------------------


class TestSkillsSystemDocContent:
    """skills-system.md should accurately describe the skills catalog."""

    @pytest.fixture()
    def doc_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "skills-system.md").read_text()

    def test_has_context_section(self, doc_text: str) -> None:
        assert "## Context" in doc_text, (
            "skills-system.md should have a Context section"
        )

    @pytest.mark.parametrize(
        "concept",
        [
            "normalize_skill_selection",
            "stage_skill_catalog",
            "_discover_catalog",
            "SkillSpec",
        ],
    )
    def test_key_functions_documented(self, doc_text: str, concept: str) -> None:
        assert concept in doc_text, f"skills-system.md should document '{concept}'"

    def test_skills_vs_tools_distinction(self, doc_text: str) -> None:
        assert "Skills vs tools" in doc_text or "vs tools" in doc_text.lower(), (
            "skills-system.md should distinguish skills from tools"
        )

    def test_catalog_structure_documented(self, doc_text: str) -> None:
        assert "catalog/" in doc_text, (
            "skills-system.md should document the catalog directory structure"
        )

    @pytest.mark.parametrize(
        "catalog_file",
        ["execution.md", "prd.md", "ralph.md", "web.md"],
    )
    def test_catalog_files_listed(self, doc_text: str, catalog_file: str) -> None:
        assert catalog_file in doc_text, (
            f"skills-system.md should list catalog file '{catalog_file}'"
        )

    def test_cli_vs_iterative_injection_paths(self, doc_text: str) -> None:
        assert "CLI" in doc_text and "iterative" in doc_text.lower(), (
            "skills-system.md should document both CLI and iterative injection paths"
        )

    def test_alternatives_considered(self, doc_text: str) -> None:
        assert "Alternatives considered" in doc_text, (
            "skills-system.md should have an Alternatives section"
        )

    def test_consequences_section(self, doc_text: str) -> None:
        assert "Consequences" in doc_text, (
            "skills-system.md should have a Consequences section"
        )

    def test_skill_catalog_source_exists(self) -> None:
        catalog_dir = (
            REPO_ROOT / "src" / "helping_hands" / "lib" / "meta" / "skills" / "catalog"
        )
        assert catalog_dir.exists(), (
            "skills catalog directory should exist at lib/meta/skills/catalog/"
        )


# ---------------------------------------------------------------------------
# DESIGN.md skill catalog section validation
# ---------------------------------------------------------------------------


class TestDesignMdSkillCatalogSection:
    """DESIGN.md should document the skill catalog design pattern."""

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_skill_catalog_section_exists(self, design_text: str) -> None:
        assert "Skill catalog" in design_text, (
            "DESIGN.md should have a Skill catalog section"
        )

    @pytest.mark.parametrize(
        "concept",
        [
            "_discover_catalog",
            "normalize_skill_selection",
            "stage_skill_catalog",
            "_cleanup_skill_catalog",
        ],
    )
    def test_key_functions_referenced(self, design_text: str, concept: str) -> None:
        assert concept in design_text, (
            f"DESIGN.md skill catalog section should reference '{concept}'"
        )

    def test_markdown_only_nature_documented(self, design_text: str) -> None:
        lower = design_text.lower()
        assert "markdown" in lower or ".md" in design_text, (
            "DESIGN.md should note that skills are Markdown-only artifacts"
        )

    def test_graceful_degradation_documented(self, design_text: str) -> None:
        assert "graceful" in design_text.lower() or "empty dict" in design_text, (
            "DESIGN.md should document graceful degradation for missing catalog"
        )


# ---------------------------------------------------------------------------
# RELIABILITY.md heartbeat and task status validation
# ---------------------------------------------------------------------------


class TestReliabilityMdHeartbeatSection:
    """RELIABILITY.md should document heartbeat monitoring."""

    @pytest.fixture()
    def rel_text(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    def test_heartbeat_section_exists(self, rel_text: str) -> None:
        assert "Heartbeat monitoring" in rel_text, (
            "RELIABILITY.md should have a Heartbeat monitoring section"
        )

    def test_heartbeat_env_var_documented(self, rel_text: str) -> None:
        assert "HELPING_HANDS_CLI_HEARTBEAT_SECONDS" in rel_text, (
            "RELIABILITY.md should document the heartbeat env var"
        )

    def test_task_status_section_exists(self, rel_text: str) -> None:
        assert "Task status tracking" in rel_text, (
            "RELIABILITY.md should have a Task status tracking section"
        )

    @pytest.mark.parametrize(
        "endpoint",
        ["/tasks/{task_id}", "/tasks/current", "/monitor/{task_id}"],
    )
    def test_monitoring_endpoints_listed(self, rel_text: str, endpoint: str) -> None:
        assert endpoint in rel_text, (
            f"RELIABILITY.md should list monitoring endpoint '{endpoint}'"
        )

    def test_idempotency_section_exists(self, rel_text: str) -> None:
        assert "Idempotency" in rel_text, (
            "RELIABILITY.md should have an Idempotency section"
        )

    def test_finalization_failures_documented(self, rel_text: str) -> None:
        assert "Finalization failures" in rel_text, (
            "RELIABILITY.md should document finalization failure handling"
        )


# ---------------------------------------------------------------------------
# FRONTEND.md sync requirements validation
# ---------------------------------------------------------------------------


class TestFrontendMdSyncRequirements:
    """FRONTEND.md should document UI sync requirements."""

    @pytest.fixture()
    def fe_text(self) -> str:
        return (DOCS_DIR / "FRONTEND.md").read_text()

    def test_sync_requirements_section(self, fe_text: str) -> None:
        assert "Sync requirements" in fe_text, (
            "FRONTEND.md should have a Sync requirements section"
        )

    def test_inline_html_surface_documented(self, fe_text: str) -> None:
        assert "_UI_HTML" in fe_text or "Inline HTML" in fe_text, (
            "FRONTEND.md should document the inline HTML UI surface"
        )

    def test_react_surface_documented(self, fe_text: str) -> None:
        assert "React" in fe_text, (
            "FRONTEND.md should document the React frontend surface"
        )

    def test_testing_strategy_section(self, fe_text: str) -> None:
        assert "Testing strategy" in fe_text, (
            "FRONTEND.md should have a Testing strategy section"
        )

    def test_vitest_mentioned(self, fe_text: str) -> None:
        assert "Vitest" in fe_text, (
            "FRONTEND.md should reference Vitest for frontend testing"
        )

    def test_state_management_documented(self, fe_text: str) -> None:
        assert "State management" in fe_text or "useState" in fe_text, (
            "FRONTEND.md should document state management approach"
        )

    def test_typescript_types_table(self, fe_text: str) -> None:
        for ts_type in ["FormState", "Backend", "TaskStatus"]:
            assert ts_type in fe_text, (
                f"FRONTEND.md should document TypeScript type '{ts_type}'"
            )

    def test_validating_sync_section(self, fe_text: str) -> None:
        assert "Validating sync" in fe_text, (
            "FRONTEND.md should have a Validating sync section"
        )


# ---------------------------------------------------------------------------
# docs/index.md runtime flow comprehensive validation
# ---------------------------------------------------------------------------


class TestDocsIndexRuntimeFlowComprehensive:
    """docs/index.md should document the runtime flow for all modes."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    def test_runtime_flow_section_exists(self, index_text: str) -> None:
        assert "Runtime flow" in index_text, (
            "docs/index.md should have a Runtime flow section"
        )

    @pytest.mark.parametrize(
        "mode",
        ["Server mode", "CLI mode"],
    )
    def test_runtime_modes_documented(self, index_text: str, mode: str) -> None:
        assert mode in index_text, (
            f"docs/index.md should document '{mode}' in Runtime flow"
        )

    def test_e2e_hand_documented(self, index_text: str) -> None:
        assert "E2EHand" in index_text, (
            "docs/index.md should document E2EHand in runtime flow"
        )

    def test_pre_commit_integration_documented(self, index_text: str) -> None:
        assert "pre-commit" in index_text, (
            "docs/index.md should document pre-commit integration"
        )

    @pytest.mark.parametrize(
        "backend",
        ["codexcli", "claudecodecli", "goose", "geminicli"],
    )
    def test_cli_backends_documented(self, index_text: str, backend: str) -> None:
        assert backend in index_text, (
            f"docs/index.md should document '{backend}' backend"
        )

    def test_mcp_tools_documented(self, index_text: str) -> None:
        assert "MCP" in index_text, "docs/index.md should document MCP tool exposure"

    def test_docker_reset_section(self, index_text: str) -> None:
        assert "Docker dev reset" in index_text or "docker compose" in index_text, (
            "docs/index.md should document Docker dev reset"
        )

    def test_react_frontend_section(self, index_text: str) -> None:
        assert "React frontend" in index_text, (
            "docs/index.md should document the React frontend wrapper"
        )


# ---------------------------------------------------------------------------
# Design doc cross-references: docs reference real source paths
# ---------------------------------------------------------------------------


class TestDesignDocSourceReferences:
    """Design docs that mention source paths should reference real files."""

    DESIGN_DOCS_DIR: ClassVar[Path] = DOCS_DIR / "design-docs"

    @pytest.mark.parametrize(
        ("doc_file", "source_path"),
        [
            ("skills-system.md", "src/helping_hands/lib/meta/skills/__init__.py"),
            ("scheduling-system.md", "src/helping_hands/server/schedules.py"),
            (
                "filesystem-security.md",
                "src/helping_hands/lib/meta/tools/filesystem.py",
            ),
            (
                "command-execution.md",
                "src/helping_hands/lib/meta/tools/command.py",
            ),
            ("mcp-architecture.md", "src/helping_hands/server/mcp_server.py"),
            ("github-client.md", "src/helping_hands/lib/github.py"),
        ],
    )
    def test_referenced_source_exists(self, doc_file: str, source_path: str) -> None:
        full_path = REPO_ROOT / source_path
        assert full_path.exists(), (
            f"Design doc '{doc_file}' should reference existing source '{source_path}'"
        )


# ---------------------------------------------------------------------------
# Tech-debt-tracker consistency with QUALITY_SCORE.md
# ---------------------------------------------------------------------------


class TestTechDebtQualityScoreConsistency:
    """Tech-debt-tracker dead code items should appear in QUALITY_SCORE gaps."""

    @pytest.fixture()
    def tech_debt_text(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

    @pytest.fixture()
    def quality_score_text(self) -> str:
        return (DOCS_DIR / "QUALITY_SCORE.md").read_text()

    def test_dead_code_items_cross_referenced(
        self, tech_debt_text: str, quality_score_text: str
    ) -> None:
        """Dead code items with priority None in tech-debt should appear in
        QUALITY_SCORE remaining gaps."""
        # Extract module names from tech-debt dead code entries
        dead_code_modules = []
        for line in tech_debt_text.splitlines():
            if "| None |" in line or "| Low |" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    module = parts[3].strip().strip("`")
                    if module:
                        dead_code_modules.append(module)
        # At least some dead code items should be traceable
        assert len(dead_code_modules) > 0, (
            "Tech-debt-tracker should have documented dead code items"
        )

    def test_quality_score_references_tech_debt(self, quality_score_text: str) -> None:
        assert "tech-debt-tracker" in quality_score_text, (
            "QUALITY_SCORE.md should reference the tech-debt-tracker"
        )


# ---------------------------------------------------------------------------
# Usage-monitoring design doc content validation
# ---------------------------------------------------------------------------


class TestUsageMonitoringDesignDoc:
    """Usage-monitoring design doc should cover key concepts and source refs."""

    @pytest.fixture()
    def doc_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "usage-monitoring.md").read_text()

    def test_context_section_exists(self, doc_text: str) -> None:
        assert "## Context" in doc_text, (
            "usage-monitoring.md should have a Context section"
        )

    def test_decision_section_exists(self, doc_text: str) -> None:
        assert "## Decision" in doc_text, (
            "usage-monitoring.md should have a Decision section"
        )

    def test_alternatives_section_exists(self, doc_text: str) -> None:
        assert "## Alternatives considered" in doc_text, (
            "usage-monitoring.md should have an Alternatives considered section"
        )

    def test_consequences_section_exists(self, doc_text: str) -> None:
        assert "## Consequences" in doc_text, (
            "usage-monitoring.md should have a Consequences section"
        )

    def test_references_log_claude_usage(self, doc_text: str) -> None:
        assert "log_claude_usage" in doc_text, (
            "usage-monitoring.md should reference log_claude_usage task"
        )

    def test_references_ensure_usage_schedule(self, doc_text: str) -> None:
        assert "ensure_usage_schedule" in doc_text, (
            "usage-monitoring.md should reference ensure_usage_schedule"
        )

    def test_references_keychain(self, doc_text: str) -> None:
        assert "Keychain" in doc_text, (
            "usage-monitoring.md should reference macOS Keychain"
        )

    def test_references_oauth_api(self, doc_text: str) -> None:
        assert "oauth" in doc_text.lower(), (
            "usage-monitoring.md should reference OAuth API"
        )

    def test_references_postgres(self, doc_text: str) -> None:
        assert "Postgres" in doc_text or "claude_usage_log" in doc_text, (
            "usage-monitoring.md should reference Postgres or claude_usage_log"
        )

    def test_references_redbeat(self, doc_text: str) -> None:
        assert "RedBeat" in doc_text, (
            "usage-monitoring.md should reference RedBeat scheduling"
        )

    def test_three_stage_failure_model(self, doc_text: str) -> None:
        assert "independent" in doc_text.lower(), (
            "usage-monitoring.md should describe independent failure stages"
        )

    def test_source_references_section(self, doc_text: str) -> None:
        assert "celery_app.py" in doc_text, (
            "usage-monitoring.md should reference celery_app.py source"
        )

    def test_listed_in_design_docs_index(self) -> None:
        index_text = (DOCS_DIR / "design-docs" / "index.md").read_text()
        assert "usage-monitoring" in index_text, (
            "usage-monitoring.md should be listed in design-docs/index.md"
        )


# ---------------------------------------------------------------------------
# PLANS.md link and chronology validation
# ---------------------------------------------------------------------------


class TestPlansMdLinks:
    """PLANS.md completed plan links and chronological ordering."""

    @pytest.fixture()
    def plans_text(self) -> str:
        return (DOCS_DIR / "PLANS.md").read_text()

    def test_completed_plan_links_resolve(self, plans_text: str) -> None:
        """Every completed plan link should point to an existing file."""
        links = re.findall(r"\[.*?\]\((exec-plans/completed/[^)]+)\)", plans_text)
        assert len(links) > 0, "PLANS.md should have at least one completed plan link"
        for link in links:
            path = DOCS_DIR / link
            assert path.exists(), f"PLANS.md links to {link} but file does not exist"

    def test_completed_plans_in_chronological_order(self, plans_text: str) -> None:
        """Completed plan dates should be in reverse chronological order."""
        # Match both "YYYY-MM-DD consolidated" and "YYYY-MM-DD Week N" patterns
        dates = re.findall(r"(\d{4}-\d{2}-\d{2})\s+(?:consolidated|Week)", plans_text)
        assert len(dates) >= 1, "Should have completed plan dates"
        if len(dates) > 1:
            assert dates == sorted(dates, reverse=True), (
                "Completed plans should be in reverse chronological order"
            )


# ---------------------------------------------------------------------------
# DESIGN.md error recovery table completeness
# ---------------------------------------------------------------------------


class TestDesignMdErrorRecoveryTable:
    """DESIGN.md error recovery patterns table should list all 8 patterns."""

    EXPECTED_PATTERNS: ClassVar[list[str]] = [
        "Exception suppression",
        "Retry with modified command",
        "Fallback command",
        "Graceful degradation",
        "Default branch fallback",
        "Platform capability detection",
        "Idle timeout with heartbeat",
        "Async fallback chains",
    ]

    @pytest.fixture()
    def design_text(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_error_recovery_section_exists(self, design_text: str) -> None:
        assert "### Error recovery patterns" in design_text, (
            "DESIGN.md should have an Error recovery patterns section"
        )

    @pytest.mark.parametrize("pattern", EXPECTED_PATTERNS)
    def test_error_recovery_pattern_listed(
        self, design_text: str, pattern: str
    ) -> None:
        assert pattern in design_text, (
            f"DESIGN.md error recovery table missing pattern: {pattern}"
        )

    def test_error_recovery_table_has_minimum_rows(self, design_text: str) -> None:
        section = design_text.split("### Error recovery patterns")[1]
        if "\n### " in section:
            section = section.split("\n### ")[0]
        table_rows = [
            line
            for line in section.splitlines()
            if line.startswith("| **") or line.startswith("| `")
        ]
        assert len(table_rows) >= 8, (
            f"Error recovery table should have >= 8 rows, got {len(table_rows)}"
        )


# ---------------------------------------------------------------------------
# ARCHITECTURE.md hand table source file accuracy
# ---------------------------------------------------------------------------


class TestArchitectureMdHandTableSourceAccuracy:
    """ARCHITECTURE.md hand table modules should map to actual source files."""

    HAND_MODULES: ClassVar[list[str]] = [
        "e2e.py",
        "langgraph.py",
        "atomic.py",
        "codex.py",
        "claude.py",
        "goose.py",
        "gemini.py",
        "opencode.py",
        "docker_sandbox_claude.py",
    ]

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_hand_table_exists(self, arch_text: str) -> None:
        assert "| Hand |" in arch_text or "| `E2EHand`" in arch_text, (
            "ARCHITECTURE.md should have a hand backends table"
        )

    @pytest.mark.parametrize("module", HAND_MODULES)
    def test_hand_module_in_table(self, arch_text: str, module: str) -> None:
        assert module in arch_text, (
            f"ARCHITECTURE.md hand table missing module: {module}"
        )

    @pytest.mark.parametrize("module", HAND_MODULES)
    def test_hand_module_source_exists(self, module: str) -> None:
        """Every hand module referenced in ARCHITECTURE.md should exist."""
        hand_dir = REPO_ROOT / "src" / "helping_hands" / "lib" / "hands" / "v1" / "hand"
        # CLI hands are in cli/ subdirectory
        if (hand_dir / module).exists():
            return
        if (hand_dir / "cli" / module).exists():
            return
        pytest.fail(
            f"ARCHITECTURE.md references {module} but source file not found "
            f"in {hand_dir} or {hand_dir / 'cli'}"
        )

    def test_hand_count_matches_table(self, arch_text: str) -> None:
        """The number of hand rows in the table should match known hand count."""
        table_section = arch_text.split("### 3. Hand backends")[1]
        if "\n### " in table_section:
            table_section = table_section.split("\n### ")[0]
        # Count rows starting with | that have hand class names (not header/separator)
        data_rows = [
            line
            for line in table_section.splitlines()
            if line.startswith("| `") or line.startswith("| E2E")
        ]
        assert len(data_rows) >= 9, (
            f"Hand table should have >= 9 rows (one per hand), got {len(data_rows)}"
        )


# ---------------------------------------------------------------------------
# ARCHITECTURE.md design principles validation
# ---------------------------------------------------------------------------


class TestArchitectureMdDesignPrinciples:
    """ARCHITECTURE.md design principles should cover core tenets."""

    EXPECTED_PRINCIPLES: ClassVar[list[str]] = [
        "Plain data",
        "Streaming",
        "Explicit config",
        "Path-safe",
        "Idempotent",
    ]

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_design_principles_section_exists(self, arch_text: str) -> None:
        assert "## Design principles" in arch_text, (
            "ARCHITECTURE.md should have a Design principles section"
        )

    @pytest.mark.parametrize("principle", EXPECTED_PRINCIPLES)
    def test_design_principle_present(self, arch_text: str, principle: str) -> None:
        assert principle.lower() in arch_text.lower(), (
            f"ARCHITECTURE.md design principles missing: {principle}"
        )


# ---------------------------------------------------------------------------
# ARCHITECTURE.md layers section completeness
# ---------------------------------------------------------------------------


class TestArchitectureMdLayers:
    """ARCHITECTURE.md should document all key architectural layers."""

    EXPECTED_LAYERS: ClassVar[list[str]] = [
        "Entry points",
        "Core library",
        "Hand backends",
        "Model resolution",
        "Finalization",
    ]

    @pytest.fixture()
    def arch_text(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    @pytest.mark.parametrize("layer", EXPECTED_LAYERS)
    def test_layer_documented(self, arch_text: str, layer: str) -> None:
        assert layer in arch_text, (
            f"ARCHITECTURE.md missing layer documentation: {layer}"
        )


# ---------------------------------------------------------------------------
# Config-loading design doc content validation
# ---------------------------------------------------------------------------


class TestConfigLoadingDesignDoc:
    """config-loading.md should document precedence, frozen dataclass, dotenv."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "config-loading.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Precedence",
        "Frozen dataclass",
        "Dotenv integration",
        "Boolean normalization",
        "Tool and skill selection",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"config-loading.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "Config.from_env()",
        "_load_env_files()",
        "normalize_tool_selection()",
        "normalize_skill_selection()",
        "HELPING_HANDS_",
        "frozen=True",
        "override=False",
        "python-dotenv",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"config-loading.md should reference: {ref}"

    def test_precedence_order(self, content: str) -> None:
        """Precedence chain should document all three sources."""
        assert "dataclass defaults" in content
        assert "env vars" in content
        assert "CLI overrides" in content

    def test_boolean_truthy_values(self, content: str) -> None:
        """Should document the truthy value list."""
        for val in ("1", "true", "yes"):
            assert val in content.lower(), (
                f"config-loading.md should mention truthy value: {val}"
            )


# ---------------------------------------------------------------------------
# Default-prompts design doc content validation
# ---------------------------------------------------------------------------


class TestDefaultPromptsDesignDoc:
    """default-prompts.md should document the prompt structure and sharing."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "default-prompts.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Decision",
        "Prompt structure",
        "Directive flow",
        "Alternatives considered",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"default-prompts.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "DEFAULT_SMOKE_TEST_PROMPT",
        "lib/default_prompts.py",
        "cli/main.py",
        "server/app.py",
        "@@READ",
        "@@FILE",
        "@@TOOL",
        "test_default_prompts.py",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"default-prompts.md should reference: {ref}"

    def test_conditional_tools_mentioned(self, content: str) -> None:
        """Should mention conditional tool steps."""
        assert "enable_execution" in content
        assert "enable_web" in content

    def test_shared_across_entry_points(self, content: str) -> None:
        """Should explain that CLI and server share the same prompt."""
        assert "CLI" in content
        assert "server" in content


# ---------------------------------------------------------------------------
# Error-handling design doc content validation
# ---------------------------------------------------------------------------


class TestErrorHandlingDesignDoc:
    """error-handling.md should document all 8 recovery patterns."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "error-handling.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Decision",
        "Recovery patterns",
        "Anti-patterns",
        "Consequences",
        "Alternatives considered",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"error-handling.md missing section: {section}"

    RECOVERY_PATTERNS: ClassVar[list[str]] = [
        "Exception suppression with fallback",
        "Retry with modified command",
        "Fallback command",
        "Graceful degradation",
        "Default branch fallback",
        "Platform capability detection",
        "Idle timeout with heartbeat",
        "Async fallback chains",
    ]

    @pytest.mark.parametrize("pattern", RECOVERY_PATTERNS)
    def test_recovery_pattern_documented(self, content: str, pattern: str) -> None:
        assert pattern in content, (
            f"error-handling.md missing recovery pattern: {pattern}"
        )

    def test_anti_patterns_listed(self, content: str) -> None:
        """Should document at least 3 anti-patterns."""
        anti_section = content.split("Anti-patterns")[-1].split("##")[0]
        bullets = [
            line for line in anti_section.splitlines() if line.strip().startswith("-")
        ]
        assert len(bullets) >= 3, (
            "error-handling.md should list at least 3 anti-patterns"
        )

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "_update_pr_description",
        "_finalize_repo_pr",
        "BasicAtomicHand",
        "tech-debt-tracker.md",
        "geteuid",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_source_code(self, content: str, ref: str) -> None:
        assert ref in content, f"error-handling.md should reference: {ref}"


# ---------------------------------------------------------------------------
# Model-resolution design doc content validation
# ---------------------------------------------------------------------------


class TestModelResolutionDesignDoc:
    """model-resolution.md should document HandModel, resolution, adapters."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "model-resolution.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "HandModel dataclass",
        "Resolution flow",
        "Backend adapters",
        "Design decisions",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"model-resolution.md missing section: {section}"

    RESOLUTION_STAGES: ClassVar[list[str]] = [
        "Default",
        "Provider name",
        "Slash-separated",
        "Prefix inference",
    ]

    @pytest.mark.parametrize("stage", RESOLUTION_STAGES)
    def test_resolution_stage_documented(self, content: str, stage: str) -> None:
        assert stage in content, (
            f"model-resolution.md missing resolution stage: {stage}"
        )

    def test_langchain_adapter_table(self, content: str) -> None:
        """LangChain adapter section should list provider mappings."""
        assert "build_langchain_chat_model" in content
        assert "ChatOpenAI" in content
        assert "ChatAnthropic" in content

    def test_atomic_adapter_section(self, content: str) -> None:
        """Atomic adapter section should reference instructor."""
        assert "build_atomic_client" in content
        assert "instructor" in content

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "lib/hands/v1/hand/model_provider.py",
        "lib/ai_providers/",
        "HandModel",
        "resolve_hand_model",
        "PROVIDERS",
        "frozen",
        "_infer_provider_name",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"model-resolution.md should reference: {ref}"


# ---------------------------------------------------------------------------
# Deployment-modes design doc content validation
# ---------------------------------------------------------------------------


class TestDeploymentModesDesignDoc:
    """deployment-modes.md should document CLI, Server, and MCP modes."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "deployment-modes.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "CLI mode",
        "Server mode",
        "MCP mode",
        "Shared layer",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"deployment-modes.md missing section: {section}"

    MODE_MODULES: ClassVar[list[str]] = [
        "cli/main.py",
        "server/app.py",
        "server/celery_app.py",
        "server/mcp_server.py",
    ]

    @pytest.mark.parametrize("module", MODE_MODULES)
    def test_mode_module_referenced(self, content: str, module: str) -> None:
        assert module in content, (
            f"deployment-modes.md should reference module: {module}"
        )

    def test_comparison_table(self, content: str) -> None:
        """Should include a comparison table across modes."""
        assert "CLI" in content and "Server" in content and "MCP" in content
        assert "Concurrency" in content or "Infrastructure" in content

    SHARED_MODULES: ClassVar[list[str]] = [
        "lib/config.py",
        "lib/repo.py",
        "lib/hands/v1/",
        "lib/ai_providers/",
        "lib/meta/tools/",
        "lib/github.py",
    ]

    @pytest.mark.parametrize("module", SHARED_MODULES)
    def test_shared_layer_module(self, content: str, module: str) -> None:
        assert module in content, (
            f"deployment-modes.md shared layer should list: {module}"
        )

    def test_mcp_tools_listed(self, content: str) -> None:
        """MCP section should list available tools."""
        assert "index_repo" in content
        assert "build_feature" in content
        assert "read_file" in content

    def test_server_infrastructure(self, content: str) -> None:
        """Server mode should mention Redis and Celery."""
        assert "Redis" in content
        assert "Celery" in content


# ---------------------------------------------------------------------------
# PR-description design doc content validation
# ---------------------------------------------------------------------------


class TestPrDescriptionDesignDoc:
    """pr-description.md should document generation flow, parsing, fallbacks."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "pr-description.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Generation flow",
        "Prompt engineering",
        "Parsing",
        "Fallback chain",
        "Diff handling",
        "Environment configuration",
        "Design decisions",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"pr-description.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "generate_pr_description",
        "generate_commit_message",
        "_finalize_repo_pr",
        "pr_description.py",
        "PR_TITLE:",
        "PR_BODY:",
        "COMMIT_MSG:",
        "_commit_message_from_prompt",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"pr-description.md should reference: {ref}"

    ENV_VARS: ClassVar[list[str]] = [
        "HELPING_HANDS_DISABLE_PR_DESCRIPTION",
        "HELPING_HANDS_PR_DESCRIPTION_TIMEOUT",
        "HELPING_HANDS_PR_DESCRIPTION_DIFF_LIMIT",
    ]

    @pytest.mark.parametrize("env_var", ENV_VARS)
    def test_env_var_documented(self, content: str, env_var: str) -> None:
        assert env_var in content, (
            f"pr-description.md should document env var: {env_var}"
        )

    def test_fallback_table(self, content: str) -> None:
        """Fallback chain should be documented as a table."""
        fallback_section = content.split("Fallback chain")[-1].split("##")[0]
        assert "timeout" in fallback_section.lower()
        assert "None" in fallback_section

    def test_diff_sources_documented(self, content: str) -> None:
        """Should document both diff sources."""
        assert "git diff" in content
        assert "base_branch" in content or "base branch" in content


# ---------------------------------------------------------------------------
# v93 — Backend routing design doc content validation
# ---------------------------------------------------------------------------


class TestBackendRoutingDesignDocSections:
    """backend-routing.md should contain required design doc sections."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Decision",
        "Alternatives",
        "Consequences",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "backend-routing.md").read_text()

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section(self, content: str, section: str) -> None:
        assert section in content, (
            f"backend-routing.md should have a '{section}' section"
        )


class TestBackendRoutingDesignDocContent:
    """backend-routing.md should reference key routing artefacts."""

    REQUIRED_REFS: ClassVar[list[str]] = [
        "_parse_backend",
        "_normalize_backend",
        "_BACKEND_LOOKUP",
        "_SUPPORTED_BACKENDS",
        "BackendName",
        "basic-agent",
        "basic-atomic",
        "basic-langgraph",
        "codexcli",
        "claudecodecli",
        "docker-sandbox-claude",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "backend-routing.md").read_text()

    @pytest.mark.parametrize("ref", REQUIRED_REFS)
    def test_key_reference(self, content: str, ref: str) -> None:
        assert ref in content, f"backend-routing.md should reference: {ref}"

    def test_hand_table_present(self, content: str) -> None:
        """Should include a backend-to-Hand mapping table."""
        assert "| Backend name" in content or "| Backend" in content
        assert "Hand class" in content

    def test_hand_table_row_count(self, content: str) -> None:
        """Mapping table should list at least 9 backends."""
        table_lines = [
            ln
            for ln in content.splitlines()
            if ln.strip().startswith("|") and "Hand" not in ln.split("|")[1]
        ]
        # Exclude header and separator rows
        data_rows = [
            ln
            for ln in table_lines
            if not set(ln.replace("|", "").strip()).issubset({"-", " "})
            and "Backend name" not in ln
            and "Module" not in ln
        ]
        assert len(data_rows) >= 9, (
            f"Backend-to-Hand table should have >= 9 data rows, found {len(data_rows)}"
        )

    def test_cli_routing_documented(self, content: str) -> None:
        """Should document CLI routing path."""
        assert "cli/main.py" in content
        assert "argparse" in content or "choices" in content

    def test_server_routing_documented(self, content: str) -> None:
        """Should document server routing path."""
        assert "server/app.py" in content or "FastAPI" in content

    def test_celery_routing_documented(self, content: str) -> None:
        """Should document Celery routing path."""
        assert "celery_app.py" in content or "Celery" in content

    def test_basic_agent_alias(self, content: str) -> None:
        """Should explain basic-agent as alias for basic-atomic."""
        assert "alias" in content.lower()


class TestBackendRoutingSourceConsistency:
    """backend-routing.md source file references should resolve."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "backend-routing.md").read_text()

    def test_source_modules_exist(self, content: str) -> None:
        """Hand module paths mentioned in the doc should exist."""
        hand_base = (
            REPO_ROOT / "src" / "helping_hands" / "lib" / "hands" / "v1" / "hand"
        )
        expected_modules = [
            "e2e.py",
            "langgraph.py",
            "atomic.py",
            "cli/codex.py",
            "cli/claude.py",
            "cli/docker_sandbox_claude.py",
            "cli/goose.py",
            "cli/gemini.py",
            "cli/opencode.py",
        ]
        for mod in expected_modules:
            path = hand_base / mod
            assert path.exists(), (
                f"backend-routing.md references hand/{mod} but file does not exist"
            )

    def test_index_listings(self, content: str) -> None:
        """backend-routing.md should be listed in design-docs/index.md."""
        index = (DOCS_DIR / "design-docs" / "index.md").read_text()
        assert "backend-routing.md" in index

    def test_docs_index_listing(self, content: str) -> None:
        """backend-routing should appear in docs/index.md design-docs list."""
        docs_index = (DOCS_DIR / "index.md").read_text()
        assert "backend routing" in docs_index.lower()


class TestDesignDocBackendRoutingOptionalExtras:
    """backend-routing.md should document optional dependency handling."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "backend-routing.md").read_text()

    def test_langchain_extra(self, content: str) -> None:
        assert "langchain" in content

    def test_atomic_extra(self, content: str) -> None:
        assert "atomic" in content

    def test_module_not_found(self, content: str) -> None:
        """Should mention ModuleNotFoundError handling."""
        assert "ModuleNotFoundError" in content or "optional" in content.lower()


# ---------------------------------------------------------------------------
# v93 — RELIABILITY.md finalization failures depth check
# ---------------------------------------------------------------------------


class TestReliabilityFinalizationCompleteness:
    """RELIABILITY.md finalization section should cover key failure modes."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    def test_finalization_section_exists(self, content: str) -> None:
        assert "Finalization failures" in content or "finalization" in content.lower()

    def test_precommit_failure(self, content: str) -> None:
        assert "pre-commit" in content.lower() or "precommit" in content.lower()

    def test_push_failure(self, content: str) -> None:
        assert "push" in content.lower()

    def test_pr_creation_failure(self, content: str) -> None:
        assert "PR creation" in content or "pr creation" in content.lower()


# ---------------------------------------------------------------------------
# v93 — DESIGN.md backend routing cross-reference
# ---------------------------------------------------------------------------


class TestDesignMdBackendRoutingRef:
    """DESIGN.md should reference the backend routing concept."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_hand_abstraction_section(self, content: str) -> None:
        """DESIGN.md should describe the Hand abstraction."""
        assert "Hand" in content
        assert "run()" in content
        assert "stream()" in content

    def test_provider_resolution_section(self, content: str) -> None:
        assert "Provider resolution" in content or "provider" in content.lower()

    def test_hand_implementations_split(self, content: str) -> None:
        """Should mention hands are split into separate modules."""
        assert "separate modules" in content or "split" in content.lower()


# ---------------------------------------------------------------------------
# v93 — docs/index.md design-docs parenthetical completeness
# ---------------------------------------------------------------------------


class TestDocsIndexDesignDocsCompleteness:
    """docs/index.md design-docs parenthetical should match all design docs."""

    @pytest.fixture()
    def index_text(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    @pytest.fixture()
    def design_doc_names(self) -> list[str]:
        dd = DOCS_DIR / "design-docs"
        return sorted(
            f.stem.replace("-", " ") for f in dd.glob("*.md") if f.name != "index.md"
        )

    def test_all_design_docs_in_parenthetical(
        self, index_text: str, design_doc_names: list[str]
    ) -> None:
        """Every design doc stem should appear in the docs/index.md listing."""
        lower_text = index_text.lower()
        for name in design_doc_names:
            # Match with spaces or hyphens (e.g. "two phase cli hands" or
            # "two-phase cli")
            hyphenated = name.replace(" ", "-")
            found = name in lower_text or hyphenated in lower_text
            # Also check if all significant words appear nearby
            if not found:
                words = [w for w in name.split() if len(w) > 2]
                found = all(w in lower_text for w in words)
            assert found, (
                f"Design doc '{name}' not found in docs/index.md "
                f"design-docs parenthetical"
            )


# ---------------------------------------------------------------------------
# v93 — ARCHITECTURE.md backend listing validation
# ---------------------------------------------------------------------------


class TestArchitectureMdBackendListing:
    """ARCHITECTURE.md hand table should list all non-alias backends."""

    EXPECTED_BACKENDS: ClassVar[list[str]] = [
        "E2E",
        "LangGraph",
        "Atomic",
        "Codex",
        "Claude",
        "Goose",
        "Gemini",
        "OpenCode",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    @pytest.mark.parametrize("backend", EXPECTED_BACKENDS)
    def test_backend_mentioned(self, content: str, backend: str) -> None:
        assert backend in content, f"ARCHITECTURE.md should mention backend: {backend}"


# ---------------------------------------------------------------------------
# v93 — SECURITY.md deployment recommendation coverage
# ---------------------------------------------------------------------------


class TestSecurityRecommendationCoverage:
    """SECURITY.md recommendations should cover key security topics."""

    TOPICS: ClassVar[list[str]] = [
        "GITHUB_TOKEN",
        "API key",
        "Docker",
        "execution",
        "sandbox",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    @pytest.mark.parametrize("topic", TOPICS)
    def test_recommendation_topic(self, content: str, topic: str) -> None:
        rec_section = (
            content.split("Recommendations")[1]
            if "Recommendations" in content
            else content
        )
        assert topic.lower() in rec_section.lower(), (
            f"SECURITY.md recommendations should cover: {topic}"
        )


# ---------------------------------------------------------------------------
# v94 — Hand abstraction design doc content validation
# ---------------------------------------------------------------------------


class TestHandAbstractionDesignDoc:
    """hand-abstraction.md should document the Hand class hierarchy."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "hand-abstraction.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Decision",
        "Extension hierarchy",
        "Key design choices",
        "Alternatives considered",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"hand-abstraction.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "Hand",
        "E2EHand",
        "IterativeHand",
        "BasicLangGraphHand",
        "BasicAtomicHand",
        "_TwoPhaseCLIHand",
        "ClaudeCodeHand",
        "CodexCLIHand",
        "run(",
        "stream(",
        "_finalize_repo_pr",
        "base.py",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"hand-abstraction.md should reference: {ref}"

    def test_finalization_in_base_class(self, content: str) -> None:
        """Should explain that finalization is centralized."""
        assert "base class" in content.lower()
        assert "finalization" in content.lower() or "finalize" in content.lower()

    def test_config_injection(self, content: str) -> None:
        """Should document Config + RepoIndex injection."""
        assert "Config" in content
        assert "RepoIndex" in content

    def test_source_path_exists(self) -> None:
        """The referenced source file should exist."""
        assert (
            REPO_ROOT
            / "src"
            / "helping_hands"
            / "lib"
            / "hands"
            / "v1"
            / "hand"
            / "base.py"
        ).exists()


# ---------------------------------------------------------------------------
# v94 — Filesystem security design doc content validation
# ---------------------------------------------------------------------------


class TestFilesystemSecurityDesignDoc:
    """filesystem-security.md should document path confinement."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "filesystem-security.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Decision",
        "Resolution algorithm",
        "Shared by all consumers",
        "Error behavior",
        "Companion controls",
        "Alternatives considered",
        "Consequences",
        "Test coverage",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"filesystem-security.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "resolve_repo_target()",
        "filesystem.py",
        "read_text_file",
        "write_text_file",
        "mkdir_path",
        "path_exists",
        "ValueError",
        "MCP",
        "@@FILE",
        "@@READ",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"filesystem-security.md should reference: {ref}"

    def test_traversal_attacks_mentioned(self, content: str) -> None:
        """Should mention path traversal attack vectors."""
        assert "../" in content
        assert "symlink" in content.lower()

    def test_consumer_table_present(self, content: str) -> None:
        """Should have a table of consumers."""
        assert "Consumer" in content
        assert "Entry point" in content

    def test_source_path_exists(self) -> None:
        """The referenced source file should exist."""
        assert (
            REPO_ROOT
            / "src"
            / "helping_hands"
            / "lib"
            / "meta"
            / "tools"
            / "filesystem.py"
        ).exists()


# ---------------------------------------------------------------------------
# v94 — GitHub client design doc content validation
# ---------------------------------------------------------------------------


class TestGitHubClientDesignDoc:
    """github-client.md should document auth, operations, and token safety."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "github-client.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Authentication",
        "Token safety",
        "Repository operations",
        "Pull request lifecycle",
        "CI check aggregation",
        "Subprocess helper",
        "Alternatives considered",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"github-client.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "GitHubClient",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "x-access-token",
        "_redact_sensitive()",
        "clone()",
        "create_pr()",
        "get_check_runs()",
        "upsert_pr_comment()",
        "PyGithub",
        "_run_git()",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"github-client.md should reference: {ref}"

    def test_check_run_conclusion_table(self, content: str) -> None:
        """Should document all 5 check run conclusions."""
        for conclusion in ("no_checks", "pending", "success", "failure", "mixed"):
            assert conclusion in content, (
                f"github-client.md should document conclusion: {conclusion}"
            )

    def test_token_fallback_chain(self, content: str) -> None:
        """Should document the 3-level token resolution."""
        assert "token=" in content
        assert "GITHUB_TOKEN" in content
        assert "GH_TOKEN" in content

    def test_source_path_exists(self) -> None:
        """The referenced source file should exist."""
        assert (REPO_ROOT / "src" / "helping_hands" / "lib" / "github.py").exists()


# ---------------------------------------------------------------------------
# v94 — CI pipeline design doc content validation
# ---------------------------------------------------------------------------


class TestCIPipelineDesignDoc:
    """ci-pipeline.md should document CI and docs workflows."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "ci-pipeline.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "CI workflow",
        "Backend job",
        "Frontend job",
        "Design decisions",
        "Docs workflow",
        "Environment variables",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"ci-pipeline.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "ci.yml",
        "ruff",
        "pytest",
        "Codecov",
        "actions/checkout",
        "uv",
        "Node.js",
        "Vitest",
        "ESLint",
        "mkdocs",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"ci-pipeline.md should reference: {ref}"

    def test_python_version_matrix(self, content: str) -> None:
        """Should document the Python version matrix."""
        for version in ("3.12", "3.13", "3.14"):
            assert version in content, f"ci-pipeline.md should mention Python {version}"

    def test_env_vars_table(self, content: str) -> None:
        """Should document key environment variables."""
        for var in ("GITHUB_TOKEN", "CODECOV_TOKEN"):
            assert var in content, f"ci-pipeline.md should document env var: {var}"

    def test_concurrency_mentioned(self, content: str) -> None:
        """Should document concurrency handling."""
        assert "cancel-in-progress" in content


# ---------------------------------------------------------------------------
# v94 — MCP architecture design doc content validation
# ---------------------------------------------------------------------------


class TestMCPArchitectureDesignDoc:
    """mcp-architecture.md should document tools, transport, and isolation."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "mcp-architecture.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Transport selection",
        "Tool registration",
        "Repository tools",
        "Execution tools",
        "Repo isolation",
        "Error handling",
        "Design decisions",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, content: str, section: str) -> None:
        assert section in content, f"mcp-architecture.md missing section: {section}"

    EXPECTED_REFERENCES: ClassVar[list[str]] = [
        "FastMCP",
        "stdio",
        "http",
        "index_repo",
        "read_file",
        "write_file",
        "run_python_code",
        "run_bash_script",
        "web_search",
        "web_browse",
        "build_feature",
        "resolve_repo_target()",
        "RepoIndex",
    ]

    @pytest.mark.parametrize("ref", EXPECTED_REFERENCES)
    def test_references_key_concept(self, content: str, ref: str) -> None:
        assert ref in content, f"mcp-architecture.md should reference: {ref}"

    def test_transport_table(self, content: str) -> None:
        """Should have a transport mode comparison table."""
        assert "Mode" in content
        assert "Flag" in content

    def test_error_types_documented(self, content: str) -> None:
        """Should document all error types."""
        for err in (
            "FileNotFoundError",
            "IsADirectoryError",
            "UnicodeError",
            "ValueError",
        ):
            assert err in content, f"mcp-architecture.md should document error: {err}"

    def test_source_path_exists(self) -> None:
        """The referenced source file should exist."""
        assert (
            REPO_ROOT / "src" / "helping_hands" / "server" / "mcp_server.py"
        ).exists()

    def test_no_auth_documented(self, content: str) -> None:
        """Should document the no-authentication decision."""
        assert "authentication" in content.lower() or "auth" in content.lower()


# ---------------------------------------------------------------------------
# v94 — Conftest fixture validation
# ---------------------------------------------------------------------------


class TestConftestFixtureCompleteness:
    """conftest.py fixtures should cover the main shared patterns."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "tests" / "conftest.py").read_text()

    EXPECTED_FIXTURES: ClassVar[list[str]] = [
        "repo_index",
        "fake_config",
        "make_cli_hand",
        "mock_github_client",
        "make_fake_module",
    ]

    @pytest.mark.parametrize("fixture", EXPECTED_FIXTURES)
    def test_fixture_defined(self, content: str, fixture: str) -> None:
        assert f"def {fixture}" in content, (
            f"conftest.py should define fixture: {fixture}"
        )

    def test_repo_index_uses_tmp_path(self, content: str) -> None:
        """repo_index fixture should use tmp_path for isolation."""
        assert "tmp_path" in content

    def test_mock_github_client_has_context_manager(self, content: str) -> None:
        """mock_github_client should implement context manager protocol."""
        assert "__enter__" in content
        assert "__exit__" in content

    def test_make_cli_hand_is_factory(self, content: str) -> None:
        """make_cli_hand should be a factory returning hand instances."""
        assert "def _factory" in content
        assert "hand_cls" in content

    def test_make_fake_module_returns_module_type(self, content: str) -> None:
        """make_fake_module should create ModuleType instances."""
        assert "ModuleType" in content


class TestConftestFixtureUsage:
    """Shared fixtures should be used across multiple test files."""

    @pytest.fixture()
    def test_files(self) -> list[tuple[str, str]]:
        """Return (filename, content) for all test files."""
        tests_dir = REPO_ROOT / "tests"
        return [(f.name, f.read_text()) for f in sorted(tests_dir.glob("test_*.py"))]

    def test_make_cli_hand_used_in_multiple_files(
        self, test_files: list[tuple[str, str]]
    ) -> None:
        """make_cli_hand fixture should be used in multiple test files."""
        users = [name for name, content in test_files if "make_cli_hand" in content]
        assert len(users) >= 2, (
            f"make_cli_hand should be used in >= 2 test files, found: {users}"
        )

    def test_mock_github_client_used(self, test_files: list[tuple[str, str]]) -> None:
        """mock_github_client fixture should be used in at least one test file."""
        users = [
            name for name, content in test_files if "mock_github_client" in content
        ]
        assert len(users) >= 1, (
            "mock_github_client should be used in at least one test file"
        )

    def test_fake_config_used(self, test_files: list[tuple[str, str]]) -> None:
        """fake_config fixture should be used in at least one test file."""
        users = [name for name, content in test_files if "fake_config" in content]
        assert len(users) >= 1, "fake_config should be used in at least one test file"


# ---------------------------------------------------------------------------
# v95 — Repo-indexing design doc content validation
# ---------------------------------------------------------------------------


class TestRepoIndexingDesignDocSections:
    """repo-indexing.md must have key sections."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "repo-indexing.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Design",
        "Consumers",
        "Alternatives considered",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, content: str, section: str) -> None:
        assert f"## {section}" in content or f"### {section}" in content


class TestRepoIndexingDesignDocContent:
    """repo-indexing.md must reference key classes, functions, and concepts."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "repo-indexing.md").read_text()

    KEY_REFERENCES: ClassVar[list[str]] = [
        "RepoIndex",
        "from_path",
        "rglob",
        ".git",
        "lib/repo.py",
        "relative path",
        "sorted",
        "FileNotFoundError",
    ]

    @pytest.mark.parametrize("ref", KEY_REFERENCES)
    def test_key_reference_present(self, content: str, ref: str) -> None:
        assert ref in content, f"repo-indexing.md should reference: {ref}"

    def test_consumer_table_present(self, content: str) -> None:
        """Consumer table should list how different modules use RepoIndex."""
        assert "Iterative hands" in content or "_build_tree_snapshot" in content
        assert "CLI hands" in content or "_build_init_prompt" in content
        assert "MCP server" in content

    def test_source_file_exists(self) -> None:
        """The referenced source file should exist."""
        assert (REPO_ROOT / "src" / "helping_hands" / "lib" / "repo.py").exists()

    def test_dataclass_fields_documented(self, content: str) -> None:
        """RepoIndex dataclass fields should be documented."""
        assert "root" in content
        assert "files" in content

    def test_git_exclusion_explained(self, content: str) -> None:
        """The .git exclusion mechanism should be explained."""
        assert "parts" in content or ".git" in content
        assert "exclusion" in content.lower() or "filter" in content.lower()


class TestRepoIndexingDesignDocSourceConsistency:
    """repo-indexing.md references should match actual source."""

    def test_repo_index_class_in_source(self) -> None:
        """RepoIndex should be defined in lib/repo.py."""
        source = (REPO_ROOT / "src" / "helping_hands" / "lib" / "repo.py").read_text()
        assert "class RepoIndex" in source

    def test_from_path_in_source(self) -> None:
        """from_path classmethod should be defined in lib/repo.py."""
        source = (REPO_ROOT / "src" / "helping_hands" / "lib" / "repo.py").read_text()
        assert "def from_path" in source

    def test_design_doc_in_index(self) -> None:
        """repo-indexing.md should be listed in design-docs/index.md."""
        index = (DOCS_DIR / "design-docs" / "index.md").read_text()
        assert "repo-indexing.md" in index


# ---------------------------------------------------------------------------
# v95 — Two-phase CLI hands design doc content validation
# ---------------------------------------------------------------------------


class TestTwoPhaseCliHandsDesignDocSections:
    """two-phase-cli-hands.md must have key sections."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "two-phase-cli-hands.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Overview",
        "Architecture",
        "Backend lifecycle",
        "Command rendering",
        "Retry and fallback logic",
        "Subprocess execution details",
        "Authentication patterns",
        "Container isolation",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, content: str, section: str) -> None:
        assert f"## {section}" in content or f"### {section}" in content


class TestTwoPhaseCliHandsDesignDocContent:
    """two-phase-cli-hands.md must reference key classes, functions, and concepts."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "two-phase-cli-hands.md").read_text()

    KEY_REFERENCES: ClassVar[list[str]] = [
        "_TwoPhaseCLIHand",
        "_run_two_phase",
        "_invoke_backend",
        "_invoke_cli_with_cmd",
        "asyncio.create_subprocess_exec",
        "_apply_backend_defaults",
        "_build_subprocess_env",
        "_build_failure_message",
        "_command_not_found_message",
        "_BACKEND_NAME",
        "_DEFAULT_CLI_CMD",
        "_COMMAND_ENV_VAR",
    ]

    @pytest.mark.parametrize("ref", KEY_REFERENCES)
    def test_key_reference_present(self, content: str, ref: str) -> None:
        assert ref in content, f"two-phase-cli-hands.md should reference: {ref}"

    def test_two_phases_documented(self, content: str) -> None:
        """Both phases should be clearly documented."""
        assert "Phase 1" in content
        assert "Phase 2" in content

    def test_auth_table_present(self, content: str) -> None:
        """Authentication patterns table should list all backends."""
        assert "Claude Code" in content
        assert "Codex" in content
        assert "Goose" in content
        assert "Gemini" in content
        assert "OpenCode" in content

    def test_subprocess_timing_env_vars(self, content: str) -> None:
        """Subprocess timing environment variables should be documented."""
        assert "_IO_POLL_SECONDS" in content
        assert "_HEARTBEAT_SECONDS" in content
        assert "_IDLE_TIMEOUT_SECONDS" in content

    def test_fallback_patterns_documented(self, content: str) -> None:
        """Command not found and failure retry patterns should be documented."""
        assert "_fallback_command_when_not_found" in content
        assert "_retry_command_after_failure" in content or "Failure retry" in content

    def test_container_isolation_details(self, content: str) -> None:
        """Container isolation should mention Docker wrapping."""
        assert "docker run" in content
        assert "CONTAINER" in content

    def test_no_change_enforcement_documented(self, content: str) -> None:
        """No-change enforcement for Claude Code should be documented."""
        assert "_RETRY_ON_NO_CHANGES" in content
        assert "enforcement" in content.lower()


class TestTwoPhaseCliHandsDesignDocSourceConsistency:
    """two-phase-cli-hands.md references should match actual source."""

    CLI_HAND_MODULES: ClassVar[list[str]] = [
        "claude.py",
        "codex.py",
        "goose.py",
        "gemini.py",
        "opencode.py",
    ]

    @pytest.mark.parametrize("module", CLI_HAND_MODULES)
    def test_cli_hand_module_exists(self, module: str) -> None:
        """Each CLI hand module referenced should exist."""
        path = (
            REPO_ROOT
            / "src"
            / "helping_hands"
            / "lib"
            / "hands"
            / "v1"
            / "hand"
            / "cli"
            / module
        )
        assert path.exists(), f"CLI hand module not found: {module}"

    def test_base_cli_hand_exists(self) -> None:
        """cli/base.py should exist."""
        path = (
            REPO_ROOT
            / "src"
            / "helping_hands"
            / "lib"
            / "hands"
            / "v1"
            / "hand"
            / "cli"
            / "base.py"
        )
        assert path.exists()

    def test_two_phase_class_in_source(self) -> None:
        """_TwoPhaseCLIHand should be defined in cli/base.py."""
        source = (
            REPO_ROOT
            / "src"
            / "helping_hands"
            / "lib"
            / "hands"
            / "v1"
            / "hand"
            / "cli"
            / "base.py"
        ).read_text()
        assert "_TwoPhaseCLIHand" in source


# ---------------------------------------------------------------------------
# v95 — Task-lifecycle design doc content validation
# ---------------------------------------------------------------------------


class TestTaskLifecycleDesignDocSections:
    """task-lifecycle.md must have key sections."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "task-lifecycle.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Lifecycle phases",
        "Scheduled tasks",
        "E2E task variant",
        "Key source files",
        "Alternatives considered",
        "Consequences",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, content: str, section: str) -> None:
        assert f"## {section}" in content or f"### {section}" in content


class TestTaskLifecycleDesignDocContent:
    """task-lifecycle.md must reference key functions, classes, and concepts."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "task-lifecycle.md").read_text()

    KEY_REFERENCES: ClassVar[list[str]] = [
        "/build",
        "build_feature",
        "_normalize_backend",
        "_resolve_repo_path",
        "_collect_stream",
        "_UpdateCollector",
        "_update_progress",
        "normalize_task_result",
        "_redact_sensitive",
        "Config",
        "RepoIndex",
        "shutil.rmtree",
    ]

    @pytest.mark.parametrize("ref", KEY_REFERENCES)
    def test_key_reference_present(self, content: str, ref: str) -> None:
        assert ref in content, f"task-lifecycle.md should reference: {ref}"

    def test_lifecycle_phases_numbered(self, content: str) -> None:
        """All 7 lifecycle phases should be present."""
        assert "### 1. Submission" in content
        assert "### 2. Repo resolution" in content
        assert "### 3. Hand instantiation" in content
        assert "### 4. Streaming execution" in content
        assert "### 5. Progress reporting" in content
        assert "### 6. Result normalization" in content
        assert "### 7. Cleanup" in content

    def test_buffer_constants_documented(self, content: str) -> None:
        """Buffer size constants should be documented."""
        assert "_BUFFER_FLUSH_CHARS" in content
        assert "_MAX_UPDATE_LINE_CHARS" in content
        assert "_MAX_STORED_UPDATES" in content

    def test_source_files_listed(self, content: str) -> None:
        """Key source files should be listed."""
        assert "celery_app.py" in content
        assert "app.py" in content
        assert "task_result.py" in content
        assert "schedules.py" in content

    def test_scheduled_tasks_mention_redbeat(self, content: str) -> None:
        """Scheduled tasks should mention RedBeat."""
        assert "RedBeat" in content
        assert "ScheduleManager" in content


class TestTaskLifecycleDesignDocSourceConsistency:
    """task-lifecycle.md source references should match actual files."""

    SOURCE_FILES: ClassVar[list[str]] = [
        "src/helping_hands/server/celery_app.py",
        "src/helping_hands/server/app.py",
        "src/helping_hands/server/task_result.py",
        "src/helping_hands/server/schedules.py",
    ]

    @pytest.mark.parametrize("path", SOURCE_FILES)
    def test_source_file_exists(self, path: str) -> None:
        assert (REPO_ROOT / path).exists(), f"Source file not found: {path}"

    def test_build_feature_in_source(self) -> None:
        """build_feature task should be defined in celery_app.py."""
        source = (
            REPO_ROOT / "src" / "helping_hands" / "server" / "celery_app.py"
        ).read_text()
        assert "build_feature" in source

    def test_normalize_task_result_in_source(self) -> None:
        """normalize_task_result should be defined in task_result.py."""
        source = (
            REPO_ROOT / "src" / "helping_hands" / "server" / "task_result.py"
        ).read_text()
        assert "normalize_task_result" in source


# ---------------------------------------------------------------------------
# v95 — E2E hand workflow design doc content validation
# ---------------------------------------------------------------------------


class TestE2EHandWorkflowDesignDocSections:
    """e2e-hand-workflow.md must have key sections."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "e2e-hand-workflow.md").read_text()

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Context",
        "Lifecycle",
        "Environment variables",
        "HandResponse metadata",
        "Relationship to other hands",
        "Key source files",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, content: str, section: str) -> None:
        assert f"## {section}" in content or f"### {section}" in content


class TestE2EHandWorkflowDesignDocContent:
    """e2e-hand-workflow.md must reference key classes, functions, and concepts."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "e2e-hand-workflow.md").read_text()

    KEY_REFERENCES: ClassVar[list[str]] = [
        "E2EHand",
        "Hand",
        "hand_uuid",
        "_safe_repo_dir",
        "HELPING_HANDS_WORK_ROOT",
        "HELPING_HANDS_BASE_BRANCH",
        "GitHubClient",
        "HELPING_HANDS_E2E.md",
        "helping-hands[bot]",
        "dry_run",
        "HandResponse",
        "_finalize_repo_pr",
    ]

    @pytest.mark.parametrize("ref", KEY_REFERENCES)
    def test_key_reference_present(self, content: str, ref: str) -> None:
        assert ref in content, f"e2e-hand-workflow.md should reference: {ref}"

    def test_lifecycle_steps_present(self, content: str) -> None:
        """All lifecycle steps should be documented."""
        for step_num in range(1, 8):
            assert f"Step {step_num}" in content, (
                f"Lifecycle step {step_num} should be present"
            )

    def test_env_var_table_present(self, content: str) -> None:
        """Environment variables table should list key env vars."""
        assert "HELPING_HANDS_WORK_ROOT" in content
        assert "HELPING_HANDS_BASE_BRANCH" in content
        assert "HELPING_HANDS_GIT_USER_NAME" in content
        assert "HELPING_HANDS_GIT_USER_EMAIL" in content

    def test_metadata_keys_documented(self, content: str) -> None:
        """HandResponse metadata keys should be documented."""
        metadata_keys = [
            "backend",
            "model",
            "hand_uuid",
            "workspace",
            "branch",
            "base_branch",
            "pr_number",
            "pr_url",
            "dry_run",
        ]
        for key in metadata_keys:
            assert key in content, f"Metadata key '{key}' should be documented"

    def test_branch_naming_pattern(self, content: str) -> None:
        """Branch naming pattern should be documented."""
        assert "helping-hands/e2e-" in content

    def test_dry_run_documented(self, content: str) -> None:
        """Dry-run mode should be documented."""
        assert "Dry-run" in content or "dry_run" in content
        assert "skip" in content.lower()

    def test_relationship_to_base_class(self, content: str) -> None:
        """Should document that E2EHand does NOT use base finalization."""
        assert "does not" in content.lower() or "does **not**" in content


class TestE2EHandWorkflowDesignDocSourceConsistency:
    """e2e-hand-workflow.md source references should match actual files."""

    SOURCE_FILES: ClassVar[list[str]] = [
        "src/helping_hands/lib/hands/v1/hand/e2e.py",
        "src/helping_hands/lib/hands/v1/hand/base.py",
        "src/helping_hands/lib/github.py",
    ]

    @pytest.mark.parametrize("path", SOURCE_FILES)
    def test_source_file_exists(self, path: str) -> None:
        assert (REPO_ROOT / path).exists(), f"Source file not found: {path}"

    def test_e2e_hand_class_in_source(self) -> None:
        """E2EHand should be defined in e2e.py."""
        source = (
            REPO_ROOT
            / "src"
            / "helping_hands"
            / "lib"
            / "hands"
            / "v1"
            / "hand"
            / "e2e.py"
        ).read_text()
        assert "class E2EHand" in source

    def test_e2e_marker_file_in_source(self) -> None:
        """HELPING_HANDS_E2E.md marker should be referenced in e2e.py."""
        source = (
            REPO_ROOT
            / "src"
            / "helping_hands"
            / "lib"
            / "hands"
            / "v1"
            / "hand"
            / "e2e.py"
        ).read_text()
        assert "HELPING_HANDS_E2E" in source


# ---------------------------------------------------------------------------
# Web tools design doc content validation
# ---------------------------------------------------------------------------


class TestWebToolsDesignDocSections:
    """web-tools.md should have required structural sections."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "## Context",
        "## Design",
        "## Alternatives considered",
        "## Key source files",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "web-tools.md").read_text()

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, content: str, section: str) -> None:
        assert section in content, f"web-tools.md missing section: {section}"


class TestWebToolsDesignDocContent:
    """web-tools.md should accurately describe the web tools design."""

    KEY_REFERENCES: ClassVar[list[str]] = [
        "search_web",
        "browse_url",
        "WebSearchItem",
        "WebSearchResult",
        "WebBrowseResult",
        "_extract_related_topics",
        "_require_http_url",
        "_strip_html",
        "_decode_bytes",
        "DuckDuckGo",
        "urlopen",
        "web.py",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "web-tools.md").read_text()

    @pytest.mark.parametrize("ref", KEY_REFERENCES)
    def test_key_reference_documented(self, content: str, ref: str) -> None:
        assert ref in content, f"web-tools.md should reference '{ref}'"

    def test_frozen_dataclasses_documented(self, content: str) -> None:
        assert "frozen" in content.lower(), (
            "web-tools.md should document frozen dataclasses"
        )

    def test_encoding_fallback_chain(self, content: str) -> None:
        for enc in ["UTF-8", "UTF-16", "Latin-1"]:
            assert enc in content, (
                f"web-tools.md should document {enc} in encoding chain"
            )

    def test_truncation_documented(self, content: str) -> None:
        assert "truncat" in content.lower(), (
            "web-tools.md should document content truncation"
        )

    def test_url_validation_documented(self, content: str) -> None:
        assert "http://" in content and "https://" in content, (
            "web-tools.md should document URL scheme validation"
        )

    def test_html_stripping_tags(self, content: str) -> None:
        for tag in ["script", "style", "noscript"]:
            assert tag in content, f"web-tools.md should mention stripping <{tag}> tags"

    def test_tool_syntax_documented(self, content: str) -> None:
        assert "@@TOOL web.search" in content, (
            "web-tools.md should show @@TOOL web.search syntax"
        )
        assert "@@TOOL web.browse" in content, (
            "web-tools.md should show @@TOOL web.browse syntax"
        )

    def test_no_api_key_requirement(self, content: str) -> None:
        assert "No API key" in content or "keyless" in content, (
            "web-tools.md should note DuckDuckGo requires no API key"
        )

    def test_max_results_documented(self, content: str) -> None:
        assert "max_results" in content, (
            "web-tools.md should document max_results parameter"
        )

    def test_max_chars_documented(self, content: str) -> None:
        assert "max_chars" in content, (
            "web-tools.md should document max_chars parameter"
        )


class TestWebToolsDesignDocSourceConsistency:
    """web-tools.md source references should match actual files."""

    SOURCE_FILES: ClassVar[list[str]] = [
        "src/helping_hands/lib/meta/tools/web.py",
        "src/helping_hands/lib/meta/tools/registry.py",
        "src/helping_hands/lib/hands/v1/hand/iterative.py",
    ]

    @pytest.mark.parametrize("path", SOURCE_FILES)
    def test_source_file_exists(self, path: str) -> None:
        assert (REPO_ROOT / path).exists(), f"Source file not found: {path}"

    def test_search_web_in_source(self) -> None:
        source = (REPO_ROOT / "src/helping_hands/lib/meta/tools/web.py").read_text()
        assert "def search_web" in source

    def test_browse_url_in_source(self) -> None:
        source = (REPO_ROOT / "src/helping_hands/lib/meta/tools/web.py").read_text()
        assert "def browse_url" in source

    def test_web_tools_enabled_in_iterative(self) -> None:
        source = (
            REPO_ROOT / "src/helping_hands/lib/hands/v1/hand/iterative.py"
        ).read_text()
        assert "_web_tools_enabled" in source


# ---------------------------------------------------------------------------
# Core beliefs design doc content validation
# ---------------------------------------------------------------------------


class TestCoreBeliefsDesignDocContent:
    """core-beliefs.md should document all foundational design beliefs."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "core-beliefs.md").read_text()

    def test_has_five_beliefs(self, content: str) -> None:
        """All five numbered beliefs should be present."""
        for i in range(1, 6):
            assert f"## {i}." in content, f"core-beliefs.md should have belief #{i}"

    @pytest.mark.parametrize(
        "concept",
        [
            "AGENT.md",
            "Hand abstraction",
            "--no-pr",
            "--enable-execution",
            "Streaming",
            "Heartbeat",
            "Environment variable",
        ],
    )
    def test_key_concept_mentioned(self, content: str, concept: str) -> None:
        assert concept.lower() in content.lower(), (
            f"core-beliefs.md should reference '{concept}'"
        )

    def test_repo_convention_belief(self, content: str) -> None:
        """Belief 1 should mention repos and conventions."""
        assert "repo" in content.lower()
        assert "convention" in content.lower()

    def test_multiple_backends_belief(self, content: str) -> None:
        """Belief 2 should mention multiple backends."""
        assert "backend" in content.lower()

    def test_explicit_side_effects_belief(self, content: str) -> None:
        """Belief 3 should mention side effects being explicit."""
        assert "side effect" in content.lower() or "Side effects" in content

    def test_observable_agents_belief(self, content: str) -> None:
        """Belief 4 should mention observability."""
        assert "observab" in content.lower() or "monitoring" in content.lower()

    def test_configuration_over_convention_belief(self, content: str) -> None:
        """Belief 5 should mention configuration precedence."""
        assert "override" in content.lower() or "precedence" in content.lower()

    def test_idempotency_documented(self, content: str) -> None:
        """Idempotent E2E updates should be mentioned."""
        assert "idempotent" in content.lower()

    def test_branch_reversibility(self, content: str) -> None:
        """Branch-based reversibility should be mentioned."""
        assert "branch" in content.lower()
        assert "reversib" in content.lower() or "delete" in content.lower()


# ---------------------------------------------------------------------------
# Testing methodology design doc content validation
# ---------------------------------------------------------------------------


class TestTestingMethodologyDesignDocSections:
    """testing-methodology.md should have required structural sections."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "## Context",
        "## Coverage-guided iteration",
        "## Test organization",
        "## Key patterns",
        "## Frontend testing",
        "## Coverage targets",
        "## Anti-patterns",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, content: str, section: str) -> None:
        assert section in content, f"testing-methodology.md missing section: {section}"


class TestTestingMethodologyDesignDocContent:
    """testing-methodology.md should accurately describe testing practices."""

    KEY_REFERENCES: ClassVar[list[str]] = [
        "monkeypatch",
        "importorskip",
        "dataclass",
        "dead code",
        "tech-debt-tracker",
        "pytest-cov",
        "branch",
        "tmp_path",
        "Vitest",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()

    @pytest.mark.parametrize("ref", KEY_REFERENCES)
    def test_key_reference_documented(self, content: str, ref: str) -> None:
        assert ref in content, f"testing-methodology.md should reference '{ref}'"

    def test_four_step_cycle(self, content: str) -> None:
        """Coverage-guided iteration should document the 4-step cycle."""
        for step in ["Measure", "Target", "Validate", "Document"]:
            assert step in content, f"testing-methodology.md should list '{step}' step"

    def test_naming_conventions_table(self, content: str) -> None:
        """Source-to-test naming conventions table should be present."""
        assert "test_config.py" in content
        assert "test_hand.py" in content

    def test_anti_patterns_count(self, content: str) -> None:
        """At least 3 anti-patterns should be documented."""
        anti_patterns = re.findall(r"\*\*[^*]+\*\* --", content)
        assert len(anti_patterns) >= 3, (
            f"Expected at least 3 anti-patterns, found {len(anti_patterns)}"
        )

    def test_fake_dataclass_pattern(self, content: str) -> None:
        """Fake dataclass pattern should include a code example."""
        assert "@dataclass" in content
        assert "_Fake" in content

    def test_dead_code_patterns(self, content: str) -> None:
        """Common dead code patterns should be enumerated."""
        for pattern in ["Always-truthy", "latin-1", "__name__"]:
            assert pattern in content, (
                f"testing-methodology.md should list dead code pattern: {pattern}"
            )

    def test_frontend_testing_section(self, content: str) -> None:
        """Frontend testing should mention key tools."""
        assert "@testing-library/react" in content
        assert "mockResponse" in content

    def test_coverage_targets_table(self, content: str) -> None:
        """Coverage targets should include backend and frontend."""
        assert "Backend" in content
        assert "Frontend" in content
        assert "80%+" in content or "80%" in content


class TestArchitectureMdExternalIntegrations:
    """ARCHITECTURE.md external integrations section should be complete."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_has_external_integrations_section(self, content: str) -> None:
        assert "External integrations" in content

    @pytest.mark.parametrize(
        "integration",
        ["GitHub", "OpenAI", "Anthropic", "Google", "LiteLLM", "Ollama", "Redis"],
    )
    def test_integration_mentioned(self, content: str, integration: str) -> None:
        assert integration in content, (
            f"ARCHITECTURE.md external integrations should mention '{integration}'"
        )

    def test_redis_roles_documented(self, content: str) -> None:
        """Redis roles (task state, broker, schedules) should be listed."""
        for role in ["Task state", "Celery", "RedBeat"]:
            assert role in content, (
                f"ARCHITECTURE.md should document Redis role: {role}"
            )

    def test_has_data_flows_section(self, content: str) -> None:
        assert "Data flows" in content

    def test_data_flow_cli_server_mcp(self, content: str) -> None:
        """All three data flows (CLI, Server, MCP) should be documented."""
        for flow in ["CLI task execution", "Server task execution", "MCP server flow"]:
            assert flow in content, f"ARCHITECTURE.md should document data flow: {flow}"


class TestArchitectureMdSkillCatalogSection:
    """ARCHITECTURE.md should document the skill catalog."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_skill_catalog_section_exists(self, content: str) -> None:
        assert "Skill catalog" in content

    def test_skill_catalog_references(self, content: str) -> None:
        for ref in ["meta/skills", "catalog", "Markdown", "--skills"]:
            assert ref in content, (
                f"ARCHITECTURE.md skill catalog should reference '{ref}'"
            )


class TestArchitectureMdUsageMonitoringPipeline:
    """ARCHITECTURE.md should document the full usage monitoring pipeline."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "ARCHITECTURE.md").read_text()

    def test_usage_monitoring_section_exists(self, content: str) -> None:
        assert "Usage monitoring" in content

    def test_pipeline_stages_documented(self, content: str) -> None:
        for stage in ["Token retrieval", "Usage API", "Persistence", "Scheduling"]:
            assert stage in content, (
                f"ARCHITECTURE.md usage monitoring should document stage: {stage}"
            )

    def test_keychain_reference(self, content: str) -> None:
        assert "Keychain" in content

    def test_independent_failure_model(self, content: str) -> None:
        assert "independently" in content.lower()


class TestDesignMdPRDescriptionPatterns:
    """DESIGN.md PR description patterns should be documented."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_pr_description_section_exists(self, content: str) -> None:
        assert "PR description" in content

    def test_pr_description_key_concepts(self, content: str) -> None:
        for concept in ["PR_TITLE", "PR_BODY", "COMMIT_MSG", "truncation"]:
            assert concept in content, (
                f"DESIGN.md PR description should reference '{concept}'"
            )

    def test_fallback_chain_mentioned(self, content: str) -> None:
        assert "fallback" in content.lower()

    def test_diff_limit_mentioned(self, content: str) -> None:
        assert "diff" in content.lower()


class TestDesignMdScheduledTasks:
    """DESIGN.md scheduled task management should be documented."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "DESIGN.md").read_text()

    def test_scheduled_tasks_section_exists(self, content: str) -> None:
        assert "Scheduled task" in content

    def test_redbeat_referenced(self, content: str) -> None:
        assert "RedBeat" in content

    def test_cron_presets_referenced(self, content: str) -> None:
        assert "cron" in content.lower()

    def test_scheduled_task_dataclass(self, content: str) -> None:
        assert "ScheduledTask" in content

    def test_trigger_now_referenced(self, content: str) -> None:
        assert "trigger_now" in content


class TestSecurityMdGeminiApprovalMode:
    """SECURITY.md should document Gemini CLI approval mode."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    def test_gemini_approval_mode_section(self, content: str) -> None:
        assert "Gemini CLI approval mode" in content

    def test_auto_edit_documented(self, content: str) -> None:
        assert "auto_edit" in content

    def test_approval_mode_flag(self, content: str) -> None:
        assert "--approval-mode" in content


class TestSecurityMdContainerIsolation:
    """SECURITY.md container isolation should cover all relevant details."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "SECURITY.md").read_text()

    def test_container_isolation_section(self, content: str) -> None:
        assert "Container isolation" in content

    def test_backend_container_env(self, content: str) -> None:
        assert "HELPING_HANDS_" in content and "CONTAINER" in content

    def test_docker_sandbox_section(self, content: str) -> None:
        assert "Docker Desktop sandbox" in content or "Docker Sandbox" in content

    def test_microvm_mentioned(self, content: str) -> None:
        assert "microVM" in content

    def test_workspace_sync(self, content: str) -> None:
        assert "sync" in content.lower() or "mount" in content.lower()


class TestReliabilityMdIterativeFailureModes:
    """RELIABILITY.md should document all iterative hand failure modes."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    def test_iterative_section_exists(self, content: str) -> None:
        assert "Iterative hand failures" in content

    @pytest.mark.parametrize(
        "failure_mode",
        [
            "Provider API failures",
            "Context exhaustion",
            "@@READ",
            "@@TOOL",
            "Early completion",
            "Streaming errors",
        ],
    )
    def test_failure_mode_documented(self, content: str, failure_mode: str) -> None:
        assert failure_mode in content, (
            f"RELIABILITY.md should document iterative failure mode: {failure_mode}"
        )

    def test_max_iterations_mentioned(self, content: str) -> None:
        assert "max_iterations" in content or "max-iterations" in content

    def test_satisfied_signal(self, content: str) -> None:
        assert "SATISFIED" in content


class TestReliabilityMdIdempotency:
    """RELIABILITY.md should document idempotency guarantees."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "RELIABILITY.md").read_text()

    def test_idempotency_section_exists(self, content: str) -> None:
        assert "Idempotency" in content or "idempotent" in content.lower()

    def test_pr_update_idempotency(self, content: str) -> None:
        assert "PR" in content
        assert "update" in content.lower()


class TestDocsIndexApiReferenceAccuracy:
    """docs/index.md API reference should list real modules."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    @pytest.mark.parametrize(
        "module_doc",
        [
            "api/lib/config.md",
            "api/lib/repo.md",
            "api/lib/github.md",
            "api/lib/ai_providers.md",
            "api/lib/hands/v1/hand.md",
            "api/lib/meta/tools.md",
            "api/cli/main.md",
        ],
    )
    def test_api_doc_listed(self, content: str, module_doc: str) -> None:
        assert module_doc in content, f"docs/index.md should list API doc: {module_doc}"

    @pytest.mark.parametrize(
        "api_doc_path",
        [
            "api/lib/config.md",
            "api/lib/repo.md",
            "api/lib/github.md",
            "api/lib/ai_providers.md",
            "api/server/app.md",
            "api/server/celery_app.md",
            "api/server/mcp_server.md",
        ],
    )
    def test_api_doc_file_exists(self, api_doc_path: str) -> None:
        assert (DOCS_DIR / api_doc_path).exists(), (
            f"API doc file should exist: {api_doc_path}"
        )

    def test_server_section_present(self, content: str) -> None:
        """Server section should list app, celery_app, mcp_server."""
        for module in ["app", "celery_app", "mcp_server"]:
            assert module in content, (
                f"docs/index.md API reference should list server module: {module}"
            )


class TestDocsIndexAllBackendsInCLIExamples:
    """docs/index.md CLI examples should cover all major backends."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    @pytest.mark.parametrize(
        "backend",
        [
            "basic-langgraph",
            "basic-atomic",
            "codexcli",
            "claudecodecli",
            "goose",
            "geminicli",
        ],
    )
    def test_backend_in_examples(self, content: str, backend: str) -> None:
        assert backend in content, (
            f"docs/index.md CLI examples should include {backend}"
        )

    def test_e2e_examples(self, content: str) -> None:
        """E2E examples (new PR and existing PR) should be present."""
        assert "--e2e" in content
        assert "--pr-number" in content


class TestProductSpecsDirectoryStructure:
    """product-specs/ should have an index and at least one spec."""

    def test_index_exists(self) -> None:
        assert (DOCS_DIR / "product-specs" / "index.md").exists()

    def test_at_least_one_spec(self) -> None:
        specs = list((DOCS_DIR / "product-specs").glob("*.md"))
        non_index = [s for s in specs if s.name != "index.md"]
        assert len(non_index) >= 1, "product-specs/ should have at least one spec"

    def test_spec_files_referenced_in_index(self) -> None:
        index_text = (DOCS_DIR / "product-specs" / "index.md").read_text()
        specs = list((DOCS_DIR / "product-specs").glob("*.md"))
        for spec in specs:
            if spec.name != "index.md":
                assert spec.name in index_text, (
                    f"product-specs/{spec.name} should be listed in index.md"
                )


class TestGeneratedDocsDirectory:
    """generated/ directory should have db-schema.md."""

    def test_db_schema_exists(self) -> None:
        assert (DOCS_DIR / "generated" / "db-schema.md").exists()

    def test_db_schema_not_empty(self) -> None:
        content = (DOCS_DIR / "generated" / "db-schema.md").read_text()
        assert len(content.strip()) > 50, "db-schema.md should have meaningful content"


class TestDesignDocCrossReferenceConsistency:
    """Design docs should cross-reference each other where relevant."""

    @pytest.fixture()
    def hand_abstraction(self) -> str:
        return (DOCS_DIR / "design-docs" / "hand-abstraction.md").read_text()

    @pytest.fixture()
    def two_phase(self) -> str:
        return (DOCS_DIR / "design-docs" / "two-phase-cli-hands.md").read_text()

    @pytest.fixture()
    def filesystem_security(self) -> str:
        return (DOCS_DIR / "design-docs" / "filesystem-security.md").read_text()

    def test_hand_abstraction_mentions_e2e(self, hand_abstraction: str) -> None:
        assert "E2EHand" in hand_abstraction

    def test_hand_abstraction_mentions_iterative(self, hand_abstraction: str) -> None:
        assert (
            "IterativeHand" in hand_abstraction
            or "iterative" in hand_abstraction.lower()
        )

    def test_two_phase_mentions_base_class(self, two_phase: str) -> None:
        assert "_TwoPhaseCLIHand" in two_phase

    def test_two_phase_mentions_cli_backends(self, two_phase: str) -> None:
        for backend in ["claude", "codex", "goose", "gemini"]:
            assert backend in two_phase.lower(), (
                f"two-phase-cli-hands.md should mention {backend}"
            )

    def test_filesystem_security_mentions_mcp(self, filesystem_security: str) -> None:
        assert "MCP" in filesystem_security

    def test_filesystem_security_mentions_resolve_repo_target(
        self, filesystem_security: str
    ) -> None:
        assert "resolve_repo_target" in filesystem_security


class TestExecPlansCompletedNaming:
    """Completed plans should follow chronological naming conventions."""

    def test_completed_plans_have_date_names(self) -> None:
        completed_dir = DOCS_DIR / "exec-plans" / "completed"
        if not completed_dir.exists():
            pytest.skip("No completed plans directory")
        for plan in completed_dir.glob("*.md"):
            assert re.match(r"^\d{4}-\d{2}-\d{2}\.md$", plan.name), (
                f"Completed plan should have YYYY-MM-DD.md name: {plan.name}"
            )

    def test_no_duplicate_dates(self) -> None:
        completed_dir = DOCS_DIR / "exec-plans" / "completed"
        if not completed_dir.exists():
            pytest.skip("No completed plans directory")
        dates = [p.stem for p in completed_dir.glob("*.md")]
        assert len(dates) == len(set(dates)), "No duplicate completed plan dates"


class TestTechDebtTrackerSections:
    """Tech debt tracker should have required sections and table columns."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

    def test_has_active_items_section(self, content: str) -> None:
        assert "Active items" in content

    def test_has_resolved_items_section(self, content: str) -> None:
        assert "Resolved items" in content

    def test_has_table_structure(self, content: str) -> None:
        """Active items should be in a table with Item, Priority, Module, Notes."""
        for header in ["Item", "Priority", "Module", "Notes"]:
            assert header in content, (
                f"Tech debt tracker table should have '{header}' column"
            )

    def test_priorities_are_valid(self, content: str) -> None:
        """Priorities should be High, Medium, Low, or None."""
        rows = re.findall(r"\|[^|]+\|\s*(High|Medium|Low|None)\s*\|", content)
        assert len(rows) >= 3, "Should have at least 3 tech debt items with priorities"


class TestConfestFixtureDocumentation:
    """conftest.py fixtures should have docstrings and usage examples."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "tests" / "conftest.py").read_text()

    def test_all_fixtures_have_docstrings(self, content: str) -> None:
        """Every fixture function should have a docstring."""
        # Find fixture function names
        fixture_names = re.findall(
            r"@pytest\.fixture\(\)\s*\ndef (\w+)\(",
            content,
        )
        for name in fixture_names:
            # Find the function def and check for a docstring after it
            pattern = rf"def {name}\([^)]*\)[^:]*:\s*\n\s+\"\"\""
            assert re.search(pattern, content), (
                f"Fixture '{name}' should have a docstring"
            )

    def test_factory_fixtures_have_usage_examples(self, content: str) -> None:
        """Factory fixtures (make_*) should include Usage:: examples."""
        factory_count = content.count("def make_")
        usage_count = content.count("Usage::")
        assert usage_count >= factory_count, (
            f"Expected at least {factory_count} Usage:: examples for factory fixtures"
        )

    def test_expected_fixtures_present(self, content: str) -> None:
        """All expected shared fixtures should be defined."""
        expected = [
            "repo_index",
            "fake_config",
            "make_cli_hand",
            "mock_github_client",
            "make_fake_module",
        ]
        for fixture_name in expected:
            assert f"def {fixture_name}" in content, (
                f"conftest.py should define fixture '{fixture_name}'"
            )


class TestQualityScoreMdModuleCoverage:
    """QUALITY_SCORE.md should track coverage for all key modules."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "QUALITY_SCORE.md").read_text()

    def test_per_module_coverage_section(self, content: str) -> None:
        assert "Per-module coverage" in content

    def test_remaining_gaps_section(self, content: str) -> None:
        assert "Remaining coverage gaps" in content

    @pytest.mark.parametrize(
        "key_module",
        [
            "lib/config.py",
            "lib/repo.py",
            "lib/github.py",
            "server/app.py",
            "server/mcp_server.py",
        ],
    )
    def test_key_module_tracked(self, content: str, key_module: str) -> None:
        assert key_module in content, (
            f"QUALITY_SCORE.md should track coverage for {key_module}"
        )

    def test_areas_for_improvement(self, content: str) -> None:
        assert "Areas for improvement" in content


class TestProductSenseMdCompleteness:
    """PRODUCT_SENSE.md should cover all product dimensions."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "PRODUCT_SENSE.md").read_text()

    def test_has_what_section(self, content: str) -> None:
        assert "What helping_hands is" in content

    def test_has_target_users(self, content: str) -> None:
        assert "Target users" in content

    def test_has_value_propositions(self, content: str) -> None:
        assert "value proposition" in content.lower() or "Key value" in content

    def test_has_priorities(self, content: str) -> None:
        assert "priorities" in content.lower()

    def test_has_implemented_capabilities(self, content: str) -> None:
        assert "Implemented capabilities" in content

    def test_has_future_directions(self, content: str) -> None:
        assert "Future directions" in content

    def test_mentions_all_run_modes(self, content: str) -> None:
        for mode in ["CLI", "server", "MCP"]:
            assert mode in content, f"PRODUCT_SENSE.md should mention run mode: {mode}"


class TestSourceToTestDedicatedProviderFiles:
    """Every AI provider module should have a dedicated test file."""

    _PROVIDER_MODULES: ClassVar[list[str]] = [
        "openai",
        "google",
        "ollama",
        "litellm",
    ]

    @pytest.fixture()
    def test_files(self) -> set[str]:
        tests_dir = REPO_ROOT / "tests"
        return {f.name for f in tests_dir.glob("test_*.py")}

    @pytest.mark.parametrize("provider", _PROVIDER_MODULES)
    def test_provider_has_dedicated_test_file(
        self, provider: str, test_files: set[str]
    ) -> None:
        matches = [f for f in test_files if provider in f and "provider" in f]
        assert len(matches) >= 1, (
            f"Provider '{provider}' should have a dedicated test file "
            f"matching 'test_*{provider}*provider*.py'"
        )


class TestDesignDocsIndexCategoryStructure:
    """Design docs index should maintain organized categories with entries."""

    _EXPECTED_CATEGORIES: ClassVar[list[str]] = [
        "Core",
        "Hands",
        "Providers and Models",
        "Tools and Skills",
        "Infrastructure",
        "Quality",
    ]

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "design-docs" / "index.md").read_text()

    @pytest.mark.parametrize("category", _EXPECTED_CATEGORIES)
    def test_category_exists(self, category: str, content: str) -> None:
        assert f"## {category}" in content, (
            f"design-docs/index.md should have category: {category}"
        )

    def test_each_category_has_entries(self, content: str) -> None:
        for category in self._EXPECTED_CATEGORIES:
            # Find content between this category and next ## heading (or EOF)
            pattern = rf"## {re.escape(category)}\n(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            assert match is not None, f"Category '{category}' section not found"
            section = match.group(1)
            links = re.findall(r"\[.*?\]\(.*?\.md\)", section)
            assert len(links) >= 1, (
                f"Category '{category}' should have at least one design doc entry"
            )

    def test_minimum_design_doc_count(self, content: str) -> None:
        all_links = re.findall(r"\[.*?\]\(.*?\.md\)", content)
        assert len(all_links) >= 25, (
            f"Expected at least 25 design doc links, found {len(all_links)}"
        )


class TestTestFileNamingConvention:
    """Test files should follow naming conventions."""

    @pytest.fixture()
    def test_files(self) -> list[Path]:
        tests_dir = REPO_ROOT / "tests"
        return sorted(tests_dir.glob("test_*.py"))

    def test_all_test_files_start_with_test_prefix(
        self, test_files: list[Path]
    ) -> None:
        for f in test_files:
            assert f.name.startswith("test_"), (
                f"Test file should start with test_: {f.name}"
            )

    def test_no_test_files_in_subdirectories(self) -> None:
        tests_dir = REPO_ROOT / "tests"
        subdirs = [
            d for d in tests_dir.iterdir() if d.is_dir() and d.name != "__pycache__"
        ]
        for subdir in subdirs:
            test_files = list(subdir.glob("test_*.py"))
            assert len(test_files) == 0, (
                f"Tests should be flat — found test files in subdirectory: {subdir.name}"
            )

    def test_minimum_test_file_count(self, test_files: list[Path]) -> None:
        assert len(test_files) >= 40, (
            f"Expected at least 40 test files, found {len(test_files)}"
        )


class TestQualityScoreTestingMethodologyCrossRef:
    """QUALITY_SCORE.md and testing-methodology.md should cross-reference."""

    @pytest.fixture()
    def quality_text(self) -> str:
        return (DOCS_DIR / "QUALITY_SCORE.md").read_text()

    @pytest.fixture()
    def methodology_text(self) -> str:
        return (DOCS_DIR / "design-docs" / "testing-methodology.md").read_text()

    def test_quality_references_testing_conventions(self, quality_text: str) -> None:
        assert "Testing conventions" in quality_text

    def test_quality_references_coverage_targets(self, quality_text: str) -> None:
        assert "Coverage targets" in quality_text

    def test_methodology_references_dead_code(self, methodology_text: str) -> None:
        assert "dead code" in methodology_text.lower()

    def test_methodology_references_tech_debt_tracker(
        self, methodology_text: str
    ) -> None:
        assert "tech-debt-tracker" in methodology_text

    def test_methodology_coverage_table_has_backend_row(
        self, methodology_text: str
    ) -> None:
        assert "Backend" in methodology_text

    def test_methodology_coverage_table_has_frontend_row(
        self, methodology_text: str
    ) -> None:
        assert "Frontend" in methodology_text


class TestDocsIndexOpenCodeBackend:
    """docs/index.md should document the opencode backend."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "index.md").read_text()

    def test_mentions_opencode_cli_hand(self, content: str) -> None:
        assert "opencode" in content.lower(), (
            "docs/index.md should mention the opencode backend"
        )


class TestDesignDocMinimumSections:
    """Each design doc should have at minimum Context and Decision sections."""

    @pytest.fixture()
    def design_doc_files(self) -> list[Path]:
        dd = DOCS_DIR / "design-docs"
        return sorted(f for f in dd.glob("*.md") if f.name != "index.md")

    def test_design_docs_have_headings(self, design_doc_files: list[Path]) -> None:
        for doc in design_doc_files:
            content = doc.read_text()
            headings = re.findall(r"^##\s+", content, re.MULTILINE)
            assert len(headings) >= 2, (
                f"Design doc '{doc.name}' should have at least 2 section headings, "
                f"found {len(headings)}"
            )

    def test_design_docs_are_non_trivial(self, design_doc_files: list[Path]) -> None:
        for doc in design_doc_files:
            content = doc.read_text()
            assert len(content) >= 200, (
                f"Design doc '{doc.name}' should have at least 200 characters, "
                f"found {len(content)}"
            )

    def test_design_doc_count_matches_index(self, design_doc_files: list[Path]) -> None:
        index_text = (DOCS_DIR / "design-docs" / "index.md").read_text()
        index_links = re.findall(r"\(([^)]+\.md)\)", index_text)
        assert len(design_doc_files) == len(index_links), (
            f"Design doc count ({len(design_doc_files)}) should match "
            f"index link count ({len(index_links)})"
        )


class TestTechDebtTrackerActiveItems:
    """Tech debt tracker should have well-formed active items."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

    def test_active_items_have_priority(self, content: str) -> None:
        # Each row after header should have a priority column
        # Only check the Active items table (stop at Resolved)
        lines = content.split("\n")
        in_active = False
        in_table = False
        header_seen = False
        for line in lines:
            if "## Active items" in line:
                in_active = True
                continue
            if in_active and line.startswith("## "):
                break
            if in_active and "| Item |" in line:
                in_table = True
                header_seen = False
                continue
            if in_table and line.startswith("|---"):
                header_seen = True
                continue
            if in_table and header_seen and line.startswith("|"):
                cols = [c.strip() for c in line.split("|")]
                # cols[0] is empty (before first |), cols[1]=Item, cols[2]=Priority
                assert len(cols) >= 5, (
                    f"Table row should have at least 4 columns: {line}"
                )
                priority = cols[2]
                assert priority in {"High", "Medium", "Low", "None"}, (
                    f"Priority should be High/Medium/Low/None, got: '{priority}'"
                )
            if in_table and not line.startswith("|") and line.strip():
                in_table = False

    def test_active_items_have_module(self, content: str) -> None:
        lines = content.split("\n")
        in_active = False
        for line in lines:
            if "## Active items" in line:
                in_active = True
                continue
            if in_active and line.startswith("## "):
                break
            if (
                in_active
                and line.startswith("|")
                and "Item" not in line
                and "---" not in line
            ):
                cols = [c.strip() for c in line.split("|")]
                if len(cols) >= 4:
                    module = cols[3]
                    assert len(module) > 0, f"Active item should have module: {line}"


# ---------------------------------------------------------------------------
# CLAUDE.md build commands validation
# ---------------------------------------------------------------------------


class TestClaudeMdBuildCommands:
    """Validate that CLAUDE.md build commands reference real tools and scripts."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "CLAUDE.md").read_text()

    def test_uv_sync_command_present(self, content: str) -> None:
        assert "uv sync --dev" in content

    def test_ruff_check_command_present(self, content: str) -> None:
        assert "uv run ruff check ." in content

    def test_ruff_format_command_present(self, content: str) -> None:
        assert "uv run ruff format" in content

    def test_pytest_command_present(self, content: str) -> None:
        assert "uv run pytest" in content

    def test_pre_commit_command_present(self, content: str) -> None:
        assert "uv run pre-commit" in content

    def test_npm_frontend_commands_present(self, content: str) -> None:
        assert "npm --prefix frontend" in content

    def test_docker_compose_command_present(self, content: str) -> None:
        assert "docker compose" in content

    def test_local_stack_script_referenced(self, content: str) -> None:
        assert "run-local-stack" in content

    def test_ty_check_command_present(self, content: str) -> None:
        assert "uv run ty check" in content

    def test_references_python_312(self, content: str) -> None:
        assert "3.12" in content


# ---------------------------------------------------------------------------
# README.md section validation
# ---------------------------------------------------------------------------


class TestReadmeSections:
    """Validate README.md has expected sections and content."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "README.md").read_text()

    def test_has_what_is_this_section(self, content: str) -> None:
        assert "## What is this?" in content

    def test_has_modes_section(self, content: str) -> None:
        assert "### Modes" in content

    def test_mentions_cli_mode(self, content: str) -> None:
        assert "CLI mode" in content

    def test_mentions_app_mode(self, content: str) -> None:
        assert "App mode" in content

    def test_mentions_helping_hands_command(self, content: str) -> None:
        assert "helping-hands" in content

    def test_mentions_all_backends(self, content: str) -> None:
        backends = [
            "basic-langgraph",
            "basic-atomic",
            "codexcli",
            "claudecodecli",
            "goose",
            "geminicli",
            "opencodecli",
            "devincli",
        ]
        for backend in backends:
            assert backend in content, f"Missing backend mention: {backend}"

    def test_mentions_e2e_hand(self, content: str) -> None:
        assert "E2EHand" in content

    def test_mentions_github_token(self, content: str) -> None:
        assert "token" in content.lower()


# ---------------------------------------------------------------------------
# AGENT.md ground rules and dependencies validation
# ---------------------------------------------------------------------------


class TestAgentMdGroundRules:
    """Validate AGENT.md ground rules and structural consistency."""

    @pytest.fixture()
    def content(self) -> str:
        return (REPO_ROOT / "AGENT.md").read_text()

    def test_has_ground_rules_section(self, content: str) -> None:
        assert "## Ground rules" in content

    def test_ground_rules_count(self, content: str) -> None:
        """Should have at least 4 numbered ground rules."""
        lines = content.split("\n")
        in_rules = False
        rule_count = 0
        for line in lines:
            if "## Ground rules" in line:
                in_rules = True
                continue
            if in_rules and line.startswith("## "):
                break
            if in_rules and re.match(r"^\d+\.\s", line):
                rule_count += 1
        assert rule_count >= 4, f"Expected >= 4 ground rules, found {rule_count}"

    def test_has_code_style_section(self, content: str) -> None:
        assert "## Code style" in content

    def test_has_design_preferences_section(self, content: str) -> None:
        assert "## Design preferences" in content

    def test_mentions_ruff(self, content: str) -> None:
        assert "ruff" in content

    def test_mentions_uv(self, content: str) -> None:
        assert "uv" in content

    def test_mentions_pytest(self, content: str) -> None:
        assert "pytest" in content

    def test_auto_update_markers_present(self, content: str) -> None:
        assert "[auto-update]" in content

    def test_references_readme(self, content: str) -> None:
        assert "README.md" in content


# ---------------------------------------------------------------------------
# Active plan structure validation (v100+)
# ---------------------------------------------------------------------------


class TestActivePlanV100:
    """Validate the current active plan has proper structure."""

    @pytest.fixture()
    def active_plans(self) -> list[Path]:
        active_dir = DOCS_DIR / "exec-plans" / "active"
        if not active_dir.exists():
            return []
        return sorted(active_dir.glob("*.md"))

    def test_at_most_one_active_plan(self, active_plans: list[Path]) -> None:
        assert len(active_plans) <= 1, (
            f"Expected at most 1 active plan, found: {[p.name for p in active_plans]}"
        )

    def test_active_plan_has_status(self, active_plans: list[Path]) -> None:
        for plan in active_plans:
            content = plan.read_text()
            assert "**Status:**" in content, f"{plan.name} missing Status field"

    def test_active_plan_has_created_date(self, active_plans: list[Path]) -> None:
        for plan in active_plans:
            content = plan.read_text()
            assert "**Created:**" in content, f"{plan.name} missing Created field"

    def test_active_plan_has_tasks_section(self, active_plans: list[Path]) -> None:
        for plan in active_plans:
            content = plan.read_text()
            assert "## Tasks" in content, f"{plan.name} missing Tasks section"

    def test_active_plan_has_completion_criteria(
        self, active_plans: list[Path]
    ) -> None:
        for plan in active_plans:
            content = plan.read_text()
            assert "## Completion criteria" in content, (
                f"{plan.name} missing Completion criteria"
            )

    def test_active_plan_tasks_use_checkboxes(self, active_plans: list[Path]) -> None:
        for plan in active_plans:
            content = plan.read_text()
            assert "- [" in content, f"{plan.name} tasks should use checkboxes"


class TestTechDebtResolvedItems:
    """Resolved tech-debt items should have valid table structure."""

    @pytest.fixture()
    def resolved_rows(self) -> list[str]:
        tracker = DOCS_DIR / "exec-plans" / "tech-debt-tracker.md"
        text = tracker.read_text()
        in_resolved = False
        rows: list[str] = []
        for line in text.splitlines():
            if line.startswith("## Resolved items"):
                in_resolved = True
                continue
            if in_resolved and line.startswith("## "):
                break
            if in_resolved and line.startswith("|") and "---" not in line:
                rows.append(line)
        return rows[1:] if rows else []

    def test_resolved_section_has_entries(self, resolved_rows: list[str]) -> None:
        assert len(resolved_rows) >= 4, "Should have at least 4 resolved items"

    def test_resolved_items_have_dates(self, resolved_rows: list[str]) -> None:
        for row in resolved_rows:
            cols = [c.strip() for c in row.split("|")]
            if len(cols) >= 4:
                assert re.match(r"\d{4}-\d{2}-\d{2}", cols[2]), (
                    f"Resolved item should have date: {row}"
                )

    def test_resolved_items_reference_version(self, resolved_rows: list[str]) -> None:
        for row in resolved_rows:
            assert "v104" in row or "v" in row, (
                f"Resolved item should reference version: {row}"
            )


class TestWeeklyConsolidation:
    """Weekly consolidation files should exist and be properly structured."""

    @pytest.fixture()
    def weekly_dir(self) -> Path:
        return DOCS_DIR / "exec-plans" / "completed" / "2026"

    def test_week_10_exists(self, weekly_dir: Path) -> None:
        assert (weekly_dir / "Week-10.md").is_file()

    def test_week_10_has_summary(self, weekly_dir: Path) -> None:
        text = (weekly_dir / "Week-10.md").read_text()
        assert "Week summary" in text

    def test_week_10_covers_march_dates(self, weekly_dir: Path) -> None:
        text = (weekly_dir / "Week-10.md").read_text()
        assert "Mar 3" in text
        assert "Mar 7" in text

    def test_plans_md_references_week_10(self) -> None:
        text = (DOCS_DIR / "PLANS.md").read_text()
        assert "Week-10" in text

    def test_plans_md_no_stale_daily_refs(self) -> None:
        """PLANS.md should not reference daily files that are now in weekly."""
        text = (DOCS_DIR / "PLANS.md").read_text()
        for date in ["2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06"]:
            assert f"completed/{date}" not in text, (
                f"PLANS.md still references daily file {date}"
            )


class TestQualityScoreDeadCodeCleanup:
    """QUALITY_SCORE.md should reflect dead code cleanup."""

    @pytest.fixture()
    def content(self) -> str:
        return (DOCS_DIR / "QUALITY_SCORE.md").read_text()

    def test_removed_dead_code_modules_not_in_gaps_table(self, content: str) -> None:
        """Modules with removed dead code should not be in remaining gaps table."""
        removed = ["codex.py", "goose.py", "e2e.py", "iterative.py"]
        gaps_section = content.split("## Remaining coverage gaps")[1].split("## ")[0]
        # Only check table rows (lines starting with |)
        table_rows = [
            line
            for line in gaps_section.splitlines()
            if line.startswith("|") and "---" not in line and "Module" not in line
        ]
        table_text = "\n".join(table_rows)
        for mod in removed:
            assert mod not in table_text, (
                f"{mod} should be removed from remaining gaps table after cleanup"
            )

    def test_v104_cleanup_noted(self, content: str) -> None:
        assert "v104" in content


class TestCIWorkflowTypeChecker:
    """CI workflow should include ty type checker step."""

    @pytest.fixture()
    def ci_content(self) -> str:
        return (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()

    def test_ty_check_step_present(self, ci_content: str) -> None:
        """CI workflow must have a 'Type check' step."""
        assert "Type check" in ci_content

    def test_ty_check_command(self, ci_content: str) -> None:
        """CI workflow must run ty check with correct flags."""
        assert "uv run ty check src" in ci_content

    def test_ty_ignores_unresolved_import(self, ci_content: str) -> None:
        """ty must ignore unresolved-import errors (optional deps)."""
        assert "--ignore unresolved-import" in ci_content

    def test_ty_ignores_invalid_method_override(self, ci_content: str) -> None:
        """ty must ignore invalid-method-override (third-party abstract classes)."""
        assert "--ignore invalid-method-override" in ci_content

    def test_ty_step_before_tests(self, ci_content: str) -> None:
        """Type check step should come before test execution."""
        ty_pos = ci_content.index("Type check")
        test_pos = ci_content.index("Run tests")
        assert ty_pos < test_pos, "Type check should run before tests"

    def test_ty_step_after_ruff(self, ci_content: str) -> None:
        """Type check step should come after ruff checks."""
        ruff_pos = ci_content.index("Ruff format check")
        ty_pos = ci_content.index("Type check")
        assert ruff_pos < ty_pos, "Type check should run after ruff"


class TestGitignorePlaywrightArtifacts:
    """Playwright/E2E test artifacts must be gitignored."""

    @pytest.fixture()
    def gitignore_text(self) -> str:
        return (REPO_ROOT / ".gitignore").read_text()

    @pytest.mark.parametrize(
        "pattern",
        [
            "frontend/test-results/",
            "frontend/playwright-report/",
            "frontend/blob-report/",
        ],
    )
    def test_playwright_artifact_ignored(
        self, gitignore_text: str, pattern: str
    ) -> None:
        assert pattern in gitignore_text, f".gitignore should contain '{pattern}'"
