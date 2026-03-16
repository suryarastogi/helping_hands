"""Tests for v246: Simplify getattr(self.config, ...) to direct attribute access.

Covers:
- AST source consistency: no getattr(self.config, ...) in hand files
- Config dataclass guarantees: all fields have defaults and are accessible
- Behavioral: hands read config attributes correctly with direct access
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from helping_hands.lib.config import Config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HAND_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "helping_hands"
    / "lib"
    / "hands"
    / "v1"
    / "hand"
)

_HAND_FILES = [
    _HAND_DIR / "base.py",
    _HAND_DIR / "iterative.py",
    _HAND_DIR / "e2e.py",
    _HAND_DIR / "cli" / "base.py",
]

_CONFIG_BOOL_FIELDS = ("enable_execution", "enable_web", "use_native_cli_auth")
_CONFIG_STR_FIELDS = ("github_token",)
_CONFIG_TUPLE_FIELDS = ("enabled_tools", "enabled_skills")


# ===========================================================================
# AST: No getattr(self.config, ...) in hand source files
# ===========================================================================


class _GetattrConfigVisitor(ast.NodeVisitor):
    """Find getattr(self.config, ...) calls in an AST."""

    def __init__(self) -> None:
        self.hits: list[int] = []

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
            and isinstance(node.args[0], ast.Attribute)
            and isinstance(node.args[0].value, ast.Name)
            and node.args[0].value.id == "self"
            and node.args[0].attr == "config"
        ):
            self.hits.append(node.lineno)
        self.generic_visit(node)


class TestNoGetattrConfigInSource:
    """No hand file should use getattr(self.config, ...) anymore."""

    @pytest.mark.parametrize("hand_file", _HAND_FILES, ids=lambda p: p.name)
    def test_no_getattr_self_config(self, hand_file: Path) -> None:
        source = hand_file.read_text()
        tree = ast.parse(source, filename=str(hand_file))
        visitor = _GetattrConfigVisitor()
        visitor.visit(tree)
        assert visitor.hits == [], (
            f"{hand_file.name} still has getattr(self.config, ...) "
            f"at line(s): {visitor.hits}"
        )


# ===========================================================================
# Config dataclass field guarantees
# ===========================================================================


class TestConfigFieldDefaults:
    """All Config fields referenced by hands have defaults."""

    def test_all_bool_fields_exist_with_defaults(self) -> None:
        cfg = Config()
        for name in _CONFIG_BOOL_FIELDS:
            val = getattr(cfg, name)
            assert isinstance(val, bool), f"Config.{name} should be bool"
            assert val is False, f"Config.{name} default should be False"

    def test_all_str_fields_exist_with_defaults(self) -> None:
        cfg = Config()
        for name in _CONFIG_STR_FIELDS:
            val = getattr(cfg, name)
            assert isinstance(val, str), f"Config.{name} should be str"
            assert val == "", f"Config.{name} default should be empty string"

    def test_all_tuple_fields_exist_with_defaults(self) -> None:
        cfg = Config()
        for name in _CONFIG_TUPLE_FIELDS:
            val = getattr(cfg, name)
            assert isinstance(val, tuple), f"Config.{name} should be tuple"
            assert val == (), f"Config.{name} default should be empty tuple"

    def test_config_is_frozen_dataclass(self) -> None:
        cfg = Config()
        with pytest.raises(AttributeError):
            cfg.repo = "changed"  # type: ignore[misc]

    def test_field_names_cover_all_hand_usages(self) -> None:
        """Every field name used by hands exists in Config's declared fields."""
        all_names = _CONFIG_BOOL_FIELDS + _CONFIG_STR_FIELDS + _CONFIG_TUPLE_FIELDS
        declared = {f.name for f in fields(Config)}
        for name in all_names:
            assert name in declared, f"{name} not in Config fields"


# ===========================================================================
# Behavioral: Hands read config attributes via direct access
# ===========================================================================


def _make_concrete(base_cls: type) -> type:
    """Create a concrete subclass that stubs abstract methods."""
    from collections.abc import AsyncIterator

    stubs: dict[str, object] = {}
    for name in getattr(base_cls, "__abstractmethods__", frozenset()):
        if "stream" in name:

            async def _stream_stub(self: object, prompt: str) -> AsyncIterator[str]:
                yield ""  # pragma: no cover

            stubs[name] = _stream_stub
        else:

            async def _run_stub(self: object, prompt: str) -> str:
                return ""  # pragma: no cover

            stubs[name] = _run_stub
    return type(f"_Concrete{base_cls.__name__}", (base_cls,), stubs)


def _make_hand_stub(hand_cls: type) -> object:
    """Create a hand instance bypassing __init__ via concrete subclass."""
    concrete = _make_concrete(hand_cls)
    inst = concrete.__new__(concrete)
    return inst


class TestHandConfigDirectAccess:
    """Hands correctly read Config attributes without getattr."""

    def test_base_hand_reads_enable_execution(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        hand = _make_hand_stub(Hand)
        hand.config = Config(enable_execution=True)  # type: ignore[attr-defined]
        assert hand._should_run_precommit_before_pr() is True  # type: ignore[attr-defined]

    def test_base_hand_reads_enable_execution_false(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        hand = _make_hand_stub(Hand)
        hand.config = Config(enable_execution=False)  # type: ignore[attr-defined]
        assert hand._should_run_precommit_before_pr() is False  # type: ignore[attr-defined]

    def test_base_hand_reads_use_native_cli_auth(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        hand = _make_hand_stub(Hand)
        hand.config = Config(use_native_cli_auth=True)  # type: ignore[attr-defined]
        assert hand._use_native_git_auth_for_push(github_token="") is True  # type: ignore[attr-defined]

    def test_base_hand_reads_use_native_cli_auth_token_overrides(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        hand = _make_hand_stub(Hand)
        hand.config = Config(use_native_cli_auth=True)  # type: ignore[attr-defined]
        # Token takes precedence: if token present, native auth is not used
        assert hand._use_native_git_auth_for_push(github_token="ghp_abc") is False  # type: ignore[attr-defined]

    def test_iterative_hand_reads_execution_enabled(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        hand = _make_hand_stub(_BasicIterativeHand)
        hand.config = Config(enable_execution=True)  # type: ignore[attr-defined]
        assert hand._execution_tools_enabled() is True  # type: ignore[attr-defined]

    def test_iterative_hand_reads_execution_disabled(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        hand = _make_hand_stub(_BasicIterativeHand)
        hand.config = Config(enable_execution=False)  # type: ignore[attr-defined]
        assert hand._execution_tools_enabled() is False  # type: ignore[attr-defined]

    def test_iterative_hand_reads_web_enabled(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        hand = _make_hand_stub(_BasicIterativeHand)
        hand.config = Config(enable_web=True)  # type: ignore[attr-defined]
        assert hand._web_tools_enabled() is True  # type: ignore[attr-defined]

    def test_iterative_hand_reads_web_disabled(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        hand = _make_hand_stub(_BasicIterativeHand)
        hand.config = Config(enable_web=False)  # type: ignore[attr-defined]
        assert hand._web_tools_enabled() is False  # type: ignore[attr-defined]

    def test_cli_base_reads_use_native_cli_auth(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        hand = _make_hand_stub(_TwoPhaseCLIHand)
        hand.config = Config(use_native_cli_auth=True)  # type: ignore[attr-defined]
        assert hand._use_native_cli_auth() is True  # type: ignore[attr-defined]

    def test_cli_base_reads_use_native_cli_auth_false(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        hand = _make_hand_stub(_TwoPhaseCLIHand)
        hand.config = Config(use_native_cli_auth=False)  # type: ignore[attr-defined]
        assert hand._use_native_cli_auth() is False  # type: ignore[attr-defined]

    def test_config_github_token_direct(self) -> None:
        """Config.github_token is directly accessible without getattr."""
        cfg = Config(github_token="ghp_test123")
        assert cfg.github_token == "ghp_test123"

    def test_config_github_token_default(self) -> None:
        cfg = Config()
        assert cfg.github_token == ""
