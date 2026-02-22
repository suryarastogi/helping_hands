"""System tools package shared by hands and MCP.

This package contains reusable system-facing helpers. The primary module is
``filesystem``, which implements path-confined repo file operations used by
iterative hands and exposed through MCP tools.
"""

from helping_hands.lib.meta.tools.filesystem import (
    mkdir_path,
    normalize_relative_path,
    path_exists,
    read_text_file,
    resolve_repo_target,
    write_text_file,
)

__all__ = [
    "mkdir_path",
    "normalize_relative_path",
    "path_exists",
    "read_text_file",
    "resolve_repo_target",
    "write_text_file",
]
