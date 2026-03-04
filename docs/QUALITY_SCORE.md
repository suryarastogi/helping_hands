# Quality Score

Metrics and standards for code quality in helping_hands.

## Current quality gates

### CI pipeline (GitHub Actions)

| Check | Tool | Scope | Status |
|---|---|---|---|
| Lint | `ruff check` | All Python | Enforced |
| Format | `ruff format --check` | All Python | Enforced |
| Tests | `pytest -v` | `tests/` | Enforced |
| Coverage | `pytest-cov` + Codecov | Python 3.12 job | Reporting |
| Frontend lint | `eslint` | `frontend/src/` | Enforced |
| Frontend types | `tsc --noEmit` | `frontend/src/` | Enforced |
| Frontend tests | Vitest | `frontend/src/` | Enforced |

### Local quality checks

```bash
uv run ruff check .               # lint
uv run ruff format --check .      # format
uv run pytest -v                  # tests + coverage
uv run pre-commit run --all-files # all hooks
npm --prefix frontend run lint    # frontend lint
npm --prefix frontend run typecheck  # frontend types
npm --prefix frontend run test    # frontend tests
```

## Coverage targets

- **Backend:** Track via Codecov; aim for increasing coverage each PR
- **Frontend:** Track via Codecov (separate flag); aim for component coverage

## Testing conventions

- Tests live in `tests/` (flat structure, `test_*.py` naming)
- Use `pytest` fixtures (`tmp_path`, `monkeypatch`) over manual setup/teardown
- Mock external services (GitHub API, AI providers) in unit tests
- Integration tests are opt-in (`HELPING_HANDS_RUN_E2E_INTEGRATION=1`)

## Ruff configuration

Rules enabled: `E, W, F, I, N, UP, B, SIM, RUF`
Line length: 88
Target Python: 3.12+

## Areas for improvement

- [ ] Add type checking to CI (ty, when stable for CI runners)
- [ ] Add mutation testing for critical path safety (filesystem tools)
- [ ] Increase coverage for CLI hand subprocess wrappers
- [ ] Add load testing for app mode concurrent task handling
