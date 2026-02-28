"""Skill catalog: knowledge files selected via ``--skills``.

Skills are composable bundles of domain knowledge (Markdown files) that can be
selected per run and injected into hand prompts.  Unlike *tools* (callable
capabilities in ``meta.tools.registry``), skills carry no executable code —
they are pure knowledge artifacts.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillSpec:
    """Declarative skill metadata loaded from the catalog."""

    name: str
    title: str
    content: str


# ---------------------------------------------------------------------------
# Catalog discovery
# ---------------------------------------------------------------------------

_CATALOG_DIR = Path(__file__).parent / "catalog"


def _discover_catalog() -> dict[str, SkillSpec]:
    """Scan ``catalog/*.md`` and build a name → SkillSpec mapping."""
    skills: dict[str, SkillSpec] = {}
    if not _CATALOG_DIR.is_dir():
        return skills
    for md_file in sorted(_CATALOG_DIR.glob("*.md")):
        name = md_file.stem
        text = md_file.read_text(encoding="utf-8")
        # Extract title from the first ``# Heading`` line.
        title = name.replace("-", " ").replace("_", " ").title()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
        skills[name] = SkillSpec(name=name, title=title, content=text)
    return skills


_SKILLS: dict[str, SkillSpec] = _discover_catalog()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def available_skill_names() -> tuple[str, ...]:
    """Return all supported runtime-selectable skills (alphabetical)."""
    return tuple(sorted(_SKILLS.keys()))


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


# ---------------------------------------------------------------------------
# Skill knowledge formatting
# ---------------------------------------------------------------------------


def format_skill_knowledge(skills: tuple[SkillSpec, ...]) -> str:
    """Embed full skill ``.md`` content labeled per skill (for iterative prompts)."""
    if not skills:
        return ""
    lines: list[str] = []
    for skill in skills:
        lines.append(f"Skill enabled: {skill.name} \u2014 {skill.title}")
        lines.append(skill.content.strip())
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Skill catalog staging (for CLI subprocess hands)
# ---------------------------------------------------------------------------


def stage_skill_catalog(
    skills: tuple[SkillSpec, ...],
    target_dir: Path,
) -> None:
    """Copy selected skill ``.md`` files to *target_dir*.

    CLI subprocess hands run outside the helping_hands package, so they cannot
    directly access the catalog directory.  This function copies the relevant
    files to a temp directory that the subprocess can ``Read``.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    for skill in skills:
        src = _CATALOG_DIR / f"{skill.name}.md"
        if src.is_file():
            shutil.copy2(src, target_dir / f"{skill.name}.md")


def format_skill_catalog_instructions(
    skills: tuple[SkillSpec, ...],
    catalog_dir: Path | None,
) -> str:
    """Tell a CLI subprocess where staged skill files live.

    Returns a prompt snippet listing skill names and the directory path.
    """
    if not skills:
        return ""
    lines: list[str] = [
        "The following skill knowledge files are available for reference:"
    ]
    for skill in skills:
        if catalog_dir:
            lines.append(f"  - {skill.name}: {catalog_dir / (skill.name + '.md')}")
        else:
            lines.append(f"  - {skill.name}: {skill.title}")
    if catalog_dir:
        lines.append(
            "Read the relevant skill file(s) when you need guidance on that topic."
        )
    return "\n".join(lines)


__all__ = [
    "SkillSpec",
    "available_skill_names",
    "format_skill_catalog_instructions",
    "format_skill_knowledge",
    "normalize_skill_selection",
    "resolve_skills",
    "stage_skill_catalog",
    "validate_skill_names",
]
