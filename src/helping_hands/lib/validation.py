"""Shared validation helpers used across the codebase.

Centralises the two most common guard patterns — non-empty string checks and
positive integer checks — so that call-sites can replace 2-3 lines of
boilerplate with a single function call.
"""

from __future__ import annotations

__all__ = [
    "require_non_empty_string",
    "require_positive_int",
]


def require_non_empty_string(value: str, name: str) -> str:
    """Validate that *value* is a non-empty, non-whitespace-only string.

    Args:
        value: The string to validate.
        name: Human-readable parameter name for error messages.

    Returns:
        The stripped value.

    Raises:
        ValueError: If *value* is empty or whitespace-only.
    """
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value.strip()


def require_positive_int(value: int, name: str) -> int:
    """Validate that *value* is a positive integer (> 0).

    Args:
        value: The integer to validate.
        name: Human-readable parameter name for error messages.

    Returns:
        The value unchanged.

    Raises:
        ValueError: If *value* is <= 0.
    """
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value
