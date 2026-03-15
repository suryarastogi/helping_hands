"""v180 — Docstring presence tests for celery_app.py progress-tracking helpers.

Validates that _trim_updates, _append_update, _update_progress,
_setup_periodic_tasks, and _UpdateCollector methods have Google-style
docstrings with appropriate sections.
"""

from __future__ import annotations

import inspect

import pytest

celery_app = pytest.importorskip(
    "helping_hands.server.celery_app",
    reason="celery extras not installed",
)

# ---------------------------------------------------------------------------
# Standalone function docstrings
# ---------------------------------------------------------------------------

_STANDALONE_FUNCTIONS = [
    "_trim_updates",
    "_append_update",
    "_update_progress",
    "_setup_periodic_tasks",
]


class TestCeleryProgressFunctionDocstrings:
    """Verify standalone progress functions have Google-style docstrings."""

    @pytest.mark.parametrize("func_name", _STANDALONE_FUNCTIONS)
    def test_function_has_docstring(self, func_name: str) -> None:
        func = getattr(celery_app, func_name)
        doc = inspect.getdoc(func)
        assert doc and len(doc.strip()) >= 10, f"{func_name} is missing a docstring"

    def test_trim_updates_has_args(self) -> None:
        doc = inspect.getdoc(celery_app._trim_updates)
        assert "Args:" in doc

    def test_append_update_has_args(self) -> None:
        doc = inspect.getdoc(celery_app._append_update)
        assert "Args:" in doc

    def test_update_progress_has_args(self) -> None:
        doc = inspect.getdoc(celery_app._update_progress)
        assert "Args:" in doc

    def test_update_progress_documents_task_arg(self) -> None:
        doc = inspect.getdoc(celery_app._update_progress)
        assert "task:" in doc

    def test_update_progress_documents_stage_arg(self) -> None:
        doc = inspect.getdoc(celery_app._update_progress)
        assert "stage:" in doc

    def test_setup_periodic_tasks_has_args(self) -> None:
        doc = inspect.getdoc(celery_app._setup_periodic_tasks)
        assert "Args:" in doc


# ---------------------------------------------------------------------------
# _UpdateCollector method docstrings
# ---------------------------------------------------------------------------

_UPDATE_COLLECTOR_METHODS = [
    "__init__",
    "feed",
    "flush",
]


class TestUpdateCollectorDocstrings:
    """Verify _UpdateCollector methods have Google-style docstrings."""

    @pytest.mark.parametrize("method_name", _UPDATE_COLLECTOR_METHODS)
    def test_method_has_docstring(self, method_name: str) -> None:
        method = getattr(celery_app._UpdateCollector, method_name)
        doc = inspect.getdoc(method)
        assert doc and len(doc.strip()) >= 10, (
            f"_UpdateCollector.{method_name} is missing a docstring"
        )

    def test_init_has_args(self) -> None:
        doc = inspect.getdoc(celery_app._UpdateCollector.__init__)
        assert "Args:" in doc

    def test_feed_has_args(self) -> None:
        doc = inspect.getdoc(celery_app._UpdateCollector.feed)
        assert "Args:" in doc

    def test_feed_documents_chunk_arg(self) -> None:
        doc = inspect.getdoc(celery_app._UpdateCollector.feed)
        assert "chunk:" in doc

    def test_flush_mentions_buffer(self) -> None:
        doc = inspect.getdoc(celery_app._UpdateCollector.flush)
        assert "buffer" in doc.lower()
