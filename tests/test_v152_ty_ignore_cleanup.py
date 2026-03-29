"""Tests for v152: codebase-wide guard against re-introduction of stale ty: ignore comments.

ty: ignore suppression comments were added during early development to silence
the type checker while fixes were deferred.  Once the underlying type issues were
resolved, these comments became dead weight that masks future real type errors.

These tests scan the entire src/ tree so that a developer adding a new ty: ignore
as a quick fix receives an immediate test failure instead of silently accumulating
technical debt.  The per-module tests (model_provider, celery_app, schedules) catch
specific known hot-spots before the codebase-wide scan even runs.
"""

from __future__ import annotations

import inspect
import textwrap

# ---------------------------------------------------------------------------
# model_provider.py — no ty: ignore[unknown-argument]
# ---------------------------------------------------------------------------


class TestModelProviderNoStaleIgnore:
    """Verify model_provider.py has no stale ty: ignore comments."""

    def test_source_has_no_ty_ignore_comments(self) -> None:
        from helping_hands.lib.hands.v1.hand import model_provider

        source = inspect.getsource(model_provider)
        assert "ty: ignore" not in source, (
            "model_provider.py still contains a 'ty: ignore' comment"
        )

    def test_build_langchain_chat_model_source_clean(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import (
            build_langchain_chat_model,
        )

        source = inspect.getsource(build_langchain_chat_model)
        assert "ty: ignore" not in source


# ---------------------------------------------------------------------------
# celery_app.py — no ty: ignore[unresolved-attribute]
# ---------------------------------------------------------------------------


class TestCeleryAppNoStaleIgnore:
    """Verify celery_app.py has no stale ty: ignore comments."""

    def test_source_has_no_ty_ignore_comments(self) -> None:
        pytest = __import__("pytest")
        celery_app = pytest.importorskip(
            "helping_hands.server.celery_app",
            reason="celery extras not installed",
        )
        source = inspect.getsource(celery_app)
        assert "ty: ignore" not in source, (
            "celery_app.py still contains a 'ty: ignore' comment"
        )


# ---------------------------------------------------------------------------
# schedules.py — no ty: ignore[invalid-assignment]
# ---------------------------------------------------------------------------


class TestSchedulesNoStaleIgnore:
    """Verify schedules.py has no stale ty: ignore comments."""

    def test_source_has_no_ty_ignore_comments(self) -> None:
        pytest = __import__("pytest")
        schedules = pytest.importorskip(
            "helping_hands.server.schedules",
            reason="celery extras not installed",
        )
        source = inspect.getsource(schedules)
        assert "ty: ignore" not in source, (
            "schedules.py still contains a 'ty: ignore' comment"
        )


# ---------------------------------------------------------------------------
# Codebase-wide guard — no ty: ignore in any source file
# ---------------------------------------------------------------------------


class TestNoTyIgnoreInSource:
    """Ensure no ty: ignore comments exist anywhere in src/."""

    def test_no_ty_ignore_in_source_tree(self) -> None:
        from pathlib import Path

        src_root = Path(__file__).resolve().parent.parent / "src"
        violations: list[str] = []
        for py_file in src_root.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(content.splitlines(), 1):
                if "ty: ignore" in line:
                    rel = py_file.relative_to(src_root)
                    violations.append(f"{rel}:{i}: {line.strip()}")
        assert not violations, "Found stale 'ty: ignore' comments:\n" + textwrap.indent(
            "\n".join(violations), "  "
        )
