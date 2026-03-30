# Examples

Sample repositories for trying out `helping_hands` locally.

## Available examples

| Example | Description | Difficulty |
|---|---|---|
| [fix-greeting](fix-greeting/) | Fix a bug in a greeting function | Beginner |

## Usage

Each example includes a `run.sh` script that invokes `helping-hands` with
`--no-pr` so no GitHub access is required. You need:

1. Python 3.12+ with `uv` installed
2. `helping_hands` installed (`uv sync --dev` from the repo root)
3. At least one AI provider API key set (e.g. `OPENAI_API_KEY`)

Then from the repo root:

```bash
./examples/fix-greeting/run.sh
```
