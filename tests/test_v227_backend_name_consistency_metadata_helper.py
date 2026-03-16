"""Tests for v227 — backend name consistency, langchain_user_message helper."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.langgraph import (
    LangGraphHand,
    langchain_user_message,
)

SRC = Path(__file__).resolve().parent.parent / "src"

# ---------------------------------------------------------------------------
# langchain_user_message helper
# ---------------------------------------------------------------------------


class TestLangchainUserMessage:
    """Verify the langchain_user_message helper builds correct dicts."""

    def test_basic_structure(self) -> None:
        result = langchain_user_message("hello")
        assert result == {"messages": [{"role": "user", "content": "hello"}]}

    def test_empty_prompt(self) -> None:
        result = langchain_user_message("")
        assert result == {"messages": [{"role": "user", "content": ""}]}

    def test_multiline_prompt(self) -> None:
        prompt = "line1\nline2\nline3"
        result = langchain_user_message(prompt)
        assert result["messages"][0]["content"] == prompt

    def test_returns_fresh_dict_each_call(self) -> None:
        a = langchain_user_message("x")
        b = langchain_user_message("x")
        assert a == b
        assert a is not b
        assert a["messages"] is not b["messages"]

    def test_exported_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand import langgraph as mod

        assert "langchain_user_message" in mod.__all__


# ---------------------------------------------------------------------------
# _BACKEND_NAME class constants
# ---------------------------------------------------------------------------


class TestBackendNameConstants:
    """Verify _BACKEND_NAME is defined as a class attribute (not hardcoded)."""

    def test_langgraph_hand_has_backend_name(self) -> None:
        assert hasattr(LangGraphHand, "_BACKEND_NAME")
        assert LangGraphHand._BACKEND_NAME == "langgraph"

    def test_atomic_hand_has_backend_name(self) -> None:
        from helping_hands.lib.hands.v1.hand.atomic import AtomicHand

        assert hasattr(AtomicHand, "_BACKEND_NAME")
        assert AtomicHand._BACKEND_NAME == "atomic"

    def test_iterative_langgraph_backend_name(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        assert BasicLangGraphHand._BACKEND_NAME == "basic-langgraph"

    def test_iterative_atomic_backend_name(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        assert BasicAtomicHand._BACKEND_NAME == "basic-atomic"

    def test_all_backend_names_unique(self) -> None:
        """All hand _BACKEND_NAME values must be distinct."""
        from helping_hands.lib.hands.v1.hand.atomic import AtomicHand
        from helping_hands.lib.hands.v1.hand.iterative import (
            BasicAtomicHand,
            BasicLangGraphHand,
        )

        names = [
            LangGraphHand._BACKEND_NAME,
            AtomicHand._BACKEND_NAME,
            BasicLangGraphHand._BACKEND_NAME,
            BasicAtomicHand._BACKEND_NAME,
        ]
        assert len(names) == len(set(names)), f"Duplicate backend names: {names}"


# ---------------------------------------------------------------------------
# Source-level: no hardcoded backend strings in langgraph.py / atomic.py
# ---------------------------------------------------------------------------


class TestNoHardcodedBackendStrings:
    """Verify that langgraph.py and atomic.py use _BACKEND_NAME, not literals."""

    def test_langgraph_run_uses_backend_name(self) -> None:
        source = inspect.getsource(LangGraphHand.run)
        assert "self._BACKEND_NAME" in source
        assert 'backend="langgraph"' not in source
        assert '"backend": "langgraph"' not in source

    def test_langgraph_stream_uses_backend_name(self) -> None:
        source = inspect.getsource(LangGraphHand.stream)
        assert "self._BACKEND_NAME" in source
        assert 'backend="langgraph"' not in source

    def test_atomic_run_uses_backend_name(self) -> None:
        from helping_hands.lib.hands.v1.hand.atomic import AtomicHand

        source = inspect.getsource(AtomicHand.run)
        assert "self._BACKEND_NAME" in source
        assert 'backend="atomic"' not in source
        assert '"backend": "atomic"' not in source

    def test_atomic_stream_uses_backend_name(self) -> None:
        from helping_hands.lib.hands.v1.hand.atomic import AtomicHand

        source = inspect.getsource(AtomicHand.stream)
        assert "self._BACKEND_NAME" in source
        assert 'backend="atomic"' not in source


# ---------------------------------------------------------------------------
# Source-level: langchain_user_message used in iterative.py
# ---------------------------------------------------------------------------


class TestLangchainUserMessageUsedInIterative:
    """Verify iterative.py delegates to langchain_user_message, not inline dicts."""

    def test_iterative_imports_helper(self) -> None:
        path = SRC / "helping_hands" / "lib" / "hands" / "v1" / "hand" / "iterative.py"
        source = path.read_text()
        assert "langchain_user_message" in source
        # Should NOT have inline message dict construction
        assert '{"messages": [{"role": "user"' not in source

    def test_langgraph_module_no_inline_message_dicts(self) -> None:
        # The helper function itself has the dict, but the class methods
        # should use langchain_user_message()
        run_source = inspect.getsource(LangGraphHand.run)
        assert "langchain_user_message(" in run_source
        assert '{"messages":' not in run_source

    def test_langgraph_stream_uses_helper(self) -> None:
        stream_source = inspect.getsource(LangGraphHand.stream)
        assert "langchain_user_message(" in stream_source
        assert '{"messages":' not in stream_source


# ---------------------------------------------------------------------------
# AST-level: verify _BACKEND_NAME is a class variable in standalone hands
# ---------------------------------------------------------------------------


class TestBackendNameAST:
    """AST-level checks that _BACKEND_NAME is a class-level assignment."""

    @pytest.mark.parametrize(
        "module_path,class_name,expected_value",
        [
            (
                "helping_hands/lib/hands/v1/hand/langgraph.py",
                "LangGraphHand",
                "langgraph",
            ),
            (
                "helping_hands/lib/hands/v1/hand/atomic.py",
                "AtomicHand",
                "atomic",
            ),
        ],
    )
    def test_backend_name_is_class_constant(
        self, module_path: str, class_name: str, expected_value: str
    ) -> None:
        path = SRC / module_path
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if (
                        isinstance(item, ast.Assign)
                        and any(
                            isinstance(t, ast.Name) and t.id == "_BACKEND_NAME"
                            for t in item.targets
                        )
                        and isinstance(item.value, ast.Constant)
                    ):
                        assert item.value.value == expected_value
                        return
                pytest.fail(
                    f"_BACKEND_NAME not found as class constant in {class_name}"
                )
        pytest.fail(f"Class {class_name} not found in {module_path}")
