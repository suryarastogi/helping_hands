#!/usr/bin/env python3
"""Populate src/helping_hands/lib/meta/skills/ with skills from external repos.

Clones GitHub repositories and copies skill directories into the local skills
tree. Each skill lands as a subdirectory (e.g. skills/prd/SKILL.md).

Usage:
    python scripts/populate_skills.py          # fetch all configured sources
    python scripts/populate_skills.py --clean   # wipe fetched skills first
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / "src" / "helping_hands" / "lib" / "meta" / "skills"

# Files that belong to the package and should never be removed by --clean.
PROTECTED = {"__init__.py", "__pycache__"}


@dataclass
class SkillSource:
    """A GitHub repo containing one or more skills to fetch."""

    name: str
    repo: str  # HTTPS clone URL
    skills_path: str = "skills"  # path within the repo to the skills directory
    skills: list[str] = field(default_factory=list)  # empty = ALL skills in path


SOURCES: list[SkillSource] = [
    SkillSource(
        name="ralph",
        repo="https://github.com/snarktank/ralph.git",
        skills_path="skills",
        skills=[],  # ALL — fetches prd and ralph
    ),
    SkillSource(
        name="anthropic",
        repo="https://github.com/anthropics/skills.git",
        skills_path="skills",
        skills=["internal-comms"],
    ),
]


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)


def _clone_sparse(repo: str, skills_path: str, tmpdir: Path) -> Path:
    """Sparse-clone a repo, checking out only the skills subtree."""
    dest = tmpdir / repo.split("/")[-1].removesuffix(".git")
    _git("clone", "--depth=1", "--filter=blob:none", "--sparse", repo, str(dest))
    _git("sparse-checkout", "set", skills_path, cwd=dest)
    return dest


def _copy_skill(src: Path, dest: Path) -> None:
    """Copy a single skill directory, overwriting if it exists."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def clean(skills_dir: Path) -> None:
    """Remove all fetched skill subdirectories (preserves __init__.py etc.)."""
    for child in skills_dir.iterdir():
        if child.name in PROTECTED:
            continue
        if child.is_dir():
            shutil.rmtree(child)
            print(f"  removed {child.name}/")


def populate(sources: list[SkillSource], skills_dir: Path) -> None:
    """Fetch skills from each configured source into the local skills dir."""
    skills_dir.mkdir(parents=True, exist_ok=True)

    for source in sources:
        print(f"\n[{source.name}] cloning {source.repo} ...")
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                repo_dir = _clone_sparse(source.repo, source.skills_path, Path(tmpdir))
            except subprocess.CalledProcessError as exc:
                print(f"  ERROR cloning: {exc.stderr.strip()}", file=sys.stderr)
                continue

            remote_skills_dir = repo_dir / source.skills_path
            if not remote_skills_dir.is_dir():
                print(
                    f"  ERROR: {source.skills_path}/ not found in repo",
                    file=sys.stderr,
                )
                continue

            # Discover which skills to copy.
            if source.skills:
                skill_names = source.skills
            else:
                skill_names = sorted(
                    d.name
                    for d in remote_skills_dir.iterdir()
                    if d.is_dir() and not d.name.startswith(".")
                )

            for skill_name in skill_names:
                src_path = remote_skills_dir / skill_name
                if not src_path.is_dir():
                    print(
                        f"  WARN: skill '{skill_name}' not found, skipping",
                        file=sys.stderr,
                    )
                    continue
                dest_path = skills_dir / skill_name
                _copy_skill(src_path, dest_path)
                file_count = sum(1 for _ in dest_path.rglob("*") if _.is_file())
                print(f"  + {skill_name}/ ({file_count} file(s))")

    print("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previously fetched skill directories before populating.",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only clean, don't fetch.",
    )
    args = parser.parse_args()

    if args.clean or args.clean_only:
        print("Cleaning fetched skills ...")
        clean(SKILLS_DIR)
        if args.clean_only:
            return

    populate(SOURCES, SKILLS_DIR)


if __name__ == "__main__":
    main()
