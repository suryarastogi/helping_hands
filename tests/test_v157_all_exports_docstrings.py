"""Tests for v157: __all__ declarations on core library modules.

Without __all__, star-imports and documentation generators expose private helpers
as part of the public API.  These tests pin the exact set of publicly exported
names for types.py, github.py, filesystem.py, and command.py so that a refactor
that accidentally removes a key export (e.g. PRResult) is caught immediately rather
than discovered when downstream code breaks at runtime.

The "no private names" assertion prevents internal helpers from leaking into the
public surface; the "all importable" assertion catches __all__ entries that were
renamed without updating the declaration.
"""

from __future__ import annotations

import helping_hands.lib.ai_providers.types as types_module
import helping_hands.lib.github as github_module
import helping_hands.lib.meta.tools.command as command_module
import helping_hands.lib.meta.tools.filesystem as filesystem_module
from helping_hands.lib.ai_providers.types import normalize_messages

# ---------------------------------------------------------------------------
# types.py __all__
# ---------------------------------------------------------------------------


class TestTypesModuleAll:
    def test_all_contains_prompt_input(self) -> None:
        assert "PromptInput" in types_module.__all__

    def test_all_contains_normalize_messages(self) -> None:
        assert "normalize_messages" in types_module.__all__

    def test_all_contains_ai_provider(self) -> None:
        assert "AIProvider" in types_module.__all__

    def test_all_does_not_contain_private_names(self) -> None:
        for name in types_module.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in types_module.__all__:
            assert hasattr(types_module, name), f"{name!r} not found in module"


# ---------------------------------------------------------------------------
# github.py __all__
# ---------------------------------------------------------------------------


class TestGitHubModuleAll:
    def test_all_contains_pr_result(self) -> None:
        assert "PRResult" in github_module.__all__

    def test_all_contains_github_client(self) -> None:
        assert "GitHubClient" in github_module.__all__

    def test_all_does_not_contain_private_names(self) -> None:
        for name in github_module.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in github_module.__all__:
            assert hasattr(github_module, name), f"{name!r} not found in module"


# ---------------------------------------------------------------------------
# filesystem.py __all__
# ---------------------------------------------------------------------------


class TestFilesystemModuleAll:
    def test_all_contains_normalize_relative_path(self) -> None:
        assert "normalize_relative_path" in filesystem_module.__all__

    def test_all_contains_resolve_repo_target(self) -> None:
        assert "resolve_repo_target" in filesystem_module.__all__

    def test_all_contains_read_text_file(self) -> None:
        assert "read_text_file" in filesystem_module.__all__

    def test_all_contains_write_text_file(self) -> None:
        assert "write_text_file" in filesystem_module.__all__

    def test_all_contains_mkdir_path(self) -> None:
        assert "mkdir_path" in filesystem_module.__all__

    def test_all_contains_path_exists(self) -> None:
        assert "path_exists" in filesystem_module.__all__

    def test_all_does_not_contain_private_names(self) -> None:
        for name in filesystem_module.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in filesystem_module.__all__:
            assert hasattr(filesystem_module, name), f"{name!r} not found in module"


# ---------------------------------------------------------------------------
# command.py __all__
# ---------------------------------------------------------------------------


class TestCommandModuleAll:
    def test_all_contains_command_result(self) -> None:
        assert "CommandResult" in command_module.__all__

    def test_all_contains_run_python_code(self) -> None:
        assert "run_python_code" in command_module.__all__

    def test_all_contains_run_python_script(self) -> None:
        assert "run_python_script" in command_module.__all__

    def test_all_contains_run_bash_script(self) -> None:
        assert "run_bash_script" in command_module.__all__

    def test_all_does_not_contain_private_names(self) -> None:
        for name in command_module.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in command_module.__all__:
            assert hasattr(command_module, name), f"{name!r} not found in module"


# ---------------------------------------------------------------------------
# normalize_messages docstring
# ---------------------------------------------------------------------------


class TestNormalizeMessagesDocstring:
    def test_has_docstring(self) -> None:
        assert normalize_messages.__doc__ is not None

    def test_docstring_has_args_section(self) -> None:
        assert "Args:" in normalize_messages.__doc__

    def test_docstring_has_returns_section(self) -> None:
        assert "Returns:" in normalize_messages.__doc__

    def test_docstring_has_raises_section(self) -> None:
        assert "Raises:" in normalize_messages.__doc__
