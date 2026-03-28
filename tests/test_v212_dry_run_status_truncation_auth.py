"""Guard run-status string constants and auth-presence labels in iterative.py.

The three run-status constants (interrupted, satisfied, max_iterations) end up in
the hand result dict returned to the caller and to Celery task state. If their
values change or diverge between the constant definition and the actual assignment
in run()/stream(), the server and frontend receive unexpected status strings,
breaking the status-display logic. _TRUNCATION_MARKER is inserted when large repo
context is truncated before being sent to the AI — if the marker changes, any
downstream code that splits on it would break silently. The source-level tests
verify that the actual run() implementations reference the constants rather than
inline literal strings, catching regressions that value-only tests would miss.
"""

from __future__ import annotations

import inspect

from helping_hands.lib.hands.v1.hand import iterative as iterative_module

# ---------------------------------------------------------------------------
# _RUN_STATUS_* constants
# ---------------------------------------------------------------------------


class TestRunStatusConstants:
    """Tests for the extracted run-status string constants."""

    def test_interrupted_exists(self) -> None:
        assert hasattr(iterative_module, "_RUN_STATUS_INTERRUPTED")

    def test_satisfied_exists(self) -> None:
        assert hasattr(iterative_module, "_RUN_STATUS_SATISFIED")

    def test_max_iterations_exists(self) -> None:
        assert hasattr(iterative_module, "_RUN_STATUS_MAX_ITERATIONS")

    def test_interrupted_value(self) -> None:
        assert iterative_module._RUN_STATUS_INTERRUPTED == "interrupted"

    def test_satisfied_value(self) -> None:
        assert iterative_module._RUN_STATUS_SATISFIED == "satisfied"

    def test_max_iterations_value(self) -> None:
        assert iterative_module._RUN_STATUS_MAX_ITERATIONS == "max_iterations"

    def test_all_are_strings(self) -> None:
        for const in (
            iterative_module._RUN_STATUS_INTERRUPTED,
            iterative_module._RUN_STATUS_SATISFIED,
            iterative_module._RUN_STATUS_MAX_ITERATIONS,
        ):
            assert isinstance(const, str)

    def test_all_are_non_empty(self) -> None:
        for const in (
            iterative_module._RUN_STATUS_INTERRUPTED,
            iterative_module._RUN_STATUS_SATISFIED,
            iterative_module._RUN_STATUS_MAX_ITERATIONS,
        ):
            assert len(const) > 0

    def test_all_are_distinct(self) -> None:
        values = {
            iterative_module._RUN_STATUS_INTERRUPTED,
            iterative_module._RUN_STATUS_SATISFIED,
            iterative_module._RUN_STATUS_MAX_ITERATIONS,
        }
        assert len(values) == 3

    def test_all_are_lowercase(self) -> None:
        for const in (
            iterative_module._RUN_STATUS_INTERRUPTED,
            iterative_module._RUN_STATUS_SATISFIED,
            iterative_module._RUN_STATUS_MAX_ITERATIONS,
        ):
            assert const == const.lower()

    def test_source_uses_constant_not_inline(self) -> None:
        """Both run() methods must reference the constant, not inline strings."""
        source = inspect.getsource(iterative_module)
        assert "_RUN_STATUS_INTERRUPTED" in source
        assert "_RUN_STATUS_SATISFIED" in source
        assert "_RUN_STATUS_MAX_ITERATIONS" in source
        # Verify the inline strings are NOT used in status assignment
        # (they still appear in the constant definition and docstrings)
        lines = source.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("status = "):
                assert '"interrupted"' not in stripped
                assert '"satisfied"' not in stripped
                assert '"max_iterations"' not in stripped


# ---------------------------------------------------------------------------
# _TRUNCATION_MARKER constant
# ---------------------------------------------------------------------------


class TestTruncationMarker:
    """Tests for the extracted _TRUNCATION_MARKER constant."""

    def test_exists(self) -> None:
        assert hasattr(iterative_module, "_TRUNCATION_MARKER")

    def test_is_string(self) -> None:
        assert isinstance(iterative_module._TRUNCATION_MARKER, str)

    def test_value(self) -> None:
        assert iterative_module._TRUNCATION_MARKER == "\n[truncated]"

    def test_starts_with_newline(self) -> None:
        """Marker begins with newline for clean append to output."""
        assert iterative_module._TRUNCATION_MARKER.startswith("\n")

    def test_contains_truncated(self) -> None:
        assert "truncated" in iterative_module._TRUNCATION_MARKER

    def test_source_uses_constant_not_inline(self) -> None:
        """Format methods must reference the constant, not inline strings."""
        source = inspect.getsource(iterative_module)
        assert "_TRUNCATION_MARKER" in source
        lines = source.splitlines()
        for line in lines:
            stripped = line.strip()
            # Lines assigning truncation notes should use the constant
            has_note_var = (
                "truncated_note" in stripped
                or "stdout_note" in stripped
                or "stderr_note" in stripped
            )
            if has_note_var and "if" in stripped:
                assert "_TRUNCATION_MARKER" in stripped or '= ""' in stripped


# ---------------------------------------------------------------------------
# _AUTH_PRESENT_LABEL / _AUTH_ABSENT_LABEL constants
# ---------------------------------------------------------------------------


class TestAuthPresenceLabels:
    """Tests for the extracted auth-presence label constants."""

    def test_present_exists(self) -> None:
        assert hasattr(iterative_module, "_AUTH_PRESENT_LABEL")

    def test_absent_exists(self) -> None:
        assert hasattr(iterative_module, "_AUTH_ABSENT_LABEL")

    def test_present_value(self) -> None:
        assert iterative_module._AUTH_PRESENT_LABEL == "set"

    def test_absent_value(self) -> None:
        assert iterative_module._AUTH_ABSENT_LABEL == "not set"

    def test_both_are_strings(self) -> None:
        assert isinstance(iterative_module._AUTH_PRESENT_LABEL, str)
        assert isinstance(iterative_module._AUTH_ABSENT_LABEL, str)

    def test_both_are_non_empty(self) -> None:
        assert len(iterative_module._AUTH_PRESENT_LABEL) > 0
        assert len(iterative_module._AUTH_ABSENT_LABEL) > 0

    def test_are_distinct(self) -> None:
        assert (
            iterative_module._AUTH_PRESENT_LABEL != iterative_module._AUTH_ABSENT_LABEL
        )

    def test_source_uses_constants_not_inline(self) -> None:
        """Stream methods must reference the constants, not inline strings."""
        source = inspect.getsource(iterative_module)
        assert "_AUTH_PRESENT_LABEL" in source
        assert "_AUTH_ABSENT_LABEL" in source
