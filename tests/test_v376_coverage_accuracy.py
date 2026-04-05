"""Tests for v376 — Coverage accuracy: dynamic server omit & pragma cleanup.

Validates that the coverage configuration correctly handles the split
between local dev (without server extras) and CI (with server extras).
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestCoverageRcNoServer:
    """The .coveragerc-no-server file must stay in sync with expectations."""

    @pytest.fixture()
    def rc_path(self) -> Path:
        return REPO_ROOT / ".coveragerc-no-server"

    @pytest.fixture()
    def rc_config(self, rc_path: Path) -> configparser.ConfigParser:
        cp = configparser.ConfigParser()
        cp.read(rc_path)
        return cp

    def test_file_exists(self, rc_path: Path) -> None:
        assert rc_path.is_file(), ".coveragerc-no-server must exist in repo root"

    def test_run_section_has_branch(self, rc_config: configparser.ConfigParser) -> None:
        assert rc_config.getboolean("run", "branch") is True

    def test_run_section_has_source(self, rc_config: configparser.ConfigParser) -> None:
        source = rc_config.get("run", "source")
        assert "src/helping_hands" in source

    def test_omit_includes_server_app(
        self, rc_config: configparser.ConfigParser
    ) -> None:
        omit = rc_config.get("run", "omit")
        assert "*/server/app.py" in omit

    def test_omit_includes_server_celery(
        self, rc_config: configparser.ConfigParser
    ) -> None:
        omit = rc_config.get("run", "omit")
        assert "*/server/celery_app.py" in omit

    def test_omit_includes_server_schedules(
        self, rc_config: configparser.ConfigParser
    ) -> None:
        omit = rc_config.get("run", "omit")
        assert "*/server/schedules.py" in omit

    def test_report_fail_under_at_least_95(
        self, rc_config: configparser.ConfigParser
    ) -> None:
        fail_under = rc_config.getint("report", "fail_under")
        assert fail_under >= 95

    def test_report_excludes_pragma_no_cover(
        self, rc_config: configparser.ConfigParser
    ) -> None:
        exclude = rc_config.get("report", "exclude_lines")
        assert "pragma: no cover" in exclude

    def test_report_excludes_type_checking(
        self, rc_config: configparser.ConfigParser
    ) -> None:
        exclude = rc_config.get("report", "exclude_lines")
        assert "TYPE_CHECKING" in exclude


class TestPyprojectCoverageConfig:
    """pyproject.toml coverage config must be valid for CI (all extras)."""

    @pytest.fixture()
    def pyproject_text(self) -> str:
        return (REPO_ROOT / "pyproject.toml").read_text()

    def test_addopts_references_no_server_config(self, pyproject_text: str) -> None:
        """Default addopts should use .coveragerc-no-server for local dev."""
        assert "--cov-config=.coveragerc-no-server" in pyproject_text

    def test_pyproject_has_coverage_run_section(self, pyproject_text: str) -> None:
        assert "[tool.coverage.run]" in pyproject_text

    def test_pyproject_coverage_fail_under_75(self, pyproject_text: str) -> None:
        """CI coverage threshold (with server extras) should be 75%."""
        assert "fail_under = 75" in pyproject_text


class TestCiWorkflowCoverageOverride:
    """CI workflow must override cov-config to use pyproject.toml."""

    @pytest.fixture()
    def ci_text(self) -> str:
        return (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()

    def test_ci_uses_pyproject_cov_config(self, ci_text: str) -> None:
        assert "--cov-config=pyproject.toml" in ci_text

    def test_ci_installs_server_extras(self, ci_text: str) -> None:
        assert "--extra server" in ci_text


class TestPragmaNocover:
    """Unreachable and optional-dep lines should have pragma: no cover."""

    def test_cli_main_unreachable_returns(self) -> None:
        content = (REPO_ROOT / "src" / "helping_hands" / "cli" / "main.py").read_text()
        # Both unreachable returns after _error_exit() should have pragma
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if 'return ""' in line and "unreachable" in line.lower():
                assert "pragma: no cover" in line, (
                    f"cli/main.py:{i} unreachable return missing pragma"
                )

    def test_cli_main_name_guard(self) -> None:
        content = (REPO_ROOT / "src" / "helping_hands" / "cli" / "main.py").read_text()
        for line in content.splitlines():
            if "__name__" in line and "__main__" in line:
                assert "pragma: no cover" in line

    def test_mcp_server_name_guard(self) -> None:
        content = (
            REPO_ROOT / "src" / "helping_hands" / "server" / "mcp_server.py"
        ).read_text()
        for line in content.splitlines():
            if "__name__" in line and "__main__" in line:
                assert "pragma: no cover" in line

    def test_multiplayer_yjs_optional_import_pragmas(self) -> None:
        content = (
            REPO_ROOT / "src" / "helping_hands" / "server" / "multiplayer_yjs.py"
        ).read_text()
        # The _HAS_PYCRDT = True lines should have pragma
        for i, line in enumerate(content.splitlines(), 1):
            if "_HAS_PYCRDT = True" in line:
                assert "pragma: no cover" in line, (
                    f"multiplayer_yjs.py:{i} optional import success "
                    f"path missing pragma"
                )
