"""Tool registry: callable capabilities selected via ``--tools``.

Tools are composable bundles of callable functions (Python/Bash execution, web
browsing, etc.) that can be selected per run and dispatched by iterative hands
or translated into natural-language guidance for CLI-backed hands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from helping_hands.lib.meta.tools import command as command_tools
from helping_hands.lib.meta.tools import git as git_tools
from helping_hands.lib.meta.tools import search as search_tools
from helping_hands.lib.meta.tools import web as web_tools


@dataclass(frozen=True)
class ToolSpec:
    """One callable tool exposed by a tool category."""

    name: str
    payload_example: dict[str, Any]
    runner: Any


@dataclass(frozen=True)
class ToolCategory:
    """Declarative tool category metadata and attached tool handlers."""

    name: str
    title: str
    tools: tuple[ToolSpec, ...]


# ---------------------------------------------------------------------------
# Payload validators
# ---------------------------------------------------------------------------


def _parse_str_list(payload: dict[str, Any], *, key: str) -> list[str]:
    raw = payload.get(key, [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{key} must be a list of strings")
    values: list[str] = []
    for value in raw:
        if not isinstance(value, str):
            raise ValueError(f"{key} must contain only strings")
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{key} contains empty or whitespace-only strings")
        values.append(stripped)
    return values


def _parse_positive_int(
    payload: dict[str, Any],
    *,
    key: str,
    default: int,
) -> int:
    raw = payload.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{key} must be an integer")
    if raw <= 0:
        raise ValueError(f"{key} must be > 0")
    return raw


def _parse_optional_str(payload: dict[str, Any], *, key: str) -> str | None:
    raw = payload.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be a string")
    value = raw.strip()
    return value or None


# ---------------------------------------------------------------------------
# Runner wrappers
# ---------------------------------------------------------------------------


def _run_python_code(
    root: Path, payload: dict[str, Any]
) -> command_tools.CommandResult:
    code = payload.get("code")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code must be a non-empty string")
    python_version = _parse_optional_str(payload, key="python_version") or "3.13"
    return command_tools.run_python_code(
        root,
        code=code,
        python_version=python_version,
        args=_parse_str_list(payload, key="args"),
        timeout_s=_parse_positive_int(payload, key="timeout_s", default=60),
        cwd=_parse_optional_str(payload, key="cwd"),
    )


def _run_python_script(
    root: Path,
    payload: dict[str, Any],
) -> command_tools.CommandResult:
    script_path = payload.get("script_path")
    if not isinstance(script_path, str) or not script_path.strip():
        raise ValueError("script_path must be a non-empty string")
    python_version = _parse_optional_str(payload, key="python_version") or "3.13"
    return command_tools.run_python_script(
        root,
        script_path=script_path,
        python_version=python_version,
        args=_parse_str_list(payload, key="args"),
        timeout_s=_parse_positive_int(payload, key="timeout_s", default=60),
        cwd=_parse_optional_str(payload, key="cwd"),
    )


def _run_bash_script(
    root: Path, payload: dict[str, Any]
) -> command_tools.CommandResult:
    script_path = payload.get("script_path")
    inline_script = payload.get("inline_script")
    if script_path is not None and not isinstance(script_path, str):
        raise ValueError("script_path must be a string")
    if inline_script is not None and not isinstance(inline_script, str):
        raise ValueError("inline_script must be a string")
    has_path = script_path is not None
    has_inline = inline_script is not None
    if has_path == has_inline:
        raise ValueError("provide exactly one of script_path or inline_script")
    return command_tools.run_bash_script(
        root,
        script_path=script_path,
        inline_script=inline_script,
        args=_parse_str_list(payload, key="args"),
        timeout_s=_parse_positive_int(payload, key="timeout_s", default=60),
        cwd=_parse_optional_str(payload, key="cwd"),
    )


def _run_git_status(root: Path, payload: dict[str, Any]) -> git_tools.GitResult:
    del payload
    return git_tools.git_status(root)


def _run_git_diff(root: Path, payload: dict[str, Any]) -> git_tools.GitResult:
    return git_tools.git_diff(
        root,
        ref=_parse_optional_str(payload, key="ref"),
        staged=bool(payload.get("staged", False)),
        name_only=bool(payload.get("name_only", False)),
    )


def _run_git_log(root: Path, payload: dict[str, Any]) -> git_tools.GitResult:
    return git_tools.git_log(
        root,
        max_count=_parse_positive_int(payload, key="max_count", default=20),
    )


def _run_git_grep(root: Path, payload: dict[str, Any]) -> git_tools.GitResult:
    pattern = payload.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("pattern must be a non-empty string")
    return git_tools.git_grep(
        root,
        pattern=pattern,
        paths=_parse_str_list(payload, key="paths"),
        max_count=_parse_positive_int(payload, key="max_count", default=50),
        ignore_case=bool(payload.get("ignore_case", False)),
    )


def _run_glob_files(root: Path, payload: dict[str, Any]) -> search_tools.GlobResult:
    pattern = payload.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("pattern must be a non-empty string")
    return search_tools.glob_files(
        root,
        pattern=pattern,
        base_dir=_parse_optional_str(payload, key="base_dir"),
        max_results=_parse_positive_int(payload, key="max_results", default=100),
    )


def _run_grep_content(root: Path, payload: dict[str, Any]) -> search_tools.GrepResult:
    pattern = payload.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("pattern must be a non-empty string")
    return search_tools.grep_content(
        root,
        pattern=pattern,
        glob=_parse_optional_str(payload, key="glob"),
        base_dir=_parse_optional_str(payload, key="base_dir"),
        max_results=_parse_positive_int(payload, key="max_results", default=50),
        ignore_case=bool(payload.get("ignore_case", False)),
    )


def _run_list_directory(root: Path, payload: dict[str, Any]) -> tuple[list[str], bool]:
    return search_tools.list_directory(
        root,
        rel_path=_parse_optional_str(payload, key="rel_path") or ".",
        max_entries=_parse_positive_int(payload, key="max_entries", default=200),
        include_hidden=bool(payload.get("include_hidden", False)),
    )


def _run_web_search(root: Path, payload: dict[str, Any]) -> web_tools.WebSearchResult:
    del root
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    return web_tools.search_web(
        query,
        max_results=_parse_positive_int(payload, key="max_results", default=5),
        timeout_s=_parse_positive_int(payload, key="timeout_s", default=20),
    )


def _run_web_browse(root: Path, payload: dict[str, Any]) -> web_tools.WebBrowseResult:
    del root
    url = payload.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")
    return web_tools.browse_url(
        url,
        max_chars=_parse_positive_int(payload, key="max_chars", default=12000),
        timeout_s=_parse_positive_int(payload, key="timeout_s", default=20),
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_TOOL_CATEGORIES: dict[str, ToolCategory] = {
    "execution": ToolCategory(
        name="execution",
        title="Execution tools for Python/Bash runtime actions.",
        tools=(
            ToolSpec(
                name="python.run_code",
                payload_example={
                    "code": "print('hello')",
                    "python_version": "3.13",
                    "args": [],
                },
                runner=_run_python_code,
            ),
            ToolSpec(
                name="python.run_script",
                payload_example={
                    "script_path": "scripts/task.py",
                    "python_version": "3.13",
                    "args": [],
                },
                runner=_run_python_script,
            ),
            ToolSpec(
                name="bash.run_script",
                payload_example={"script_path": "scripts/task.sh", "args": []},
                runner=_run_bash_script,
            ),
        ),
    ),
    "web": ToolCategory(
        name="web",
        title="Web search and browsing tools.",
        tools=(
            ToolSpec(
                name="web.search",
                payload_example={"query": "latest python release", "max_results": 5},
                runner=_run_web_search,
            ),
            ToolSpec(
                name="web.browse",
                payload_example={"url": "https://example.com", "max_chars": 6000},
                runner=_run_web_browse,
            ),
        ),
    ),
    "git": ToolCategory(
        name="git",
        title="Git tools for version control context.",
        tools=(
            ToolSpec(
                name="git.status",
                payload_example={},
                runner=_run_git_status,
            ),
            ToolSpec(
                name="git.diff",
                payload_example={"ref": "HEAD~1", "staged": False, "name_only": False},
                runner=_run_git_diff,
            ),
            ToolSpec(
                name="git.log",
                payload_example={"max_count": 10},
                runner=_run_git_log,
            ),
            ToolSpec(
                name="git.grep",
                payload_example={
                    "pattern": "def main",
                    "paths": ["src/"],
                    "ignore_case": False,
                },
                runner=_run_git_grep,
            ),
        ),
    ),
    "search": ToolCategory(
        name="search",
        title="Code search and file discovery tools.",
        tools=(
            ToolSpec(
                name="search.glob",
                payload_example={"pattern": "**/*.py", "base_dir": "src"},
                runner=_run_glob_files,
            ),
            ToolSpec(
                name="search.grep",
                payload_example={
                    "pattern": "class Hand",
                    "glob": "*.py",
                    "ignore_case": False,
                },
                runner=_run_grep_content,
            ),
            ToolSpec(
                name="search.ls",
                payload_example={"rel_path": "src", "max_entries": 50},
                runner=_run_list_directory,
            ),
        ),
    ),
}

_TOOL_TO_CATEGORY = {
    tool.name: cat_name
    for cat_name, cat in _TOOL_CATEGORIES.items()
    for tool in cat.tools
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def available_tool_category_names() -> tuple[str, ...]:
    """Return all supported runtime-selectable tool categories."""
    return tuple(_TOOL_CATEGORIES.keys())


def normalize_tool_selection(
    values: str | list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    """Normalize user-provided tool category names into a deduplicated tuple."""
    if values is None:
        return ()
    if not isinstance(values, (str, list, tuple)):
        raise TypeError("tools must be a string, list, or tuple")

    tokens: list[str] = []
    candidates = values.split(",") if isinstance(values, str) else list(values)

    for raw in candidates:
        if not isinstance(raw, str):
            raise ValueError("tools must contain only strings")
        for item in raw.split(","):
            normalized = item.strip().lower().replace("_", "-")
            if normalized:
                tokens.append(normalized)

    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


def validate_tool_category_names(tool_names: tuple[str, ...]) -> None:
    """Validate tool category names and raise for unknown values."""
    unknown = [name for name in tool_names if name not in _TOOL_CATEGORIES]
    if not unknown:
        return
    choices = ", ".join(available_tool_category_names())
    unknown_text = ", ".join(sorted(unknown))
    raise ValueError(f"unknown tool(s): {unknown_text}; available: {choices}")


def resolve_tool_categories(
    tool_names: tuple[str, ...],
) -> tuple[ToolCategory, ...]:
    """Resolve validated names into concrete tool category specs."""
    validate_tool_category_names(tool_names)
    return tuple(_TOOL_CATEGORIES[name] for name in tool_names)


def merge_with_legacy_tool_flags(
    tool_names: tuple[str, ...],
    *,
    enable_execution: bool,
    enable_web: bool,
) -> tuple[str, ...]:
    """Fold old boolean tool flags into dynamic tool selection."""
    merged: list[str] = list(tool_names)
    if enable_execution:
        merged.insert(0, "execution")
    if enable_web:
        merged.append("web")
    return normalize_tool_selection(tuple(merged))


def build_tool_runner_map(
    categories: tuple[ToolCategory, ...],
) -> dict[str, Any]:
    """Build tool_name -> callable runner mapping for selected categories."""
    mapping: dict[str, Any] = {}
    for cat in categories:
        for tool in cat.tools:
            mapping[tool.name] = tool.runner
    return mapping


def category_name_for_tool(tool_name: str) -> str | None:
    """Return the owning category for a known tool name."""
    return _TOOL_TO_CATEGORY.get(tool_name)


def format_tool_instructions(categories: tuple[ToolCategory, ...]) -> str:
    """Build prompt-ready instructions with ``@@TOOL:`` blocks for iterative hands."""
    if not categories:
        return "No dynamic tools enabled for this run."

    lines: list[str] = []
    for cat in categories:
        lines.append(f"Tool category enabled: {cat.name} \u2014 {cat.title}")
        lines.append(
            "Use execution tools for deterministic local validation (scripts, "
            "tests, and quick checks) and include concise result summaries."
            if cat.name == "execution"
            else "Use web tools for targeted research and source verification when "
            "the task needs external context."
            if cat.name == "web"
            else "Use git tools to understand repo history, current changes, "
            "and search tracked files before making modifications."
            if cat.name == "git"
            else "Use search tools to discover files and find code patterns "
            "before reading or editing. Search narrowly to save context."
            if cat.name == "search"
            else ""
        )
        for tool in cat.tools:
            payload = json.dumps(tool.payload_example, ensure_ascii=False)
            lines.extend(
                [
                    f"@@TOOL: {tool.name}",
                    "```json",
                    payload,
                    "```",
                ]
            )
    return "\n".join(lines)


_CLI_TOOL_GUIDANCE: dict[str, str] = {
    "python.run_code": (
        "Run inline Python code using your shell/Bash tool. "
        "Write the code to a temp file and execute with python3."
    ),
    "python.run_script": (
        "Run Python scripts using your shell/Bash tool (e.g. python3 scripts/task.py)."
    ),
    "bash.run_script": (
        "Run Bash scripts using your shell/Bash tool (e.g. bash scripts/task.sh)."
    ),
    "web.search": ("Use your web search capability to find information online."),
    "web.browse": ("Use your web browsing capability to read web page content."),
    "git.status": ("Run git status to see the current state of the working tree."),
    "git.diff": (
        "Run git diff to see changes. Use --cached for staged, "
        "or specify a ref like HEAD~1."
    ),
    "git.log": ("Run git log to see recent commit history."),
    "git.grep": ("Run git grep to search tracked files for a pattern."),
    "search.glob": (
        "Use your file search capability to find files by glob pattern "
        "(e.g. **/*.py, src/**/*.ts)."
    ),
    "search.grep": (
        "Use your content search capability to search file contents "
        "for a regex pattern."
    ),
    "search.ls": ("List directory contents to explore the repo structure."),
}


def format_tool_instructions_for_cli(
    categories: tuple[ToolCategory, ...],
) -> str:
    """Build prompt-ready tool instructions for CLI-backed hands.

    Unlike :func:`format_tool_instructions` (which emits ``@@TOOL`` blocks for
    iterative dispatch), this variant produces natural-language guidance that
    works with external CLIs that have their own native tool systems.
    """
    if not categories:
        return ""

    lines: list[str] = []
    for cat in categories:
        lines.append(f"Tool category enabled: {cat.name} \u2014 {cat.title}")
        for tool in cat.tools:
            guidance = _CLI_TOOL_GUIDANCE.get(tool.name)
            if guidance:
                lines.append(f"  - {tool.name}: {guidance}")
    return "\n".join(lines)


__all__ = [
    "ToolCategory",
    "ToolSpec",
    "available_tool_category_names",
    "build_tool_runner_map",
    "category_name_for_tool",
    "format_tool_instructions",
    "format_tool_instructions_for_cli",
    "merge_with_legacy_tool_flags",
    "normalize_tool_selection",
    "resolve_tool_categories",
    "validate_tool_category_names",
]
