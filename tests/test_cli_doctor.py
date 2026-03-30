"""Tests for helping_hands.cli.doctor — environment prerequisite checks.

These tests protect the ``helping-hands doctor`` subcommand contract:
individual checks report the correct status for present/missing
prerequisites, the report formatter produces the expected output,
``run_doctor`` returns exit code 0 when all required checks pass and 1
when any fails, and the ``main()`` dispatcher routes ``doctor`` before
the regular argument parser runs.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from helping_hands.cli.doctor import (
    CheckResult,
    _check_git,
    _check_github_token,
    _check_optional_cli_tools,
    _check_optional_extras,
    _check_provider_keys,
    _check_python,
    _check_uv,
    collect_checks,
    format_results,
    run_doctor,
)


class TestCheckPython:
    def test_ok_when_version_meets_minimum(self) -> None:
        vi = type("V", (), {"major": 3, "minor": 13, "micro": 1})()
        with patch("helping_hands.cli.doctor.sys") as mock_sys:
            mock_sys.version_info = vi
            result = _check_python()
        assert result.status == "ok"
        assert "3.13.1" in result.message

    def test_fail_when_version_below_minimum(self) -> None:
        vi = type("V", (), {"major": 3, "minor": 11, "micro": 0})()
        with patch("helping_hands.cli.doctor.sys") as mock_sys:
            mock_sys.version_info = vi
            result = _check_python()
        assert result.status == "fail"
        assert "3.12" in result.message


class TestCheckGit:
    def test_ok_when_git_found(self) -> None:
        with patch(
            "helping_hands.cli.doctor.shutil.which", return_value="/usr/bin/git"
        ):
            result = _check_git()
        assert result.status == "ok"

    def test_fail_when_git_missing(self) -> None:
        with patch("helping_hands.cli.doctor.shutil.which", return_value=None):
            result = _check_git()
        assert result.status == "fail"


class TestCheckUv:
    def test_ok_when_uv_found(self) -> None:
        with patch("helping_hands.cli.doctor.shutil.which", return_value="/usr/bin/uv"):
            result = _check_uv()
        assert result.status == "ok"

    def test_warn_when_uv_missing(self) -> None:
        with patch("helping_hands.cli.doctor.shutil.which", return_value=None):
            result = _check_uv()
        assert result.status == "warn"


class TestCheckProviderKeys:
    def test_ok_when_at_least_one_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        results = _check_provider_keys()
        statuses = {r.name: r.status for r in results}
        assert statuses["OPENAI_API_KEY"] == "ok"
        assert statuses["ANTHROPIC_API_KEY"] == "warn"
        # No aggregate failure entry when at least one is set
        assert "provider_keys" not in statuses

    def test_fail_when_no_keys_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        results = _check_provider_keys()
        statuses = {r.name: r.status for r in results}
        assert statuses["provider_keys"] == "fail"

    def test_whitespace_only_key_treated_as_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "  ")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        results = _check_provider_keys()
        statuses = {r.name: r.status for r in results}
        assert statuses["OPENAI_API_KEY"] == "warn"
        assert "provider_keys" in statuses


class TestCheckGitHubToken:
    def test_ok_when_github_token_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        result = _check_github_token()
        assert result.status == "ok"
        assert "GITHUB_TOKEN" in result.message

    def test_ok_when_gh_token_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "ghp_test")
        result = _check_github_token()
        assert result.status == "ok"
        assert "GH_TOKEN" in result.message

    def test_warn_when_no_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        result = _check_github_token()
        assert result.status == "warn"


class TestCheckOptionalCliTools:
    def test_found_tools_report_ok(self) -> None:
        with patch(
            "helping_hands.cli.doctor.shutil.which",
            side_effect=lambda name: f"/usr/bin/{name}",
        ):
            results = _check_optional_cli_tools()
        assert all(r.status == "ok" for r in results)

    def test_missing_tools_report_warn(self) -> None:
        with patch("helping_hands.cli.doctor.shutil.which", return_value=None):
            results = _check_optional_cli_tools()
        assert all(r.status == "warn" for r in results)
        assert len(results) == 4  # claude, codex, goose, gemini


class TestCheckOptionalExtras:
    def test_installed_extras_report_ok(self) -> None:
        with patch("helping_hands.cli.doctor.importlib.import_module"):
            results = _check_optional_extras()
        assert all(r.status == "ok" for r in results)

    def test_missing_extras_report_warn(self) -> None:
        with patch(
            "helping_hands.cli.doctor.importlib.import_module",
            side_effect=ImportError("not installed"),
        ):
            results = _check_optional_extras()
        assert all(r.status == "warn" for r in results)
        assert any("uv sync --extra" in r.message for r in results)


class TestCollectChecks:
    def test_returns_list_of_check_results(self) -> None:
        with (
            patch("helping_hands.cli.doctor.shutil.which", return_value="/usr/bin/x"),
            patch("helping_hands.cli.doctor.importlib.import_module"),
            patch("helping_hands.cli.doctor.os.environ.get", return_value="set"),
        ):
            results = collect_checks()
        assert isinstance(results, list)
        assert all(isinstance(r, CheckResult) for r in results)
        assert len(results) > 0


class TestFormatResults:
    def test_header_present(self) -> None:
        results = [CheckResult("test", "ok", "all good")]
        output = format_results(results)
        assert "helping-hands doctor" in output

    def test_ok_symbol(self) -> None:
        results = [CheckResult("test", "ok", "all good")]
        output = format_results(results)
        assert "[+]" in output

    def test_warn_symbol(self) -> None:
        results = [CheckResult("test", "warn", "missing optional")]
        output = format_results(results)
        assert "[!]" in output

    def test_fail_symbol(self) -> None:
        results = [CheckResult("test", "fail", "critical")]
        output = format_results(results)
        assert "[x]" in output

    def test_all_passed_message(self) -> None:
        results = [CheckResult("test", "ok", "fine")]
        output = format_results(results)
        assert "All checks passed" in output

    def test_warnings_only_message(self) -> None:
        results = [
            CheckResult("a", "ok", "fine"),
            CheckResult("b", "warn", "optional"),
        ]
        output = format_results(results)
        assert "1 optional warning" in output

    def test_failure_message(self) -> None:
        results = [CheckResult("a", "fail", "bad")]
        output = format_results(results)
        assert "1 issue(s) must be fixed" in output


class TestRunDoctor:
    def test_returns_zero_when_no_failures(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch(
            "helping_hands.cli.doctor.collect_checks",
            return_value=[CheckResult("test", "ok", "fine")],
        ):
            code = run_doctor()
        assert code == 0
        assert "All checks passed" in capsys.readouterr().out

    def test_returns_one_when_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(
            "helping_hands.cli.doctor.collect_checks",
            return_value=[CheckResult("test", "fail", "bad")],
        ):
            code = run_doctor()
        assert code == 1
        assert "must be fixed" in capsys.readouterr().out


class TestMainDoctorDispatch:
    def test_main_dispatches_doctor_subcommand(self) -> None:
        """Verify ``main(["doctor"])`` routes to ``run_doctor``."""
        from helping_hands.cli.main import main

        with (
            patch("helping_hands.cli.doctor.run_doctor", return_value=0) as mock_doc,
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["doctor"])
        mock_doc.assert_called_once()
        assert exc_info.value.code == 0

    def test_main_doctor_propagates_exit_code(self) -> None:
        """Verify ``main(["doctor"])`` propagates non-zero exit."""
        from helping_hands.cli.main import main

        with (
            patch("helping_hands.cli.doctor.run_doctor", return_value=1),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["doctor"])
        assert exc_info.value.code == 1

    def test_main_doctor_early_return(self) -> None:
        """Cover the ``return`` after ``doctor()`` when it does not raise."""
        from helping_hands.cli.main import main

        # Patch the local ``doctor`` function so it returns normally
        # instead of calling ``sys.exit()``.  This exercises line 340.
        with patch("helping_hands.cli.main.doctor") as mock_doctor:
            main(["doctor", "--verbose"])
        mock_doctor.assert_called_once_with(["--verbose"])
