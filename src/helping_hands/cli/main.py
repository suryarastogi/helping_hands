"""CLI entry point: parse args, load config, run the agent loop."""

from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from tempfile import mkdtemp
from typing import cast

from helping_hands.lib.config import Config
from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.lib.hands.v1.hand import (
    BasicAtomicHand,
    BasicLangGraphHand,
    ClaudeCodeHand,
    CodexCLIHand,
    E2EHand,
    GeminiCLIHand,
    GooseCLIHand,
    Hand,
)
from helping_hands.lib.repo import RepoIndex


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
            "goose",
            "geminicli",
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

    if args.e2e:
        config = Config.from_env(
            overrides={
                "repo": args.repo,
                "model": args.model,
                "verbose": args.verbose,
                "enable_execution": args.enable_execution,
                "enable_web": args.enable_web,
                "use_native_cli_auth": args.use_native_cli_auth,
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
        }
    )
    repo_index = RepoIndex.from_path(Path(config.repo))

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
            elif args.backend == "goose":
                hand = GooseCLIHand(config, repo_index)
            elif args.backend == "geminicli":
                hand = GeminiCLIHand(config, repo_index)
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
            if args.backend in {"codexcli", "claudecodecli", "goose", "geminicli"}:
                print(f"Error: {msg}", file=sys.stderr)
                sys.exit(1)
            raise
        return

    n = len(repo_index.files)
    s = "s" if n != 1 else ""
    print(f"Ready. Indexed {n} file{s} in {repo_index.root}.")


async def _stream_hand(hand: Hand, prompt: str) -> None:
    stream = cast(AsyncIterator[str], hand.stream(prompt))
    async for chunk in stream:
        print(chunk, end="", flush=True)
    print()


def _resolve_repo_path(repo: str) -> tuple[Path, str | None]:
    path = Path(repo).expanduser().resolve()
    if path.is_dir():
        return path, None

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        dest_root = Path(mkdtemp(prefix="helping_hands_repo_"))
        dest = dest_root / "repo"
        url = f"https://github.com/{repo}.git"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown git clone error"
            msg = f"failed to clone {repo}: {stderr}"
            raise ValueError(msg)
        return dest.resolve(), repo

    raise ValueError(f"{repo} is not a directory or owner/repo reference")


if __name__ == "__main__":
    main()
