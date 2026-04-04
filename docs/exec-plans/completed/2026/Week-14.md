# Week 14 (Mar 30 – Apr 5, 2026)

Meta tools coverage hardening, hand base & GitHub coverage hardening, remaining
branch coverage gaps, server helper coverage, CLI main coverage, the
`helping-hands doctor` command, the `examples/` directory for new-user
onboarding, Quick Start enhancement with first-run welcome banner, and test
regression fixes with weekly consolidation.

---

## Mar 30 — Meta Tools → Quick Start (v339–v346)

Eight execution plans completed on 2026-03-30.

| Plan | Theme | New Tests |
|---|---|---|
| v346 | Quick Start rewrite & first-run banner | 5 |
| v345 | Examples directory & new-user onboarding | 6 |
| v344 | Doctor command (new feature) | 28 |
| v343 | CLI main coverage & daily consolidation | 4 |
| v342 | Server helper coverage & weekly consolidation | 12 |
| v341 | Remaining branch coverage gaps | 5 |
| v340 | Hand base & GitHub coverage hardening | 10 |
| v339 | Meta tools coverage hardening | 42 |

**v339 — Meta Tools Coverage Hardening:** `web.py` 81% → 98% (`_raise_url_error`,
`_require_http_url`, `_decode_bytes`, `_as_string_keyed_dict`, `_extract_related_topics`,
`search_web`, `browse_url`). `filesystem.py` 92% → 100%. 42 new tests.

**v340 — Hand Base & GitHub Coverage Hardening:** `hand/base.py` 99% → 100%
(`_working_tree_is_clean`, `_push_to_existing_pr`). `github.py`
`add_to_project_v2` RuntimeError paths. 10 new tests.

**v341 — Remaining Branch Coverage Gaps:** `github.py` 99% → 100% (graphql
without-variables). `e2e.py` 99% → 100% (dry_run+pr_number). `cli/base.py`
4 miss → 0 miss (poll deadline, loop timeout). 5 new tests, 45 files at 100%.

**v342 — Server Helper Coverage:** `_maybe_persist_pr_to_schedule`,
`_validate_path_param`, `_is_running_in_docker`. 12 new tests, 96.62% with
server extras.

**v343 — CLI Main Coverage:** `--max-iterations` argparse default None → branch
reachable. 4 new tests.

**v344 — Doctor Command:** New `helping-hands doctor` subcommand — checks Python,
git, uv, API keys, GitHub token, optional CLIs, optional extras. 28 new tests,
`doctor.py` at 100%.

**v345 — Examples Directory:** `examples/fix-greeting/` with deliberate bug,
`run.sh` script, structure tests. 6 new tests.

**v346 — Quick Start & First-Run Banner:** README Quick Start rewritten as 3
steps. `_maybe_show_first_run_banner()` with marker file tracking. 5 new tests.

## Apr 4 — Test Regression Fixes (v347)

**v347 — Fix Test Regressions & Weekly Consolidation:** Fixed 17 test failures
introduced by README slim-down (c7601f0): updated `docs/index.md` to reference
`app-mode.md`/`development.md`/`backends.md`, added `GITHUB_TOKEN` mention to
README Quick Start, updated `TestReadmeMdSections` to match slimmed README
(dropped `## Configuration`/`## Development` expectations), and added
`pytest.importorskip("celery")` guard to `test_grill.py` so grill tests skip
gracefully without server extras. Created Week-14 consolidation.
