# PRD: Exception Specificity, Doc Reconciliation & Obsidian Sync

## Goal

Harden exception handling in server and hand modules by replacing bare `except Exception:` with specific types, then reconcile all documentation surfaces (Obsidian vault, AGENT.md, README, MkDocs) to reflect current stats and conventions.

## Measurable Success Criteria

1. Zero bare `except Exception:` patterns remain in `src/` — all use specific types or `as e:` with logging
2. Test count (579) is consistent across all surfaces: AGENT.md, Obsidian Architecture.md, Concepts.md, Project todos.md
3. Obsidian vault footers and cross-references match the current repo state
4. All 579 tests pass after changes

## User Stories

- As a maintainer, I want all exception handlers to catch specific types so debugging is straightforward.
- As a contributor reading Obsidian docs, I want stats and cross-references to match reality.

## Acceptance Criteria

- [ ] `server/app.py`: 6 bare `except Exception:` replaced with specific types (`redis.exceptions.ConnectionError`, `psycopg2.OperationalError`, `celery.exceptions.OperationalError`, etc.)
- [ ] `e2e.py`: 1 bare `except Exception:` replaced with `GithubException` or specific type
- [ ] `base.py`: 1 bare `except Exception:` replaced with specific type
- [ ] Obsidian Architecture.md footer: 569 → 579 tests
- [ ] Obsidian Concepts.md footer updated
- [ ] Obsidian W10 project log entry added for this session
- [ ] All 579 tests pass

## Non-Goals

- Adding new tests (exception handlers are already covered)
- Changing exception behavior or control flow
- Modifying README content beyond date/stats

## TODO

- [x] Fix 8 bare `except Exception:` patterns in `server/app.py`, `e2e.py`, `base.py`
- [x] Update Obsidian Architecture.md test count footer (569 → 579)
- [x] Update Obsidian Concepts.md footer with current stats
- [x] Add W10 project log entry for this session
- [x] Reconcile remaining cross-surface stats
- [x] Run tests to verify all changes pass

---

## Activity Log

- **Started:** 2026-03-01
- **Status:** Completed
