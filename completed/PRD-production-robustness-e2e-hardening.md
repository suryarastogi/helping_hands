# PRD: Production Robustness & E2E Hardening

**Status:** Completed
**Completed:** 2026-03-01
**Created:** 2026-03-01
**Goal:** Close the three highest-impact robustness gaps in helping_hands — GitHub API error handling, E2E branch collision / draft PR safety, and config input validation — then reconcile all documentation surfaces.

---

## Problem Statement

The helping_hands codebase has strong architecture and comprehensive documentation, but a production audit reveals three concrete robustness gaps:

1. **`lib/github.py` has no error handling around PyGithub API calls.** Methods like `create_pr()`, `get_pr()`, `whoami()`, and `upsert_pr_comment()` make raw API calls that will surface opaque `github.GithubException` tracebacks to users on auth failures, rate limits, 404s, and network errors. This affects every hand's finalization workflow.

2. **E2E hardening is incomplete** (the sole unchecked TODO item under hand scaffolding). Specifically:
   - Branch collision: `create_branch()` fails silently if the branch already exists from a prior run.
   - Draft PR mode: `create_pr()` already accepts `draft=True` but `E2EHand.run()` provides no way to request it.
   - Idempotency: re-running without `--pr-number` creates duplicate branches/PRs instead of detecting and reusing the prior one.

3. **`lib/config.py` lacks input validation.** The `repo` and `model` fields accept any string without checking format. Invalid inputs produce confusing downstream errors instead of clear validation messages.

## Success Criteria

- [x] GitHub API methods in `github.py` wrap PyGithub exceptions with clear error messages and logging
- [x] `E2EHand` handles branch collisions by switching to existing branch instead of failing
- [x] `E2EHand` supports draft PR mode via config/env
- [x] `Config` validates `repo` format when non-empty (path or `owner/repo` pattern)
- [x] All documentation surfaces reconciled (obsidian project log, project todos, AGENT.md)
- [x] All tests pass

## Non-Goals

- Adding retry logic for transient API errors (future work)
- Adding rate-limit backoff (future work)
- Rewriting E2E hand architecture
- Adding new backends or features

---

## TODO

### 1. Add GitHub API error handling to `github.py`
- [x] Wrap `whoami()`, `get_repo()`, `create_pr()`, `get_pr()`, `list_prs()`, `default_branch()`, `update_pr_body()`, `upsert_pr_comment()` with try/except for `github.GithubException`
- [x] Log clear error messages with status codes and context
- [x] Re-raise as `RuntimeError` with actionable messages (e.g., "GitHub auth failed — check GITHUB_TOKEN")

### 2. Add E2E hardening
- [x] Handle branch collision: detect existing branch and switch to it instead of failing on `create_branch()`
- [x] Add `draft_pr` support: read `HELPING_HANDS_DRAFT_PR` env var, pass `draft=True` to `create_pr()`
- [x] Add idempotency guard: before creating a new PR, check if an open PR already exists for the head branch and reuse it

### 3. Add config input validation
- [x] Validate `repo` format: when non-empty, must be a filesystem path or match `owner/repo` pattern
- [x] Log a warning for `model` values that don't match known patterns (bare name or `provider/model`)

### 4. Reconcile documentation surfaces
- [x] Update Obsidian Project Log `2026-W09.md` with this session's work
- [x] Sync `obsidian/docs/Project todos.md` design notes with current TODO.md state
- [x] Update AGENT.md recurring decisions with new E2E hardening decision

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created; codebase audit identified three robustness gaps |
| 2026-03-01 | Wrapped 8 GitHub API methods in `github.py` with `GithubException` handling; added `_github_error_message()` helper with status-code hints; added `find_open_pr_for_branch()` and `local_branch_exists()` methods |
| 2026-03-01 | E2E hardening: branch collision detection/switch, draft PR mode (`HELPING_HANDS_DRAFT_PR`), idempotency guard (detect/reuse open PR for head branch) |
| 2026-03-01 | Config validation: `__post_init__` validates `repo` format and warns on unexpected `model` patterns |
| 2026-03-01 | Reconciled obsidian (Project Log W09, Project todos, Architecture, Concepts), AGENT.md recurring decisions, TODO.md E2E hardening item |
| 2026-03-01 | All 367 tests pass; lint and format clean. PRD moved to completed/ |
