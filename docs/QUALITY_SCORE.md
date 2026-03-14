# Quality score

Quality metrics and targets for helping_hands.

## Current status (2026-03-14)

| Metric | Status | Target |
|---|---|---|
| Test count | 30+ | Growing with features |
| Test pass rate | 100% | 100% |
| Lint (ruff check) | Clean | Zero warnings |
| Format (ruff format) | Clean | Consistent |
| Type coverage | Partial (ty) | Full when ty stable in CI |
| Doc coverage | Public APIs | All public APIs documented |
| CI pipeline | Green | Always green on main |

## Quality practices

- **Pre-commit hooks**: ruff lint + format on every commit.
- **CI matrix**: Tests run on Python 3.11, 3.12, 3.13.
- **Google-style docstrings**: Required for public functions and classes.
- **Type hints everywhere**: `X | None` style, checked by ty.
- **Small diffs**: Prefer focused changes over large rewrites.
