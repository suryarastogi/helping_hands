Go through every test file in tests/ and add a module-level docstring block at the top of each file (after imports, before the first class/function) that documents the **why** behind the tests — not just what they test, but the real-world behavior or system invariant they protect.

For each test file:

1. Read the test file to understand what it's testing
2. Trace back to the source code being tested — read the actual implementation to understand the production behavior
3. For server/frontend-adjacent code, check how the frontend consumes the relevant data (look in frontend/src/ for polling, API consumption, component usage) to understand downstream impact
4. Write a concise docstring block at the module level that covers:
   - **What system behavior these tests protect** (not just "tests for X class" — explain the invariant)
   - **Why it matters** — what breaks in production or for users if this behavior regresses (e.g., "the frontend polls /tasks/{id}/diff every 5s and relies on workspace being present in progress metadata — if emit() stops persisting it, the filetree and diff views break")
   - **Non-obvious design decisions** being validated — if a test encodes a deliberate choice (like sticky vs transient fields, or a DRY refactor boundary), call that out so future developers understand the test isn't arbitrary

5. **If you cannot determine a concrete "why" for a test file** — i.e., the tests don't protect a meaningful invariant, duplicate coverage that exists elsewhere, or test trivial/obvious behavior with no real regression risk — add a `# TODO: CLEANUP CANDIDATE` comment at the top of the file with a brief explanation of why the tests seem unnecessary (e.g., "tests only assert constructor args are stored — no behavioral invariant protected", "duplicates coverage in test_hand_base.py"). If individual tests within an otherwise valuable file lack justification, mark those specific tests with `# TODO: CLEANUP CANDIDATE` inline instead of the whole file. For files where every test lacks justification, remove the file entirely rather than marking it.

Keep the documentation concise — aim for 3-8 lines per file. Don't repeat information already in class-level or method-level docstrings. Focus on context that would help a developer who's wondering "why does this test exist and what would go wrong if I deleted it."

Skip files that already have good module-level reasoning documentation. If a file only has a bare "Tests for X" docstring, replace it with the richer version.

Do NOT modify any test logic, only docstrings and the cleanup markers described above. Run the full test suite at the end to confirm nothing broke.
