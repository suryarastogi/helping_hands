"""Task result normalization helpers for server and MCP endpoints."""

from __future__ import annotations

from typing import Any

__all__ = ["normalize_task_result"]


def normalize_task_result(status: str, raw_result: Any) -> dict[str, Any] | None:
    """Normalize Celery task results into JSON-serializable dicts.

    Celery can return non-dict objects (including exception instances) for
    failed tasks. API surfaces should return structured JSON payloads instead
    of leaking non-serializable objects.
    """
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
    return {
        "value": str(raw_result),
        "value_type": type(raw_result).__name__,
        "status": status,
    }
