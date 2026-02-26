"""Shared default prompts used by CLI and app entry points."""

DEFAULT_SMOKE_TEST_PROMPT = (
    "Update README.md with results of your smoke test.\n"
    "Try out each capability and summarize outcome:\n"
    "1. @@READ to inspect README.md.\n"
    "2. @@FILE to apply README.md updates.\n"
    "3. If execution tools are enabled, @@TOOL python.run_code "
    "(python_version=3.13) for a tiny inline check.\n"
    "4. If execution tools are enabled, @@TOOL python.run_script by creating "
    "and running scripts/smoke_test.py.\n"
    "5. If execution tools are enabled, @@TOOL bash.run_script by creating "
    "and running scripts/smoke_test.sh.\n"
    "6. If web tools are enabled, use @@TOOL web.search and @@TOOL web.browse.\n"
    "Keep changes minimal and safe."
)
