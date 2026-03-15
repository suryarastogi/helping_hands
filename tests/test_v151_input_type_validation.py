"""Tests for v151: Input type validation for filesystem, tool/skill selection, truncation."""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.meta.tools.filesystem import normalize_relative_path

# ---------------------------------------------------------------------------
# 1. normalize_relative_path non-string rejection
# ---------------------------------------------------------------------------


class TestNormalizeRelativePathTypeValidation:
    """normalize_relative_path rejects non-string inputs with TypeError."""

    def test_rejects_none(self) -> None:
        with pytest.raises(TypeError, match="rel_path must be a string"):
            normalize_relative_path(None)  # type: ignore[arg-type]

    def test_rejects_int(self) -> None:
        with pytest.raises(TypeError, match="rel_path must be a string"):
            normalize_relative_path(42)  # type: ignore[arg-type]

    def test_rejects_list(self) -> None:
        with pytest.raises(TypeError, match="rel_path must be a string"):
            normalize_relative_path(["foo"])  # type: ignore[arg-type]

    def test_rejects_dict(self) -> None:
        with pytest.raises(TypeError, match="rel_path must be a string"):
            normalize_relative_path({"a": 1})  # type: ignore[arg-type]

    def test_accepts_valid_string(self) -> None:
        result = normalize_relative_path("src/foo.py")
        assert result == "src/foo.py"

    def test_guard_in_source(self) -> None:
        """Verify isinstance guard exists in source."""
        source = inspect.getsource(normalize_relative_path)
        assert "isinstance(rel_path, str)" in source


# ---------------------------------------------------------------------------
# 2. normalize_tool_selection input type validation
# ---------------------------------------------------------------------------


class TestNormalizeToolSelectionTypeValidation:
    """normalize_tool_selection rejects non-(str|list|tuple|None) inputs."""

    def test_rejects_dict(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        with pytest.raises(TypeError, match="tools must be a string, list, or tuple"):
            normalize_tool_selection({"execution": True})  # type: ignore[arg-type]

    def test_rejects_set(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        with pytest.raises(TypeError, match="tools must be a string, list, or tuple"):
            normalize_tool_selection({"execution", "web"})  # type: ignore[arg-type]

    def test_rejects_int(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        with pytest.raises(TypeError, match="tools must be a string, list, or tuple"):
            normalize_tool_selection(42)  # type: ignore[arg-type]

    def test_accepts_none(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        assert normalize_tool_selection(None) == ()

    def test_accepts_string(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        result = normalize_tool_selection("execution")
        assert "execution" in result

    def test_accepts_list(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        result = normalize_tool_selection(["execution"])
        assert "execution" in result

    def test_accepts_tuple(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        result = normalize_tool_selection(("execution",))
        assert "execution" in result

    def test_guard_in_source(self) -> None:
        from helping_hands.lib.meta.tools.registry import _normalize_and_deduplicate

        source = inspect.getsource(_normalize_and_deduplicate)
        assert "isinstance(values, (str, list, tuple))" in source


# ---------------------------------------------------------------------------
# 3. normalize_skill_selection input type validation
# ---------------------------------------------------------------------------


class TestNormalizeSkillSelectionTypeValidation:
    """normalize_skill_selection rejects non-(str|list|tuple|None) inputs."""

    def test_rejects_dict(self) -> None:
        from helping_hands.lib.meta.skills import normalize_skill_selection

        with pytest.raises(TypeError, match="skills must be a string, list, or tuple"):
            normalize_skill_selection({"prd": True})  # type: ignore[arg-type]

    def test_rejects_set(self) -> None:
        from helping_hands.lib.meta.skills import normalize_skill_selection

        with pytest.raises(TypeError, match="skills must be a string, list, or tuple"):
            normalize_skill_selection({"prd", "ralph"})  # type: ignore[arg-type]

    def test_rejects_int(self) -> None:
        from helping_hands.lib.meta.skills import normalize_skill_selection

        with pytest.raises(TypeError, match="skills must be a string, list, or tuple"):
            normalize_skill_selection(42)  # type: ignore[arg-type]

    def test_accepts_none(self) -> None:
        from helping_hands.lib.meta.skills import normalize_skill_selection

        assert normalize_skill_selection(None) == ()

    def test_accepts_string(self) -> None:
        from helping_hands.lib.meta.skills import normalize_skill_selection

        result = normalize_skill_selection("prd")
        assert "prd" in result

    def test_accepts_list(self) -> None:
        from helping_hands.lib.meta.skills import normalize_skill_selection

        result = normalize_skill_selection(["prd"])
        assert "prd" in result

    def test_accepts_tuple(self) -> None:
        from helping_hands.lib.meta.skills import normalize_skill_selection

        result = normalize_skill_selection(("prd",))
        assert "prd" in result

    def test_guard_in_source(self) -> None:
        from helping_hands.lib.meta.tools.registry import _normalize_and_deduplicate

        source = inspect.getsource(_normalize_and_deduplicate)
        assert "isinstance(values, (str, list, tuple))" in source


# ---------------------------------------------------------------------------
# 4. _truncate_summary positive limit validation
# ---------------------------------------------------------------------------


class TestTruncateSummaryLimitValidation:
    """_truncate_summary rejects non-positive limit values."""

    def test_rejects_zero(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            _TwoPhaseCLIHand._truncate_summary("hello", limit=0)

    def test_rejects_negative(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            _TwoPhaseCLIHand._truncate_summary("hello", limit=-1)

    def test_rejects_large_negative(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            _TwoPhaseCLIHand._truncate_summary("hello", limit=-100)

    def test_accepts_one(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        result = _TwoPhaseCLIHand._truncate_summary("hello", limit=1)
        assert result == "h\n...[truncated]"

    def test_accepts_exact_length(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        result = _TwoPhaseCLIHand._truncate_summary("hello", limit=5)
        assert result == "hello"

    def test_guard_in_source(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        source = inspect.getsource(_TwoPhaseCLIHand._truncate_summary)
        assert "limit < 1" in source
