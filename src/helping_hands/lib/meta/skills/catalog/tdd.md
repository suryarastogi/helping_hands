# TDD

Follow test-driven development when implementing features or fixing bugs:

1. **Red** — Write a failing test that captures the expected behavior or reproduces the bug. Run it to confirm it fails for the right reason.
2. **Green** — Write the minimum code to make the test pass. Resist the urge to over-engineer.
3. **Refactor** — Clean up the implementation while keeping tests green. Extract helpers only when duplication is real, not anticipated.

Guidelines:
- Name tests descriptively: `test_<unit>_<scenario>_<expected_outcome>`.
- Prefer focused unit tests over broad integration tests unless the task specifically involves cross-component behavior.
- Use the project's existing test framework and conventions (check for pytest, vitest, jest, etc.).
- Run the relevant test file after each change to verify red/green transitions.
- When fixing a bug, first write a test that reproduces it before applying the fix.
