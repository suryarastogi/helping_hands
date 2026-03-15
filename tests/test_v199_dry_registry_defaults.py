"""v199 — DRY registry.py default constants.

Tests verify that hardcoded defaults in registry.py runner wrappers now
reference named constants from command.py and web.py.
"""

from __future__ import annotations

import inspect

# ---------------------------------------------------------------------------
# 1. _DEFAULT_PYTHON_VERSION constant
# ---------------------------------------------------------------------------


class TestDefaultPythonVersion:
    """_DEFAULT_PYTHON_VERSION extracted in command.py."""

    def test_value(self) -> None:
        from helping_hands.lib.meta.tools.command import _DEFAULT_PYTHON_VERSION

        assert _DEFAULT_PYTHON_VERSION == "3.13"

    def test_type(self) -> None:
        from helping_hands.lib.meta.tools.command import _DEFAULT_PYTHON_VERSION

        assert isinstance(_DEFAULT_PYTHON_VERSION, str)

    def test_run_python_code_default_uses_constant(self) -> None:
        from helping_hands.lib.meta.tools.command import (
            _DEFAULT_PYTHON_VERSION,
            run_python_code,
        )

        sig = inspect.signature(run_python_code)
        assert sig.parameters["python_version"].default == _DEFAULT_PYTHON_VERSION

    def test_run_python_script_default_uses_constant(self) -> None:
        from helping_hands.lib.meta.tools.command import (
            _DEFAULT_PYTHON_VERSION,
            run_python_script,
        )

        sig = inspect.signature(run_python_script)
        assert sig.parameters["python_version"].default == _DEFAULT_PYTHON_VERSION


# ---------------------------------------------------------------------------
# 2. DEFAULT_SEARCH_MAX_RESULTS constant
# ---------------------------------------------------------------------------


class TestDefaultSearchMaxResults:
    """DEFAULT_SEARCH_MAX_RESULTS extracted in web.py."""

    def test_value(self) -> None:
        from helping_hands.lib.meta.tools.web import DEFAULT_SEARCH_MAX_RESULTS

        assert DEFAULT_SEARCH_MAX_RESULTS == 5

    def test_type(self) -> None:
        from helping_hands.lib.meta.tools.web import DEFAULT_SEARCH_MAX_RESULTS

        assert isinstance(DEFAULT_SEARCH_MAX_RESULTS, int)

    def test_positive(self) -> None:
        from helping_hands.lib.meta.tools.web import DEFAULT_SEARCH_MAX_RESULTS

        assert DEFAULT_SEARCH_MAX_RESULTS > 0

    def test_in_all(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert "DEFAULT_SEARCH_MAX_RESULTS" in __all__

    def test_search_web_default_uses_constant(self) -> None:
        from helping_hands.lib.meta.tools.web import (
            DEFAULT_SEARCH_MAX_RESULTS,
            search_web,
        )

        sig = inspect.signature(search_web)
        assert sig.parameters["max_results"].default == DEFAULT_SEARCH_MAX_RESULTS


# ---------------------------------------------------------------------------
# 4. Registry imports — constants are the same objects
# ---------------------------------------------------------------------------


class TestRegistryImportsCommandConstants:
    """registry.py imports _DEFAULT_SCRIPT_TIMEOUT_S and _DEFAULT_PYTHON_VERSION."""

    def test_script_timeout_imported(self) -> None:
        from helping_hands.lib.meta.tools import registry
        from helping_hands.lib.meta.tools.command import _DEFAULT_SCRIPT_TIMEOUT_S

        assert registry._DEFAULT_SCRIPT_TIMEOUT_S is _DEFAULT_SCRIPT_TIMEOUT_S

    def test_python_version_imported(self) -> None:
        from helping_hands.lib.meta.tools import registry
        from helping_hands.lib.meta.tools.command import _DEFAULT_PYTHON_VERSION

        assert registry._DEFAULT_PYTHON_VERSION is _DEFAULT_PYTHON_VERSION


class TestRegistryImportsWebConstants:
    """registry.py imports _DEFAULT_WEB_TIMEOUT_S and DEFAULT_SEARCH_MAX_RESULTS."""

    def test_web_timeout_imported(self) -> None:
        from helping_hands.lib.meta.tools import registry
        from helping_hands.lib.meta.tools.web import _DEFAULT_WEB_TIMEOUT_S

        assert registry._DEFAULT_WEB_TIMEOUT_S is _DEFAULT_WEB_TIMEOUT_S

    def test_search_max_results_imported(self) -> None:
        from helping_hands.lib.meta.tools import registry
        from helping_hands.lib.meta.tools.web import DEFAULT_SEARCH_MAX_RESULTS

        assert registry.DEFAULT_SEARCH_MAX_RESULTS is DEFAULT_SEARCH_MAX_RESULTS


# ---------------------------------------------------------------------------
# 5. No remaining hardcoded literals in registry runner wrappers
# ---------------------------------------------------------------------------


class TestRegistryNoHardcodedDefaults:
    """Verify registry source no longer contains hardcoded default literals."""

    def test_no_hardcoded_60_in_runners(self) -> None:
        """Runner wrappers should not contain 'default=60'."""
        from helping_hands.lib.meta.tools import registry

        source = inspect.getsource(registry._run_python_code)
        source += inspect.getsource(registry._run_python_script)
        source += inspect.getsource(registry._run_bash_script)
        assert "default=60" not in source

    def test_no_hardcoded_20_in_runners(self) -> None:
        """Runner wrappers should not contain 'default=20'."""
        from helping_hands.lib.meta.tools import registry

        source = inspect.getsource(registry._run_web_search)
        source += inspect.getsource(registry._run_web_browse)
        assert "default=20" not in source

    def test_no_hardcoded_5_in_search_runner(self) -> None:
        """Web search runner should not contain 'default=5'."""
        from helping_hands.lib.meta.tools import registry

        source = inspect.getsource(registry._run_web_search)
        assert "default=5" not in source

    def test_no_hardcoded_python_version_in_runners(self) -> None:
        """Runner wrappers should not contain 'or \"3.13\"'."""
        from helping_hands.lib.meta.tools import registry

        source = inspect.getsource(registry._run_python_code)
        source += inspect.getsource(registry._run_python_script)
        assert 'or "3.13"' not in source
