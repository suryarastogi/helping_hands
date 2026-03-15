"""Tests for v211 — DRY truncation suffix, code fences, and _bool_lower helper.

Covers:
- Module-level constants: _TRUNCATION_SUFFIX, _FENCE_TEXT, _FENCE_JSON, _FENCE_CLOSE
- _BasicIterativeHand._truncation_note() classmethod
- _BasicIterativeHand._bool_lower() staticmethod
- Formatting methods use the new constants (no inline duplicates)
"""

from __future__ import annotations

import inspect

from helping_hands.lib.hands.v1.hand import iterative as iterative_module

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestTruncationSuffix:
    """Tests for the _TRUNCATION_SUFFIX constant."""

    def test_constant_exists(self) -> None:
        assert hasattr(iterative_module, "_TRUNCATION_SUFFIX")

    def test_is_string(self) -> None:
        assert isinstance(iterative_module._TRUNCATION_SUFFIX, str)

    def test_value(self) -> None:
        assert iterative_module._TRUNCATION_SUFFIX == "\n[truncated]"

    def test_starts_with_newline(self) -> None:
        assert iterative_module._TRUNCATION_SUFFIX.startswith("\n")


class TestFenceConstants:
    """Tests for the code-fence marker constants."""

    def test_fence_text_exists(self) -> None:
        assert hasattr(iterative_module, "_FENCE_TEXT")

    def test_fence_json_exists(self) -> None:
        assert hasattr(iterative_module, "_FENCE_JSON")

    def test_fence_close_exists(self) -> None:
        assert hasattr(iterative_module, "_FENCE_CLOSE")

    def test_fence_text_value(self) -> None:
        assert iterative_module._FENCE_TEXT == "```text"

    def test_fence_json_value(self) -> None:
        assert iterative_module._FENCE_JSON == "```json"

    def test_fence_close_value(self) -> None:
        assert iterative_module._FENCE_CLOSE == "```"

    def test_all_are_strings(self) -> None:
        for name in ("_FENCE_TEXT", "_FENCE_JSON", "_FENCE_CLOSE"):
            val = getattr(iterative_module, name)
            assert isinstance(val, str), f"{name} is not a string"

    def test_fence_text_starts_with_backticks(self) -> None:
        assert iterative_module._FENCE_TEXT.startswith("```")

    def test_fence_json_starts_with_backticks(self) -> None:
        assert iterative_module._FENCE_JSON.startswith("```")


# ---------------------------------------------------------------------------
# _truncation_note helper
# ---------------------------------------------------------------------------


class TestTruncationNote:
    """Tests for _BasicIterativeHand._truncation_note()."""

    def test_returns_suffix_when_truncated(self) -> None:
        hand_cls = iterative_module._BasicIterativeHand
        result = hand_cls._truncation_note(True)
        assert result == iterative_module._TRUNCATION_SUFFIX

    def test_returns_empty_when_not_truncated(self) -> None:
        hand_cls = iterative_module._BasicIterativeHand
        result = hand_cls._truncation_note(False)
        assert result == ""

    def test_is_static_or_classmethod(self) -> None:
        """The method should be callable without an instance."""
        hand_cls = iterative_module._BasicIterativeHand
        assert callable(hand_cls._truncation_note)


# ---------------------------------------------------------------------------
# _bool_lower helper
# ---------------------------------------------------------------------------


class TestBoolLower:
    """Tests for _BasicIterativeHand._bool_lower()."""

    def test_true_returns_lowercase(self) -> None:
        hand_cls = iterative_module._BasicIterativeHand
        assert hand_cls._bool_lower(True) == "true"

    def test_false_returns_lowercase(self) -> None:
        hand_cls = iterative_module._BasicIterativeHand
        assert hand_cls._bool_lower(False) == "false"

    def test_return_type_is_string(self) -> None:
        hand_cls = iterative_module._BasicIterativeHand
        assert isinstance(hand_cls._bool_lower(True), str)
        assert isinstance(hand_cls._bool_lower(False), str)

    def test_is_static_method(self) -> None:
        """_bool_lower should be a staticmethod on the class."""
        raw = inspect.getattr_static(
            iterative_module._BasicIterativeHand, "_bool_lower"
        )
        assert isinstance(raw, staticmethod)


# ---------------------------------------------------------------------------
# No inline duplicates in formatting methods
# ---------------------------------------------------------------------------


class TestNoInlineDuplicates:
    """Verify formatting methods reference constants, not inline literals."""

    def _source(self, method_name: str) -> str:
        hand_cls = iterative_module._BasicIterativeHand
        return inspect.getsource(getattr(hand_cls, method_name))

    def test_format_command_result_uses_truncation_note(self) -> None:
        src = self._source("_format_command_result")
        assert '"\n[truncated]"' not in src
        assert "_truncation_note" in src

    def test_format_command_result_uses_bool_lower(self) -> None:
        src = self._source("_format_command_result")
        assert "str(result.timed_out).lower()" not in src
        assert "_bool_lower" in src

    def test_format_command_result_uses_fence_text(self) -> None:
        src = self._source("_format_command_result")
        assert "_FENCE_TEXT" in src

    def test_format_web_search_result_uses_truncation_note(self) -> None:
        src = self._source("_format_web_search_result")
        assert '"\n[truncated]"' not in src
        assert "_truncation_note" in src

    def test_format_web_search_result_uses_fence_json(self) -> None:
        src = self._source("_format_web_search_result")
        assert "_FENCE_JSON" in src

    def test_format_web_browse_result_uses_truncation_note(self) -> None:
        src = self._source("_format_web_browse_result")
        assert '"\n[truncated]"' not in src
        assert "_truncation_note" in src

    def test_format_web_browse_result_uses_bool_lower(self) -> None:
        src = self._source("_format_web_browse_result")
        assert "str(result.truncated).lower()" not in src
        assert "_bool_lower" in src

    def test_format_web_browse_result_uses_fence_text(self) -> None:
        src = self._source("_format_web_browse_result")
        assert "_FENCE_TEXT" in src

    def test_execute_read_requests_uses_fence_text(self) -> None:
        src = self._source("_execute_read_requests")
        assert "_FENCE_TEXT" in src

    def test_read_bootstrap_doc_uses_fence_text(self) -> None:
        src = self._source("_read_bootstrap_doc")
        assert "_FENCE_TEXT" in src

    def test_read_bootstrap_doc_uses_truncation_note(self) -> None:
        src = self._source("_read_bootstrap_doc")
        assert '"\n[truncated]"' not in src
        assert "_truncation_note" in src
