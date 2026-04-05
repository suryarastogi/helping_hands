# Based on OpenAI's Harness Engineering [Blog Post](https://openai.com/index/harness-engineering/)

```
Iterate with this example structure:
AGENTS.md
ARCHITECTURE.md
INTENT.md
WAITING_ON.md
docs/
├── design-docs/
│   ├── index.md
│   ├── core-beliefs.md
│   └── ...
├── exec-plans/
│   ├── active/
│   ├── completed/
│   └── tech-debt-tracker.md
├── generated/
│   └── db-schema.md
├── product-specs/
│   ├── index.md
│   ├── new-user-onboarding.md
│   └── ...
├── references/
│   ├── design-system-reference-llms.txt
│   ├── nixpacks-llms.txt
│   ├── uv-llms.txt
│   └── ...
├── DESIGN.md
├── FRONTEND.md
├── PLANS.md
├── PRODUCT_SENSE.md
├── QUALITY_SCORE.md
├── RELIABILITY.md
└── SECURITY.md
INTENT.md contains users' intents and desires.
Create an active plan if one does not exist. Continue executing the active plan. If there is nothing more to do, move the plan to completed. Consolidate previous days into completed/20XX-MM-DD.md. Consolidate previous weeks into 2026/Week-X.md.
```

## Additional Action Commands

```

> Go through the git history and populate previous activity reports

> Implement the most actionable/self contained improvements. Always update docs and add testing. Do not add excessive testing, seek >80% and semantically meaningful tests. 
```

# Review Tests

```
Review tests/ for tests that don't protect meaningful behavioral invariants. Remove tests that:

1. Use inspect.getsource() to assert source code contains specific strings (e.g., constant names, import names) — these test syntax choices, not behavior
2. Assert docstring presence/format (checking __doc__, inspect.getdoc, "Args:" sections, "Returns:" sections) — linters handle this
3. Assert markdown prose structure in docs (exact section headings, minimum content lengths, table row counts, keyword mentions, timestamp formats) — keep only file-existence, link-resolution, and index-completeness checks
4. Pin exact constant values without testing the behavior those constants drive (e.g., `assert _TIMEOUT == 30` without testing what happens at timeout)

Do NOT remove tests that:
- Test function input/output behavior (call a function, check the result)
- Verify files exist and indexes/links resolve (structural doc tests)
- Validate enum values, priority orderings, or dispatch table completeness
- Test error handling paths (exceptions, fallbacks, edge cases)

For each removal, verify the behavior is already covered by a behavioral test in the same or another file. If a getsource/docstring test is the ONLY coverage for important logic, convert it to a behavioral test instead of deleting it.

Run the full test suite afterward. Coverage must stay above 95%
```