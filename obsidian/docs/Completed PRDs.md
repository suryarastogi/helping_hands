# Completed PRDs

Index of completed product requirement documents. Each PRD includes a TODO checklist and activity log at the bottom. All files live in the repo's [`completed/`](../../completed/) directory.

## Template

- **[PRD.md](../../completed/PRD.md)** — Reusable PRD template with standard sections (problem statement, success criteria, non-goals, TODO, activity log)

## 2026-03-01 — Documentation, Testing & Hardening Sprint

| PRD | Theme |
|-----|-------|
| [cross-surface-reconciliation-packaging-polish](../../completed/PRD-2026-03-01-cross-surface-reconciliation-packaging-polish.md) | Cross-surface doc reconciliation, `pyproject.toml` URLs, Obsidian Home.md footer |
| [dry-validation-finalize-refactor-doc-reconciliation](../../completed/PRD-2026-03-01-dry-validation-finalize-refactor-doc-reconciliation.md) | DRY `validation.py` extraction, `_finalize_repo_pr` refactor, 37th API page |
| [exception-specificity-doc-reconciliation](../../completed/PRD-2026-03-01-exception-specificity-doc-reconciliation.md) | Replace 8 bare `except Exception` with specific types |
| [cli-hand-robustness-docstrings-stream-interrupt-tests-doc-reconciliation](../../completed/PRD-2026-03-01-cli-hand-robustness-docstrings-stream-interrupt-tests-doc-reconciliation.md) | CLI hand private method docstrings, stream/interrupt tests, retry depth guard |
| [type-safety-docstring-polish-doc-reconciliation](../../completed/PRD-2026-03-01-type-safety-docstring-polish-doc-reconciliation.md) | Type hints, `_build_agent` docstrings, `GitHubClient` docstrings |
| [hand-provider-docstring-completion-doc-reconciliation](../../completed/PRD-2026-03-01-hand-provider-docstring-completion-doc-reconciliation.md) | AI provider `_build_inner`/`_complete_impl` docstrings, skills runner docstrings |
| [test-coverage-readme-completeness-doc-reconciliation](../../completed/PRD-2026-03-01-test-coverage-readme-completeness-doc-reconciliation.md) | 30+ tests for `command.py`/`web.py` helpers, README flag documentation |
| [doc-reconciliation-obsidian-sync-final-sweep](../../completed/PRD-2026-03-01-doc-reconciliation-obsidian-sync-final-sweep.md) | Final reconciliation sweep across all surfaces |
| [doc-reconciliation-obsidian-sync-cross-surface-audit](../../completed/PRD-2026-03-01-doc-reconciliation-obsidian-sync-cross-surface-audit.md) | Obsidian sync with Architecture.md, Concepts.md, AGENT.md |
| [cross-surface-doc-reconciliation](../../completed/PRD-2026-03-01-cross-surface-doc-reconciliation.md) | Initial cross-surface audit |
| [doc-reconciliation-mkdocs-coverage-completeness](../../completed/PRD-2026-03-01-doc-reconciliation-mkdocs-coverage-completeness.md) | MkDocs coverage and page completeness |
| [doc-reconciliation-packaging-polish-obsidian-sync](../../completed/PRD-2026-03-01-doc-reconciliation-packaging-polish-obsidian-sync.md) | Packaging polish + Obsidian sync |
| [doc-reconciliation-type-safety-error-logging](../../completed/PRD-2026-03-01-doc-reconciliation-type-safety-error-logging.md) | Type safety and error logging |
| [type-safety-error-handling-provider-tests-doc-reconciliation](../../completed/PRD-2026-03-01-type-safety-error-handling-provider-tests-doc-reconciliation.md) | Provider tests, error handling |
| [cli-hand-test-coverage-doc-reconciliation](../../completed/PRD-2026-03-01-cli-hand-test-coverage-doc-reconciliation.md) | CLI hand test coverage |
| [cli-logging-exception-hardening-doc-reconciliation](../../completed/PRD-2026-03-01-cli-logging-exception-hardening-doc-reconciliation.md) | CLI logging and exception hardening |
| [mcp-app-test-hardening-doc-reconciliation](../../completed/PRD-2026-03-01-mcp-app-test-hardening-doc-reconciliation.md) | MCP and app test hardening |
| [mkdocs-hand-documentation-expansion](../../completed/PRD-2026-03-01-mkdocs-hand-documentation-expansion.md) | MkDocs hand documentation expansion |
| [test-coverage-expansion-robustness-hardening](../../completed/PRD-2026-03-01-test-coverage-expansion-robustness-hardening.md) | Test coverage expansion and robustness |
| [docstring-completion-doc-reconciliation](../../completed/PRD-2026-03-01-docstring-completion-doc-reconciliation.md) | Docstring completion across 12 files |
| [docstring-exports-test-gaps-doc-reconciliation](../../completed/PRD-2026-03-01-docstring-exports-test-gaps-doc-reconciliation.md) | Docstrings, `__all__` exports, test_validation.py, E2EHand tests, Obsidian reconciliation |
| [obsidian-completeness-prd-workflow-doc-reconciliation](../../completed/PRD-2026-03-01-obsidian-completeness-prd-workflow-doc-reconciliation.md) | Obsidian completeness, PRD workflow, active/ directory, validation in README |
| [module-exports-doc-reconciliation-obsidian-sync](../../completed/PRD-2026-03-01-module-exports-doc-reconciliation-obsidian-sync.md) | `__all__` exports for 19 modules, Obsidian test count fix, Completed PRDs index fix |
| [export-hardening-cross-surface-doc-reconciliation](../../completed/PRD-2026-03-01-export-hardening-cross-surface-doc-reconciliation.md) | `__all__` for `atomic.py`/`iterative.py` (40 total), stale test/API counts fixed across obsidian |
| [iterative-hand-docstrings-cross-surface-reconciliation](../../completed/PRD-2026-03-01-iterative-hand-docstrings-cross-surface-reconciliation.md) | 12 iterative.py private method docstrings, Obsidian AGENT.md module count fix (38→40) |
| [package-exports-error-enrichment-doc-reconciliation](../../completed/PRD-2026-03-01-package-exports-error-enrichment-doc-reconciliation.md) | `__all__` for 5 package `__init__.py` (45 total), `filesystem.py` error enrichment, `schedules.py` assert→RuntimeError |
| [code-quality-exports-doc-reconciliation](../../completed/PRD-2026-03-01-code-quality-exports-doc-reconciliation.md) | Module-level imports, `server/app.py` `__all__` completion (15 exports), skills `__all__` relocation, CLI hand docstrings, README↔CLAUDE.md reconciliation |
| [cross-surface-reconciliation-doc-hygiene](../../completed/PRD-2026-03-01-cross-surface-reconciliation-doc-hygiene.md) | PRD naming fix, W10→W09 log entry migration, README structure tree update, cross-surface metric verification |

## Earlier PRDs (undated)

| PRD | Theme |
|-----|-------|
| [api-validation-hardening](../../completed/PRD-api-validation-hardening.md) | API input validation and bounds checks |
| [production-robustness-e2e-hardening](../../completed/PRD-production-robustness-e2e-hardening.md) | Production robustness and E2E hardening |
| [test-coverage-and-docs-quality](../../completed/PRD-test-coverage-and-docs-quality.md) | Test coverage and documentation quality |

---

*Last updated: 2026-03-01 — 31 completed PRDs indexed.*
