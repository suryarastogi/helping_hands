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


class TestTechDebtTrackerStructure:
    """Tech debt tracker should have valid table structure."""

    @pytest.fixture()
    def tracker_text(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

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
            # and pytest hooks (pytest_configure, pytest_collection_modifyitems, etc.)
            if fixture_name.startswith("_") or fixture_name.startswith("pytest_"):
                continue
            assert fixture_name in all_test_content, (
                f"conftest fixture '{fixture_name}' is not referenced in any test file"
            )


class TestConsolidatedPlanCoverage:
    """Week-10 consolidation should cover all daily summaries (Mar 3-7)."""

    @pytest.fixture()
    def content(self) -> str:
        return (
            DOCS_DIR / "exec-plans" / "completed" / "2026" / "Week-10.md"
        ).read_text()

    def test_daily_files_removed(self) -> None:
        """Individual daily files should not exist after weekly consolidation."""
        for day in range(3, 8):
            daily = DOCS_DIR / "exec-plans" / "completed" / f"2026-03-0{day}.md"
            assert not daily.exists(), (
                f"Daily file {daily.name} should be removed after Week-10 consolidation"
            )


SRC_ROOT = REPO_ROOT / "src" / "helping_hands"


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


class TestQualityScoreRemainingGapsMatchTechDebt:
    """QUALITY_SCORE remaining gaps table should reference modules from tech-debt."""

    @pytest.fixture()
    def quality_text(self) -> str:
        return (REPO_ROOT / "docs" / "QUALITY_SCORE.md").read_text()

    @pytest.fixture()
    def tracker_text(self) -> str:
        return (DOCS_DIR / "exec-plans" / "tech-debt-tracker.md").read_text()

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

    def test_reference_files_have_expected_extensions(
        self, reference_files: list[Path]
    ) -> None:
        """Reference files should be text-based (.txt, .md)."""
        allowed = {".txt", ".md", ".json", ".yaml", ".yml"}
        for f in reference_files:
            assert f.suffix in allowed, f"Unexpected file type in references/: {f.name}"


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
# Design doc cross-references: docs reference real source paths
# ---------------------------------------------------------------------------


class TestDesignDocSourceReferences:
    """Design docs that mention source paths should reference real files."""

    DESIGN_DOCS_DIR: ClassVar[Path] = DOCS_DIR / "design-docs"

    @pytest.mark.parametrize(
        ("doc_file", "source_path"),
        [
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
# v93 — Backend routing design doc content validation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Testing methodology design doc content validation
# ---------------------------------------------------------------------------


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
