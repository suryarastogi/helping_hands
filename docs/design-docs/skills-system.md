# Skills System

How helping_hands injects domain knowledge into AI agent prompts via the
composable skills catalog.

## Context

Hands need contextual knowledge beyond the codebase itself -- product
requirements, execution patterns, communication styles. Hard-coding this into
prompts couples knowledge to backend logic and makes per-run customization
impossible.

Skills solve this by separating domain knowledge (Markdown files) from
executable capabilities (tools). A user selects skills per run via `--skills`
and the hand injects the relevant knowledge into its prompt context.

## Design

### Skills vs tools

| Concept | Location | Nature | Example |
|---|---|---|---|
| **Skill** | `lib/meta/skills/catalog/*.md` | Pure knowledge (Markdown) | `prd.md`, `execution.md` |
| **Tool** | `lib/meta/tools/registry.py` | Callable capability | `python.run_code`, `web.search` |

Skills carry no executable code. They are read-only knowledge artifacts that
augment the agent's context window.

### Catalog structure

```
lib/meta/skills/
  __init__.py          # Public API: normalize, validate, resolve, format, stage
  catalog/
    execution.md       # Execution patterns and conventions
    prd.md             # Product requirements gathering
    ralph.md           # Code review and quality
    web.md             # Web research patterns
  internal-comms/      # Non-catalog skill (SKILL.md + examples/)
    SKILL.md
    examples/
  prd/                 # Subdirectory-based skill variant
    SKILL.md
  ralph/
    SKILL.md
```

Only `catalog/*.md` files are auto-discovered. Subdirectory skills
(`internal-comms/`, `prd/`, `ralph/`) have their own `SKILL.md` and are
separate from the catalog discovery mechanism.

### Discovery and loading

At module import time, `_discover_catalog()` scans `catalog/*.md` and builds
a `name -> SkillSpec` mapping:

1. Each `.md` file's stem becomes the skill name (`prd.md` -> `prd`)
2. The first `# Heading` line becomes the title (fallback: filename titlecased)
3. Full file content is stored in `SkillSpec.content`

The catalog is loaded once at import time into the module-level `_SKILLS` dict.

### Normalization

User input goes through `normalize_skill_selection()`:

- Accepts `str` (comma-separated), `list[str]`, `tuple[str, ...]`, or `None`
- Lowercases, replaces `_` with `-`, strips whitespace
- Deduplicates while preserving order
- Non-string items raise `ValueError`

### Validation and resolution

`validate_skill_names()` checks all names exist in the catalog and raises
`ValueError` with available choices if any are unknown.

`resolve_skills()` validates then maps names to `SkillSpec` instances.

### Prompt injection

Two paths depending on hand type:

**Iterative hands** (LangGraph, Atomic): `format_skill_knowledge()` embeds the
full Markdown content directly into the prompt with `Skill enabled: name`
headers. The agent sees the knowledge inline.

**CLI subprocess hands** (Claude, Codex, Goose, Gemini):
1. `stage_skill_catalog()` copies selected `.md` files to a temp directory
2. `format_skill_catalog_instructions()` tells the subprocess where the files
   are and that it should `Read` them when relevant
3. The CLI hand's `_run_two_phase` method handles staging before invoke and
   cleanup after (including cleanup on exception)

This two-path design exists because CLI subprocesses cannot access the
helping_hands package's internal catalog directory.

## Alternatives considered

**Inline all knowledge in default prompts.** Rejected: bloats prompts for
every run regardless of relevance; no per-run customization.

**Dynamic skill loading from external URLs.** Rejected: adds network
dependency and latency; current catalog is fast (filesystem only) and
version-controlled.

**Skills as Python classes.** Rejected: unnecessary complexity for pure
knowledge artifacts. The Markdown-only constraint keeps skills accessible to
non-developers and trivially versionable.

## Consequences

- Adding a new skill requires only creating a `.md` file in `catalog/` -- no
  code changes needed for discovery
- CLI hands must stage/unstage files around subprocess invocations, adding a
  small amount of lifecycle management
- The module-level `_SKILLS` dict means catalog changes require process restart
  (acceptable for a CLI/server tool)
- Skill content is injected verbatim -- there is no templating or variable
  substitution, keeping the system predictable
