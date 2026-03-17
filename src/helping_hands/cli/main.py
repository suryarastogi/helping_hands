"""CLI entry point: parse args, load config, run the agent loop."""

from __future__ import annotations

import argparse
import asyncio
import atexit
import re
import shutil
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from subprocess import TimeoutExpired
from tempfile import mkdtemp
from typing import Any, cast

from helping_hands.lib.config import Config, ConfigValue
from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.lib.github_url import (
    DEFAULT_CLONE_ERROR_MSG as _DEFAULT_CLONE_ERROR_MSG,
    GIT_CLONE_TIMEOUT_S as _GIT_CLONE_TIMEOUT_S,
    REPO_SPEC_PATTERN as _REPO_SPEC_PATTERN,
    build_clone_url as _build_clone_url,
    invalid_repo_msg as _invalid_repo_msg,
    noninteractive_env as _git_noninteractive_env,
    redact_credentials as _redact_sensitive,
    repo_tmp_dir as _repo_tmp_dir,
    validate_repo_spec as _validate_repo_spec,
)
from helping_hands.lib.hands.v1.hand import E2EHand, Hand
from helping_hands.lib.hands.v1.hand.factory import (
    BACKEND_BASIC_AGENT,
    BACKEND_BASIC_ATOMIC,
    BACKEND_BASIC_LANGGRAPH,
    BACKEND_CLAUDECODECLI,
    BACKEND_CODEXCLI,
    BACKEND_DOCKER_SANDBOX_CLAUDE,
    BACKEND_E2E,
    BACKEND_GEMINICLI,
    BACKEND_GOOSE,
    SUPPORTED_BACKENDS,
    create_hand,
)
from helping_hands.lib.meta import skills as meta_skills
from helping_hands.lib.meta.tools import registry as meta_tools
from helping_hands.lib.repo import RepoIndex
from helping_hands.lib.validation import install_hint, require_positive_int

__all__ = ["build_parser", "main"]

# --- Module-level constants ---------------------------------------------------

_DEFAULT_CLONE_DEPTH = 1
"""Shallow clone depth used when cloning ``owner/repo`` inputs."""

_TEMP_CLONE_PREFIX = "helping_hands_repo_"
"""Prefix for temporary directories created for cloned repositories."""

_MODEL_NOT_FOUND_MARKERS: tuple[str, ...] = ("model_not_found", "does not exist")
"""Substrings in exception messages that indicate a model-not-found error."""

_MODEL_NOT_AVAILABLE_MSG = (
    "model {model!r} is not available. "
    "Pass a valid model via --model (or HELPING_HANDS_MODEL), "
    "for example: --model gpt-5.2"
)
"""User-facing message template when the requested model is not found."""

_CLI_ERROR_EXIT_BACKENDS: frozenset[str] = frozenset(
    {
        BACKEND_CODEXCLI,
        BACKEND_CLAUDECODECLI,
        BACKEND_DOCKER_SANDBOX_CLAUDE,
        BACKEND_GOOSE,
        BACKEND_GEMINICLI,
    }
)
"""Backends that print the error and ``sys.exit(1)`` instead of re-raising."""


def _error_exit(msg: str) -> None:
    """Print *msg* to stderr prefixed with ``Error:`` and exit with code 1.

    Args:
        msg: The error description to display.
    """
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def _validate_or_exit(fn: object, *args: object, **kwargs: object) -> object:
    """Call *fn* and exit on ``ValueError``.

    Wraps a validation callable so that a ``ValueError`` is printed to
    *stderr* and the process exits with code 1.  Returns *fn*'s result
    on success.

    Args:
        fn: Callable to invoke.
        *args: Positional arguments forwarded to *fn*.
        **kwargs: Keyword arguments forwarded to *fn*.

    Returns:
        The return value of *fn* when no ``ValueError`` is raised.
    """
    try:
        return fn(*args, **kwargs)  # type: ignore[operator]
    except ValueError as exc:
        _error_exit(str(exc))


def _run_git_clone(
    url: str, dest: Path, *, label: str
) -> subprocess.CompletedProcess[str]:
    """Run ``git clone --depth …`` and return the completed process.

    Args:
        url: The HTTPS clone URL.
        dest: Destination directory for the clone.
        label: Human-readable label for error messages (e.g. ``owner/repo``).

    Returns:
        The :class:`subprocess.CompletedProcess` on success.

    Raises:
        ValueError: If cloning times out or exits with a non-zero code.
    """
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", str(_DEFAULT_CLONE_DEPTH), url, str(dest)],
            capture_output=True,
            text=True,
            check=False,
            env=_git_noninteractive_env(),
            timeout=_GIT_CLONE_TIMEOUT_S,
        )
    except TimeoutExpired as exc:
        raise ValueError(
            f"git clone timed out after {_GIT_CLONE_TIMEOUT_S}s for {label}"
        ) from exc
    if result.returncode != 0:
        stderr = _redact_sensitive(result.stderr.strip() or _DEFAULT_CLONE_ERROR_MSG)
        raise ValueError(f"failed to clone {label}: {stderr}")
    return result


def _make_temp_clone_dir(prefix: str) -> Path:
    """Create a temporary directory for cloning and register it for cleanup.

    Creates a temp directory with the given *prefix* under the configured
    temp root, registers ``shutil.rmtree`` via ``atexit``, and returns
    the nested ``repo`` subdirectory path (which does not yet exist).

    Args:
        prefix: Prefix for the ``mkdtemp`` call.

    Returns:
        Path to the ``<tmpdir>/repo`` subdirectory.
    """
    dest_root = Path(mkdtemp(prefix=prefix, dir=_repo_tmp_dir()))
    atexit.register(shutil.rmtree, dest_root, True)
    return dest_root / "repo"


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for CLI mode."""
    parser = argparse.ArgumentParser(
        prog="helping-hands",
        description="AI-powered repo builder.",
    )
    parser.add_argument(
        "repo",
        help=(
            "Local repository path (default mode) or GitHub owner/repo "
            "when using --e2e."
        ),
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_SMOKE_TEST_PROMPT,
        help="Prompt to pass to the selected hand.",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        default=None,
        help="Optional existing PR number to resume/update in --e2e mode.",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Run E2EHand flow: clone/edit/commit/push/PR.",
    )
    parser.add_argument(
        "--backend",
        choices=sorted(SUPPORTED_BACKENDS - {BACKEND_E2E}),
        default=None,
        help="Run an iterative coding hand in CLI mode.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=6,
        help="Maximum iterations for basic hands.",
    )
    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Disable final commit/push/PR step.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="AI model to use (overrides env/config).",
    )
    parser.add_argument(
        "--enable-execution",
        action="store_true",
        help="Enable python.run_code/python.run_script/bash.run_script tools.",
    )
    parser.add_argument(
        "--enable-web",
        action="store_true",
        help="Enable web.search/web.browse tools.",
    )
    parser.add_argument(
        "--use-native-cli-auth",
        action="store_true",
        help=(
            "For codexcli/claudecodecli, prefer existing native CLI auth/session "
            "by removing provider API key env vars from subprocess execution."
        ),
    )
    parser.add_argument(
        "--tools",
        default=None,
        help=(
            "Comma-separated tool category names "
            f"(available: {', '.join(meta_tools.available_tool_category_names())})."
        ),
    )
    parser.add_argument(
        "--skills",
        default=None,
        help=(
            "Comma-separated skill knowledge files to inject "
            f"(available: {', '.join(meta_skills.available_skill_names())})."
        ),
    )
    parser.add_argument(
        "--github-token",
        default=None,
        help=(
            "GitHub token for this task (overrides GITHUB_TOKEN / GH_TOKEN). "
            "Useful when a task requires different permissions."
        ),
    )
    parser.add_argument(
        "--reference-repos",
        default=None,
        help=(
            "Comma-separated owner/repo references to clone as read-only "
            "context (e.g. 'owner/repo1,owner/repo2')."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=None,
        help="Enable verbose output.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    selected_tools = _validate_or_exit(meta_tools.normalize_tool_selection, args.tools)
    _validate_or_exit(meta_tools.validate_tool_category_names, selected_tools)

    selected_skills = _validate_or_exit(
        meta_skills.normalize_skill_selection, args.skills
    )
    _validate_or_exit(meta_skills.validate_skill_names, selected_skills)

    if args.pr_number is not None:
        _validate_or_exit(require_positive_int, args.pr_number, "--pr-number")
    if args.max_iterations is not None:
        _validate_or_exit(require_positive_int, args.max_iterations, "--max-iterations")

    if args.e2e:
        e2e_overrides: dict[str, ConfigValue] = cast(
            dict[str, Any],
            {
                "repo": args.repo,
                "model": args.model,
                "verbose": args.verbose,
                "enable_execution": args.enable_execution,
                "enable_web": args.enable_web,
                "use_native_cli_auth": args.use_native_cli_auth,
                "enabled_tools": selected_tools,
                "enabled_skills": selected_skills,
                "github_token": args.github_token,
                "reference_repos": args.reference_repos,
            },
        )
        config = Config.from_env(overrides=e2e_overrides)
        repo_index = RepoIndex(root=Path(config.repo or "."), files=[])
        response = E2EHand(config, repo_index).run(
            args.prompt,
            pr_number=args.pr_number,
            dry_run=args.no_pr,
        )
        print(response.message)
        print(f"hand_uuid={response.metadata.get('hand_uuid')}")
        print(f"workspace={response.metadata.get('workspace')}")
        print(f"pr_url={response.metadata.get('pr_url')}")
        return

    try:
        repo_path, cloned_from = _resolve_repo_path(args.repo)
    except ValueError as exc:
        _error_exit(str(exc))
    if cloned_from:
        print(f"Cloned {cloned_from} to {repo_path}")

    run_overrides: dict[str, ConfigValue] = cast(
        dict[str, Any],
        {
            "repo": str(repo_path),
            "model": args.model,
            "verbose": args.verbose,
            "enable_execution": args.enable_execution,
            "enable_web": args.enable_web,
            "use_native_cli_auth": args.use_native_cli_auth,
            "enabled_tools": selected_tools,
            "enabled_skills": selected_skills,
            "github_token": args.github_token,
            "reference_repos": args.reference_repos,
        },
    )
    config = Config.from_env(overrides=run_overrides)
    repo_index = RepoIndex.from_path(Path(config.repo))
    if config.reference_repos:
        _clone_reference_repos(
            config.reference_repos, repo_index, github_token=config.github_token
        )

    if args.backend:
        hand: Hand
        try:
            hand = create_hand(
                args.backend,
                config,
                repo_index,
                max_iterations=args.max_iterations,
            )
            hand.auto_pr = not args.no_pr
        except ModuleNotFoundError as exc:
            extra = "langchain" if args.backend == BACKEND_BASIC_LANGGRAPH else "atomic"
            if args.backend in {
                BACKEND_BASIC_ATOMIC,
                BACKEND_BASIC_AGENT,
            } and sys.version_info < (
                3,
                12,
            ):
                _error_exit(
                    f"--backend {args.backend} requires Python >= 3.12. "
                    "Current Python is "
                    f"{sys.version_info.major}.{sys.version_info.minor}. "
                    "Re-run with Python 3.12+, e.g. "
                    "'uv sync --python 3.12 --dev --extra atomic' and "
                    "'uv run --python 3.12 helping-hands ...'"
                )
            _error_exit(
                f"missing dependency for --backend {args.backend}: {exc}. "
                f"{install_hint(extra)}"
            )
        try:
            asyncio.run(_stream_hand(hand, args.prompt))
        except KeyboardInterrupt:
            hand.interrupt()
            print("\nInterrupted by user.")
        except Exception as exc:
            msg = str(exc)
            if any(marker in msg for marker in _MODEL_NOT_FOUND_MARKERS):
                _error_exit(_MODEL_NOT_AVAILABLE_MSG.format(model=config.model))
            if args.backend in _CLI_ERROR_EXIT_BACKENDS:
                _error_exit(msg)
            raise
        return

    n = len(repo_index.files)
    s = "s" if n != 1 else ""
    print(f"Ready. Indexed {n} file{s} in {repo_index.root}.")


async def _stream_hand(hand: Hand, prompt: str) -> None:
    """Stream hand output to stdout, printing each chunk as it arrives.

    Args:
        hand: The hand instance to stream from.
        prompt: The task prompt to pass to the hand.
    """
    stream = cast(AsyncIterator[str], hand.stream(prompt))
    async for chunk in stream:
        print(chunk, end="", flush=True)
    print()


def _github_clone_url(repo: str, token: str | None = None) -> str:
    """Build the HTTPS clone URL for a GitHub repository.

    Delegates to :func:`helping_hands.lib.github_url.build_clone_url`.

    Args:
        repo: GitHub repository in ``owner/repo`` format.
        token: Optional explicit GitHub token (overrides env vars).

    Returns:
        The HTTPS clone URL string.

    Raises:
        ValueError: If *repo* is not in valid ``owner/repo`` format.
    """
    return _build_clone_url(repo, token=token)


def _resolve_repo_path(repo: str) -> tuple[Path, str | None]:
    """Resolve a repo argument to a local directory path.

    If *repo* is an existing local directory, returns it directly.
    If *repo* matches ``owner/repo`` format, clones it to a temporary
    directory (registered for cleanup via ``atexit``).

    Args:
        repo: Local directory path or GitHub ``owner/repo`` reference.

    Returns:
        A tuple of ``(resolved_path, cloned_from)`` where *cloned_from*
        is the original ``owner/repo`` string if a clone was performed,
        or ``None`` for local directories.

    Raises:
        ValueError: If *repo* is not a directory and not a valid
            ``owner/repo`` reference, or if cloning fails.
    """
    path = Path(repo).expanduser().resolve()
    if path.is_dir():
        return path, None

    if re.fullmatch(_REPO_SPEC_PATTERN, repo):
        dest = _make_temp_clone_dir(_TEMP_CLONE_PREFIX)
        url = _github_clone_url(repo)
        try:
            _run_git_clone(url, dest, label=repo)
        except ValueError:
            shutil.rmtree(dest.parent, ignore_errors=True)
            raise
        return dest.resolve(), repo

    raise ValueError(_invalid_repo_msg(repo))


def _clone_reference_repos(
    repos: tuple[str, ...],
    repo_index: RepoIndex,
    *,
    github_token: str = "",
) -> None:
    """Clone reference repos as shallow read-only clones and attach to *repo_index*."""
    for spec in repos:
        try:
            _validate_repo_spec(spec)
        except ValueError as exc:
            print(f"Warning: skipping invalid reference repo {spec!r}: {exc}")
            continue
        safe_name = spec.replace("/", "_")
        dest = _make_temp_clone_dir(f"helping_hands_ref_{safe_name}_")
        url = _github_clone_url(spec, token=github_token)
        try:
            _run_git_clone(url, dest, label=spec)
        except ValueError as exc:
            print(f"Warning: {exc}")
            continue
        resolved = dest.resolve()
        repo_index.reference_repos.append((spec, resolved))
        print(f"Cloned reference repo {spec} to {resolved}")


if __name__ == "__main__":
    main()
