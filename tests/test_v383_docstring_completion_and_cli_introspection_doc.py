"""Tests for v383: Docstring completion and CLI introspection design doc.

Protects the extension-point documentation for the two optional-extra hand
backends: BasicLangGraphHand and BasicAtomicHand are the primary subclass
targets for anyone adding a new LangGraph or Atomic Agents backend, so their
__init__ docstrings (with Args: sections) are the onboarding surface — without
them, new contributors must read the source to discover required kwargs like
``config`` and ``max_iterations``.  The Pydantic model checks ensure the
arcade leaderboard API models carry documentation for OpenAPI schema generation.
The design-doc checks prevent cli-introspection.md from being deleted or
de-listed, which would orphan the rationale behind --version, --list-backends,
--list-tools, and ``doctor`` subcommand decisions.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"


# ---------------------------------------------------------------------------
# CLI introspection design doc structure
# ---------------------------------------------------------------------------


class TestCliIntrospectionDesignDoc:
    """cli-introspection.md must exist and be listed in the index."""

    def test_design_doc_exists(self) -> None:
        path = DOCS_DIR / "design-docs" / "cli-introspection.md"
        assert path.exists(), "docs/design-docs/cli-introspection.md missing"

    def test_design_doc_listed_in_index(self) -> None:
        index = (DOCS_DIR / "design-docs" / "index.md").read_text()
        assert "cli-introspection.md" in index

    def test_design_doc_covers_version_flag(self) -> None:
        text = (DOCS_DIR / "design-docs" / "cli-introspection.md").read_text()
        assert "--version" in text

    def test_design_doc_covers_list_backends(self) -> None:
        text = (DOCS_DIR / "design-docs" / "cli-introspection.md").read_text()
        assert "--list-backends" in text

    def test_design_doc_covers_list_tools(self) -> None:
        text = (DOCS_DIR / "design-docs" / "cli-introspection.md").read_text()
        assert "--list-tools" in text

    def test_design_doc_covers_doctor(self) -> None:
        text = (DOCS_DIR / "design-docs" / "cli-introspection.md").read_text()
        assert "doctor" in text

    def test_design_doc_covers_interactive_mode(self) -> None:
        text = (DOCS_DIR / "design-docs" / "cli-introspection.md").read_text()
        assert "interactive" in text.lower()

    def test_design_doc_has_alternatives_section(self) -> None:
        text = (DOCS_DIR / "design-docs" / "cli-introspection.md").read_text()
        assert "## Alternatives considered" in text

    def test_design_doc_has_consequences_section(self) -> None:
        text = (DOCS_DIR / "design-docs" / "cli-introspection.md").read_text()
        assert "## Consequences" in text
