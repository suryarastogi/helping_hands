"""CLI entry point: parse args, load config, run the agent loop."""

from __future__ import annotations

import argparse
import asyncio
import atexit
import os
import re
import shutil
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from subprocess import TimeoutExpired
from tempfile import mkdtemp
from typing import cast

from helping_hands.lib.config import Config
from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.lib.github_url import (
    DEFAULT_GIT_CLONE_ERROR_MSG as _DEFAULT_GIT_CLONE_ERROR_MSG,
)
from helping_hands.lib.github_url import (
    GIT_CLONE_TIMEOUT_S as _GIT_CLONE_TIMEOUT_S,
)
from helping_hands.lib.github_url import (
    build_clone_url as _build_clone_url,
)
from helping_hands.lib.github_url import (
    noninteractive_env as _git_noninteractive_env,
)
from helping_hands.lib.github_url import (
    redact_credentials as _redact_sensitive,
)
from helping_hands.lib.github_url import (
    validate_repo_spec as _validate_repo_spec,
)
from helping_hands.lib.hands.v1.hand import (
    BasicAtomicHand,
    BasicLangGraphHand,
    ClaudeCodeHand,
    CodexCLIHand,
    DockerSandboxClaudeCodeHand,
    E2EHand,
    GeminiCLIHand,
    GooseCLIHand,
    Hand,
    OpenCodeCLIHand,
)
from helping_hands.lib.meta import skills as meta_skills
from helping_hands.lib.meta.tools import registry as meta_tools
from helping_hands.lib.repo import RepoIndex

__all__ = ["build_parser", "main"]

# --- Module-level constants ---------------------------------------------------

_DEFAULT_CLONE_DEPTH = 1
"""Shallow clone depth used when cloning ``owner/repo`` inputs."""

_TEMP_CLONE_PREFIX = "helping_hands_repo_"
"""Prefix for temporary directories created for cloned repositories."""


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
        choices=(
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
            "opencodecli",
        ),
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
    try:
        selected_tools = meta_tools.normalize_tool_selection(args.tools)
        meta_tools.validate_tool_category_names(selected_tools)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        selected_skills = meta_skills.normalize_skill_selection(args.skills)
        meta_skills.validate_skill_names(selected_skills)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.pr_number is not None and args.pr_number <= 0:
        print(
            f"Error: --pr-number must be a positive integer (got {args.pr_number})",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.max_iterations is not None and args.max_iterations <= 0:
        print(
            f"Error: --max-iterations must be a positive integer"
            f" (got {args.max_iterations})",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.e2e:
        config = Config.from_env(
            overrides={
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
            }
        )
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
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    if cloned_from:
        print(f"Cloned {cloned_from} to {repo_path}")

    config = Config.from_env(
        overrides={
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
        }
    )
    repo_index = RepoIndex.from_path(Path(config.repo))
    if config.reference_repos:
        _clone_reference_repos(
            config.reference_repos, repo_index, github_token=config.github_token
        )

    if args.backend:
        hand: Hand
        try:
            if args.backend == "basic-langgraph":
                hand = BasicLangGraphHand(
                    config,
                    repo_index,
                    max_iterations=args.max_iterations,
                )
            elif args.backend == "codexcli":
                hand = CodexCLIHand(config, repo_index)
            elif args.backend == "claudecodecli":
                hand = ClaudeCodeHand(config, repo_index)
            elif args.backend == "docker-sandbox-claude":
                hand = DockerSandboxClaudeCodeHand(config, repo_index)
            elif args.backend == "goose":
                hand = GooseCLIHand(config, repo_index)
            elif args.backend == "geminicli":
                hand = GeminiCLIHand(config, repo_index)
            elif args.backend == "opencodecli":
                hand = OpenCodeCLIHand(config, repo_index)
            else:
                hand = BasicAtomicHand(
                    config,
                    repo_index,
                    max_iterations=args.max_iterations,
                )
            hand.auto_pr = not args.no_pr
        except ModuleNotFoundError as exc:
            extra = "langchain" if args.backend == "basic-langgraph" else "atomic"
            if args.backend in {"basic-atomic", "basic-agent"} and sys.version_info < (
                3,
                12,
            ):
                print(
                    (
                        f"Error: --backend {args.backend} requires Python >= 3.12. "
                        "Current Python is "
                        f"{sys.version_info.major}.{sys.version_info.minor}. "
                        "Re-run with Python 3.12+, e.g. "
                        "'uv sync --python 3.12 --dev --extra atomic' and "
                        "'uv run --python 3.12 helping-hands ...'"
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)
            print(
                (
                    f"Error: missing dependency for --backend {args.backend}: {exc}. "
                    f"Install with: uv sync --extra {extra}"
                ),
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            asyncio.run(_stream_hand(hand, args.prompt))
        except KeyboardInterrupt:
            hand.interrupt()
            print("\nInterrupted by user.")
        except Exception as exc:
            msg = str(exc)
            if "model_not_found" in msg or "does not exist" in msg:
                print(
                    (
                        f"Error: model {config.model!r} is not available. "
                        "Pass a valid model via --model (or HELPING_HANDS_MODEL), "
                        "for example: --model gpt-5.2"
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)
            if args.backend in {
                "codexcli",
                "claudecodecli",
                "docker-sandbox-claude",
                "goose",
                "geminicli",
            }:
                print(f"Error: {msg}", file=sys.stderr)
                sys.exit(1)
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


def _repo_tmp_dir() -> Path | None:
    """Return the directory to use for temporary repo clones.

    Reads HELPING_HANDS_REPO_TMP; falls back to the OS default temp dir.
    Setting this to a known path (e.g. /tmp/helping_hands or a project tmp/)
    keeps clones out of /var/folders and makes manual cleanup easy.
    """
    d = os.environ.get("HELPING_HANDS_REPO_TMP", "").strip()
    if d:
        p = Path(d).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return None


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

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        dest_root = Path(mkdtemp(prefix=_TEMP_CLONE_PREFIX, dir=_repo_tmp_dir()))
        atexit.register(shutil.rmtree, dest_root, True)
        dest = dest_root / "repo"
        url = _github_clone_url(repo)
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
            shutil.rmtree(dest_root, ignore_errors=True)
            raise ValueError(
                f"git clone timed out after {_GIT_CLONE_TIMEOUT_S}s for {repo}"
            ) from exc
        if result.returncode != 0:
            stderr = result.stderr.strip() or _DEFAULT_GIT_CLONE_ERROR_MSG
            stderr = _redact_sensitive(stderr)
            msg = f"failed to clone {repo}: {stderr}"
            raise ValueError(msg)
        return dest.resolve(), repo

    raise ValueError(f"{repo} is not a directory or owner/repo reference")


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
        dest_root = Path(
            mkdtemp(prefix=f"helping_hands_ref_{safe_name}_", dir=_repo_tmp_dir())
        )
        atexit.register(shutil.rmtree, dest_root, True)
        dest = dest_root / "repo"
        url = _github_clone_url(spec, token=github_token)
        try:
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    str(_DEFAULT_CLONE_DEPTH),
                    url,
                    str(dest),
                ],
                capture_output=True,
                text=True,
                check=False,
                env=_git_noninteractive_env(),
                timeout=_GIT_CLONE_TIMEOUT_S,
            )
        except TimeoutExpired:
            print(f"Warning: git clone timed out for reference repo {spec}")
            continue
        if result.returncode != 0:
            stderr = _redact_sensitive(result.stderr.strip() or "unknown error")
            print(f"Warning: failed to clone reference repo {spec}: {stderr}")
            continue
        resolved = dest.resolve()
        repo_index.reference_repos.append((spec, resolved))
        print(f"Cloned reference repo {spec} to {resolved}")


if __name__ == "__main__":
    main()
