# Code Review

When reviewing code changes, follow a structured checklist approach inspired by systematic audit patterns:

1. **Correctness** — Does the code do what it claims? Check edge cases, off-by-one errors, null/None handling, and error paths.
2. **Security** — Look for injection risks (SQL, command, XSS), path traversal, hardcoded secrets, and improper input validation.
3. **Performance** — Identify N+1 queries, unnecessary allocations, missing indexes, and unbounded loops or data structures.
4. **Maintainability** — Evaluate naming, function length, coupling, and whether the change follows existing project conventions.
5. **Test coverage** — Are new code paths covered? Are edge cases tested? Do existing tests still pass?

Provide feedback as actionable items with file paths and line references. Prioritize issues by severity: security > correctness > performance > maintainability. When changes look good, say so concisely.
