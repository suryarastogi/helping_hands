"""v195 — DRY git identity, browse max chars, and clone timeout constants.

Tests verify that duplicated constants now reference their shared sources.
"""

from __future__ import annotations

import inspect


# ---------------------------------------------------------------------------
# 1. DRY git identity: e2e.py re-exports from base.py
# ---------------------------------------------------------------------------


class TestDryGitIdentity:
    """E2E git identity constants reference base.py shared constants."""

    def test_e2e_user_name_matches_base(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_GIT_USER_NAME
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_GIT_USER_NAME

        assert _E2E_GIT_USER_NAME == _DEFAULT_GIT_USER_NAME

    def test_e2e_user_email_matches_base(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_GIT_USER_EMAIL
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_GIT_USER_EMAIL

        assert _E2E_GIT_USER_EMAIL == _DEFAULT_GIT_USER_EMAIL

    def test_e2e_user_name_is_same_object(self) -> None:
        """Verify e2e constant is an alias, not a copy."""
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_GIT_USER_NAME
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_GIT_USER_NAME

        assert _E2E_GIT_USER_NAME is _DEFAULT_GIT_USER_NAME

    def test_e2e_user_email_is_same_object(self) -> None:
        """Verify e2e constant is an alias, not a copy."""
        from helping_hands.lib.hands.v1.hand.base import _DEFAULT_GIT_USER_EMAIL
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_GIT_USER_EMAIL

        assert _E2E_GIT_USER_EMAIL is _DEFAULT_GIT_USER_EMAIL


# ---------------------------------------------------------------------------
# 2. DRY browse max chars: web.py defines, registry.py & mcp_server.py use
# ---------------------------------------------------------------------------


class TestDryBrowseMaxChars:
    """DEFAULT_BROWSE_MAX_CHARS is the single source for the 12000 default."""

    def test_web_constant_value(self) -> None:
        from helping_hands.lib.meta.tools.web import DEFAULT_BROWSE_MAX_CHARS

        assert DEFAULT_BROWSE_MAX_CHARS == 12000

    def test_web_constant_type(self) -> None:
        from helping_hands.lib.meta.tools.web import DEFAULT_BROWSE_MAX_CHARS

        assert isinstance(DEFAULT_BROWSE_MAX_CHARS, int)

    def test_web_constant_positive(self) -> None:
        from helping_hands.lib.meta.tools.web import DEFAULT_BROWSE_MAX_CHARS

        assert DEFAULT_BROWSE_MAX_CHARS > 0

    def test_web_constant_in_all(self) -> None:
        from helping_hands.lib.meta.tools.web import __all__

        assert "DEFAULT_BROWSE_MAX_CHARS" in __all__

    def test_browse_url_default_uses_constant(self) -> None:
        from helping_hands.lib.meta.tools.web import (
            DEFAULT_BROWSE_MAX_CHARS,
            browse_url,
        )

        sig = inspect.signature(browse_url)
        assert sig.parameters["max_chars"].default == DEFAULT_BROWSE_MAX_CHARS

    def test_mcp_server_uses_web_constant(self) -> None:
        from helping_hands.lib.meta.tools.web import DEFAULT_BROWSE_MAX_CHARS
        from helping_hands.server.mcp_server import _DEFAULT_BROWSE_MAX_CHARS

        assert _DEFAULT_BROWSE_MAX_CHARS == DEFAULT_BROWSE_MAX_CHARS


# ---------------------------------------------------------------------------
# 3. DRY clone timeout: github_url.py defines, cli/main.py & celery use
# ---------------------------------------------------------------------------


class TestDryCloneTimeout:
    """GIT_CLONE_TIMEOUT_S is the single source for clone timeout."""

    def test_github_url_constant_value(self) -> None:
        from helping_hands.lib.github_url import GIT_CLONE_TIMEOUT_S

        assert GIT_CLONE_TIMEOUT_S == 120

    def test_github_url_constant_type(self) -> None:
        from helping_hands.lib.github_url import GIT_CLONE_TIMEOUT_S

        assert isinstance(GIT_CLONE_TIMEOUT_S, int)

    def test_github_url_constant_positive(self) -> None:
        from helping_hands.lib.github_url import GIT_CLONE_TIMEOUT_S

        assert GIT_CLONE_TIMEOUT_S > 0

    def test_github_url_constant_in_all(self) -> None:
        from helping_hands.lib.github_url import __all__

        assert "GIT_CLONE_TIMEOUT_S" in __all__

    def test_cli_main_imports_from_github_url(self) -> None:
        from helping_hands.cli.main import _GIT_CLONE_TIMEOUT_S
        from helping_hands.lib.github_url import GIT_CLONE_TIMEOUT_S

        assert _GIT_CLONE_TIMEOUT_S == GIT_CLONE_TIMEOUT_S

    def test_celery_imports_from_github_url(self) -> None:
        from helping_hands.lib.github_url import GIT_CLONE_TIMEOUT_S

        try:
            from helping_hands.server.celery_app import _GIT_CLONE_TIMEOUT_S

            assert _GIT_CLONE_TIMEOUT_S == GIT_CLONE_TIMEOUT_S
        except ImportError:
            import pytest

            pytest.skip("celery not installed")
