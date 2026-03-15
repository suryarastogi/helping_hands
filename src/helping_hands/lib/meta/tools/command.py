"""Command execution tools for repo-aware runtime actions.

These helpers provide a shared, path-confined execution surface for:
- ``python.run_code`` (defaulting to ``_DEFAULT_PYTHON_VERSION`` via ``uv run``)
- ``python.run_script``
- ``bash.run_script``
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from helping_hands.lib.meta.tools.filesystem import resolve_repo_target

__all__ = [
    "CommandResult",
    "run_bash_script",
    "run_python_code",
    "run_python_script",
]

# --- Exit code constants (standard Unix conventions) --------------------------

_EXIT_CODE_TIMEOUT = 124
"""Exit code returned when a command is killed due to timeout (matches coreutils timeout)."""

_EXIT_CODE_CANNOT_EXECUTE = 126
"""Exit code returned when the command exists but cannot be executed (OSError)."""

_EXIT_CODE_NOT_FOUND = 127
"""Exit code returned when the command binary is not found (FileNotFoundError)."""

_DEFAULT_SCRIPT_TIMEOUT_S = 60
"""Default timeout in seconds for Python and bash script execution."""

_DEFAULT_PYTHON_VERSION = "3.13"
"""Default Python version used for code/script execution tools."""


@dataclass(frozen=True)
class CommandResult:
    """Captured result of a command execution.

    Attributes:
        command: Argv list that was executed.
        cwd: Working directory the command ran in.
        exit_code: Process exit code (0 = success).
        stdout: Captured standard output.
        stderr: Captured standard error.
        timed_out: Whether the command was killed due to timeout.
    """

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
    """Validate and normalise a command argument sequence.

    Args:
        args: Optional sequence of argument strings.  ``None`` or an empty
            sequence produces an empty list.

    Returns:
        A new list of validated string arguments.

    Raises:
        TypeError: If any element in *args* is not a string.
    """
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
    """Resolve the working directory for a command execution.

    If *cwd* is ``None`` or whitespace-only the resolved *repo_root* is
    returned.  Otherwise the path is resolved relative to *repo_root*
    using :func:`resolve_repo_target` and verified to be a directory.

    Args:
        repo_root: Absolute path to the repository root.
        cwd: Optional repo-relative working directory.

    Returns:
        The resolved working directory as an absolute :class:`~pathlib.Path`.

    Raises:
        NotADirectoryError: If *cwd* resolves to a non-directory path.
    """
    root = repo_root.resolve()
    if cwd is None or not cwd.strip():
        return root
    target = resolve_repo_target(root, cwd)
    if not target.is_dir():
        msg = f"cwd is not a directory: {cwd}"
        raise NotADirectoryError(msg)
    return target


def _resolve_python_command(python_version: str) -> list[str]:
    """Build the argv prefix for running Python at a specific version.

    Prefers ``uv run --python <version> python`` when *uv* is available,
    falling back to a bare ``python<version>`` binary on ``PATH``.

    Args:
        python_version: Desired Python version string (e.g. ``"3.13"``).

    Returns:
        Argv list suitable for prepending to a Python command.

    Raises:
        ValueError: If *python_version* is empty or whitespace-only.
        RuntimeError: If neither *uv* nor the versioned Python binary is
            found on ``PATH``.
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
    """Execute a subprocess and capture its result.

    Handles timeout (exit code 124), missing binary (exit code 127), and
    general OS errors (exit code 126) without raising — the caller
    inspects the returned :class:`CommandResult` instead.

    Args:
        command: Argv list to execute.
        cwd: Working directory for the subprocess.
        timeout_s: Maximum execution time in seconds.

    Returns:
        A :class:`CommandResult` with captured stdout/stderr and exit code.

    Raises:
        ValueError: If *timeout_s* is not positive.
    """
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
            exit_code=_EXIT_CODE_TIMEOUT,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )
    except FileNotFoundError:
        return CommandResult(
            command=command,
            cwd=str(cwd),
            exit_code=_EXIT_CODE_NOT_FOUND,
            stdout="",
            stderr=f"command not found: {command[0]}",
        )
    except OSError as exc:
        return CommandResult(
            command=command,
            cwd=str(cwd),
            exit_code=_EXIT_CODE_CANNOT_EXECUTE,
            stdout="",
            stderr=f"cannot execute command: {exc}",
        )

    return CommandResult(
        command=command,
        cwd=str(cwd),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=False,
    )


def _validate_script_path(root: Path, script_path: str) -> Path:
    """Resolve and validate a repo-relative script path.

    Args:
        root: Resolved repository root directory.
        script_path: Repo-relative path to the script file.

    Returns:
        The resolved absolute :class:`~pathlib.Path` to the script.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
        IsADirectoryError: If the resolved path is a directory.
    """
    script = resolve_repo_target(root, script_path)
    if not script.exists():
        msg = f"script not found: {script_path}"
        raise FileNotFoundError(msg)
    if script.is_dir():
        msg = f"script path is a directory: {script_path}"
        raise IsADirectoryError(msg)
    return script


def run_python_code(
    repo_root: Path,
    *,
    code: str,
    python_version: str = _DEFAULT_PYTHON_VERSION,
    args: list[str] | tuple[str, ...] | None = None,
    timeout_s: int = _DEFAULT_SCRIPT_TIMEOUT_S,
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
    python_version: str = _DEFAULT_PYTHON_VERSION,
    args: list[str] | tuple[str, ...] | None = None,
    timeout_s: int = _DEFAULT_SCRIPT_TIMEOUT_S,
    cwd: str | None = None,
) -> CommandResult:
    """Execute a repo-relative Python script with a version-constrained runner."""
    root = repo_root.resolve()
    script = _validate_script_path(root, script_path)

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
    timeout_s: int = _DEFAULT_SCRIPT_TIMEOUT_S,
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
        if script_path is None:  # pragma: no cover - guarded by has_script_path
            raise RuntimeError("script_path is unexpectedly None")
        script = _validate_script_path(root, script_path)
        command = ["bash", str(script), *normalized_args]
        return _run_command(command, cwd=working_dir, timeout_s=timeout_s)

    if inline_script is None:  # pragma: no cover - guarded by has_inline
        raise RuntimeError("inline_script is unexpectedly None")
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
