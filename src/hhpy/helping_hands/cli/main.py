"""CLI entry point: parse args, load config, run the agent loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hhpy.helping_hands.lib.agent import Agent
from hhpy.helping_hands.lib.config import Config
from hhpy.helping_hands.lib.repo import RepoIndex


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for CLI mode."""
    parser = argparse.ArgumentParser(
        prog="helping-hands",
        description="AI-powered repo builder.",
    )
    parser.add_argument("repo", help="Path or URL of the target repository.")
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

    repo_path = Path(args.repo).resolve()
    if not repo_path.is_dir():
        print(f"Error: {args.repo} is not a directory.", file=sys.stderr)
        sys.exit(1)

    config = Config.from_env(
        overrides={"repo": str(repo_path), "model": args.model, "verbose": args.verbose}
    )
    repo_index = RepoIndex.from_path(repo_path)
    agent = Agent(config=config, repo_index=repo_index)

    print(agent.greet())


if __name__ == "__main__":
    main()
