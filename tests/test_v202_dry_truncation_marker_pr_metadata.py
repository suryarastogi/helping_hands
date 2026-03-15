"""Tests for v202: DRY truncation marker and PR metadata factory.

Covers:
- _TRUNCATION_MARKER shared constant in base.py (value, type)
- _default_pr_metadata() factory function (output shape, field values)
- Cross-module import identity (cli/base.py, pr_description.py, celery_app.py)
- Usage sites produce output containing the shared marker
"""

from __future__ import annotations

import pytest

from helping_hands.lib.hands.v1.hand.base import (
    _TRUNCATION_MARKER,
    _default_pr_metadata,
)

# ---------------------------------------------------------------------------
# _TRUNCATION_MARKER constant
# ---------------------------------------------------------------------------


class TestTruncationMarker:
    """Verify _TRUNCATION_MARKER in base.py."""

    def test_is_string(self) -> None:
        assert isinstance(_TRUNCATION_MARKER, str)

    def test_value(self) -> None:
        assert _TRUNCATION_MARKER == "...[truncated]"

    def test_not_empty(self) -> None:
        assert len(_TRUNCATION_MARKER) > 0

    def test_starts_with_ellipsis(self) -> None:
        assert _TRUNCATION_MARKER.startswith("...")

    def test_contains_truncated(self) -> None:
        assert "truncated" in _TRUNCATION_MARKER


class TestTruncationMarkerCrossModuleImport:
    """Verify that other modules import the same constant object."""

    def test_cli_base_imports_same_object(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _TRUNCATION_MARKER as _CLI_MARKER,
        )

        assert _CLI_MARKER is _TRUNCATION_MARKER

    def test_pr_description_imports_same_object(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            _TRUNCATION_MARKER as _PR_MARKER,
        )

        assert _PR_MARKER is _TRUNCATION_MARKER

    def test_celery_app_imports_same_object(self) -> None:
        pytest.importorskip("celery", reason="celery extra not installed")
        from helping_hands.server.celery_app import (
            _TRUNCATION_MARKER as _CELERY_MARKER,
        )

        assert _CELERY_MARKER is _TRUNCATION_MARKER


class TestTruncationMarkerUsageInTruncateSummary:
    """Verify _truncate_summary in cli/base.py uses the shared marker."""

    def test_truncated_output_ends_with_marker(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        result = _TwoPhaseCLIHand._truncate_summary("a" * 200, limit=10)
        assert result.endswith(_TRUNCATION_MARKER)

    def test_short_text_has_no_marker(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        result = _TwoPhaseCLIHand._truncate_summary("short", limit=100)
        assert _TRUNCATION_MARKER not in result


class TestTruncationMarkerUsageInTruncateText:
    """Verify _truncate_text in pr_description.py uses the shared marker."""

    def test_truncated_output_ends_with_marker(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_text

        result = _truncate_text("b" * 200, limit=10)
        assert result.endswith(_TRUNCATION_MARKER)

    def test_short_text_has_no_marker(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_text

        result = _truncate_text("short", limit=100)
        assert _TRUNCATION_MARKER not in result


# ---------------------------------------------------------------------------
# _default_pr_metadata() factory
# ---------------------------------------------------------------------------


class TestDefaultPrMetadata:
    """Verify _default_pr_metadata() factory in base.py."""

    def test_returns_dict(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="test")
        assert isinstance(result, dict)

    def test_has_all_required_keys(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="test")
        expected_keys = {
            "auto_pr",
            "pr_status",
            "pr_url",
            "pr_number",
            "pr_branch",
            "pr_commit",
        }
        assert set(result.keys()) == expected_keys

    def test_auto_pr_true(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="x")
        assert result["auto_pr"] == "true"

    def test_auto_pr_false(self) -> None:
        result = _default_pr_metadata(auto_pr=False, pr_status="x")
        assert result["auto_pr"] == "false"

    def test_pr_status_passthrough(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="not_attempted")
        assert result["pr_status"] == "not_attempted"

    def test_pr_url_empty(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="x")
        assert result["pr_url"] == ""

    def test_pr_number_empty(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="x")
        assert result["pr_number"] == ""

    def test_pr_branch_empty(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="x")
        assert result["pr_branch"] == ""

    def test_pr_commit_empty(self) -> None:
        result = _default_pr_metadata(auto_pr=True, pr_status="x")
        assert result["pr_commit"] == ""

    def test_returns_new_dict_each_call(self) -> None:
        a = _default_pr_metadata(auto_pr=True, pr_status="x")
        b = _default_pr_metadata(auto_pr=True, pr_status="x")
        assert a == b
        assert a is not b

    def test_interrupted_status(self) -> None:
        result = _default_pr_metadata(auto_pr=False, pr_status="interrupted")
        assert result["pr_status"] == "interrupted"
        assert result["auto_pr"] == "false"


class TestDefaultPrMetadataCrossModuleImport:
    """Verify cli/base.py imports the same factory."""

    def test_cli_base_imports_same_function(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _default_pr_metadata as cli_factory,
        )

        assert cli_factory is _default_pr_metadata
