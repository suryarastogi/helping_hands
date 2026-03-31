# Config Loading

How helping_hands loads and merges configuration from multiple sources into a
single immutable `Config` dataclass.

## Context

The application runs in three modes (CLI, server, MCP) that all need consistent
configuration. Config values come from environment variables, `.env` files, and
CLI flags, with a clear precedence order. The design must prevent accidental
mutation during a run and handle optional dependencies gracefully.

## Precedence

Configuration merges in this order (later wins):

```
dataclass defaults  <  env vars  <  CLI overrides
```

The `Config.from_env()` classmethod implements this chain:

1. **Dotenv loading** -- `_load_env_files()` loads `.env` from cwd and
   (optionally) the target repo directory. Uses `override=False` so existing
   env vars are never clobbered.
2. **Env var reading** -- reads `HELPING_HANDS_*` vars into a dict.
3. **Truthy filtering** -- falsy env values are dropped so defaults are preserved
   (e.g. `HELPING_HANDS_VERBOSE=""` keeps the default `verbose=True`).
4. **Override merge** -- CLI-provided `overrides` dict is merged on top, with
   `None` values filtered out so unset CLI flags don't clobber env vars.
5. **Normalization** -- tool selections are passed through
   `normalize_tool_selection()`, which accepts comma-separated strings,
   tuples, or booleans.

## Frozen dataclass

`Config` is `@dataclass(frozen=True)`. Once constructed, no attribute can be
reassigned. This guarantees that hands, providers, and finalization logic all
see the same config snapshot throughout a run.

## Dotenv integration

`python-dotenv` is a soft dependency:

```python
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
```

When absent, `_load_env_files()` returns immediately. When present, it loads
from two paths in order:

1. `Path.cwd() / ".env"` -- project-level defaults
2. `Path(repo) / ".env"` -- repo-specific overrides (only when `repo` is a
   directory)

Both use `override=False`, so an env var already set in the shell always wins.

## Boolean normalization

Boolean env vars (`HELPING_HANDS_VERBOSE`, `HELPING_HANDS_ENABLE_EXECUTION`,
etc.) are recognized as truthy for values `"1"`, `"true"`, `"yes"` (case-
insensitive). All other values, including empty strings, produce `False`.

Because the merge step filters falsy values, boolean env vars can only turn
features *on*, not explicitly off. To disable a default-on feature like
`verbose`, use CLI overrides (`overrides={"verbose": False}`).

## Tool selection

The `enabled_tools` field accepts multiple input types:

| Input | Behavior |
|---|---|
| `None` or unset | Empty tuple (no tools) |
| `bool` (`True`/`False`) | Normalized to empty tuple |
| Comma-separated string | Split and normalized by registry module |
| Tuple of strings | Passed through to normalizer |

This flexibility supports both env var strings (`"python.run_code, bash"`) and
programmatic tuple inputs.

## Consequences

- **No runtime mutation** -- frozen dataclass prevents accidental config changes
  mid-run.
- **Env-only activation** -- boolean env vars can activate features but not
  deactivate default-on features; this is intentional to keep the env var
  interface simple.
- **Soft dependencies** -- missing `python-dotenv` degrades gracefully; the
  rest of config loading proceeds normally.
- **Testability** -- `monkeypatch.setenv` / `monkeypatch.setattr` in tests
  cleanly control all config inputs without leaking state between tests.
