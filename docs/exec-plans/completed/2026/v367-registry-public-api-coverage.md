# v367 — Registry Public API Test Coverage

**Created:** 2026-04-05
**Status:** Completed
**Theme:** Close test gaps in registry.py public API functions that lack dedicated coverage

## Context

The tool registry module (`lib/meta/tools/registry.py`) has 45 tests covering
runner wrappers and validator helpers, but the public API functions — selection,
validation, resolution, merging, formatting — have no dedicated tests. These
functions are called by both iterative hands and CLI hands to select and
configure runtime tools. A regression here would silently break tool dispatch
for all hand types.

## Tasks

- [x] Test `available_tool_category_names()` — returns known categories (3 tests)
- [x] Test `normalize_tool_selection()` — comma strings, lists, tuples, None, dedup, case normalization (11 tests)
- [x] Test `validate_tool_category_names()` — valid names pass, unknown names raise ValueError (5 tests)
- [x] Test `resolve_tool_categories()` — returns ToolCategory objects for valid names (5 tests)
- [x] Test `merge_with_legacy_tool_flags()` — folds boolean flags into tool names with dedup (5 tests)
- [x] Test `build_tool_runner_map()` — produces callable mapping from categories (4 tests)
- [x] Test `category_name_for_tool()` — known tool returns category, unknown returns None (4 tests)
- [x] Test `format_tool_instructions()` — empty categories, execution, web, mixed (6 tests)
- [x] Test `format_tool_instructions_for_cli()` — empty categories, with tools (4 tests)
- [x] Test `_normalize_and_deduplicate()` — type errors, value errors, edge cases (5 tests)
- [x] Update docs (PLANS.md, INTENT.md, Week-14)

## Completion criteria

- All registry public API functions have dedicated test coverage
- All existing tests still pass
- No mocking beyond what's necessary (these are pure functions)
