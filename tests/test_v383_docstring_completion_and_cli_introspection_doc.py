"""Tests for v383: Docstring completion and CLI introspection design doc.

Verifies that:
1. BasicLangGraphHand.__init__() and BasicAtomicHand.__init__() have docstrings
   with Args: sections.
2. ArcadeScoreEntry and ArcadeScoreSubmit Pydantic models have docstrings.
3. The cli-introspection.md design doc exists and is listed in the index.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.iterative import (
    BasicAtomicHand,
    BasicLangGraphHand,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"


# ---------------------------------------------------------------------------
# Docstring presence: BasicLangGraphHand.__init__
# ---------------------------------------------------------------------------


class TestBasicLangGraphHandInitDocstring:
    """BasicLangGraphHand.__init__ must have a Google-style docstring."""

    def test_docstring_exists(self) -> None:
        doc = inspect.getdoc(BasicLangGraphHand.__init__)
        assert doc, "BasicLangGraphHand.__init__ is missing a docstring"

    def test_docstring_has_args_section(self) -> None:
        doc = inspect.getdoc(BasicLangGraphHand.__init__)
        assert doc and "Args:" in doc, (
            "BasicLangGraphHand.__init__ docstring missing 'Args:' section"
        )

    def test_docstring_mentions_config(self) -> None:
        doc = inspect.getdoc(BasicLangGraphHand.__init__)
        assert doc and "config" in doc.lower()

    def test_docstring_mentions_max_iterations(self) -> None:
        doc = inspect.getdoc(BasicLangGraphHand.__init__)
        assert doc and "max_iterations" in doc


# ---------------------------------------------------------------------------
# Docstring presence: BasicAtomicHand.__init__
# ---------------------------------------------------------------------------


class TestBasicAtomicHandInitDocstring:
    """BasicAtomicHand.__init__ must have a Google-style docstring."""

    def test_docstring_exists(self) -> None:
        doc = inspect.getdoc(BasicAtomicHand.__init__)
        assert doc, "BasicAtomicHand.__init__ is missing a docstring"

    def test_docstring_has_args_section(self) -> None:
        doc = inspect.getdoc(BasicAtomicHand.__init__)
        assert doc and "Args:" in doc, (
            "BasicAtomicHand.__init__ docstring missing 'Args:' section"
        )

    def test_docstring_mentions_config(self) -> None:
        doc = inspect.getdoc(BasicAtomicHand.__init__)
        assert doc and "config" in doc.lower()

    def test_docstring_mentions_max_iterations(self) -> None:
        doc = inspect.getdoc(BasicAtomicHand.__init__)
        assert doc and "max_iterations" in doc


# ---------------------------------------------------------------------------
# Docstring presence: Pydantic arcade models
# ---------------------------------------------------------------------------


class TestArcadePydanticModelDocstrings:
    """ArcadeScoreEntry and ArcadeScoreSubmit must have docstrings."""

    @pytest.fixture()
    def _skip_without_server(self) -> None:
        pytest.importorskip("fastapi")

    @pytest.mark.usefixtures("_skip_without_server")
    def test_arcade_score_entry_has_docstring(self) -> None:
        from helping_hands.server.app import ArcadeScoreEntry

        assert ArcadeScoreEntry.__doc__, "ArcadeScoreEntry is missing a docstring"

    @pytest.mark.usefixtures("_skip_without_server")
    def test_arcade_score_submit_has_docstring(self) -> None:
        from helping_hands.server.app import ArcadeScoreSubmit

        assert ArcadeScoreSubmit.__doc__, "ArcadeScoreSubmit is missing a docstring"

    @pytest.mark.usefixtures("_skip_without_server")
    def test_arcade_score_entry_docstring_non_trivial(self) -> None:
        from helping_hands.server.app import ArcadeScoreEntry

        doc = ArcadeScoreEntry.__doc__
        assert doc and len(doc.strip()) >= 10

    @pytest.mark.usefixtures("_skip_without_server")
    def test_arcade_score_submit_docstring_non_trivial(self) -> None:
        from helping_hands.server.app import ArcadeScoreSubmit

        doc = ArcadeScoreSubmit.__doc__
        assert doc and len(doc.strip()) >= 10


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
