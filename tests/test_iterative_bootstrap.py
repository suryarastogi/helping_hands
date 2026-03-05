"""Tests for _BasicIterativeHand bootstrap and inline edit methods.

Covers: _build_tree_snapshot, _read_bootstrap_doc, _build_bootstrap_context,
        _apply_inline_edits.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import HandResponse
from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand
from helping_hands.lib.repo import RepoIndex


class _StubIterativeHand(_BasicIterativeHand):
    """Concrete stub so we can instantiate _BasicIterativeHand for testing."""

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield prompt


# ---------------------------------------------------------------------------
# Helper to build a _BasicIterativeHand with a real tmp_path repo
# ---------------------------------------------------------------------------


def _make_hand(
    tmp_path: Path, files: dict[str, str] | None = None
) -> _StubIterativeHand:
    """Create a _StubIterativeHand backed by a real tmp_path repo."""
    if files:
        for rel_path, content in files.items():
            full = tmp_path / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
    repo_index = RepoIndex.from_path(tmp_path)
    config = Config(repo=str(tmp_path), model="test-model")
    with patch(
        "helping_hands.lib.meta.tools.registry.build_tool_runner_map",
        return_value={},
    ):
        hand = _StubIterativeHand(config, repo_index)
    return hand


# ---------------------------------------------------------------------------
# _build_tree_snapshot
# ---------------------------------------------------------------------------


class TestBuildTreeSnapshot:
    def test_empty_repo(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        result = hand._build_tree_snapshot()
        assert result == "- (empty)"

    def test_flat_files(self, tmp_path: Path):
        hand = _make_hand(tmp_path, {"a.py": "", "b.py": ""})
        result = hand._build_tree_snapshot()
        assert "- a.py" in result
        assert "- b.py" in result

    def test_nested_files_show_directories(self, tmp_path: Path):
        hand = _make_hand(tmp_path, {"src/main.py": "", "src/utils.py": ""})
        result = hand._build_tree_snapshot()
        assert "- src/" in result
        assert "- src/main.py" in result
        assert "- src/utils.py" in result

    def test_depth_capping(self, tmp_path: Path):
        # _BOOTSTRAP_TREE_MAX_DEPTH is 4, so depth 5+ gets truncated
        deep_path = "a/b/c/d/e/deep.py"
        hand = _make_hand(tmp_path, {deep_path: ""})
        result = hand._build_tree_snapshot()
        # Should show directories up to depth 4, then "..." for deeper
        assert "- a/" in result
        assert "- a/b/" in result
        assert "- a/b/c/" in result
        assert "- a/b/c/d/..." in result
        # Should NOT show the full path
        assert "- a/b/c/d/e/" not in result

    def test_entry_limit(self, tmp_path: Path):
        # Create enough files to exceed _BOOTSTRAP_TREE_MAX_ENTRIES
        files = {f"file_{i:04d}.py": "" for i in range(300)}
        hand = _make_hand(tmp_path, files)
        result = hand._build_tree_snapshot()
        assert "... (" in result
        assert "more)" in result

    def test_within_depth_shows_full_path(self, tmp_path: Path):
        hand = _make_hand(tmp_path, {"src/lib/core.py": ""})
        result = hand._build_tree_snapshot()
        # depth 3 is within max_depth=4
        assert "- src/lib/core.py" in result
        assert "- src/" in result
        assert "- src/lib/" in result


# ---------------------------------------------------------------------------
# _read_bootstrap_doc
# ---------------------------------------------------------------------------


class TestReadBootstrapDoc:
    def test_reads_first_match(self, tmp_path: Path):
        hand = _make_hand(tmp_path, {"README.md": "# Hello"})
        result = hand._read_bootstrap_doc(tmp_path, ("README.md", "readme.md"))
        assert "README.md" in result
        assert "# Hello" in result

    def test_skips_missing_reads_second(self, tmp_path: Path):
        # Use unambiguous names to avoid case-insensitive FS collisions
        hand = _make_hand(tmp_path, {"NOTES.md": "# Notes"})
        result = hand._read_bootstrap_doc(tmp_path, ("MISSING.md", "NOTES.md"))
        assert "NOTES.md" in result
        assert "# Notes" in result

    def test_all_missing_returns_empty(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        result = hand._read_bootstrap_doc(tmp_path, ("README.md", "readme.md"))
        assert result == ""

    def test_skips_directory_with_same_name(self, tmp_path: Path):
        # Create a directory named DOCS.md (unusual but possible)
        (tmp_path / "DOCS.md").mkdir()
        hand = _make_hand(tmp_path, {"NOTES.md": "# Fallback"})
        result = hand._read_bootstrap_doc(tmp_path, ("DOCS.md", "NOTES.md"))
        assert "NOTES.md" in result
        assert "# Fallback" in result

    def test_truncated_large_doc(self, tmp_path: Path):
        large = "x" * (_BasicIterativeHand._MAX_BOOTSTRAP_DOC_CHARS + 100)
        hand = _make_hand(tmp_path, {"README.md": large})
        result = hand._read_bootstrap_doc(tmp_path, ("README.md",))
        assert "[truncated]" in result


# ---------------------------------------------------------------------------
# _build_bootstrap_context
# ---------------------------------------------------------------------------


class TestBuildBootstrapContext:
    def test_with_readme_and_agent(self, tmp_path: Path):
        hand = _make_hand(
            tmp_path,
            {"README.md": "# Project", "AGENT.md": "# Agent Notes", "src/main.py": ""},
        )
        result = hand._build_bootstrap_context()
        assert "# Project" in result
        assert "# Agent Notes" in result
        assert "Repository tree snapshot" in result
        assert "- src/main.py" in result

    def test_without_readme(self, tmp_path: Path):
        hand = _make_hand(tmp_path, {"src/main.py": ""})
        result = hand._build_bootstrap_context()
        assert "Repository tree snapshot" in result
        assert "README" not in result

    def test_without_agent(self, tmp_path: Path):
        hand = _make_hand(tmp_path, {"README.md": "# Hi"})
        result = hand._build_bootstrap_context()
        assert "# Hi" in result
        assert "AGENT" not in result

    def test_empty_repo_still_has_tree(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        result = hand._build_bootstrap_context()
        assert "Repository tree snapshot" in result
        assert "(empty)" in result


# ---------------------------------------------------------------------------
# _apply_inline_edits
# ---------------------------------------------------------------------------


class TestApplyInlineEdits:
    def test_writes_file(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        content = "@@FILE: hello.py\n```python\nprint('hello')\n```"
        changed = hand._apply_inline_edits(content)
        assert "hello.py" in changed
        assert (tmp_path / "hello.py").read_text() == "print('hello')"

    def test_writes_multiple_files(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        content = (
            "@@FILE: a.py\n```python\ncode_a\n```\n\n"
            "@@FILE: b.py\n```python\ncode_b\n```"
        )
        changed = hand._apply_inline_edits(content)
        assert len(changed) == 2
        assert (tmp_path / "a.py").read_text() == "code_a"
        assert (tmp_path / "b.py").read_text() == "code_b"

    def test_skips_path_traversal(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        content = "@@FILE: ../escape.py\n```python\nevil\n```"
        changed = hand._apply_inline_edits(content)
        assert changed == []
        assert not (tmp_path.parent / "escape.py").exists()

    def test_no_edits_returns_empty(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        changed = hand._apply_inline_edits("No file blocks here.")
        assert changed == []

    def test_refreshes_repo_index(self, tmp_path: Path):
        hand = _make_hand(tmp_path, {"existing.py": ""})
        assert "new_file.py" not in hand.repo_index.files
        content = "@@FILE: new_file.py\n```python\npass\n```"
        hand._apply_inline_edits(content)
        assert "new_file.py" in hand.repo_index.files

    def test_nested_directory_creation(self, tmp_path: Path):
        hand = _make_hand(tmp_path)
        content = "@@FILE: src/deep/module.py\n```python\nx = 1\n```"
        changed = hand._apply_inline_edits(content)
        assert len(changed) == 1
        assert (tmp_path / "src" / "deep" / "module.py").read_text() == "x = 1"
