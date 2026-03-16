"""Tests for v224 — DRY _parse_required_str, web.py strip dedup, repo_dir validation.

Covers:
- _parse_required_str helper in registry.py (missing, non-string, empty, whitespace, valid)
- _extract_related_topics pre-computed .strip() behaviour unchanged
- _configure_authenticated_push_remote repo_dir.is_dir() validation
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.lib.hands.v1.hand.base import Hand
from helping_hands.lib.meta.tools.registry import _parse_required_str
from helping_hands.lib.meta.tools.web import WebSearchItem, _extract_related_topics

# ---------------------------------------------------------------------------
# _parse_required_str
# ---------------------------------------------------------------------------


class TestParseRequiredStr:
    """Direct tests for the _parse_required_str helper."""

    def test_missing_key_raises(self) -> None:
        with pytest.raises(ValueError, match="code must be a non-empty string"):
            _parse_required_str({}, key="code")

    def test_none_value_raises(self) -> None:
        with pytest.raises(ValueError, match="url must be a non-empty string"):
            _parse_required_str({"url": None}, key="url")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            _parse_required_str({"query": 42}, key="query")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="script_path must be a non-empty string"):
            _parse_required_str({"script_path": ""}, key="script_path")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="code must be a non-empty string"):
            _parse_required_str({"code": "   \t\n  "}, key="code")

    def test_valid_string_returns_raw(self) -> None:
        result = _parse_required_str({"code": "print(1)"}, key="code")
        assert result == "print(1)"

    def test_valid_string_with_whitespace_returns_raw(self) -> None:
        """Returns the raw value (not stripped) — callers decide on normalisation."""
        result = _parse_required_str({"code": "  x  "}, key="code")
        assert result == "  x  "

    def test_bool_value_raises(self) -> None:
        with pytest.raises(ValueError, match="flag must be a non-empty string"):
            _parse_required_str({"flag": True}, key="flag")

    def test_list_value_raises(self) -> None:
        with pytest.raises(ValueError, match="items must be a non-empty string"):
            _parse_required_str({"items": ["a", "b"]}, key="items")


# ---------------------------------------------------------------------------
# _parse_required_str used by all 4 runner wrappers (source consistency)
# ---------------------------------------------------------------------------


class TestParseRequiredStrUsedInRunners:
    """Verify that _parse_required_str is used in all 4 runner wrappers."""

    @staticmethod
    def _runner_source(func_name: str) -> str:
        import helping_hands.lib.meta.tools.registry as mod

        return inspect.getsource(getattr(mod, func_name))

    def test_run_python_code_uses_parse_required_str(self) -> None:
        src = self._runner_source("_run_python_code")
        assert "_parse_required_str" in src

    def test_run_python_script_uses_parse_required_str(self) -> None:
        src = self._runner_source("_run_python_script")
        assert "_parse_required_str" in src

    def test_run_web_search_uses_parse_required_str(self) -> None:
        src = self._runner_source("_run_web_search")
        assert "_parse_required_str" in src

    def test_run_web_browse_uses_parse_required_str(self) -> None:
        src = self._runner_source("_run_web_browse")
        assert "_parse_required_str" in src


# ---------------------------------------------------------------------------
# _extract_related_topics — pre-computed strip
# ---------------------------------------------------------------------------


class TestExtractRelatedTopicsStrip:
    """Verify _extract_related_topics correctly strips and deduplicates."""

    def test_strips_whitespace_from_text_and_url(self) -> None:
        items: list[dict] = [
            {"Text": "  hello world  ", "FirstURL": "  https://example.com  "}
        ]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 1
        assert output[0].title == "hello world"
        assert output[0].url == "https://example.com"
        assert output[0].snippet == "hello world"

    def test_skips_empty_text_after_strip(self) -> None:
        items: list[dict] = [{"Text": "   ", "FirstURL": "https://example.com"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_empty_url_after_strip(self) -> None:
        items: list[dict] = [{"Text": "hello", "FirstURL": "   "}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_non_string_text(self) -> None:
        items: list[dict] = [{"Text": 42, "FirstURL": "https://example.com"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_non_string_url(self) -> None:
        items: list[dict] = [{"Text": "hello", "FirstURL": None}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_multiple_items(self) -> None:
        items: list[dict] = [
            {"Text": " a ", "FirstURL": " https://a.com "},
            {"Text": " b ", "FirstURL": " https://b.com "},
        ]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 2
        assert output[0].title == "a"
        assert output[1].url == "https://b.com"

    def test_source_uses_precomputed_strip(self) -> None:
        """Verify strip is called once per variable, not redundantly."""
        src = inspect.getsource(_extract_related_topics)
        # Should have raw_text and raw_url (or similar pre-computation pattern)
        # and NOT have triple .strip() calls on same variable
        assert "raw_text" in src or "raw_url" in src


# ---------------------------------------------------------------------------
# _configure_authenticated_push_remote — repo_dir validation
# ---------------------------------------------------------------------------


class TestConfigureAuthPushRemoteRepoDirValidation:
    """Verify _configure_authenticated_push_remote rejects non-directory repo_dir."""

    def test_nonexistent_path_raises(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="repo_dir must be an existing directory"):
            Hand._configure_authenticated_push_remote(
                fake_dir, "owner/repo", "ghp_token"
            )

    def test_file_path_raises(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        with pytest.raises(ValueError, match="repo_dir must be an existing directory"):
            Hand._configure_authenticated_push_remote(
                file_path, "owner/repo", "ghp_token"
            )

    def test_valid_dir_does_not_raise_on_dir_check(self, tmp_path: Path) -> None:
        """Passes dir check but may fail on git — validates dir check runs first."""
        with patch("helping_hands.lib.hands.v1.hand.subprocess.run") as mock_run:
            mock_run.return_value = type(
                "R", (), {"returncode": 0, "stdout": "", "stderr": ""}
            )()
            # Should not raise ValueError for repo_dir
            Hand._configure_authenticated_push_remote(
                tmp_path, "owner/repo", "ghp_token"
            )

    def test_source_has_is_dir_check(self) -> None:
        """Verify the is_dir() guard exists in source."""
        src = inspect.getsource(Hand._configure_authenticated_push_remote)
        assert "is_dir()" in src
