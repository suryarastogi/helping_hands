# v347 — Doctor & RepoIndex Enhancements

**Status:** completed
**Created:** 2026-04-04

## Goal

Enhance the `helping-hands doctor` subcommand with Docker and Node.js
availability checks, and add utility methods to `RepoIndex` for querying
indexed file metadata. Also consolidate 2026-03-30 into Week-14.

## Tasks

- [x] Add `_check_docker()` to doctor.py — checks Docker CLI availability
      (needed for `docker-sandbox-claude` backend)
- [x] Add `_check_node()` to doctor.py — checks Node.js availability
      (needed for frontend development)
- [x] Add `file_count` property to `RepoIndex` — returns `len(self.files)`
- [x] Add `has_file(relative_path)` method to `RepoIndex` — O(log n) lookup
- [x] Write tests for all new functionality (16 new tests)
- [x] Create Week-14 consolidation doc
- [x] Update INTENT.md, PLANS.md

## Rationale

Doctor currently checks CLI backends but not Docker (required for
`docker-sandbox-claude`) or Node.js (required for frontend). RepoIndex is
used by all hands but lacks basic query methods, forcing callers to
manually search `self.files`.
