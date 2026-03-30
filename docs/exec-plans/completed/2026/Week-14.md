# Week 14 (Mar 30 – Apr 5, 2026)

Meta tools coverage hardening (v339) and server app workspace/diff/tree/worker
capacity coverage (v340).

---

## Mar 30 — Meta Tools Coverage Hardening (v339)

Close testable coverage gaps in `meta/tools/web.py` (81% → 98%) and
`meta/tools/filesystem.py` (92% → 100%): `_raise_url_error` HTTP vs URL paths,
`_require_http_url` scheme/netloc validation, `_decode_bytes` encoding fallback,
`_as_string_keyed_dict` edge cases, `_extract_related_topics` nested recursion,
`search_web` error handling and deduplication, `browse_url` non-HTML content,
`normalize_relative_path` type check, `read_text_file` large file rejection,
`mkdir_path` OSError wrapping. 42 new tests, 6580 tests passed, 75.84% coverage.

See [v339 plan](v339-meta-tools-coverage-hardening.md).

## Mar 30 — Server App Workspace, Diff, Tree & Worker Capacity Coverage (v340)

Close coverage gaps in `server/app.py` (80% → 97%): `_resolve_task_workspace`
(dict result, repo_path fallback, cleaned up, not found), `_build_task_diff`
(unified diff parsing, untracked files, git error, HEAD fallback, multi-file),
`_build_task_tree` (tree walk, git status annotations, rename/delete/add),
`_read_task_file` (content read, path traversal block, size limit, untracked
synthetic diff, new/deleted detection), `_resolve_worker_capacity` (celery
stats/env var/default cascade), arcade high-score endpoints, multiplayer
health endpoints. 50 new tests, 7753 tests passed, 99.13% coverage.

See [v340 plan](v340-server-app-workspace-diff-tree-coverage.md).
