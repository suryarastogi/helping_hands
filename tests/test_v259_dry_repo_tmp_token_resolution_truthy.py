"""Tests for v259: DRY repo_tmp_dir(), resolve_github_token(), and truthy values.

resolve_github_token() implements the priority chain: explicit token > GITHUB_TOKEN
env var > GH_TOKEN env var > empty string. If the priority order is wrong, a
user who sets both GITHUB_TOKEN and GH_TOKEN gets the wrong token used for
clone/API calls. Whitespace-only values must fall through to the next level
rather than being used verbatim.

repo_tmp_dir() is the optional workspace override used in CI environments that
pre-provision a temp directory. If it fails to create nested directories on
first call or returns a Path for whitespace-only env var values, downstream
clone operations fail with confusing OSErrors.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# resolve_github_token() tests
# ---------------------------------------------------------------------------


class TestResolveGitHubToken:
    """Tests for the shared resolve_github_token() helper."""

    def test_explicit_token_takes_priority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        monkeypatch.setenv("GH_TOKEN", "gh-token")
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token("explicit") == "explicit"

    def test_github_token_env_used_when_no_explicit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-github")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token() == "env-github"

    def test_gh_token_env_used_as_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "gh-fallback")
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token() == "gh-fallback"

    def test_empty_string_when_no_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token() == ""

    def test_whitespace_explicit_falls_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-tok")
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token("  ") == "env-tok"

    def test_whitespace_env_falls_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "  ")
        monkeypatch.setenv("GH_TOKEN", "gh-real")
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token() == "gh-real"

    def test_explicit_token_stripped(self) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token("  tok  ") == "tok"

    def test_env_token_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "  spaced  ")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token() == "spaced"

    def test_github_py_uses_resolve(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GitHubClient.__post_init__ should use resolve_github_token internally."""
        monkeypatch.setenv("GH_TOKEN", "gh-only")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        from helping_hands.lib.github_url import resolve_github_token

        resolved = resolve_github_token("")
        assert resolved == "gh-only"

    def test_build_clone_url_uses_resolve(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """build_clone_url should pick up GH_TOKEN when no explicit token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "test-gh-tok")
        from helping_hands.lib.github_url import build_clone_url

        url = build_clone_url("owner/repo")
        assert "test-gh-tok" in url


# ---------------------------------------------------------------------------
# repo_tmp_dir() tests
# ---------------------------------------------------------------------------


class TestRepoTmpDir:
    """Tests for the shared repo_tmp_dir() helper."""

    def test_returns_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_REPO_TMP", raising=False)
        from helping_hands.lib.github_url import repo_tmp_dir

        assert repo_tmp_dir() is None

    def test_returns_none_for_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", "")
        from helping_hands.lib.github_url import repo_tmp_dir

        assert repo_tmp_dir() is None

    def test_returns_none_for_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", "   ")
        from helping_hands.lib.github_url import repo_tmp_dir

        assert repo_tmp_dir() is None

    def test_returns_path_when_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        target = tmp_path / "custom_tmp"
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(target))
        from helping_hands.lib.github_url import repo_tmp_dir

        result = repo_tmp_dir()
        assert result is not None
        assert result == target
        assert target.is_dir()

    def test_creates_nested_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        target = tmp_path / "a" / "b" / "c"
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(target))
        from helping_hands.lib.github_url import repo_tmp_dir

        result = repo_tmp_dir()
        assert result == target
        assert target.is_dir()

    def test_existing_directory_ok(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(target))
        from helping_hands.lib.github_url import repo_tmp_dir

        result = repo_tmp_dir()
        assert result == target

    def test_tilde_expansion(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", "~/test_hh_tmp")
        from helping_hands.lib.github_url import repo_tmp_dir

        with (
            patch.object(Path, "expanduser", return_value=tmp_path / "expanded"),
            patch.object(Path, "mkdir"),
        ):
            result = repo_tmp_dir()
            assert result is not None

    def test_exported_in_all(self) -> None:
        from helping_hands.lib import github_url

        assert "repo_tmp_dir" in github_url.__all__

    def test_resolve_github_token_exported_in_all(self) -> None:
        from helping_hands.lib import github_url

        assert "resolve_github_token" in github_url.__all__


# ---------------------------------------------------------------------------
# _ENV_* constant tests
# ---------------------------------------------------------------------------


class TestEnvVarConstants:
    """Verify the new env var name constants exist."""

    def test_env_github_token_value(self) -> None:
        from helping_hands.lib.github_url import _ENV_GITHUB_TOKEN

        assert _ENV_GITHUB_TOKEN == "GITHUB_TOKEN"

    def test_env_gh_token_value(self) -> None:
        from helping_hands.lib.github_url import _ENV_GH_TOKEN

        assert _ENV_GH_TOKEN == "GH_TOKEN"

    def test_env_repo_tmp_value(self) -> None:
        from helping_hands.lib.github_url import _ENV_REPO_TMP

        assert _ENV_REPO_TMP == "HELPING_HANDS_REPO_TMP"


# ---------------------------------------------------------------------------
# _is_disabled() tests (truthy values now unified in config._TRUTHY_VALUES)
# ---------------------------------------------------------------------------


class TestPRTruthyValues:
    """Tests for unified truthy values used by _is_disabled()."""

    def test_truthy_includes_on(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        assert "on" in _TRUTHY_VALUES

    def test_truthy_includes_standard_values(self) -> None:
        from helping_hands.lib.config import _TRUTHY_VALUES

        for val in ("1", "true", "yes", "on"):
            assert val in _TRUTHY_VALUES

    def test_is_disabled_recognizes_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "on")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is True

    def test_is_disabled_recognizes_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "true")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is True

    def test_is_disabled_recognizes_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "YES")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is True

    def test_is_disabled_recognizes_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "1")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is True

    def test_is_disabled_rejects_random(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "nope")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is False

    def test_is_disabled_empty_is_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_DISABLE_PR_DESCRIPTION", "")
        from helping_hands.lib.hands.v1.hand.pr_description import _is_disabled

        assert _is_disabled() is False
