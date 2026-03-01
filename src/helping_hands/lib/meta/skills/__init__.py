"""Dynamic skill registry shared by iterative hands and runtime entrypoints.

Skills are composable bundles of tool capabilities that can be selected per run
and injected into hand prompts/dispatch logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from helping_hands.lib.meta.tools import command as command_tools
from helping_hands.lib.meta.tools import web as web_tools


@dataclass(frozen=True)
class SkillTool:
    """One callable tool exposed by a skill."""

    name: str
    payload_example: dict[str, Any]
    runner: Any


@dataclass(frozen=True)
class SkillSpec:
    """Declarative skill metadata and attached tool handlers."""

    name: str
    title: str
    tools: tuple[SkillTool, ...]
    instructions: str = ""


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
        values.append(value)
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
    has_path = isinstance(script_path, str) and script_path.strip()
    has_inline = isinstance(inline_script, str) and inline_script.strip()
    if not has_path and not has_inline:
        raise ValueError(
            "at least one of script_path or inline_script must be a non-empty string"
        )
    return command_tools.run_bash_script(
        root,
        script_path=script_path,
        inline_script=inline_script,
        args=_parse_str_list(payload, key="args"),
        timeout_s=_parse_positive_int(payload, key="timeout_s", default=60),
        cwd=_parse_optional_str(payload, key="cwd"),
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


_SKILLS: dict[str, SkillSpec] = {
    "execution": SkillSpec(
        name="execution",
        title="Execution tools for Python/Bash runtime actions.",
        instructions=(
            "Use execution tools for deterministic local validation (scripts, "
            "tests, and quick checks) and include concise result summaries."
        ),
        tools=(
            SkillTool(
                name="python.run_code",
                payload_example={
                    "code": "print('hello')",
                    "python_version": "3.13",
                    "args": [],
                },
                runner=_run_python_code,
            ),
            SkillTool(
                name="python.run_script",
                payload_example={
                    "script_path": "scripts/task.py",
                    "python_version": "3.13",
                    "args": [],
                },
                runner=_run_python_script,
            ),
            SkillTool(
                name="bash.run_script",
                payload_example={"script_path": "scripts/task.sh", "args": []},
                runner=_run_bash_script,
            ),
        ),
    ),
    "web": SkillSpec(
        name="web",
        title="Web search and browsing tools.",
        instructions=(
            "Use web tools for targeted research and source verification when "
            "the task needs external context."
        ),
        tools=(
            SkillTool(
                name="web.search",
                payload_example={"query": "latest python release", "max_results": 5},
                runner=_run_web_search,
            ),
            SkillTool(
                name="web.browse",
                payload_example={"url": "https://example.com", "max_chars": 6000},
                runner=_run_web_browse,
            ),
        ),
    ),
    "prd": SkillSpec(
        name="prd",
        title="PRD generator workflow for feature planning.",
        instructions=(
            "When planning a feature, ask a few critical clarifying questions "
            "first, then produce a structured PRD with measurable goals, "
            "user stories, acceptance criteria, functional requirements, "
            "non-goals, and success metrics."
        ),
        tools=(),
    ),
    "ralph": SkillSpec(
        name="ralph",
        title="Ralph PRD-to-prd.json conversion workflow.",
        instructions=(
            "Convert PRDs into Ralph-compatible `prd.json` output. Keep each "
            "story small enough for one autonomous iteration, order stories "
            "by dependency, and ensure acceptance criteria are verifiable."
        ),
        tools=(),
    ),
}

_TOOL_TO_SKILL = {
    tool.name: skill_name
    for skill_name, skill in _SKILLS.items()
    for tool in skill.tools
}


def available_skill_names() -> tuple[str, ...]:
    """Return all supported runtime-selectable skills."""
    return tuple(_SKILLS.keys())


def normalize_skill_selection(
    values: str | list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    """Normalize user-provided skill names into a deduplicated tuple."""
    if values is None:
        return ()

    tokens: list[str] = []
    candidates = values.split(",") if isinstance(values, str) else list(values)

    for raw in candidates:
        if not isinstance(raw, str):
            raise ValueError("skills must contain only strings")
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


def validate_skill_names(skill_names: tuple[str, ...]) -> None:
    """Validate skill names and raise for unknown values."""
    unknown = [name for name in skill_names if name not in _SKILLS]
    if not unknown:
        return
    choices = ", ".join(available_skill_names())
    unknown_text = ", ".join(sorted(unknown))
    raise ValueError(f"unknown skill(s): {unknown_text}; available: {choices}")


def resolve_skills(skill_names: tuple[str, ...]) -> tuple[SkillSpec, ...]:
    """Resolve validated names into concrete skill specs."""
    validate_skill_names(skill_names)
    return tuple(_SKILLS[name] for name in skill_names)


def merge_with_legacy_tool_flags(
    skill_names: tuple[str, ...],
    *,
    enable_execution: bool,
    enable_web: bool,
) -> tuple[str, ...]:
    """Fold old boolean tool flags into dynamic skill selection."""
    merged: list[str] = list(skill_names)
    if enable_execution:
        merged.insert(0, "execution")
    if enable_web:
        merged.append("web")
    return normalize_skill_selection(tuple(merged))


def build_tool_runner_map(skills: tuple[SkillSpec, ...]) -> dict[str, Any]:
    """Build tool_name -> callable runner mapping for selected skills."""
    mapping: dict[str, Any] = {}
    for skill in skills:
        for tool in skill.tools:
            mapping[tool.name] = tool.runner
    return mapping


def skill_name_for_tool(tool_name: str) -> str | None:
    """Return the owning skill for a known tool name."""
    return _TOOL_TO_SKILL.get(tool_name)


def format_skill_instructions(skills: tuple[SkillSpec, ...]) -> str:
    """Build prompt-ready instructions for selected skills."""
    if not skills:
        return "No dynamic skills enabled for this run."

    lines: list[str] = []
    for skill in skills:
        lines.append(f"Skill enabled: {skill.name} — {skill.title}")
        if skill.instructions:
            lines.append(skill.instructions)
        for tool in skill.tools:
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


__all__ = [
    "SkillSpec",
    "SkillTool",
    "available_skill_names",
    "build_tool_runner_map",
    "format_skill_instructions",
    "merge_with_legacy_tool_flags",
    "normalize_skill_selection",
    "resolve_skills",
    "skill_name_for_tool",
    "validate_skill_names",
]
