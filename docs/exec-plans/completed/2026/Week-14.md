# Week 14 (Mar 30 – Apr 5, 2026)

Meta tools coverage hardening, hand base & GitHub coverage hardening,
remaining branch coverage gaps, server helper coverage, CLI main coverage,
`helping-hands doctor` command, `examples/` directory for new-user
onboarding, Quick Start enhancement with first-run welcome banner,
doctor/RepoIndex enhancements, interactive CLI mode, grill module
testability, core utility coverage, CLI hand coverage, server coverage gaps,
remaining edge cases, troubleshooting guide, server endpoint coverage,
shared git clone utility extraction, token helper extraction, test
consolidation cleanup, `--list-backends` enabled status enrichment,
and `--list-tools` CLI flag with registry coverage completion.

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

---

## Apr 4 — Grill Module Testability & Coverage (v350)

**Grill module restructuring:**
- Deferred celery imports: `from celery import Task` moved to `TYPE_CHECKING`,
  `celery_app` import wrapped in `try/except ImportError` — pure helpers now
  importable without the server extra
- Extracted `_grill_session_body` from the `@celery_app.task` decorator wrapper
- Marked integration-only code (`_grill_session_body`, celery task wrapper)
  with `pragma: no cover`

**Test coverage (37 new tests):**
- `TestRedisClient` (2): `_redis_client` env var and default URL
- `TestRedisHelpers` (6): `_set_state`/`_get_state` round-trip, `_push_ai_msg`
  structure and custom type, `_pop_user_msg` present/empty
- `TestBuildSystemPrompt` (7 new): README.rst fallback, truncation, large file
  tree, no README, reference repos, index failure, OSError
- `TestCloneRepo` (3 new): remote clone success, failure, timeout
- `TestSummarizeToolUse` (2 new): missing key, empty pattern
- `TestInvokeClaudeTurn` (19): first turn, resume, FileNotFoundError, non-zero
  exit, stdin OSError, text blocks, on_status callbacks, github_token env,
  malformed JSON, wait timeout, thinking dedup, tool_use reset, non-dict
  message/content, empty text block, duration-only result, empty stderr,
  no-model flag, read-only tools
- `TestInvokeClaudeTurnStreamError` (1): stdout iteration exception
- Fixed `TestGrillEnabled` tests: added per-test `pytest.importorskip("fastapi")`

**grill.py coverage: 4% → 99% (pure helpers). 13 test failures → 0.**

---

## Apr 4 — Core Utility Module Test Coverage (v351)

**Three 0%-covered utility modules brought to 100%:**
- `validation.py` — 10 new tests for `has_cli_flag` (bare flag, equals form,
  absent, empty tokens, partial match rejection, single-dash rejection) and
  `install_hint` output
- `github_url.py` — 15 new tests for `resolve_github_token` (explicit, env,
  fallback, priority, whitespace), `repo_tmp_dir` (unset, set, nested, whitespace),
  and `invalid_repo_msg` format
- `factory.py` — 24 new tests for `create_hand` (all 11 backend dispatch branches
  + unknown backend error + max_iterations) and `get_enabled_backends` (all-enabled
  default, sorted, single, truthy values, falsy exclusion, multiple)

**49 new tests. All three modules at 100% coverage. 149 tests pass.**

---

## Apr 4 — CLI Hand Test Coverage: OpenCode + Devin (v352)

Closed test coverage gaps in `opencode.py` and `devin.py` CLI hand modules:
- `opencode.py` `_describe_auth()` all branches covered (7 tests)
- `opencode.py` `_pr_description_cmd()` both branches (2 tests)
- `devin.py` `_pr_description_cmd()` both branches (2 tests)
- `devin.py` `_pr_description_prompt_as_arg()` (1 test)
- `devin.py` `_resolve_cli_model` env var edge cases (5 tests)

**17 new tests. 6744 total tests pass. ruff clean.**

---

## Apr 4 — Server Module Coverage Gaps (v353)

Closed remaining coverage gaps in `server/app.py` and `server/schedules.py`
by adding tests with mocked Redis/Celery and FastAPI TestClient:

**schedules.py (77% → 95%):**
- `validate_interval_seconds` — 5 tests (None, below min, above max, valid, boundary)
- `next_interval_run_time` — 3 tests (None last_run, with last_run, naive timestamp)
- Chain nonce methods (`_save_chain_nonce`, `get_chain_nonce`, `_delete_chain_nonce`) — 8 tests
- `_revoke_interval_chain` — 4 tests (with/without task_id, connection/OS errors)
- Interval schedule CRUD — 6 tests (create, update, delete, enable, disable, trigger)
- `_create_redbeat_entry` body execution — 1 test

**app.py (77% → 90%+):**
- Arcade endpoints (GET/POST `/arcade/high-scores`) — 2 tests
- Multiplayer health endpoints (4 sub-routes) — 4 tests
- `_resolve_task_workspace` — 5 tests (all branches)
- Task diff endpoint — 2 tests (no workspace, with workspace + git diff)
- Task tree endpoint — 2 tests (no workspace, with workspace)
- Task file content endpoint — 3 tests (no workspace, not found, success)
- `_schedule_to_response` — 3 tests (cron, interval, disabled)
- Grill endpoints (disabled) — 3 tests

**Overall project coverage: 94.73% → 97.60%. ~55 new tests.**

---

## Apr 4 — Remaining Edge Case Coverage (v354)

Closed last <2% coverage gaps in `github.py` (`update_pr` validation/edit
paths), `cli/base.py` (`_LinePrefixEmitter` line buffering and flush),
`cli/claude.py` (`_summarize_tool` Skill branch), and `cli/goose.py`
(`_pr_description_cmd` Google/Gemini path). 17 targeted tests.

---

## Apr 4 — Troubleshooting Guide & Docs Refresh (v355)

Created user-facing `docs/TROUBLESHOOTING.md` covering common setup issues
surfaced by `helping-hands doctor`, backend-specific problems, and runtime
errors. Refreshed stale AGENTS.md metadata. 12 doc structure tests added.

---

## Apr 4 — Server App Endpoint Coverage Hardening (v356)

Closed coverage gaps in `server/app.py` (90% → 95%) via edge-case tests for
task diff parsing, file tree building, file content reading, and helper
functions. 7971 passed, 98.70% coverage (with server extras).

---

## Apr 4 — Extract Shared Git Clone Utility (v357)

Eliminated duplicated `git clone` subprocess logic between `cli/main.py` and
`server/celery_app.py` by extracting `run_git_clone()` into `lib/github_url.py`.
CLI's `_run_git_clone` now delegates to the shared function; server's
`_resolve_repo_path` and reference repo cloning use it directly.
Removed redundant imports (`TimeoutExpired`, `_DEFAULT_CLONE_DEPTH`,
credential-redaction helpers) from both consumer modules.

**13 new tests, 6 test files updated. 6789 passed, 75.48% coverage.**

---

## Apr 4 — Extract Token Helpers & Add Tests (v357)

Extracted `redact_token`, `read_claude_credentials_file`, and
`get_claude_oauth_token` from `server/app.py` into `server/token_helpers.py`
— a new module with no FastAPI/Celery dependency, testable in all
environments. 22 new tests covering all branches.

**6795+ total tests. 75.89% coverage (without server extras).**

---

## Apr 4 — E2E Coverage & Exports Cleanup (v358)

Closed test gaps in `e2e.py`: added 8 tests for `_draft_pr_enabled` env-var
gating (default true, explicit true/false/1/0/yes/empty/whitespace) and 2 tests
for `stream()` async wrapper (delegates to `run()`, yields exactly one message).
Added missing `__all__` to `server/multiplayer_yjs.py`. Moved completed v357
plans, fixed doc structure test link failures.

**10 new tests. 6821 total tests. 76.03% coverage.**

---

## Apr 4 — Dead Code Cleanup & Tech Debt Resolution (v359)

Removed unreachable `if not candidate:` guard in `_commit_message_from_prompt`
(`pr_description.py` line 637). The guard was always True because `candidate`
starts as `""` and `break` fires on the first non-boilerplate line — the else
path (candidate already set) was never reachable. Simplified to direct
assignment. Resolved tech debt item tracked since v173.

**0 new tests (40+ existing tests already cover the simplified logic). 6821 total tests. 76.03% coverage.**

---

## Apr 4 — Test Consolidation & Cleanup Candidate Resolution (v360)

Resolved all 6 `# TODO: CLEANUP CANDIDATE` markers across test files. Deleted
fully-duplicate `test_provider_build_inner.py` (9 tests covered by dedicated
provider test files). Removed 33 redundant isinstance/positive/type-only
assertions from constant test files (v135, v137, v138, v139) and 6
docstring-policy tests from `test_iterative_constants.py`.

**42 tests removed, 0 behavioral coverage lost. 6779 total tests. 76.03% coverage.**

---

## Apr 4 — Expand Model Inference Prefixes (v362)

Added common open-source model family prefixes to `_infer_provider_name`
for correct Ollama routing: `mistral`, `mixtral`, `phi`, `codellama`,
`deepseek`, `qwen`, `starcoder`, `vicuna`, `yi`. Added explicit OpenAI
reasoning model prefixes: `gpt`, `o1`, `o3`, `o4`. Previously, bare model
names like `mistral-7b` were silently misrouted to OpenAI. Refactored
to use `_OLLAMA_MODEL_PREFIXES` / `_OPENAI_MODEL_PREFIXES` tuple constants.
Updated `model-resolution.md` design doc.

**21 new tests. 6830 total tests. 76.05% coverage.**

---

## Apr 4 — Config Validation & Finalization Error Hardening (v364)

Hardened config validation and finalization error handling:
- `validate_repo_value()` in `validation.py` — rejects path traversal, null
  bytes, newlines; called from `Config.from_env()` for non-empty repo values
- Debug warning when model remains at `"default"` sentinel
- Catch-all `except Exception` in `_finalize_repo_pr()` logged at ERROR level
- Push error handling broadened to include OSError alongside RuntimeError

**24 new tests, 4 updated. 6854 total tests. 76.15% coverage.**

---

## Apr 4 — CLI `--version` Flag & Doctor Version Display (v365)

Added `--version` / `-V` flag to the CLI entry point, intercepted in `main()`
before `parse_args()` so it works without a positional `repo` argument. Doctor
output header now includes the version string (e.g. `helping-hands doctor v0.1.0`).

**5 new tests. 6859 total tests. 76.17% coverage.**

---

## Apr 5 — Remaining Server Coverage Gaps (v366)

Closed last coverage gaps in server modules by testing previously-uncovered
enabled paths:

- **Grill enabled-path endpoints** (5 tests): `POST /grill` with mocked
  `grill_session.delay`, `POST /grill/{id}/message` session-found and
  session-not-found paths with mocked Redis, `GET /grill/{id}` not-found
  and message-drain paths
- **`_launch_interval_chain`** (2 tests): Happy path verifying Celery chain
  dispatch with mocked `build_feature.apply_async`, nonce persistence, and
  meta save; ImportError fallback returning None
- **`_get_redis_client`** (2 tests): Uses `redbeat_redis_url` when set,
  falls back to `broker_url` when not
- **App lifespan** (1 test): Async context manager calls
  `start_yjs_server`/`stop_yjs_server`

**10 new tests. 8139 total tests (with server extras). 99.44% coverage.**

---

## Apr 5 — Registry Public API Test Coverage (v367)

Added dedicated tests for the registry module's public API functions, which
had no coverage beyond runner wrappers and validator helpers:

- **`available_tool_category_names`** (3 tests): Returns tuple, contains
  execution/web, no empty names
- **`normalize_tool_selection`** (11 tests): Comma strings, lists, tuples,
  None, dedup preserving order, case normalization, underscore-to-hyphen,
  whitespace stripping, empty inputs
- **`_normalize_and_deduplicate`** (5 tests): Type errors (int, dict),
  non-string list items, label in error messages, comma-within-element splitting
- **`validate_tool_category_names`** (5 tests): Valid names pass, empty tuple
  passes, unknown raises ValueError, mixed valid/invalid, error lists available
- **`resolve_tool_categories`** (5 tests): Single/multiple resolution,
  empty input, unknown raises, categories contain ToolSpec objects
- **`merge_with_legacy_tool_flags`** (5 tests): No-flag passthrough,
  execution prepends, web appends, both-flags dedup, empty-with-flags
- **`build_tool_runner_map`** (4 tests): Empty, execution tools callable,
  web tools present, all-category count
- **`category_name_for_tool`** (4 tests): Known execution/web tools,
  unknown returns None, empty string returns None
- **`format_tool_instructions`** (6 tests): Empty returns sentinel, execution
  has @@TOOL blocks, web has @@TOOL blocks, guidance text variants, mixed
- **`format_tool_instructions_for_cli`** (4 tests): Empty returns "",
  execution/web guidance without @@TOOL blocks, category header present

**52 new tests. 97 total registry tests. Registry coverage: 66%.**

---

## Apr 5 — Validation & Factory Hardening (v368)

Two defensive hardening changes:

- **`validate_repo_value()` type guard**: Added `isinstance` check raising
  `TypeError` for non-string input. Previously, passing `None`, `int`, or
  `list` raised `AttributeError` on `.strip()` instead of a clear error.
  Aligns with every other validation function in the module.
  (4 tests: int, None, list, bool)

- **Factory backend/env-var consistency**: Added module-level assertion that
  `SUPPORTED_BACKENDS` keys match `_BACKEND_ENABLED_ENV_VARS` keys. Catches
  future mismatches at import time rather than silently returning wrong results
  from `get_enabled_backends()`.
  (3 tests: import succeeds, sets match, env-var values non-empty)

**7 new tests.**

---

## Apr 5 — Filesystem & Web Type Guards (v369)

Two `isinstance` type guards added to security-boundary functions:

- **`resolve_repo_target()` in `filesystem.py`**: Added type guard raising
  `TypeError` when `repo_root` is not a `Path`. Previously, passing a string,
  int, or None raised `AttributeError` on `.resolve()` instead of a clear error.
  The companion parameter `rel_path` already had a type guard via
  `normalize_relative_path()`.
  (3 tests: str, int, None)

- **`_decode_bytes()` in `web.py`**: Added type guard raising `TypeError` when
  `payload` is not `bytes`. Previously, passing a string or None raised
  `AttributeError` on `.decode()` instead of a clear error.
  (3 tests: str, int, None)

**6 new tests.**

---

## Apr 5 — `--list-backends` CLI Flag (v370)

Added `--list-backends` flag to the CLI for backend discoverability:

- **`list_backends()`**: Formats a table of all supported backends with
  `[+]`/`[-]` availability markers. CLI-backed hands check `shutil.which()`
  for their binary; library hands check `__import__()` for their Python extra.
  E2E backend is always available. Footer shows registered/enabled count.
- **`_check_backend_available(backend)`**: Returns `(available, detail)` tuple
  for a single backend — delegates to `shutil.which` or `__import__` depending
  on backend type.
- **`_BACKEND_CLI_TOOL`** / **`_BACKEND_PYTHON_EXTRA`**: Lookup dicts mapping
  backend names to their CLI binary or Python import+extra names.
- **`--list-backends` flag**: Intercepted in `main()` before argparse (like
  `--version`) so it works without a positional `repo` argument.

**12 new tests. 6936 total tests. 76.21% coverage.**

---

## Apr 5 — Enrich `--list-backends` with Enabled Status (v371)

Enriched `--list-backends` output to show both availability AND enabled/disabled
status per backend via `*_ENABLED` env vars. Added `is_backend_enabled()` public
API to `factory.py`. Disabled backends now show `[-]` with the env var name.
Unmapped backends trigger a logger warning.

**10 new tests. 6946 total tests. 76.32% coverage.**

---

## Apr 5 — `--list-tools` CLI Flag & Registry Coverage (v372)

Added `--list-tools` CLI flag for tool category discoverability, complementing
`--list-backends`. `list_tools()` formats a table of all tool categories with
their tool spec names. Intercepted before argparse so it works without a
positional `repo` argument. Also closed the last registry coverage gap
(`_run_bash_script` both/neither error branch, line 255).

**9 new tests (7 list-tools + 2 registry). 6955 total tests. 76.37% coverage. Registry: 100%.**

---

## Apr 5 — CLI Error Exit Backends Consistency (v374)

Fixed `_CLI_ERROR_EXIT_BACKENDS` missing `opencodecli` and `devincli`. These
CLI backends were not in the error exit set, so failures produced full stack
traces instead of clean `_error_exit()` messages. Added structural consistency
test verifying all CLI-tool-backed backends are in the set (prevents future
regressions when new CLI backends are added).

**9 new tests (5 consistency + 4 error-exit paths). 6969 total tests. 76.49% coverage.**
