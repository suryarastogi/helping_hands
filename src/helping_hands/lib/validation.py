"""Shared payload validation helpers used by iterative hands and skills.

These functions extract and validate typed values from ``dict`` payloads
(typically deserialized JSON tool arguments) with clear error messages on
type or range violations.
"""

from __future__ import annotations

from typing import Any

__all__ = ["parse_optional_str", "parse_positive_int", "parse_str_list"]


def parse_str_list(payload: dict[str, Any], *, key: str) -> list[str]:
    """Extract and validate a list of strings from *payload* at *key*.

    Args:
        payload: Source dictionary (usually a deserialized JSON object).
        key: Dictionary key to read.

    Returns:
        List of string values, or an empty list if the key is missing or
        ``None``.

    Raises:
        ValueError: If the value is not a list or contains non-string items.
    """
    raw = payload.get(key, [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{key} must be a list of strings")
    values: list[str] = []
    for value in raw:
        if not isinstance(value, str):
            raise ValueError(f"{key} must contain only strings")
        values.append(value)
    return values


def parse_positive_int(
    payload: dict[str, Any],
    *,
    key: str,
    default: int,
) -> int:
    """Extract a positive integer from *payload* at *key*, or use *default*.

    Args:
        payload: Source dictionary.
        key: Dictionary key to read.
        default: Value returned when *key* is absent from *payload*.

    Returns:
        The validated positive integer.

    Raises:
        ValueError: If the value is not an integer, is a bool, or is <= 0.
    """
    raw = payload.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{key} must be an integer")
    if raw <= 0:
        raise ValueError(f"{key} must be > 0")
    return raw


def parse_optional_str(payload: dict[str, Any], *, key: str) -> str | None:
    """Extract an optional trimmed string from *payload*, returning ``None`` if blank.

    Args:
        payload: Source dictionary.
        key: Dictionary key to read.

    Returns:
        The trimmed string value, or ``None`` if the key is missing, the value
        is ``None``, or the trimmed result is empty.

    Raises:
        ValueError: If the value is present but not a string.
    """
    raw = payload.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be a string")
    value = raw.strip()
    return value or None
