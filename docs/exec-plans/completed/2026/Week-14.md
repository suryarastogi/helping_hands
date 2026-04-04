# Week 14 (Mar 30 – Apr 5, 2026)

Validation coverage hardening and consolidation week. Wrapped up the intensive
test-coverage and new-user-onboarding push from Week 13 with eight plans on
2026-03-30, then closed the remaining untested `validation.py` functions on
2026-04-04.

## Summary

| Day | Plans | Theme | New Tests |
|---|---|---|---|
| 2026-03-30 | v339–v346 | Meta tools, hand base, GitHub, server helpers, CLI main, doctor command, examples dir, quick start & first-run banner | 112 |
| 2026-04-04 | v347 | Validation `has_cli_flag` + `install_hint` coverage | 14 |

**Total new tests this week:** 126

## 2026-03-30 (v339–v346)

See [daily consolidation](2026-03-30.md) for full details. Highlights:

- **v339** — Meta tools coverage hardening: `web.py` 81% → 98%, `filesystem.py`
  92% → 100% (42 tests)
- **v340** — `hand/base.py` 99% → 100%, `github.py` line 949 covered (10 tests)
- **v341** — Last branch partials: `github.py` 100%, `e2e.py` 100%,
  `cli/base.py` 0 miss (5 tests)
- **v342** — Server helpers: `_maybe_persist_pr_to_schedule`,
  `_validate_path_param`, `_is_running_in_docker` (12 tests)
- **v343** — `cli/main.py` `--max-iterations` default fix (4 tests)
- **v344** — `helping-hands doctor` command, 100% coverage (28 tests)
- **v345** — `examples/fix-greeting/` sample repo (6 tests)
- **v346** — README quick start rewrite + first-run banner (5 tests)

## 2026-04-04 (v347)

Closed last two untested functions in `validation.py`:

- **`has_cli_flag`** (10 tests): bare `--flag`, `--flag=value`, missing flag,
  empty token list, partial name no-match, prefix overlap no-false-positive,
  multiple flags, single-char flag, empty equals value
- **`install_hint`** (4 tests): server/langchain extras, output format, extra
  name appears in output

`validation.py` now has 100% function coverage with all 7 public functions
tested.
