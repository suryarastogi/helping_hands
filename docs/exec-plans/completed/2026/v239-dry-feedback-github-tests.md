# v239 — DRY _collect_tool_feedback, GitHub method test coverage

**Status:** completed
**Created:** 2026-03-16
**Completed:** 2026-03-16

## Motivation

`_BasicIterativeHand` has a 4-line feedback collection pattern (execute read
requests + execute tool requests + join) duplicated 4× across `run()` and
`stream()` in both `BasicLangGraphHand` and `BasicAtomicHand`. Similarly, the
3-line transcript append pattern appears 2× in the `run()` methods.

Additionally, three important `GitHubClient` / `Hand` methods lack dedicated
test coverage: `_github_repo_from_origin()`, `get_check_runs()`, and
`upsert_pr_comment()`.

## Changes

### Code changes

- **Added `_collect_tool_feedback(self, content: str) -> str`** to
  `_BasicIterativeHand` — executes read and tool requests, joins non-empty
  results with double newline, returns stripped combined feedback
- **Added `_append_iteration_transcript(transcripts, iteration, content,
  changed, feedback)`** static method — builds consistent transcript block
  used by both `BasicLangGraphHand.run()` and `BasicAtomicHand.run()`
- **Replaced 4× inline feedback collection** in `BasicLangGraphHand.run()`,
  `BasicLangGraphHand.stream()`, `BasicAtomicHand.run()`,
  `BasicAtomicHand.stream()` with `_collect_tool_feedback()`
- **Replaced 2× inline transcript building** in `BasicLangGraphHand.run()`
  and `BasicAtomicHand.run()` with `_append_iteration_transcript()`

### Tasks completed

- [x] Extract `_collect_tool_feedback` in `_BasicIterativeHand`
- [x] Extract `_append_iteration_transcript` static method
- [x] Replace 4× inline feedback collection patterns
- [x] Replace 2× inline transcript building patterns
- [x] Tests for `_collect_tool_feedback` (6 tests: empty, read-only, tool-only, both, strip, delegation)
- [x] Tests for `_append_iteration_transcript` (7 tests: basic, changed, feedback, all, empty changed, empty feedback, append-to-existing)
- [x] Tests for `_github_repo_from_origin` (12 tests: HTTPS, HTTPS no .git, SSH, SCP, SCP no .git, non-GitHub, empty, malformed, deep path, HTTP, SCP non-GitHub, calls remote)
- [x] Tests for `get_check_runs` (9 tests: no checks, all success, pending, failure, mixed, ref in result, check run details, empty ref, started_at None)
- [x] Tests for `upsert_pr_comment` (6 tests: create new, update existing, custom marker, marker in body, skip non-matching, None body)
- [x] DRY helper docstring presence tests (2 tests)
- [x] Update PLANS.md

## Test results

- 42 new tests added
- 5720 passed, 225 skipped
- Coverage: 78.52%

## Completion criteria

- [x] All tasks checked
- [x] `uv run pytest -v` passes with no new failures
- [x] `uv run ruff check .` passes
- [x] Coverage ≥ 78.5%
