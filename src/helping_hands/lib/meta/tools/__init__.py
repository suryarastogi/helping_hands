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
from helping_hands.lib.meta.tools.web import (
    WebBrowseResult,
    WebSearchItem,
    WebSearchResult,
    browse_url,
    search_web,
)

__all__ = [
    "CommandResult",
    "WebBrowseResult",
    "WebSearchItem",
    "WebSearchResult",
    "browse_url",
    "mkdir_path",
    "normalize_relative_path",
    "path_exists",
    "read_text_file",
    "resolve_repo_target",
    "run_bash_script",
    "run_python_code",
    "run_python_script",
    "search_web",
    "write_text_file",
]
