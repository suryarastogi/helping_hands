# CI Pipeline

How helping_hands validates code quality on every push and pull request.

## Context

The project runs two GitHub Actions workflows: a primary CI pipeline that gates
every PR, and a docs deployment pipeline that publishes to GitHub Pages after CI
succeeds on the default branch.

## CI workflow (`ci.yml`)

### Triggers

- **Push** to `master` or `main`
- **Pull requests** targeting any branch

Concurrency is scoped per-ref (`ci-${{ github.ref }}`), with
`cancel-in-progress: true` so superseded runs are cancelled immediately.

### Backend job (`check`)

Runs across a Python version matrix: **3.12, 3.13, 3.14**.

Steps:

1. **Checkout** via `actions/checkout@v4`
2. **Install uv** via `astral-sh/setup-uv@v5`
3. **Install Python** for the matrix version
4. **Install dependencies** with all extras (`--dev --extra server --extra github
   --extra mcp --extra langchain --extra atomic`) so every optional module is
   exercised
5. **Ruff check** -- lint with the project ruleset (E, W, F, I, N, UP, B, SIM, RUF)
6. **Ruff format check** -- verify formatting matches `ruff format` output
7. **Type check** via `uv run ty check src --ignore unresolved-import --ignore invalid-method-override`
8. **Run tests** via `pytest -v --cov-report=xml` with `GITHUB_TOKEN` from
   secrets for E2E integration tests (opt-in via `HELPING_HANDS_RUN_E2E_INTEGRATION`)
9. **Upload coverage** to Codecov (Python 3.12 job only, `backend` flag)

### Frontend job (`frontend-check`)

Runs on `ubuntu-latest` with Node.js 20.

Steps:

1. **Checkout**
2. **Set up Node.js** with npm cache from `frontend/package-lock.json`
3. **Install dependencies** via `npm install`
4. **Lint** via `npm run lint` (ESLint)
5. **Typecheck** via `npm run typecheck` (TypeScript `--noEmit`)
6. **Tests with coverage** via `npm run coverage` (Vitest)
7. **Upload coverage** to Codecov (`frontend` flag, lcov format)

### Design decisions

- **Full extras in CI** -- all optional dependencies are installed so that
  `pytest.importorskip` never skips tests that should be exercised.  This catches
  import-time regressions across all backends.
- **Matrix across 3 Python versions** -- ensures compatibility with the minimum
  supported version (3.12) and the latest (3.14).
- **Coverage on one version only** -- uploading coverage from all matrix versions
  would create confusing Codecov reports.  Python 3.12 is the canonical coverage
  source.
- **Type checker (`ty`) in CI** -- `ty check src` runs with `--ignore
  unresolved-import` (optional dependencies) and `--ignore invalid-method-override`
  (third-party abstract classes).  Added in v109.

## Docs workflow (`docs.yml`)

### Triggers

- **After CI succeeds** on the default branch (`workflow_run` on CI completion)
- **Weekly schedule** (Monday 06:00 UTC) as a staleness check
- **Manual dispatch** for ad-hoc rebuilds

### Build and deploy

1. **Build** with `uv run mkdocs build --strict` (the `--strict` flag fails on
   warnings, catching broken links and missing references)
2. **Upload** the `site/` directory as a Pages artifact
3. **Deploy** to GitHub Pages via `actions/deploy-pages@v4`

### Design decisions

- **Gated on CI success** -- docs only deploy after CI passes, preventing broken
  documentation from being published.
- **Weekly rebuild** -- catches external link rot and dependency drift without
  requiring a code change.
- **Strict mode** -- `mkdocs build --strict` treats warnings as errors so stale
  cross-references are caught before deployment.

## Environment variables

| Variable | Source | Purpose |
|---|---|---|
| `GITHUB_TOKEN` (CI) | `secrets.BOT_GITHUB_TOKEN` | E2E integration test auth |
| `HELPING_HANDS_RUN_E2E_INTEGRATION` | `vars.*` | Opt-in E2E test gate |
| `HELPING_HANDS_E2E_PR_NUMBER` | `vars.*` | Target PR for E2E runs |
| `CODECOV_TOKEN` | `secrets.CODECOV_TOKEN` | Coverage upload auth |

## Consequences

- Every PR must pass lint, format, type check, and tests on all 3 Python versions before merge.
- Coverage trends are tracked on Codecov with separate backend/frontend flags.
- Documentation is always in sync with the default branch code.
- Adding a new optional extra requires updating the `uv sync` line in `ci.yml`.
