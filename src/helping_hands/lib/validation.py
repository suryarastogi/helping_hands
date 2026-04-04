"""Shared validation helpers used across the codebase.

Centralises the two most common guard patterns — non-empty string checks and
positive integer checks — so that call-sites can replace 2-3 lines of
boilerplate with a single function call.
"""

from __future__ import annotations

import math

__all__ = [
    "format_type_error",
    "has_cli_flag",
    "install_hint",
    "parse_comma_list",
    "require_non_empty_string",
    "require_positive_float",
    "require_positive_int",
    "validate_repo_value",
]


def has_cli_flag(tokens: list[str], flag: str) -> bool:
    """Check whether *tokens* contain a CLI long-option *flag*.

    Matches both the bare ``--flag`` form and the ``--flag=value`` prefix form,
    which is the standard pattern for GNU-style CLI options.

    Args:
        tokens: Tokenized CLI command list.
        flag: The flag name **without** the leading ``--``
              (e.g. ``"model"``, not ``"--model"``).

    Returns:
        ``True`` if any token equals ``--flag`` or starts with ``--flag=``.
    """
    long = f"--{flag}"
    prefix = f"--{flag}="
    return any(t == long or t.startswith(prefix) for t in tokens)


def install_hint(extra: str) -> str:
    """Return a human-readable install instruction for a uv extra.

    Args:
        extra: The uv extra name (e.g. ``"server"``, ``"langchain"``).

    Returns:
        A string like ``"Install with: uv sync --extra server"``.
    """
    return f"Install with: uv sync --extra {extra}"


def parse_comma_list(value: str) -> tuple[str, ...]:
    """Split a comma-separated string into a tuple of stripped, non-empty items.

    Args:
        value: Comma-separated string (e.g. ``"a, b, c"``).

    Returns:
        Tuple of stripped non-empty items.  Returns an empty tuple for
        blank or whitespace-only input.
    """
    return tuple(item.strip() for item in value.split(",") if item.strip())


def format_type_error(name: str, expected: str, value: object) -> str:
    """Format a human-readable ``TypeError`` message.

    Args:
        name: Human-readable parameter name.
        expected: Expected type description (e.g. ``"a string"``).
        value: The actual value received.

    Returns:
        A formatted error string like ``"foo must be a string, got int"``.
    """
    return f"{name} must be {expected}, got {type(value).__name__}"


def require_non_empty_string(value: str, name: str) -> str:
    """Validate that *value* is a non-empty, non-whitespace-only string.

    Args:
        value: The string to validate.
        name: Human-readable parameter name for error messages.

    Returns:
        The stripped value.

    Raises:
        TypeError: If *value* is not a string.
        ValueError: If *value* is empty or whitespace-only.
    """
    if not isinstance(value, str):
        raise TypeError(format_type_error(name, "a string", value))
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{name} must not be empty")
    return stripped


def require_positive_float(value: float | int, name: str) -> float:
    """Validate that *value* is a positive finite number (> 0).

    Accepts both ``float`` and ``int`` (but not ``bool``).  The return
    value is always a ``float``.

    Args:
        value: The number to validate.
        name: Human-readable parameter name for error messages.

    Returns:
        The value as a ``float``.

    Raises:
        TypeError: If *value* is not a number or is a ``bool``.
        ValueError: If *value* is <= 0, ``NaN``, or infinite.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(format_type_error(name, "a number", value))
    fval = float(value)
    if not math.isfinite(fval):
        raise ValueError(f"{name} must be finite, got {value}")
    if fval <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return fval


def validate_repo_value(value: str) -> str:
    """Validate that *value* is a plausible repo target.

    Accepts two forms:
    - A local filesystem path (absolute or relative, must not be empty/whitespace).
    - An ``owner/repo`` GitHub slug.

    Rejects:
    - Empty or whitespace-only strings.
    - Strings containing ``..`` path traversal segments.
    - Strings with embedded newlines or null bytes.

    Args:
        value: The raw repo string from CLI flags or environment variables.

    Returns:
        The stripped value.

    Raises:
        ValueError: If the value fails validation.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("repo must not be empty")
    if "\x00" in stripped:
        raise ValueError("repo must not contain null bytes")
    if "\n" in stripped or "\r" in stripped:
        raise ValueError("repo must not contain newlines")
    # Reject path traversal attempts.
    for segment in stripped.replace("\\", "/").split("/"):
        if segment == "..":
            raise ValueError(
                f"repo must not contain path traversal segments: {stripped!r}"
            )
    return stripped


def require_positive_int(value: int, name: str) -> int:
    """Validate that *value* is a positive integer (> 0).

    Args:
        value: The integer to validate.
        name: Human-readable parameter name for error messages.

    Returns:
        The value unchanged.

    Raises:
        TypeError: If *value* is not an ``int`` or is a ``bool``.
        ValueError: If *value* is <= 0.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(format_type_error(name, "an int", value))
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value
