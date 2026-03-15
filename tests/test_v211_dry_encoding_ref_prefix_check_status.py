"""Tests for v211 — encoding fallback chain, git ref prefix, check-run status constant.

Covers:
- _ENCODING_FALLBACK_CHAIN constant in web.py
- _decode_bytes uses the module-level constant (not inline)
- _GIT_REF_PREFIX constant in github.py
- fetch_branch uses the module-level constant (not inline)
- _CHECK_RUN_STATUS_COMPLETED constant in github.py
- get_check_runs uses the module-level constant (not inline)
"""

from __future__ import annotations

import inspect

from helping_hands.lib import github as github_module
from helping_hands.lib.meta.tools import web as web_module

# ---------------------------------------------------------------------------
# _ENCODING_FALLBACK_CHAIN constant
# ---------------------------------------------------------------------------


class TestEncodingFallbackChain:
    """Tests for the extracted _ENCODING_FALLBACK_CHAIN constant."""

    def test_constant_exists(self) -> None:
        assert hasattr(web_module, "_ENCODING_FALLBACK_CHAIN")

    def test_is_tuple(self) -> None:
        assert isinstance(web_module._ENCODING_FALLBACK_CHAIN, tuple)

    def test_has_three_entries(self) -> None:
        assert len(web_module._ENCODING_FALLBACK_CHAIN) == 3

    def test_expected_values(self) -> None:
        assert web_module._ENCODING_FALLBACK_CHAIN == (
            "utf-8",
            "utf-16",
            "latin-1",
        )

    def test_utf8_is_first(self) -> None:
        """UTF-8 should be tried first as the most common web encoding."""
        assert web_module._ENCODING_FALLBACK_CHAIN[0] == "utf-8"

    def test_latin1_is_last(self) -> None:
        """Latin-1 accepts all byte values, so it should be the final fallback."""
        assert web_module._ENCODING_FALLBACK_CHAIN[-1] == "latin-1"

    def test_all_entries_are_strings(self) -> None:
        for enc in web_module._ENCODING_FALLBACK_CHAIN:
            assert isinstance(enc, str)

    def test_all_entries_are_valid_codecs(self) -> None:
        """Each encoding must be a valid Python codec name."""
        import codecs

        for enc in web_module._ENCODING_FALLBACK_CHAIN:
            codecs.lookup(enc)  # raises LookupError if invalid

    def test_decode_bytes_uses_constant(self) -> None:
        """Verify _decode_bytes references the module-level constant."""
        source = inspect.getsource(web_module._decode_bytes)
        assert "_ENCODING_FALLBACK_CHAIN" in source

    def test_decode_bytes_utf8(self) -> None:
        """UTF-8 encoded bytes decode correctly."""
        assert web_module._decode_bytes(b"hello") == "hello"

    def test_decode_bytes_latin1(self) -> None:
        """Latin-1 bytes that are not valid UTF-8 still decode."""
        payload = bytes([0xC0, 0xC1])  # invalid UTF-8 and UTF-16
        result = web_module._decode_bytes(payload)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _GIT_REF_PREFIX constant
# ---------------------------------------------------------------------------


class TestGitRefPrefix:
    """Tests for the extracted _GIT_REF_PREFIX constant."""

    def test_constant_exists(self) -> None:
        assert hasattr(github_module, "_GIT_REF_PREFIX")

    def test_is_string(self) -> None:
        assert isinstance(github_module._GIT_REF_PREFIX, str)

    def test_expected_value(self) -> None:
        assert github_module._GIT_REF_PREFIX == "refs/heads/"

    def test_ends_with_slash(self) -> None:
        assert github_module._GIT_REF_PREFIX.endswith("/")

    def test_fetch_branch_uses_constant(self) -> None:
        """Verify fetch_branch references the module-level constant."""
        source = inspect.getsource(github_module.GitHubClient.fetch_branch)
        assert "_GIT_REF_PREFIX" in source


# ---------------------------------------------------------------------------
# _CHECK_RUN_STATUS_COMPLETED constant
# ---------------------------------------------------------------------------


class TestCheckRunStatusCompleted:
    """Tests for the extracted _CHECK_RUN_STATUS_COMPLETED constant."""

    def test_constant_exists(self) -> None:
        assert hasattr(github_module, "_CHECK_RUN_STATUS_COMPLETED")

    def test_is_string(self) -> None:
        assert isinstance(github_module._CHECK_RUN_STATUS_COMPLETED, str)

    def test_expected_value(self) -> None:
        assert github_module._CHECK_RUN_STATUS_COMPLETED == "completed"

    def test_is_lowercase(self) -> None:
        assert (
            github_module._CHECK_RUN_STATUS_COMPLETED.lower()
            == github_module._CHECK_RUN_STATUS_COMPLETED
        )

    def test_get_check_runs_uses_constant(self) -> None:
        """Verify get_check_runs references the module-level constant."""
        source = inspect.getsource(github_module.GitHubClient.get_check_runs)
        assert "_CHECK_RUN_STATUS_COMPLETED" in source
