"""Tests for v214: type hint refinement, task result logging.

Verifies:
- Hand subclass constructors accept Config and RepoIndex (not Any)
- _input_schema starts as None (no type: ignore needed)
- normalize_task_result logs debug message for non-dict/non-exception types
- normalize_task_result docstring has Args/Returns sections
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, get_type_hints

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.repo import RepoIndex
from helping_hands.server.task_result import normalize_task_result

# ---------------------------------------------------------------------------
# 1. Hand subclass constructor type hints
# ---------------------------------------------------------------------------


class TestHandConstructorTypeHints:
    """Verify Hand subclass constructors use Config/RepoIndex, not Any."""

    @staticmethod
    def _get_init_annotations(cls: type) -> dict[str, Any]:
        """Get __init__ annotations for a class."""
        return get_type_hints(cls.__init__)

    def test_e2e_hand_config_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        hints = self._get_init_annotations(E2EHand)
        assert hints["config"] is Config

    def test_e2e_hand_repo_index_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        hints = self._get_init_annotations(E2EHand)
        assert hints["repo_index"] is RepoIndex

    def test_langgraph_hand_config_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.langgraph import LangGraphHand

        hints = self._get_init_annotations(LangGraphHand)
        assert hints["config"] is Config

    def test_langgraph_hand_repo_index_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.langgraph import LangGraphHand

        hints = self._get_init_annotations(LangGraphHand)
        assert hints["repo_index"] is RepoIndex

    def test_atomic_hand_config_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.atomic import AtomicHand

        hints = self._get_init_annotations(AtomicHand)
        assert hints["config"] is Config

    def test_atomic_hand_repo_index_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.atomic import AtomicHand

        hints = self._get_init_annotations(AtomicHand)
        assert hints["repo_index"] is RepoIndex

    def test_iterative_hand_config_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _BasicIterativeHand,
        )

        hints = self._get_init_annotations(_BasicIterativeHand)
        assert hints["config"] is Config

    def test_iterative_hand_repo_index_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _BasicIterativeHand,
        )

        hints = self._get_init_annotations(_BasicIterativeHand)
        assert hints["repo_index"] is RepoIndex

    def test_basic_langgraph_hand_config_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            BasicLangGraphHand,
        )

        hints = self._get_init_annotations(BasicLangGraphHand)
        assert hints["config"] is Config

    def test_basic_atomic_hand_config_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        hints = self._get_init_annotations(BasicAtomicHand)
        assert hints["config"] is Config


# ---------------------------------------------------------------------------
# 2. _input_schema type annotation (no type: ignore)
# ---------------------------------------------------------------------------


class TestInputSchemaAnnotation:
    """Verify _input_schema allows None without type: ignore."""

    def test_atomic_hand_no_type_ignore(self) -> None:
        """atomic.py should not contain 'type: ignore' for _input_schema."""
        import helping_hands.lib.hands.v1.hand.atomic as mod

        source = inspect.getsource(mod)
        # Find the _input_schema line and verify no type: ignore
        for line in source.splitlines():
            if "_input_schema" in line and "=" in line and "None" in line:
                assert "type: ignore" not in line, (
                    f"_input_schema still has type: ignore: {line.strip()}"
                )

    def test_iterative_hand_no_type_ignore(self) -> None:
        """iterative.py should not contain 'type: ignore' for _input_schema."""
        import helping_hands.lib.hands.v1.hand.iterative as mod

        source = inspect.getsource(mod)
        for line in source.splitlines():
            if "_input_schema" in line and "=" in line and "None" in line:
                assert "type: ignore" not in line, (
                    f"_input_schema still has type: ignore: {line.strip()}"
                )

    def test_atomic_input_schema_annotation_allows_none(self) -> None:
        """The _input_schema annotation should be type[Any] | None."""
        from helping_hands.lib.hands.v1.hand.atomic import AtomicHand

        source = inspect.getsource(AtomicHand.__init__)
        assert "type[Any] | None" in source


# ---------------------------------------------------------------------------
# 3. normalize_task_result logging and docstring
# ---------------------------------------------------------------------------


class TestNormalizeTaskResultLogging:
    """Verify normalize_task_result logs for non-standard types."""

    def test_none_returns_none(self) -> None:
        assert normalize_task_result("SUCCESS", None) is None

    def test_dict_passthrough(self) -> None:
        d = {"key": "value"}
        assert normalize_task_result("SUCCESS", d) is d

    def test_exception_returns_error_dict(self) -> None:
        exc = ValueError("boom")
        result = normalize_task_result("FAILURE", exc)
        assert result == {
            "error": "boom",
            "error_type": "ValueError",
            "status": "FAILURE",
        }

    def test_string_coercion_logs_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="helping_hands.server.task_result"):
            result = normalize_task_result("SUCCESS", 42)
        assert result == {
            "value": "42",
            "value_type": "int",
            "status": "SUCCESS",
        }
        assert "coercing int to str" in caplog.text

    def test_list_coercion_logs_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="helping_hands.server.task_result"):
            result = normalize_task_result("SUCCESS", [1, 2, 3])
        assert result["value_type"] == "list"
        assert "coercing list to str" in caplog.text

    def test_custom_object_coercion_logs_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        class Foo:
            def __str__(self) -> str:
                return "foo-result"

        with caplog.at_level(logging.DEBUG, logger="helping_hands.server.task_result"):
            result = normalize_task_result("PENDING", Foo())
        assert result == {
            "value": "foo-result",
            "value_type": "Foo",
            "status": "PENDING",
        }
        assert "coercing Foo to str" in caplog.text

    def test_no_log_for_dict(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="helping_hands.server.task_result"):
            normalize_task_result("SUCCESS", {"k": "v"})
        assert "coercing" not in caplog.text

    def test_no_log_for_exception(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="helping_hands.server.task_result"):
            normalize_task_result("FAILURE", RuntimeError("err"))
        assert "coercing" not in caplog.text

    def test_docstring_has_args_section(self) -> None:
        assert "Args:" in (normalize_task_result.__doc__ or "")

    def test_docstring_has_returns_section(self) -> None:
        assert "Returns:" in (normalize_task_result.__doc__ or "")
