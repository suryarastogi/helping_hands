# Week 14 (Mar 30 – Apr 5, 2026)

Meta tools coverage hardening, hand base & GitHub coverage hardening,
remaining branch coverage gaps, server helper coverage, CLI main coverage,
`helping-hands doctor` command, `examples/` directory for new-user
onboarding, Quick Start enhancement with first-run welcome banner,
and doctor/RepoIndex enhancements (Docker + Node.js checks, `file_count`
property, `has_file()` binary search).

---

## Mar 30 — Coverage Hardening & New User Onboarding (v339–v346)

Eight execution plans covering coverage hardening across meta tools, hand
base, GitHub client, branch gaps, server helpers, and CLI main. Three
feature plans: `helping-hands doctor` command, `examples/fix-greeting/`
directory, and Quick Start README rewrite with first-run welcome banner.

See [2026-03-30 daily consolidation](2026-03-30.md) for full details.

**112 new tests. v346 final: 6886 backend tests.**

---

## Apr 4 — Doctor & RepoIndex Enhancements (v347)

**Doctor enhancements:**
- `_check_docker()` — checks Docker CLI availability, needed for
  `docker-sandbox-*` backends
- `_check_node()` — checks Node.js availability and version (v18+ minimum),
  needed for frontend development; handles missing binary, version parse
  failure, and timeout gracefully

**RepoIndex enhancements:**
- `file_count` property — returns `len(self.files)`, avoids callers
  accessing the list directly for count
- `has_file(relative_path)` — O(log n) binary search via `bisect` on the
  pre-sorted files list

**8 new doctor tests, 8 new RepoIndex tests. 16 new tests total.**

---

## Apr 4 — Doctor Server-Mode Prerequisite Checks (v348)

**Doctor server-mode checks:**
- `_check_redis_cli()` — checks `redis-cli` on PATH, needed for local-stack
  server mode
- `_check_docker_compose()` — checks `docker compose` subcommand availability
  with version output, timeout/error handling; needed for app-mode deployment

**Docs fixes:**
- `docs/index.md` — added references to app-mode.md, backends.md, development.md
- `README.md` — added Configuration and Development sections
- `__all__` — added `collect_checks` and `format_results` exports

**8 new tests (2 redis-cli, 5 docker-compose, 1 collect_checks). 45 total doctor tests.**

---

## Apr 4 — Interactive CLI Mode & AI Provider Types Coverage (v349)

**Interactive CLI mode (product spec nice-to-have #4):**
- `read_prompt_from_stdin()` — reads task from stdin when `--prompt` omitted
- TTY mode: prints interactive prompt to stderr, reads until Ctrl+D
- Pipe mode: reads silently (`echo "task" | helping-hands .`)
- Empty/whitespace input and Ctrl+C exit cleanly with error message
- `--prompt` default changed from `DEFAULT_SMOKE_TEST_PROMPT` to `None`

**AI provider types.py test coverage:**
- `normalize_messages()` — string input, sequences, OrderedDict, missing
  role/content defaults, None content, non-Mapping error, non-str content error
- `AIProvider` — lazy inner property (inject, build, cache), `_require_sdk()`
  success/failure, `complete()` model validation and empty content rejection,
  `acomplete()` async delegation
- Docstring verification for public API

**6 new CLI tests + 23 new provider types tests = 29 new tests.**
**Product spec "New User Onboarding" now fully implemented.**
