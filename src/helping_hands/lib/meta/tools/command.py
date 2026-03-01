"""Command execution tools for repo-aware runtime actions.

These helpers provide a shared, path-confined execution surface for:
- ``python.run_code`` (defaulting to Python 3.13 via ``uv run``)
- ``python.run_script``
- ``bash.run_script``
"""

from __future__ import annotations

__all__ = [
    "CommandResult",
    "run_bash_script",
    "run_python_code",
    "run_python_script",
]

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from helping_hands.lib.meta.tools.filesystem import resolve_repo_target


@dataclass(frozen=True)
class CommandResult:
    """Captured result of a command execution."""

    command: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Return whether the command completed successfully."""
        return self.exit_code == 0 and not self.timed_out


def _normalize_args(args: list[str] | tuple[str, ...] | None) -> list[str]:
    """Coerce *args* to a validated ``list[str]``, rejecting non-string items."""
    if not args:
        return []
    normalized: list[str] = []
    for value in args:
        if not isinstance(value, str):
            msg = "args must contain only strings"
            raise TypeError(msg)
        normalized.append(value)
    return normalized


def _resolve_cwd(repo_root: Path, cwd: str | None) -> Path:
    """Resolve *cwd* to a path-safe directory under *repo_root*."""
    root = repo_root.resolve()
    if cwd is None or not cwd.strip():
        return root
    target = resolve_repo_target(root, cwd)
    if not target.is_dir():
        msg = f"cwd is not a directory: {cwd}"
        raise NotADirectoryError(msg)
    return target


def _resolve_python_command(python_version: str) -> list[str]:
    """Build the Python invocation command for the requested version.

    Prefers ``uv run --python <version> python``; falls back to a
    direct ``python<version>`` executable on ``PATH``.
    """
    version = python_version.strip()
    if not version:
        raise ValueError("python_version is required")

    if shutil.which("uv") is not None:
        return ["uv", "run", "--python", version, "python"]

    direct = f"python{version}"
    if shutil.which(direct) is not None:
        return [direct]

    msg = (
        "Python runner unavailable for requested version. "
        f"Install uv or ensure {direct!r} is on PATH."
    )
    raise RuntimeError(msg)


def _run_command(command: list[str], *, cwd: Path, timeout_s: int) -> CommandResult:
    """Execute *command* as a subprocess, capturing output and handling timeouts."""
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timeout_note = f"command timed out after {timeout_s}s"
        stderr = f"{stderr}\n{timeout_note}".strip()
        return CommandResult(
            command=command,
            cwd=str(cwd),
            exit_code=124,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )

    return CommandResult(
        command=command,
        cwd=str(cwd),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=False,
    )


def run_python_code(
    repo_root: Path,
    *,
    code: str,
    python_version: str = "3.13",
    args: list[str] | tuple[str, ...] | None = None,
    timeout_s: int = 60,
    cwd: str | None = None,
) -> CommandResult:
    """Execute inline Python code with a version-constrained runner."""
    if not code.strip():
        raise ValueError("code must be non-empty")

    working_dir = _resolve_cwd(repo_root, cwd)
    command = [
        *_resolve_python_command(python_version),
        "-c",
        code,
        *_normalize_args(args),
    ]
    return _run_command(command, cwd=working_dir, timeout_s=timeout_s)


def run_python_script(
    repo_root: Path,
    *,
    script_path: str,
    python_version: str = "3.13",
    args: list[str] | tuple[str, ...] | None = None,
    timeout_s: int = 60,
    cwd: str | None = None,
) -> CommandResult:
    """Execute a repo-relative Python script with a version-constrained runner."""
    root = repo_root.resolve()
    script = resolve_repo_target(root, script_path)
    if not script.exists():
        msg = f"script not found: {script_path}"
        raise FileNotFoundError(msg)
    if script.is_dir():
        msg = f"script path is a directory: {script_path}"
        raise IsADirectoryError(msg)

    working_dir = _resolve_cwd(root, cwd)
    command = [
        *_resolve_python_command(python_version),
        str(script),
        *_normalize_args(args),
    ]
    return _run_command(command, cwd=working_dir, timeout_s=timeout_s)


def run_bash_script(
    repo_root: Path,
    *,
    script_path: str | None = None,
    inline_script: str | None = None,
    args: list[str] | tuple[str, ...] | None = None,
    timeout_s: int = 60,
    cwd: str | None = None,
) -> CommandResult:
    """Execute bash from either a repo-relative script path or inline script."""
    has_script_path = script_path is not None and script_path.strip() != ""
    has_inline = inline_script is not None and inline_script.strip() != ""
    if has_script_path == has_inline:
        msg = "provide exactly one of script_path or inline_script"
        raise ValueError(msg)

    root = repo_root.resolve()
    working_dir = _resolve_cwd(root, cwd)
    normalized_args = _normalize_args(args)

    if has_script_path:
        assert script_path is not None
        script = resolve_repo_target(root, script_path)
        if not script.exists():
            msg = f"script not found: {script_path}"
            raise FileNotFoundError(msg)
        if script.is_dir():
            msg = f"script path is a directory: {script_path}"
            raise IsADirectoryError(msg)
        command = ["bash", str(script), *normalized_args]
        return _run_command(command, cwd=working_dir, timeout_s=timeout_s)

    assert inline_script is not None
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".sh",
            delete=False,
        ) as tmp:
            tmp.write(inline_script)
            tmp.flush()
            tmp_path = Path(tmp.name)
        os.chmod(tmp_path, 0o700)
        command = ["bash", str(tmp_path), *normalized_args]
        return _run_command(command, cwd=working_dir, timeout_s=timeout_s)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
