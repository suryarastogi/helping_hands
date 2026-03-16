"""Tests for v197 — DRY field validation bounds, BackendName reuse, bytes-per-MB.

Validates:
- ``server/constants`` new field validation bound constants
- ``server/app`` BuildRequest/ScheduleRequest use shared bound constants
- ``server/app`` BackendName type alias deduplication (used in BuildRequest)
- ``server/app`` BackendName in ``__all__``
- ``lib/meta/tools/filesystem`` ``_BYTES_PER_MB`` constant extraction
"""

from __future__ import annotations

import pytest


def _get_max_length(field):
    """Extract max_length from FieldInfo metadata (works across Pydantic/Python versions).

    Always reads from ``field.metadata`` rather than the direct attribute
    because ``FieldInfo.max_length`` is not reliably accessible on Python 3.14.
    """
    for m in field.metadata:
        ml = getattr(m, "max_length", None)
        if ml is not None:
            return ml
    return None


# ---------------------------------------------------------------------------
# server/constants — field validation bound constants
# ---------------------------------------------------------------------------


class TestFieldValidationBoundConstants:
    """Verify new field bound constants in server/constants."""

    def test_max_iterations_upper_bound_value(self) -> None:
        from helping_hands.server.constants import MAX_ITERATIONS_UPPER_BOUND

        assert MAX_ITERATIONS_UPPER_BOUND == 100

    def test_max_iterations_upper_bound_is_int(self) -> None:
        from helping_hands.server.constants import MAX_ITERATIONS_UPPER_BOUND

        assert isinstance(MAX_ITERATIONS_UPPER_BOUND, int)

    def test_min_ci_wait_minutes_value(self) -> None:
        from helping_hands.server.constants import MIN_CI_WAIT_MINUTES

        assert MIN_CI_WAIT_MINUTES == 0.5

    def test_max_ci_wait_minutes_value(self) -> None:
        from helping_hands.server.constants import MAX_CI_WAIT_MINUTES

        assert MAX_CI_WAIT_MINUTES == 30.0

    def test_max_repo_path_length_value(self) -> None:
        from helping_hands.server.constants import MAX_REPO_PATH_LENGTH

        assert MAX_REPO_PATH_LENGTH == 500

    def test_max_prompt_length_value(self) -> None:
        from helping_hands.server.constants import MAX_PROMPT_LENGTH

        assert MAX_PROMPT_LENGTH == 50_000

    def test_max_model_length_value(self) -> None:
        from helping_hands.server.constants import MAX_MODEL_LENGTH

        assert MAX_MODEL_LENGTH == 200

    def test_max_github_token_length_value(self) -> None:
        from helping_hands.server.constants import MAX_GITHUB_TOKEN_LENGTH

        assert MAX_GITHUB_TOKEN_LENGTH == 500

    def test_all_bound_constants_positive(self) -> None:
        from helping_hands.server.constants import (
            MAX_CI_WAIT_MINUTES,
            MAX_GITHUB_TOKEN_LENGTH,
            MAX_ITERATIONS_UPPER_BOUND,
            MAX_MODEL_LENGTH,
            MAX_PROMPT_LENGTH,
            MAX_REPO_PATH_LENGTH,
            MIN_CI_WAIT_MINUTES,
        )

        for val in (
            MAX_ITERATIONS_UPPER_BOUND,
            MIN_CI_WAIT_MINUTES,
            MAX_CI_WAIT_MINUTES,
            MAX_REPO_PATH_LENGTH,
            MAX_PROMPT_LENGTH,
            MAX_MODEL_LENGTH,
            MAX_GITHUB_TOKEN_LENGTH,
        ):
            assert val > 0

    def test_ci_wait_bounds_ordering(self) -> None:
        from helping_hands.server.constants import (
            MAX_CI_WAIT_MINUTES,
            MIN_CI_WAIT_MINUTES,
        )

        assert MIN_CI_WAIT_MINUTES < MAX_CI_WAIT_MINUTES


# ---------------------------------------------------------------------------
# server/constants — __all__ updated
# ---------------------------------------------------------------------------


class TestServerConstantsAllUpdated:
    """Verify __all__ includes new field bound constants."""

    def test_all_exports_updated(self) -> None:
        from helping_hands.server import constants

        # Superset check: at minimum these must be present (v232 added more)
        required = {
            "ANTHROPIC_BETA_HEADER",
            "ANTHROPIC_USAGE_URL",
            "DEFAULT_BACKEND",
            "DEFAULT_CI_WAIT_MINUTES",
            "DEFAULT_MAX_ITERATIONS",
            "JWT_TOKEN_PREFIX",
            "KEYCHAIN_ACCESS_TOKEN_KEY",
            "KEYCHAIN_OAUTH_KEY",
            "KEYCHAIN_SERVICE_NAME",
            "MAX_CI_WAIT_MINUTES",
            "MAX_GITHUB_TOKEN_LENGTH",
            "MAX_ITERATIONS_UPPER_BOUND",
            "MAX_MODEL_LENGTH",
            "MAX_PROMPT_LENGTH",
            "MAX_REFERENCE_REPOS",
            "MAX_REPO_PATH_LENGTH",
            "MIN_CI_WAIT_MINUTES",
            "KEYCHAIN_TIMEOUT_S",
            "USAGE_API_TIMEOUT_S",
            "USAGE_CACHE_TTL_S",
            "USAGE_USER_AGENT",
        }
        assert required <= set(constants.__all__)


# ---------------------------------------------------------------------------
# server/app — BuildRequest field bounds use shared constants
# ---------------------------------------------------------------------------


class TestBuildRequestFieldBounds:
    """Verify BuildRequest fields reference shared constants."""

    def test_max_iterations_le_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_ITERATIONS_UPPER_BOUND

        field = BuildRequest.model_fields["max_iterations"]
        meta = field.metadata
        le_val = next(
            (
                getattr(m, "le", None)
                for m in meta
                if hasattr(m, "le") and getattr(m, "le", None) is not None
            ),
            None,
        )
        assert le_val == MAX_ITERATIONS_UPPER_BOUND

    def test_ci_check_ge_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MIN_CI_WAIT_MINUTES

        field = BuildRequest.model_fields["ci_check_wait_minutes"]
        meta = field.metadata
        ge_val = next(
            (
                getattr(m, "ge", None)
                for m in meta
                if hasattr(m, "ge") and getattr(m, "ge", None) is not None
            ),
            None,
        )
        assert ge_val == MIN_CI_WAIT_MINUTES

    def test_ci_check_le_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_CI_WAIT_MINUTES

        field = BuildRequest.model_fields["ci_check_wait_minutes"]
        meta = field.metadata
        le_val = next(
            (
                getattr(m, "le", None)
                for m in meta
                if hasattr(m, "le") and getattr(m, "le", None) is not None
            ),
            None,
        )
        assert le_val == MAX_CI_WAIT_MINUTES

    def test_repo_path_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_REPO_PATH_LENGTH

        field = BuildRequest.model_fields["repo_path"]
        assert _get_max_length(field) == MAX_REPO_PATH_LENGTH

    def test_prompt_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_PROMPT_LENGTH

        field = BuildRequest.model_fields["prompt"]
        assert _get_max_length(field) == MAX_PROMPT_LENGTH

    def test_model_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_MODEL_LENGTH

        field = BuildRequest.model_fields["model"]
        assert _get_max_length(field) == MAX_MODEL_LENGTH

    def test_github_token_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest
        from helping_hands.server.constants import MAX_GITHUB_TOKEN_LENGTH

        field = BuildRequest.model_fields["github_token"]
        assert _get_max_length(field) == MAX_GITHUB_TOKEN_LENGTH


# ---------------------------------------------------------------------------
# server/app — ScheduleRequest field bounds use shared constants
# ---------------------------------------------------------------------------


class TestScheduleRequestFieldBounds:
    """Verify ScheduleRequest fields reference shared constants."""

    def test_max_iterations_le_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_ITERATIONS_UPPER_BOUND

        field = ScheduleRequest.model_fields["max_iterations"]
        meta = field.metadata
        le_val = next(
            (
                getattr(m, "le", None)
                for m in meta
                if hasattr(m, "le") and getattr(m, "le", None) is not None
            ),
            None,
        )
        assert le_val == MAX_ITERATIONS_UPPER_BOUND

    def test_ci_check_ge_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MIN_CI_WAIT_MINUTES

        field = ScheduleRequest.model_fields["ci_check_wait_minutes"]
        meta = field.metadata
        ge_val = next(
            (
                getattr(m, "ge", None)
                for m in meta
                if hasattr(m, "ge") and getattr(m, "ge", None) is not None
            ),
            None,
        )
        assert ge_val == MIN_CI_WAIT_MINUTES

    def test_ci_check_le_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_CI_WAIT_MINUTES

        field = ScheduleRequest.model_fields["ci_check_wait_minutes"]
        meta = field.metadata
        le_val = next(
            (
                getattr(m, "le", None)
                for m in meta
                if hasattr(m, "le") and getattr(m, "le", None) is not None
            ),
            None,
        )
        assert le_val == MAX_CI_WAIT_MINUTES

    def test_repo_path_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_REPO_PATH_LENGTH

        field = ScheduleRequest.model_fields["repo_path"]
        assert _get_max_length(field) == MAX_REPO_PATH_LENGTH

    def test_prompt_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_PROMPT_LENGTH

        field = ScheduleRequest.model_fields["prompt"]
        assert _get_max_length(field) == MAX_PROMPT_LENGTH

    def test_model_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_MODEL_LENGTH

        field = ScheduleRequest.model_fields["model"]
        assert _get_max_length(field) == MAX_MODEL_LENGTH

    def test_github_token_max_length_matches_constant(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import ScheduleRequest
        from helping_hands.server.constants import MAX_GITHUB_TOKEN_LENGTH

        field = ScheduleRequest.model_fields["github_token"]
        assert _get_max_length(field) == MAX_GITHUB_TOKEN_LENGTH


# ---------------------------------------------------------------------------
# server/app — BackendName type alias deduplication
# ---------------------------------------------------------------------------


class TestBackendNameDeduplication:
    """Verify BackendName type alias is shared and exported."""

    def test_backend_name_in_all(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import __all__

        assert "BackendName" in __all__

    def test_backend_name_importable(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BackendName

        assert BackendName is not None

    def test_build_request_backend_accepts_valid(self) -> None:
        """BuildRequest backend field accepts a valid BackendName value."""
        pytest.importorskip("fastapi")
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/r", prompt="test", backend="goose")
        assert req.backend == "goose"

    def test_build_request_backend_rejects_invalid(self) -> None:
        """BuildRequest backend field rejects unknown backend."""
        pytest.importorskip("fastapi")
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError):
            BuildRequest(repo_path="/tmp/r", prompt="test", backend="not-a-backend")


# ---------------------------------------------------------------------------
# filesystem — _BYTES_PER_MB constant
# ---------------------------------------------------------------------------


class TestBytesPerMbConstant:
    """Verify _BYTES_PER_MB in filesystem.py."""

    def test_bytes_per_mb_value(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import _BYTES_PER_MB

        assert _BYTES_PER_MB == 1024 * 1024

    def test_bytes_per_mb_is_int(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import _BYTES_PER_MB

        assert isinstance(_BYTES_PER_MB, int)

    def test_max_file_size_uses_bytes_per_mb(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import (
            _BYTES_PER_MB,
            _MAX_FILE_SIZE_BYTES,
        )

        assert _MAX_FILE_SIZE_BYTES == 10 * _BYTES_PER_MB

    def test_bytes_per_mb_positive(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import _BYTES_PER_MB

        assert _BYTES_PER_MB > 0
