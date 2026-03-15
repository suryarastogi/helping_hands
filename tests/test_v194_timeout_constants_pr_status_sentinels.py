"""Tests for v194: DRY timeout constants and PR status sentinel extraction.

Covers:
- _DEFAULT_SCRIPT_TIMEOUT_S in command.py (value, type, function signature defaults)
- _DEFAULT_WEB_TIMEOUT_S in web.py (value, type, function signature defaults)
- _PR_STATUS_* sentinel constants in base.py (values, types, frozensets)
- Cross-module import consistency (iterative.py, cli/base.py use base.py constants)
"""

from __future__ import annotations

import inspect

# ---------------------------------------------------------------------------
# _DEFAULT_SCRIPT_TIMEOUT_S constant tests
# ---------------------------------------------------------------------------


class TestDefaultScriptTimeoutConstant:
    """Verify _DEFAULT_SCRIPT_TIMEOUT_S in command.py."""

    def test_value_is_60(self) -> None:
        from helping_hands.lib.meta.tools.command import _DEFAULT_SCRIPT_TIMEOUT_S

        assert _DEFAULT_SCRIPT_TIMEOUT_S == 60

    def test_is_int(self) -> None:
        from helping_hands.lib.meta.tools.command import _DEFAULT_SCRIPT_TIMEOUT_S

        assert isinstance(_DEFAULT_SCRIPT_TIMEOUT_S, int)

    def test_positive(self) -> None:
        from helping_hands.lib.meta.tools.command import _DEFAULT_SCRIPT_TIMEOUT_S

        assert _DEFAULT_SCRIPT_TIMEOUT_S > 0

    def test_run_python_code_default(self) -> None:
        """run_python_code uses _DEFAULT_SCRIPT_TIMEOUT_S as default."""
        from helping_hands.lib.meta.tools.command import (
            _DEFAULT_SCRIPT_TIMEOUT_S,
            run_python_code,
        )

        sig = inspect.signature(run_python_code)
        assert sig.parameters["timeout_s"].default == _DEFAULT_SCRIPT_TIMEOUT_S

    def test_run_python_script_default(self) -> None:
        """run_python_script uses _DEFAULT_SCRIPT_TIMEOUT_S as default."""
        from helping_hands.lib.meta.tools.command import (
            _DEFAULT_SCRIPT_TIMEOUT_S,
            run_python_script,
        )

        sig = inspect.signature(run_python_script)
        assert sig.parameters["timeout_s"].default == _DEFAULT_SCRIPT_TIMEOUT_S

    def test_run_bash_script_default(self) -> None:
        """run_bash_script uses _DEFAULT_SCRIPT_TIMEOUT_S as default."""
        from helping_hands.lib.meta.tools.command import (
            _DEFAULT_SCRIPT_TIMEOUT_S,
            run_bash_script,
        )

        sig = inspect.signature(run_bash_script)
        assert sig.parameters["timeout_s"].default == _DEFAULT_SCRIPT_TIMEOUT_S


# ---------------------------------------------------------------------------
# _DEFAULT_WEB_TIMEOUT_S constant tests
# ---------------------------------------------------------------------------


class TestDefaultWebTimeoutConstant:
    """Verify _DEFAULT_WEB_TIMEOUT_S in web.py."""

    def test_value_is_20(self) -> None:
        from helping_hands.lib.meta.tools.web import _DEFAULT_WEB_TIMEOUT_S

        assert _DEFAULT_WEB_TIMEOUT_S == 20

    def test_is_int(self) -> None:
        from helping_hands.lib.meta.tools.web import _DEFAULT_WEB_TIMEOUT_S

        assert isinstance(_DEFAULT_WEB_TIMEOUT_S, int)

    def test_positive(self) -> None:
        from helping_hands.lib.meta.tools.web import _DEFAULT_WEB_TIMEOUT_S

        assert _DEFAULT_WEB_TIMEOUT_S > 0

    def test_search_web_default(self) -> None:
        """search_web uses _DEFAULT_WEB_TIMEOUT_S as default."""
        from helping_hands.lib.meta.tools.web import (
            _DEFAULT_WEB_TIMEOUT_S,
            search_web,
        )

        sig = inspect.signature(search_web)
        assert sig.parameters["timeout_s"].default == _DEFAULT_WEB_TIMEOUT_S

    def test_browse_url_default(self) -> None:
        """browse_url uses _DEFAULT_WEB_TIMEOUT_S as default."""
        from helping_hands.lib.meta.tools.web import (
            _DEFAULT_WEB_TIMEOUT_S,
            browse_url,
        )

        sig = inspect.signature(browse_url)
        assert sig.parameters["timeout_s"].default == _DEFAULT_WEB_TIMEOUT_S


# ---------------------------------------------------------------------------
# _PR_STATUS_* sentinel constant tests
# ---------------------------------------------------------------------------


class TestPRStatusSentinelConstants:
    """Verify individual PR status sentinel values in base.py."""

    def test_created_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_CREATED

        assert _PR_STATUS_CREATED == "created"

    def test_updated_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_UPDATED

        assert _PR_STATUS_UPDATED == "updated"

    def test_no_changes_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NO_CHANGES

        assert _PR_STATUS_NO_CHANGES == "no_changes"

    def test_disabled_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_DISABLED

        assert _PR_STATUS_DISABLED == "disabled"

    def test_not_attempted_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUS_NOT_ATTEMPTED

        assert _PR_STATUS_NOT_ATTEMPTED == "not_attempted"

    def test_all_are_strings(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUS_CREATED,
            _PR_STATUS_DISABLED,
            _PR_STATUS_NO_CHANGES,
            _PR_STATUS_NOT_ATTEMPTED,
            _PR_STATUS_UPDATED,
        )

        for val in (
            _PR_STATUS_CREATED,
            _PR_STATUS_UPDATED,
            _PR_STATUS_NO_CHANGES,
            _PR_STATUS_DISABLED,
            _PR_STATUS_NOT_ATTEMPTED,
        ):
            assert isinstance(val, str), f"{val!r} is not a string"

    def test_all_unique(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUS_CREATED,
            _PR_STATUS_DISABLED,
            _PR_STATUS_NO_CHANGES,
            _PR_STATUS_NOT_ATTEMPTED,
            _PR_STATUS_UPDATED,
        )

        values = [
            _PR_STATUS_CREATED,
            _PR_STATUS_UPDATED,
            _PR_STATUS_NO_CHANGES,
            _PR_STATUS_DISABLED,
            _PR_STATUS_NOT_ATTEMPTED,
        ]
        assert len(values) == len(set(values))


class TestPRStatusesFrozensets:
    """Verify _PR_STATUSES_WITH_URL and _PR_STATUSES_SKIPPED frozensets."""

    def test_with_url_is_frozenset(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUSES_WITH_URL

        assert isinstance(_PR_STATUSES_WITH_URL, frozenset)

    def test_with_url_contains_created(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUS_CREATED,
            _PR_STATUSES_WITH_URL,
        )

        assert _PR_STATUS_CREATED in _PR_STATUSES_WITH_URL

    def test_with_url_contains_updated(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUS_UPDATED,
            _PR_STATUSES_WITH_URL,
        )

        assert _PR_STATUS_UPDATED in _PR_STATUSES_WITH_URL

    def test_with_url_has_exactly_two_members(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUSES_WITH_URL

        assert len(_PR_STATUSES_WITH_URL) == 2

    def test_skipped_is_frozenset(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUSES_SKIPPED

        assert isinstance(_PR_STATUSES_SKIPPED, frozenset)

    def test_skipped_contains_no_changes(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUS_NO_CHANGES,
            _PR_STATUSES_SKIPPED,
        )

        assert _PR_STATUS_NO_CHANGES in _PR_STATUSES_SKIPPED

    def test_skipped_contains_disabled(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUS_DISABLED,
            _PR_STATUSES_SKIPPED,
        )

        assert _PR_STATUS_DISABLED in _PR_STATUSES_SKIPPED

    def test_skipped_has_exactly_two_members(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _PR_STATUSES_SKIPPED

        assert len(_PR_STATUSES_SKIPPED) == 2

    def test_with_url_and_skipped_are_disjoint(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            _PR_STATUSES_SKIPPED,
            _PR_STATUSES_WITH_URL,
        )

        assert _PR_STATUSES_WITH_URL.isdisjoint(_PR_STATUSES_SKIPPED)


# ---------------------------------------------------------------------------
# Cross-module import consistency
# ---------------------------------------------------------------------------


class TestPRStatusCrossModuleSync:
    """Verify that consumers import PR status constants from base.py."""

    def test_iterative_imports_skipped_from_base(self) -> None:
        """iterative.py uses _PR_STATUSES_SKIPPED from base."""
        from helping_hands.lib.hands.v1.hand import base, iterative

        assert iterative._PR_STATUSES_SKIPPED is base._PR_STATUSES_SKIPPED

    def test_cli_base_imports_created_from_base(self) -> None:
        """cli/base.py uses _PR_STATUS_CREATED from base."""
        from helping_hands.lib.hands.v1.hand import base
        from helping_hands.lib.hands.v1.hand.cli import base as cli_base

        assert cli_base._PR_STATUS_CREATED is base._PR_STATUS_CREATED

    def test_cli_base_imports_updated_from_base(self) -> None:
        """cli/base.py uses _PR_STATUS_UPDATED from base."""
        from helping_hands.lib.hands.v1.hand import base
        from helping_hands.lib.hands.v1.hand.cli import base as cli_base

        assert cli_base._PR_STATUS_UPDATED is base._PR_STATUS_UPDATED

    def test_cli_base_imports_with_url_from_base(self) -> None:
        """cli/base.py uses _PR_STATUSES_WITH_URL from base."""
        from helping_hands.lib.hands.v1.hand import base
        from helping_hands.lib.hands.v1.hand.cli import base as cli_base

        assert cli_base._PR_STATUSES_WITH_URL is base._PR_STATUSES_WITH_URL

    def test_cli_base_imports_disabled_from_base(self) -> None:
        """cli/base.py uses _PR_STATUS_DISABLED from base."""
        from helping_hands.lib.hands.v1.hand import base
        from helping_hands.lib.hands.v1.hand.cli import base as cli_base

        assert cli_base._PR_STATUS_DISABLED is base._PR_STATUS_DISABLED

    def test_cli_base_imports_no_changes_from_base(self) -> None:
        """cli/base.py uses _PR_STATUS_NO_CHANGES from base."""
        from helping_hands.lib.hands.v1.hand import base
        from helping_hands.lib.hands.v1.hand.cli import base as cli_base

        assert cli_base._PR_STATUS_NO_CHANGES is base._PR_STATUS_NO_CHANGES
