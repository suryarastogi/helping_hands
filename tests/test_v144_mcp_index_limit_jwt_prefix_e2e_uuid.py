"""Tests for v144: MCP index file limit, JWT prefix constant, and E2E UUID reuse.

_INDEX_FILES_LIMIT caps how many files index_repo returns to MCP callers; without
this cap a large monorepo would serialize thousands of file paths into the MCP
response, timing out the client.  The "used in source" test ensures index_repo
slices with the constant, not a stale hardcoded 200 — so changing the limit in one
place takes effect everywhere.

_JWT_TOKEN_PREFIX ("ey") guards the Claude OAuth token extraction path: tokens that
don't start with "ey" are almost certainly not JWTs and should be rejected early.
If the code reverts to a hardcoded string literal instead of the constant, the
check becomes invisible to grep and harder to audit.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# 1. MCP server _INDEX_FILES_LIMIT constant
# ---------------------------------------------------------------------------


class TestMcpIndexFilesLimit:
    """Verify _INDEX_FILES_LIMIT in mcp_server.py."""

    def test_index_files_limit_value(self) -> None:
        from helping_hands.server.mcp_server import _INDEX_FILES_LIMIT

        assert _INDEX_FILES_LIMIT == 200

    def test_index_files_limit_is_int(self) -> None:
        from helping_hands.server.mcp_server import _INDEX_FILES_LIMIT

        assert isinstance(_INDEX_FILES_LIMIT, int)

    def test_index_files_limit_positive(self) -> None:
        from helping_hands.server.mcp_server import _INDEX_FILES_LIMIT

        assert _INDEX_FILES_LIMIT > 0

    def test_index_repo_uses_constant(self, tmp_path: object) -> None:
        """Verify index_repo slices files with _INDEX_FILES_LIMIT, not a hardcoded 200."""
        import inspect

        from helping_hands.server.mcp_server import index_repo

        # Check source code uses the constant name, not a literal 200
        source = inspect.getsource(index_repo)
        assert "_INDEX_FILES_LIMIT" in source
        assert "[:200]" not in source


# ---------------------------------------------------------------------------
# 2. JWT token prefix constant in server/app.py
# ---------------------------------------------------------------------------


class TestAppJwtTokenPrefix:
    """Verify JWT_TOKEN_PREFIX in server/constants.py."""

    def test_jwt_token_prefix_value(self) -> None:
        from helping_hands.server.constants import JWT_TOKEN_PREFIX

        assert JWT_TOKEN_PREFIX == "ey"

    def test_jwt_token_prefix_is_str(self) -> None:
        from helping_hands.server.constants import JWT_TOKEN_PREFIX

        assert isinstance(JWT_TOKEN_PREFIX, str)

    def test_jwt_token_prefix_nonempty(self) -> None:
        from helping_hands.server.constants import JWT_TOKEN_PREFIX

        assert len(JWT_TOKEN_PREFIX) > 0

    def test_get_claude_oauth_token_uses_constant(self) -> None:
        """Verify get_claude_oauth_token uses JWT_TOKEN_PREFIX, not hardcoded 'ey'."""
        import inspect

        from helping_hands.server.token_helpers import get_claude_oauth_token

        source = inspect.getsource(get_claude_oauth_token)
        assert "JWT_TOKEN_PREFIX" in source
        assert 'startswith("ey")' not in source


# ---------------------------------------------------------------------------
# 3. JWT token prefix constant in server/celery_app.py
# ---------------------------------------------------------------------------


class TestCeleryJwtTokenPrefix:
    """Verify _JWT_TOKEN_PREFIX in server/celery_app.py."""

    def test_jwt_token_prefix_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _JWT_TOKEN_PREFIX

        assert _JWT_TOKEN_PREFIX == "ey"

    def test_jwt_token_prefix_is_str(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _JWT_TOKEN_PREFIX

        assert isinstance(_JWT_TOKEN_PREFIX, str)

    def test_jwt_token_prefix_nonempty(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _JWT_TOKEN_PREFIX

        assert len(_JWT_TOKEN_PREFIX) > 0

    def test_jwt_prefix_matches_constants_module(self) -> None:
        """Ensure celery_app.py JWT prefix matches constants.py."""
        pytest.importorskip("celery")
        from helping_hands.server import (
            celery_app as celery_mod,
            constants as const_mod,
        )

        assert const_mod.JWT_TOKEN_PREFIX == celery_mod._JWT_TOKEN_PREFIX


# ---------------------------------------------------------------------------
# 4. E2E hand uses _UUID_HEX_LENGTH from base.py
# ---------------------------------------------------------------------------


class TestE2EUuidHexLengthReuse:
    """Verify E2EHand imports and uses _UUID_HEX_LENGTH from base.py."""

    def test_e2e_imports_uuid_hex_length(self) -> None:
        """Verify _UUID_HEX_LENGTH is importable from e2e module (re-exported from base)."""
        from helping_hands.lib.hands.v1.hand.e2e import _UUID_HEX_LENGTH

        assert _UUID_HEX_LENGTH == 8

    def test_e2e_uuid_hex_length_matches_base(self) -> None:
        """Ensure e2e.py and base.py share the same _UUID_HEX_LENGTH identity."""
        from helping_hands.lib.hands.v1.hand.base import (
            _UUID_HEX_LENGTH as _BASE_VAL,
        )
        from helping_hands.lib.hands.v1.hand.e2e import (
            _UUID_HEX_LENGTH as _E2E_VAL,
        )

        assert _E2E_VAL is _BASE_VAL

    def test_e2e_run_uses_constant_in_source(self) -> None:
        """Verify e2e.py source uses _UUID_HEX_LENGTH, not hardcoded [:8]."""
        import inspect

        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        source = inspect.getsource(E2EHand.run)
        assert "_UUID_HEX_LENGTH" in source
        assert "uuid[:8]" not in source
