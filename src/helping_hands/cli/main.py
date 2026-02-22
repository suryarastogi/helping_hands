"""CLI entry point: parse args, load config, run the agent loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand import E2EHand
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
        default="E2E smoke test: minimal edit and PR",
        help="Prompt to pass to the hand (used by --e2e mode).",
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
        "--model",
        default=None,
        help="AI model to use (overrides env/config).",
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
            overrides={"repo": args.repo, "model": args.model, "verbose": args.verbose}
        )
        repo_index = RepoIndex(root=Path(config.repo or "."), files=[])
        response = E2EHand(config, repo_index).run(
            args.prompt,
            pr_number=args.pr_number,
        )
        print(response.message)
        print(f"hand_uuid={response.metadata.get('hand_uuid')}")
        print(f"workspace={response.metadata.get('workspace')}")
        print(f"pr_url={response.metadata.get('pr_url')}")
        return

    repo_path = Path(args.repo).resolve()
    if not repo_path.is_dir():
        print(f"Error: {args.repo} is not a directory.", file=sys.stderr)
        sys.exit(1)

    config = Config.from_env(
        overrides={"repo": str(repo_path), "model": args.model, "verbose": args.verbose}
    )
    repo_index = RepoIndex.from_path(Path(config.repo))
    n = len(repo_index.files)
    s = "s" if n != 1 else ""
    print(f"Ready. Indexed {n} file{s} in {repo_index.root}.")


if __name__ == "__main__":
    main()
