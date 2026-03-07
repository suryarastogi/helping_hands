# Testing Methodology

How helping_hands achieves high test coverage through iterative, coverage-guided
development.

## Context

The project started with minimal test coverage and iterated through 60+
execution plans, each targeting specific coverage gaps identified from
`pytest-cov` branch reports. This document captures the methodology so future
contributors can follow the same approach.

## Coverage-guided iteration

Each execution plan follows a cycle:

1. **Measure** -- Run `pytest --cov --cov-branch --cov-report=term-missing` and
   identify modules with the largest coverage gaps or unclosed branch partials.
2. **Target** -- Pick 2-5 specific branch gaps (identified by line numbers in
   the `Missing` column) and write tests that exercise those paths.
3. **Validate** -- Run the full suite, confirm new tests pass and no regressions,
   then update `QUALITY_SCORE.md` with the new coverage state.
4. **Document** -- Record dead code (branches proven unreachable) in
   `docs/exec-plans/tech-debt-tracker.md` rather than writing contorted tests.

The goal is not 100% line coverage but rather closing **branch gaps** that
represent untested error paths, fallback logic, or edge cases.

## Test organization

All tests live in `tests/` with a flat structure (`test_*.py` naming). There
are no subdirectories -- every test file corresponds to one or more source
modules.

### Naming conventions

| Source module | Test file(s) |
|---|---|
| `lib/config.py` | `test_config.py` |
| `lib/hands/v1/hand/base.py` | `test_hand.py`, `test_hand_base_statics.py` |
| `lib/hands/v1/hand/cli/base.py` | `test_cli_hand_base_*.py` (multiple files by concern) |
| `lib/hands/v1/hand/cli/claude.py` | `test_cli_hand_claude.py`, `test_claude_stream_emitter.py` |
| `server/app.py` | `test_server_app.py`, `test_server_app_helpers.py` |

When a module grows many tests, split by concern (e.g. `_ci`, `_retry`,
`_utils`, `_helpers`, `_prompts`) rather than keeping a single large file.

### Test class structure

Tests are grouped into classes by the behavior cluster they exercise:

```python
class TestE2EHandRunDryRun:
    """Tests for E2EHand.run() in dry-run mode."""

class TestE2EHandRunResumedPR:
    """Tests for E2EHand.run() when resuming an existing PR."""
```

Each class tests a single logical path, making failures easy to locate.

## Key patterns

### Isolation via monkeypatch

External dependencies are always mocked:

- `monkeypatch.setenv` / `monkeypatch.delenv` for environment variables
- `unittest.mock.patch` for heavy objects (GitHubClient, AI providers)
- `tmp_path` fixture for filesystem operations

No test touches the real network, GitHub API, or AI provider APIs.

### `importorskip` for optional extras

Modules requiring optional packages (`langchain`, `atomic_agents`, `redbeat`,
`croniter`) use `pytest.importorskip()` at test module level:

```python
pytest.importorskip("langchain_core")
```

This silently skips the file when the extra is not installed, rather than
failing the entire suite.

### Fake dataclasses for API responses

Rather than importing heavy SDK response objects, tests define minimal fakes:

```python
@dataclass
class _FakePRResult:
    number: int = 42
    html_url: str = "https://github.com/owner/repo/pull/42"
```

This makes the test contract explicit and avoids SDK import overhead.

### Dead code documentation

When analysis proves a branch is unreachable (e.g. a guard that can never be
False due to upstream logic), the branch is documented in
`docs/exec-plans/tech-debt-tracker.md` with a priority of `None` or `Low` and
a brief explanation of why it is unreachable. This keeps the test suite
honest -- every test exercises a real execution path.

Common dead code patterns:
- **Always-truthy guards** -- a variable is always set before the check
- **Encoding fallbacks** -- `latin-1` decodes all byte values, making the
  post-loop fallback unreachable
- **`if __name__` guards** -- standard entry point checks that pytest cannot
  trigger

## Frontend testing

Frontend tests use Vitest with `@testing-library/react`. The same
coverage-guided iteration applies:

1. Export pure utility functions for direct unit testing
2. Add component-level render and interaction tests
3. Target branch coverage gaps in UI logic

The frontend uses a `mockResponse` helper with `clone()` support for testing
fetch-based API interactions.

## Coverage targets

| Scope | Target | Current |
|---|---|---|
| Backend (overall) | Increasing per PR | 77% (2435 tests) |
| Per-module (core) | 90%+ | Most modules 95-100% |
| Frontend (statements) | 80%+ | 82.3% (153 tests) |
| Frontend (branches) | 80%+ | 80.2% |

Remaining gaps are documented dead code or inherently untestable paths (e.g.
`if __name__` guards, async subprocess timing).

## Anti-patterns

- **Contorted tests for dead code** -- If a branch is provably unreachable,
  document it rather than writing a test that would require production code
  changes to exercise.
- **Over-mocking** -- Mock at the boundary (subprocess, HTTP, filesystem), not
  deep internals. Test the actual logic.
- **Flaky timing tests** -- Avoid tests that depend on real async timing. Use
  deterministic mocks for IO loops and heartbeats.
- **Catch-all assertions** -- Each test should assert a specific behavior, not
  just "it didn't crash."
