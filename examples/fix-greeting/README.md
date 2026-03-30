# fix-greeting

A tiny Python package with a deliberate bug in `src/greet.py`. The `greet()`
function should return `"Hello, Alice!"` but instead returns `"Hello, !"` —
the name is missing from the format string.

## The bug

```python
def greet(name: str) -> str:
    return "Hello, !"   # <-- name is not interpolated
```

## Running the example

From the repo root:

```bash
./examples/fix-greeting/run.sh
```

This invokes `helping-hands` with `--no-pr` so no GitHub token is required.
The AI agent will read the code, identify the bug, and fix it.

## Verifying the fix

After the agent runs, check that the tests pass:

```bash
cd examples/fix-greeting
python -m pytest tests/ -v
```
