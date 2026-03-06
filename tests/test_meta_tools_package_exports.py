"""Tests for helping_hands.lib.meta.tools package-level re-exports."""

from __future__ import annotations

import helping_hands.lib.meta.tools as pkg
from helping_hands.lib.meta.tools import __all__


class TestMetaToolsPackageAll:
    """Verify __all__ lists every public re-export."""

    def test_all_contains_expected_symbols(self) -> None:
        expected = {
            "CommandResult",
            "ToolCategory",
            "ToolSpec",
            "WebBrowseResult",
            "WebSearchItem",
            "WebSearchResult",
            "available_tool_category_names",
            "browse_url",
            "build_tool_runner_map",
            "category_name_for_tool",
            "format_tool_instructions",
            "format_tool_instructions_for_cli",
            "merge_with_legacy_tool_flags",
            "mkdir_path",
            "normalize_relative_path",
            "normalize_tool_selection",
            "path_exists",
            "read_text_file",
            "resolve_repo_target",
            "resolve_tool_categories",
            "run_bash_script",
            "run_python_code",
            "run_python_script",
            "search_web",
            "validate_tool_category_names",
            "write_text_file",
        }
        assert set(__all__) == expected

    def test_all_entries_are_importable(self) -> None:
        for name in __all__:
            assert hasattr(pkg, name), f"{name} listed in __all__ but not importable"


class TestMetaToolsFilesystemIdentity:
    """Verify filesystem re-exports match source module."""

    def test_resolve_repo_target_identity(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import (
            resolve_repo_target as src,
        )

        assert pkg.resolve_repo_target is src

    def test_read_text_file_identity(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file as src

        assert pkg.read_text_file is src

    def test_write_text_file_identity(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import write_text_file as src

        assert pkg.write_text_file is src

    def test_mkdir_path_identity(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import mkdir_path as src

        assert pkg.mkdir_path is src

    def test_path_exists_identity(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import path_exists as src

        assert pkg.path_exists is src

    def test_normalize_relative_path_identity(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import (
            normalize_relative_path as src,
        )

        assert pkg.normalize_relative_path is src


class TestMetaToolsCommandIdentity:
    """Verify command re-exports match source module."""

    def test_command_result_identity(self) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult as Src

        assert pkg.CommandResult is Src

    def test_run_python_code_identity(self) -> None:
        from helping_hands.lib.meta.tools.command import run_python_code as src

        assert pkg.run_python_code is src

    def test_run_python_script_identity(self) -> None:
        from helping_hands.lib.meta.tools.command import run_python_script as src

        assert pkg.run_python_script is src

    def test_run_bash_script_identity(self) -> None:
        from helping_hands.lib.meta.tools.command import run_bash_script as src

        assert pkg.run_bash_script is src


class TestMetaToolsRegistryIdentity:
    """Verify registry re-exports match source module."""

    def test_tool_category_identity(self) -> None:
        from helping_hands.lib.meta.tools.registry import ToolCategory as Src

        assert pkg.ToolCategory is Src

    def test_tool_spec_identity(self) -> None:
        from helping_hands.lib.meta.tools.registry import ToolSpec as Src

        assert pkg.ToolSpec is Src

    def test_build_tool_runner_map_identity(self) -> None:
        from helping_hands.lib.meta.tools.registry import build_tool_runner_map as src

        assert pkg.build_tool_runner_map is src

    def test_format_tool_instructions_identity(self) -> None:
        from helping_hands.lib.meta.tools.registry import (
            format_tool_instructions as src,
        )

        assert pkg.format_tool_instructions is src


class TestMetaToolsWebIdentity:
    """Verify web re-exports match source module."""

    def test_web_search_result_identity(self) -> None:
        from helping_hands.lib.meta.tools.web import WebSearchResult as Src

        assert pkg.WebSearchResult is Src

    def test_web_browse_result_identity(self) -> None:
        from helping_hands.lib.meta.tools.web import WebBrowseResult as Src

        assert pkg.WebBrowseResult is Src

    def test_web_search_item_identity(self) -> None:
        from helping_hands.lib.meta.tools.web import WebSearchItem as Src

        assert pkg.WebSearchItem is Src

    def test_search_web_identity(self) -> None:
        from helping_hands.lib.meta.tools.web import search_web as src

        assert pkg.search_web is src

    def test_browse_url_identity(self) -> None:
        from helping_hands.lib.meta.tools.web import browse_url as src

        assert pkg.browse_url is src
