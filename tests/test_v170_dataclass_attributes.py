"""Tests for v170: Attributes sections in public dataclass docstrings."""

from __future__ import annotations

import inspect

import pytest

# ---------------------------------------------------------------------------
# Target classes and their expected attribute names
# ---------------------------------------------------------------------------

_TARGETS: list[tuple[str, str, list[str]]] = [
    (
        "helping_hands.lib.meta.tools.registry",
        "ToolSpec",
        ["name", "payload_example", "runner"],
    ),
    (
        "helping_hands.lib.meta.tools.registry",
        "ToolCategory",
        ["name", "title", "tools"],
    ),
    (
        "helping_hands.lib.meta.tools.web",
        "WebSearchItem",
        ["title", "url", "snippet"],
    ),
    (
        "helping_hands.lib.meta.tools.web",
        "WebSearchResult",
        ["query", "results"],
    ),
    (
        "helping_hands.lib.meta.tools.web",
        "WebBrowseResult",
        ["url", "final_url", "status_code", "content", "truncated"],
    ),
    (
        "helping_hands.lib.meta.tools.command",
        "CommandResult",
        ["command", "cwd", "exit_code", "stdout", "stderr", "timed_out"],
    ),
    (
        "helping_hands.lib.hands.v1.hand.base",
        "HandResponse",
        ["message", "metadata"],
    ),
    (
        "helping_hands.lib.github",
        "PRResult",
        ["number", "url", "title", "head", "base"],
    ),
    (
        "helping_hands.lib.hands.v1.hand.pr_description",
        "PRDescription",
        ["title", "body"],
    ),
    (
        "helping_hands.lib.hands.v1.hand.model_provider",
        "HandModel",
        ["provider", "model", "raw"],
    ),
    (
        "helping_hands.lib.meta.skills",
        "SkillSpec",
        ["name", "title", "content"],
    ),
    (
        "helping_hands.lib.repo",
        "RepoIndex",
        ["root", "files", "reference_repos"],
    ),
]


def _import_class(module_path: str, class_name: str) -> type:
    """Import and return a class by module path and name."""
    import importlib

    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


# Generate test IDs from class names
_IDS = [f"{t[1]}" for t in _TARGETS]


class TestDataclassAttributesSections:
    """Every public dataclass must have an Attributes: section in its docstring."""

    @pytest.mark.parametrize(
        ("module_path", "class_name", "expected_attrs"),
        _TARGETS,
        ids=_IDS,
    )
    def test_has_attributes_section(
        self, module_path: str, class_name: str, expected_attrs: list[str]
    ) -> None:
        cls = _import_class(module_path, class_name)
        doc = inspect.getdoc(cls)
        assert doc, f"{class_name} missing docstring"
        assert "Attributes:" in doc, (
            f"{class_name} docstring missing Attributes: section"
        )

    @pytest.mark.parametrize(
        ("module_path", "class_name", "expected_attrs"),
        _TARGETS,
        ids=_IDS,
    )
    def test_attributes_mention_all_fields(
        self, module_path: str, class_name: str, expected_attrs: list[str]
    ) -> None:
        cls = _import_class(module_path, class_name)
        doc = inspect.getdoc(cls) or ""
        # Extract the Attributes block
        attrs_start = doc.find("Attributes:")
        assert attrs_start != -1, f"{class_name} missing Attributes: section"
        attrs_block = doc[attrs_start:]
        for attr in expected_attrs:
            assert f"{attr}:" in attrs_block, (
                f"{class_name}.{attr} not documented in Attributes section"
            )


class TestScheduledTaskAttributesSection:
    """ScheduledTask needs server extras; skip gracefully."""

    @pytest.fixture()
    def cls(self):
        try:
            from helping_hands.server.schedules import ScheduledTask
        except ImportError:
            pytest.skip("server extras not installed")
        return ScheduledTask

    def test_has_attributes_section(self, cls: type) -> None:
        doc = inspect.getdoc(cls)
        assert doc, "ScheduledTask missing docstring"
        assert "Attributes:" in doc

    def test_attributes_mention_key_fields(self, cls: type) -> None:
        doc = inspect.getdoc(cls) or ""
        attrs_start = doc.find("Attributes:")
        assert attrs_start != -1
        attrs_block = doc[attrs_start:]
        for field_name in (
            "schedule_id",
            "name",
            "cron_expression",
            "repo_path",
            "prompt",
            "backend",
            "enabled",
            "run_count",
        ):
            assert f"{field_name}:" in attrs_block, (
                f"ScheduledTask.{field_name} not documented"
            )
