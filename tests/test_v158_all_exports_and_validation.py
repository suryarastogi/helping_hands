"""Tests for v158: __all__ exports, web.py constant extraction, filesystem validation."""

from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# web.py __all__ tests
# ---------------------------------------------------------------------------
class TestWebAllExport:
    """Verify web.py __all__ declaration."""

    def test_all_contains_web_search_item(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert "WebSearchItem" in __all__

    def test_all_contains_web_search_result(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert "WebSearchResult" in __all__

    def test_all_contains_web_browse_result(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert "WebBrowseResult" in __all__

    def test_all_contains_search_web(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert "search_web" in __all__

    def test_all_contains_browse_url(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert "browse_url" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.meta.tools.web as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert len(__all__) == 5


# ---------------------------------------------------------------------------
# repo.py __all__ tests
# ---------------------------------------------------------------------------
class TestRepoAllExport:
    """Verify repo.py __all__ declaration."""

    def test_all_contains_repo_index(self) -> None:
        from helping_hands.lib.repo import __all__

        assert "RepoIndex" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.repo import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.repo as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.repo import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# default_prompts.py __all__ tests
# ---------------------------------------------------------------------------
class TestDefaultPromptsAllExport:
    """Verify default_prompts.py __all__ declaration."""

    def test_all_contains_default_smoke_test_prompt(self) -> None:
        from helping_hands.lib.default_prompts import __all__

        assert "DEFAULT_SMOKE_TEST_PROMPT" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.lib.default_prompts import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.lib.default_prompts as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.lib.default_prompts import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# task_result.py __all__ tests
# ---------------------------------------------------------------------------
class TestTaskResultAllExport:
    """Verify task_result.py __all__ declaration."""

    def test_all_contains_normalize_task_result(self) -> None:
        from helping_hands.server.task_result import __all__

        assert "normalize_task_result" in __all__

    def test_all_has_no_private_names(self) -> None:
        from helping_hands.server.task_result import __all__

        private = [name for name in __all__ if name.startswith("_")]
        assert private == [], f"Private names in __all__: {private}"

    def test_all_symbols_importable(self) -> None:
        import helping_hands.server.task_result as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} declared in __all__ but not importable"

    def test_all_count(self) -> None:
        from helping_hands.server.task_result import __all__

        assert len(__all__) == 1


# ---------------------------------------------------------------------------
# web.py _DUCKDUCKGO_API_URL constant tests
# ---------------------------------------------------------------------------
class TestDuckDuckGoApiUrlConstant:
    """Verify _DUCKDUCKGO_API_URL constant extraction."""

    def test_constant_value(self) -> None:
        from helping_hands.lib.meta.tools.web import _DUCKDUCKGO_API_URL

        assert _DUCKDUCKGO_API_URL == "https://api.duckduckgo.com/"

    def test_constant_is_string(self) -> None:
        from helping_hands.lib.meta.tools.web import _DUCKDUCKGO_API_URL

        assert isinstance(_DUCKDUCKGO_API_URL, str)

    def test_constant_is_https(self) -> None:
        from helping_hands.lib.meta.tools.web import _DUCKDUCKGO_API_URL

        assert _DUCKDUCKGO_API_URL.startswith("https://")

    def test_constant_used_in_search_web(self) -> None:
        """Verify _DUCKDUCKGO_API_URL is actually referenced in search_web source."""
        from helping_hands.lib.meta.tools import web

        source = inspect.getsource(web.search_web)
        assert "_DUCKDUCKGO_API_URL" in source


# ---------------------------------------------------------------------------
# filesystem.py normalize_relative_path empty string validation tests
# ---------------------------------------------------------------------------
class TestNormalizeRelativePathEmptyValidation:
    """Verify normalize_relative_path rejects empty/whitespace strings."""

    def test_rejects_empty_string(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import normalize_relative_path

        with pytest.raises(ValueError, match="non-empty"):
            normalize_relative_path("")

    def test_rejects_whitespace_only(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import normalize_relative_path

        with pytest.raises(ValueError, match="non-empty"):
            normalize_relative_path("   ")

    def test_rejects_tab_only(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import normalize_relative_path

        with pytest.raises(ValueError, match="non-empty"):
            normalize_relative_path("\t")

    def test_accepts_valid_path(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import normalize_relative_path

        result = normalize_relative_path("src/main.py")
        assert result == "src/main.py"

    def test_accepts_single_char_path(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import normalize_relative_path

        result = normalize_relative_path("a")
        assert result == "a"
