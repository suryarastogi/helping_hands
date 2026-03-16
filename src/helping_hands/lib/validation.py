"""Shared validation helpers used across the codebase.

Centralises the two most common guard patterns — non-empty string checks and
positive integer checks — so that call-sites can replace 2-3 lines of
boilerplate with a single function call.
"""

from __future__ import annotations

import math

__all__ = [
    "require_non_empty_string",
    "require_positive_float",
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
        TypeError: If *value* is not a string.
        ValueError: If *value* is empty or whitespace-only.
    """
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string, got {type(value).__name__}")
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
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    fval = float(value)
    if not math.isfinite(fval):
        raise ValueError(f"{name} must be finite, got {value}")
    if fval <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return fval


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
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value
