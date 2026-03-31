"""Enforce Google-style docstring coverage on Config, web.py helpers, and registry.py.

These tests protect the contract that all public-facing configuration fields and
private helper functions carry structured documentation. Without this, the
Attributes: section in Config becomes stale and helpers like _require_http_url or
_strip_html lose their Args/Returns/Raises contract, making it harder to understand
security-sensitive behaviour (URL validation, HTML sanitization, credential handling).
If these tests regress, new contributors will lack the context to safely extend these
modules and type checkers lose the parameter-intent signal from the docstrings.
"""

# TODO: CLEANUP CANDIDATE — all tests only assert docstring presence and section
# keywords (Attributes:, Args:, Returns:); no runtime behavior is exercised.
# Could be replaced by enabling ruff D rules (pydocstyle) for these modules.

from __future__ import annotations

import inspect

import pytest

# ---------------------------------------------------------------------------
# Config Attributes section
# ---------------------------------------------------------------------------


class TestConfigAttributesSection:
    """Config dataclass must have an Attributes: section documenting all fields."""

    def test_has_attributes_section(self) -> None:
        from helping_hands.lib.config import Config

        doc = inspect.getdoc(Config)
        assert doc, "Config missing docstring"
        assert "Attributes:" in doc, "Config docstring missing Attributes: section"

    @pytest.mark.parametrize(
        "field_name",
        [
            "repo",
            "model",
            "verbose",
            "enable_execution",
            "enable_web",
            "use_native_cli_auth",
            "enabled_tools",
            "enabled_skills",
            "github_token",
            "reference_repos",
            "config_path",
        ],
    )
    def test_attributes_mention_field(self, field_name: str) -> None:
        from helping_hands.lib.config import Config

        doc = inspect.getdoc(Config) or ""
        attrs_start = doc.find("Attributes:")
        assert attrs_start != -1
        attrs_block = doc[attrs_start:]
        assert f"{field_name}:" in attrs_block, (
            f"Config.{field_name} not documented in Attributes section"
        )


# ---------------------------------------------------------------------------
# web.py private helper docstrings
# ---------------------------------------------------------------------------

_WEB_HELPERS = [
    "_require_http_url",
    "_strip_html",
    "_as_string_keyed_dict",
    "_extract_related_topics",
]


class TestWebHelperDocstrings:
    """All web.py private helpers must have Google-style docstrings."""

    @pytest.mark.parametrize("func_name", _WEB_HELPERS)
    def test_has_docstring(self, func_name: str) -> None:
        from helping_hands.lib.meta.tools import web

        func = getattr(web, func_name)
        doc = inspect.getdoc(func)
        assert doc, f"web.{func_name} missing docstring"
        assert len(doc) > 20, f"web.{func_name} docstring too short"

    @pytest.mark.parametrize(
        ("func_name", "expected_sections"),
        [
            ("_require_http_url", ["Args:", "Returns:", "Raises:"]),
            ("_strip_html", ["Args:", "Returns:"]),
            ("_as_string_keyed_dict", ["Args:", "Returns:"]),
            ("_extract_related_topics", ["Args:"]),
        ],
    )
    def test_has_expected_sections(
        self, func_name: str, expected_sections: list[str]
    ) -> None:
        from helping_hands.lib.meta.tools import web

        func = getattr(web, func_name)
        doc = inspect.getdoc(func) or ""
        for section in expected_sections:
            assert section in doc, (
                f"web.{func_name} docstring missing {section} section"
            )


# ---------------------------------------------------------------------------
# registry.py private helper docstrings
# ---------------------------------------------------------------------------

_REGISTRY_HELPERS = [
    "_parse_str_list",
    "_parse_positive_int",
    "_parse_optional_str",
    "_run_python_code",
    "_run_python_script",
    "_run_bash_script",
    "_run_web_search",
    "_run_web_browse",
]


class TestRegistryHelperDocstrings:
    """All registry.py private helpers must have Google-style docstrings."""

    @pytest.mark.parametrize("func_name", _REGISTRY_HELPERS)
    def test_has_docstring(self, func_name: str) -> None:
        from helping_hands.lib.meta.tools import registry

        func = getattr(registry, func_name)
        doc = inspect.getdoc(func)
        assert doc, f"registry.{func_name} missing docstring"
        assert len(doc) > 20, f"registry.{func_name} docstring too short"

    @pytest.mark.parametrize(
        ("func_name", "expected_sections"),
        [
            ("_parse_str_list", ["Args:", "Returns:", "Raises:"]),
            ("_parse_positive_int", ["Args:", "Returns:", "Raises:"]),
            ("_parse_optional_str", ["Args:", "Returns:", "Raises:"]),
            ("_run_python_code", ["Args:", "Returns:", "Raises:"]),
            ("_run_python_script", ["Args:", "Returns:", "Raises:"]),
            ("_run_bash_script", ["Args:", "Returns:", "Raises:"]),
            ("_run_web_search", ["Args:", "Returns:", "Raises:"]),
            ("_run_web_browse", ["Args:", "Returns:", "Raises:"]),
        ],
    )
    def test_has_expected_sections(
        self, func_name: str, expected_sections: list[str]
    ) -> None:
        from helping_hands.lib.meta.tools import registry

        func = getattr(registry, func_name)
        doc = inspect.getdoc(func) or ""
        for section in expected_sections:
            assert section in doc, (
                f"registry.{func_name} docstring missing {section} section"
            )
