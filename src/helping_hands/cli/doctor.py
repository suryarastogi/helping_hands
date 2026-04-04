"""``helping-hands doctor`` — verify environment prerequisites.

Checks Python version, required tools, provider API keys, optional
extras, and optional CLI backends so a new user can quickly diagnose
what's missing before their first run.
"""

from __future__ import annotations

import importlib
import os
import shutil
import sys
from dataclasses import dataclass

__all__ = ["CheckResult", "collect_checks", "format_results", "run_doctor"]

# ---------------------------------------------------------------------------
# Check result type
# ---------------------------------------------------------------------------

_OK = "ok"
_WARN = "warn"
_FAIL = "fail"


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single doctor check.

    Attributes:
        name: Short human-readable label (e.g. ``"python"``).
        status: One of ``"ok"``, ``"warn"``, or ``"fail"``.
        message: Detail message displayed to the user.
    """

    name: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

_MIN_PYTHON = (3, 12)
"""Minimum required Python version."""

_PROVIDER_ENV_VARS: tuple[tuple[str, str], ...] = (
    ("OPENAI_API_KEY", "OpenAI"),
    ("ANTHROPIC_API_KEY", "Anthropic"),
    ("GOOGLE_API_KEY", "Google (Gemini)"),
)
"""Provider API key env vars and their human-readable names."""

_GITHUB_TOKEN_ENV_VARS: tuple[str, ...] = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
)
"""GitHub token env vars checked in priority order."""

_OPTIONAL_CLI_TOOLS: tuple[tuple[str, str], ...] = (
    ("claude", "claudecodecli backend"),
    ("codex", "codexcli backend"),
    ("goose", "goose backend"),
    ("gemini", "geminicli backend"),
)
"""Optional CLI tools and what they enable."""

_OPTIONAL_EXTRAS: tuple[tuple[str, str, str], ...] = (
    ("langchain_core", "langchain", "basic-langgraph backend"),
    ("atomic_agents", "atomic", "basic-atomic / basic-agent backends"),
    ("fastapi", "server", "FastAPI server + Celery workers"),
)
"""(import_name, extra_name, description) for optional pip extras."""

_MIN_NODE = 18
"""Minimum recommended Node.js major version for frontend development."""


def _check_python() -> CheckResult:
    """Check Python version meets minimum requirement."""
    vi = sys.version_info
    version_str = f"{vi.major}.{vi.minor}.{vi.micro}"
    if (vi.major, vi.minor) >= _MIN_PYTHON:
        return CheckResult("python", _OK, f"Python {version_str}")
    return CheckResult(
        "python",
        _FAIL,
        f"Python {version_str} — requires {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}+",
    )


def _check_git() -> CheckResult:
    """Check that ``git`` is on PATH."""
    if shutil.which("git"):
        return CheckResult("git", _OK, "git found")
    return CheckResult("git", _FAIL, "git not found — install git")


def _check_uv() -> CheckResult:
    """Check that ``uv`` is on PATH."""
    if shutil.which("uv"):
        return CheckResult("uv", _OK, "uv found")
    return CheckResult(
        "uv", _WARN, "uv not found — recommended for dependency management"
    )


def _check_provider_keys() -> list[CheckResult]:
    """Check for at least one AI provider API key."""
    results: list[CheckResult] = []
    found_any = False
    for env_var, provider_name in _PROVIDER_ENV_VARS:
        if os.environ.get(env_var, "").strip():
            results.append(CheckResult(env_var, _OK, f"{provider_name} key set"))
            found_any = True
        else:
            results.append(CheckResult(env_var, _WARN, f"{provider_name} key not set"))
    if not found_any:
        results.append(
            CheckResult(
                "provider_keys",
                _FAIL,
                "no AI provider key found — set at least one of: "
                + ", ".join(var for var, _ in _PROVIDER_ENV_VARS),
            )
        )
    return results


def _check_github_token() -> CheckResult:
    """Check for a GitHub token."""
    for var in _GITHUB_TOKEN_ENV_VARS:
        if os.environ.get(var, "").strip():
            return CheckResult("github_token", _OK, f"{var} set")
    return CheckResult(
        "github_token",
        _WARN,
        "no GitHub token — set GITHUB_TOKEN or GH_TOKEN for PR creation",
    )


def _check_optional_cli_tools() -> list[CheckResult]:
    """Check availability of optional external CLI tools."""
    results: list[CheckResult] = []
    for tool_name, description in _OPTIONAL_CLI_TOOLS:
        if shutil.which(tool_name):
            results.append(CheckResult(tool_name, _OK, f"{tool_name} found"))
        else:
            results.append(
                CheckResult(
                    tool_name,
                    _WARN,
                    f"{tool_name} not found — needed for {description}",
                )
            )
    return results


def _check_docker() -> CheckResult:
    """Check that ``docker`` is on PATH (needed for docker-sandbox backends)."""
    if shutil.which("docker"):
        return CheckResult("docker", _OK, "docker found")
    return CheckResult(
        "docker",
        _WARN,
        "docker not found — needed for docker-sandbox-* backends",
    )


def _check_node() -> CheckResult:
    """Check that ``node`` is on PATH and meets the minimum version.

    Node.js is required for frontend development (React + Vite).
    """
    node_path = shutil.which("node")
    if not node_path:
        return CheckResult(
            "node",
            _WARN,
            "node not found — needed for frontend development",
        )
    import subprocess

    try:
        raw = subprocess.run(
            [node_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        # Node outputs "vXX.YY.ZZ"
        version_str = raw.lstrip("v")
        major = int(version_str.split(".")[0])
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return CheckResult(
            "node",
            _WARN,
            "node found but could not determine version",
        )
    if major >= _MIN_NODE:
        return CheckResult("node", _OK, f"node v{version_str}")
    return CheckResult(
        "node",
        _WARN,
        f"node v{version_str} — recommend v{_MIN_NODE}+ for frontend dev",
    )


def _check_redis_cli() -> CheckResult:
    """Check that ``redis-cli`` is on PATH (needed for local-stack server mode)."""
    if shutil.which("redis-cli"):
        return CheckResult("redis-cli", _OK, "redis-cli found")
    return CheckResult(
        "redis-cli",
        _WARN,
        "redis-cli not found — needed for local-stack server mode",
    )


def _check_docker_compose() -> CheckResult:
    """Check that ``docker compose`` subcommand is available.

    Required for app-mode deployment via ``docker compose up`` or
    ``./scripts/run-local-stack.sh``.
    """
    import subprocess

    docker_path = shutil.which("docker")
    if not docker_path:
        return CheckResult(
            "docker-compose",
            _WARN,
            "docker compose not available — docker not found",
        )
    try:
        cp = subprocess.run(
            [docker_path, "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if cp.returncode == 0:
            version_line = cp.stdout.strip()
            return CheckResult("docker-compose", _OK, f"docker compose: {version_line}")
        return CheckResult(
            "docker-compose",
            _WARN,
            "docker found but 'docker compose' subcommand not available",
        )
    except (subprocess.TimeoutExpired, OSError):
        return CheckResult(
            "docker-compose",
            _WARN,
            "docker found but could not verify 'docker compose'",
        )


def _check_optional_extras() -> list[CheckResult]:
    """Check availability of optional Python package extras."""
    results: list[CheckResult] = []
    for import_name, extra_name, description in _OPTIONAL_EXTRAS:
        try:
            importlib.import_module(import_name)
            results.append(
                CheckResult(extra_name, _OK, f"{extra_name} extra installed")
            )
        except ImportError:
            results.append(
                CheckResult(
                    extra_name,
                    _WARN,
                    f"{extra_name} extra not installed — needed for {description}. "
                    f"Install with: uv sync --extra {extra_name}",
                )
            )
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def collect_checks() -> list[CheckResult]:
    """Run all doctor checks and return the results.

    Returns:
        Ordered list of :class:`CheckResult` objects.
    """
    results: list[CheckResult] = [
        _check_python(),
        _check_git(),
        _check_uv(),
    ]
    results.extend(_check_provider_keys())
    results.append(_check_github_token())
    results.extend(_check_optional_cli_tools())
    results.append(_check_docker())
    results.append(_check_docker_compose())
    results.append(_check_redis_cli())
    results.append(_check_node())
    results.extend(_check_optional_extras())
    return results


_STATUS_SYMBOLS: dict[str, str] = {
    _OK: "+",
    _WARN: "!",
    _FAIL: "x",
}
"""Symbols used for formatting check results."""


def format_results(results: list[CheckResult]) -> str:
    """Format check results as a human-readable report.

    Args:
        results: List of check results to format.

    Returns:
        Multi-line string with one line per check.
    """
    from helping_hands import __version__

    lines: list[str] = [f"helping-hands doctor v{__version__}", ""]
    for r in results:
        symbol = _STATUS_SYMBOLS.get(r.status, "?")
        lines.append(f"  [{symbol}] {r.message}")

    fails = sum(1 for r in results if r.status == _FAIL)
    warns = sum(1 for r in results if r.status == _WARN)
    lines.append("")
    if fails:
        lines.append(f"{fails} issue(s) must be fixed before helping-hands can run.")
    elif warns:
        lines.append(f"All required checks passed. {warns} optional warning(s).")
    else:
        lines.append("All checks passed.")
    return "\n".join(lines)


def run_doctor() -> int:
    """Run all checks, print the report, and return an exit code.

    Returns:
        0 if no failures, 1 if any check has status ``"fail"``.
    """
    results = collect_checks()
    print(format_results(results))
    has_failure = any(r.status == _FAIL for r in results)
    return 1 if has_failure else 0
