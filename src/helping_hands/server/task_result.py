"""Task result normalization helpers for server and MCP endpoints."""

from __future__ import annotations

__all__ = ["normalize_task_result"]

import json
from typing import Any

from helping_hands.lib.validation import require_non_empty_string


def normalize_task_result(status: str, raw_result: Any) -> dict[str, Any] | None:
    """Normalize Celery task results into JSON-serializable dicts.

    Celery can return non-dict objects (including exception instances) for
    failed tasks. API surfaces should return structured JSON payloads instead
    of leaking non-serializable objects.
    """
    require_non_empty_string(status, "status")
    if raw_result is None:
        return None
    if isinstance(raw_result, dict):
        return raw_result
    if isinstance(raw_result, BaseException):
        return {
            "error": str(raw_result),
            "error_type": type(raw_result).__name__,
            "status": status,
        }
    # Try JSON serialization first to preserve structure for lists, ints, etc.
    try:
        json.dumps(raw_result)
        value = raw_result
    except (TypeError, ValueError, OverflowError):
        value = str(raw_result)
    return {
        "value": value,
        "value_type": type(raw_result).__name__,
        "status": status,
    }
