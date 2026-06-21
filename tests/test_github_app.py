"""Unit tests for helping_hands.lib.github_app (GitHub App installation auth).

Covers the env-driven configuration check, private-key loading from a ``.pem``
path or inline value, installation-id resolution (explicit / auto-discovery /
ambiguous), and the mint-and-cache behaviour for installation access tokens
including refresh-before-expiry and error normalisation. Also verifies that
``resolve_github_token`` falls back to a minted App token only when no PAT is
available, so existing token auth is never perturbed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from helping_hands.lib import github_app
from helping_hands.lib.github_app import (
    GitHubAppError,
    github_app_configured,
    resolve_app_installation_token,
)

_APP_ENV_VARS = (
    "GITHUB_APP_ID",
    "GITHUB_APP_PRIVATE_KEY_PATH",
    "GITHUB_APP_PRIVATE_KEY",
    "GITHUB_APP_INSTALLATION_ID",
    "GITHUB_TOKEN",
    "GH_TOKEN",
)

_FAKE_PEM = "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate every test from ambient GitHub env vars and the token cache."""
    for name in _APP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    github_app._token_cache.clear()


# ---------------------------------------------------------------------------
# Fakes for PyGithub
# ---------------------------------------------------------------------------


class _FakeInstallation:
    def __init__(self, install_id: int) -> None:
        self.id = install_id


class _FakeAccessToken:
    def __init__(self, token: str, expires_at: datetime) -> None:
        self.token = token
        self.expires_at = expires_at


def _install_fake_github(
    monkeypatch: pytest.MonkeyPatch,
    *,
    installations: list[int] | None = None,
    expires_in: timedelta = timedelta(hours=1),
    token_value: str = "ghs_minted_token",
    raise_on_access: Exception | None = None,
) -> dict[str, int]:
    """Patch ``github.Auth.AppAuth`` / ``github.GithubIntegration`` with fakes.

    Returns a mutable counter dict tracking how many tokens were minted.
    """
    counter = {"mints": 0}
    installs = [_FakeInstallation(i) for i in (installations or [42])]

    class _FakeAppAuth:
        def __init__(self, app_id: object, private_key: str) -> None:
            self.app_id = app_id
            self.private_key = private_key

    class _FakeIntegration:
        def __init__(self, auth: object) -> None:
            self.auth = auth

        def get_installations(self) -> list[_FakeInstallation]:
            return installs

        def get_access_token(
            self, installation_id: int, permissions: object = None
        ) -> _FakeAccessToken:
            if raise_on_access is not None:
                raise raise_on_access
            counter["mints"] += 1
            return _FakeAccessToken(
                f"{token_value}_{counter['mints']}",
                datetime.now(UTC) + expires_in,
            )

    import github

    monkeypatch.setattr(github.Auth, "AppAuth", _FakeAppAuth)
    monkeypatch.setattr(github, "GithubIntegration", _FakeIntegration)
    return counter


# ---------------------------------------------------------------------------
# github_app_configured
# ---------------------------------------------------------------------------


class TestConfigured:
    def test_unconfigured_is_false(self) -> None:
        assert github_app_configured() is False

    def test_app_id_without_key_is_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        assert github_app_configured() is False

    def test_app_id_with_path_is_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", "/tmp/key.pem")
        assert github_app_configured() is True

    def test_app_id_with_inline_key_is_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        assert github_app_configured() is True


# ---------------------------------------------------------------------------
# _load_private_key
# ---------------------------------------------------------------------------


class TestLoadPrivateKey:
    def test_reads_from_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        pem = tmp_path / "app.pem"
        pem.write_text(_FAKE_PEM, encoding="utf-8")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
        assert github_app._load_private_key() == _FAKE_PEM

    def test_path_takes_precedence_over_inline(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        pem = tmp_path / "app.pem"
        pem.write_text("FROM_PATH", encoding="utf-8")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "FROM_INLINE")
        assert github_app._load_private_key() == "FROM_PATH"

    def test_reads_inline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        assert github_app._load_private_key() == _FAKE_PEM

    def test_unescapes_inline_newlines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        single_line = _FAKE_PEM.replace("\n", "\\n")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", single_line)
        assert github_app._load_private_key() == _FAKE_PEM

    def test_missing_path_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", "/no/such/key.pem")
        with pytest.raises(GitHubAppError, match="could not read"):
            github_app._load_private_key()

    def test_no_source_raises(self) -> None:
        with pytest.raises(GitHubAppError, match="not configured"):
            github_app._load_private_key()


# ---------------------------------------------------------------------------
# _resolve_installation_id
# ---------------------------------------------------------------------------


class _IntegrationStub:
    def __init__(self, ids: list[int]) -> None:
        self._ids = ids

    def get_installations(self) -> list[_FakeInstallation]:
        return [_FakeInstallation(i) for i in self._ids]


class TestResolveInstallationId:
    def test_explicit_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "777")
        assert github_app._resolve_installation_id(_IntegrationStub([1, 2])) == 777

    def test_explicit_non_numeric_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "abc")
        with pytest.raises(GitHubAppError, match="must be an integer"):
            github_app._resolve_installation_id(_IntegrationStub([1]))

    def test_auto_discovers_single(self) -> None:
        assert github_app._resolve_installation_id(_IntegrationStub([99])) == 99

    def test_zero_installations_raises(self) -> None:
        with pytest.raises(GitHubAppError, match="not installed"):
            github_app._resolve_installation_id(_IntegrationStub([]))

    def test_multiple_installations_raises(self) -> None:
        with pytest.raises(GitHubAppError, match="multiple installations"):
            github_app._resolve_installation_id(_IntegrationStub([1, 2]))


# ---------------------------------------------------------------------------
# resolve_app_installation_token: mint, cache, refresh, errors
# ---------------------------------------------------------------------------


class TestResolveAppInstallationToken:
    def test_returns_none_when_unconfigured(self) -> None:
        assert resolve_app_installation_token() is None

    def test_mints_and_caches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        counter = _install_fake_github(monkeypatch)

        first = resolve_app_installation_token()
        second = resolve_app_installation_token()

        assert first == "ghs_minted_token_1"
        assert second == first  # served from cache
        assert counter["mints"] == 1

    def test_refreshes_when_near_expiry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        # Expiry inside the 5-minute refresh margin → never cached.
        counter = _install_fake_github(monkeypatch, expires_in=timedelta(minutes=1))

        first = resolve_app_installation_token()
        second = resolve_app_installation_token()

        assert first == "ghs_minted_token_1"
        assert second == "ghs_minted_token_2"
        assert counter["mints"] == 2

    def test_uses_explicit_installation_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "555")
        # Multiple installs would be ambiguous without the explicit id.
        _install_fake_github(monkeypatch, installations=[1, 2, 3])
        assert resolve_app_installation_token() == "ghs_minted_token_1"

    def test_wraps_api_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        _install_fake_github(monkeypatch, raise_on_access=RuntimeError("boom"))
        with pytest.raises(GitHubAppError, match="failed to mint"):
            resolve_app_installation_token()


# ---------------------------------------------------------------------------
# resolve_github_token fallback
# ---------------------------------------------------------------------------


class TestResolveGithubTokenFallback:
    def test_falls_back_to_app_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        _install_fake_github(monkeypatch)
        assert resolve_github_token() == "ghs_minted_token_1"

    def test_pat_takes_precedence_over_app(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_real_pat")
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", _FAKE_PEM)
        counter = _install_fake_github(monkeypatch)

        assert resolve_github_token() == "ghp_real_pat"
        assert counter["mints"] == 0  # App auth never consulted

    def test_returns_empty_when_nothing_configured(self) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token() == ""
