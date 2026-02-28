"""System tools package shared by hands and MCP.

This package contains reusable system-facing helpers:
- ``filesystem`` for path-confined repo file operations.
- ``command`` for path-confined Python/Bash command execution.
"""

from helping_hands.lib.meta.tools.command import (
    CommandResult,
    run_bash_script,
    run_python_code,
    run_python_script,
)
from helping_hands.lib.meta.tools.filesystem import (
    mkdir_path,
    normalize_relative_path,
    path_exists,
    read_text_file,
    resolve_repo_target,
    write_text_file,
)
from helping_hands.lib.meta.tools.registry import (
    ToolCategory,
    ToolSpec,
    available_tool_category_names,
    build_tool_runner_map,
    category_name_for_tool,
    format_tool_instructions,
    format_tool_instructions_for_cli,
    merge_with_legacy_tool_flags,
    normalize_tool_selection,
    resolve_tool_categories,
    validate_tool_category_names,
)
from helping_hands.lib.meta.tools.web import (
    WebBrowseResult,
    WebSearchItem,
    WebSearchResult,
    browse_url,
    search_web,
)

__all__ = [
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
]
