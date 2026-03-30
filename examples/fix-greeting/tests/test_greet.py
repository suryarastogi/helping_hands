"""Tests for the greeting module."""

from src.greet import greet


def test_greet_includes_name() -> None:
    """The greeting should include the person's name."""
    assert greet("Alice") == "Hello, Alice!"


def test_greet_another_name() -> None:
    """Verify with a different name."""
    assert greet("Bob") == "Hello, Bob!"
