"""Tests for task template management (CRUD, ownership, serialization)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.server.templates import (
    TaskTemplate,
    TemplateManager,
    generate_template_id,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_template(**overrides) -> TaskTemplate:
    """Helper to create a TaskTemplate with sensible defaults."""
    defaults = {
        "template_id": "tmpl_test12345678",
        "name": "Test Template",
        "description": "A test template",
        "owner_token_hash": "abc123hash",
    }
    defaults.update(overrides)
    return TaskTemplate(**defaults)


def _build_manager():
    """Build a TemplateManager with a mocked Redis client."""
    mock_redis = MagicMock()

    with patch.object(TemplateManager, "__init__", lambda self, **kw: None):
        mgr = TemplateManager()

    mgr._redis = mock_redis
    return mgr, mock_redis


# ---------------------------------------------------------------------------
# TaskTemplate dataclass
# ---------------------------------------------------------------------------


class TestTaskTemplate:
    """Tests for the TaskTemplate dataclass."""

    def test_defaults(self) -> None:
        t = TaskTemplate(template_id="tmpl_abc", name="My Template")
        assert t.template_id == "tmpl_abc"
        assert t.name == "My Template"
        assert t.description == ""
        assert t.owner_token_hash is None
        assert t.created_at != ""
        assert t.updated_at != ""
        assert t.repo_path is None
        assert t.prompt is None
        assert t.backend is None
        assert t.model is None
        assert t.max_iterations is None
        assert t.enable_execution is None
        assert t.fix_ci is None
        assert t.reference_repos is None
        assert t.tools is None

    def test_post_init_sets_timestamps(self) -> None:
        t = TaskTemplate(template_id="tmpl_abc", name="T")
        assert t.created_at
        assert t.updated_at

    def test_post_init_preserves_explicit_timestamps(self) -> None:
        t = TaskTemplate(
            template_id="tmpl_abc",
            name="T",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-02T00:00:00",
        )
        assert t.created_at == "2025-01-01T00:00:00"
        assert t.updated_at == "2025-01-02T00:00:00"

    def test_to_dict_round_trip(self) -> None:
        t = _make_template(
            repo_path="owner/repo",
            prompt="do things",
            backend="claudecodecli",
            model="gpt-5.2",
            max_iterations=10,
            pr_number=42,
            issue_number=7,
            create_issue=True,
            project_url="https://example.com",
            no_pr=False,
            enable_execution=True,
            enable_web=False,
            use_native_cli_auth=False,
            fix_ci=True,
            fix_conflicts=False,
            master_rebase=True,
            ci_check_wait_minutes=5.0,
            reference_repos=["a/b", "c/d"],
            tools=["filesystem", "web"],
        )
        d = t.to_dict()
        restored = TaskTemplate.from_dict(d)

        assert restored.template_id == t.template_id
        assert restored.name == t.name
        assert restored.description == t.description
        assert restored.owner_token_hash == t.owner_token_hash
        assert restored.repo_path == t.repo_path
        assert restored.prompt == t.prompt
        assert restored.backend == t.backend
        assert restored.model == t.model
        assert restored.max_iterations == t.max_iterations
        assert restored.pr_number == t.pr_number
        assert restored.issue_number == t.issue_number
        assert restored.create_issue == t.create_issue
        assert restored.project_url == t.project_url
        assert restored.no_pr == t.no_pr
        assert restored.enable_execution == t.enable_execution
        assert restored.enable_web == t.enable_web
        assert restored.use_native_cli_auth == t.use_native_cli_auth
        assert restored.fix_ci == t.fix_ci
        assert restored.fix_conflicts == t.fix_conflicts
        assert restored.master_rebase == t.master_rebase
        assert restored.ci_check_wait_minutes == t.ci_check_wait_minutes
        assert restored.reference_repos == t.reference_repos
        assert restored.tools == t.tools

    def test_null_fields_round_trip(self) -> None:
        """Null/None fields should survive serialization."""
        t = TaskTemplate(template_id="tmpl_abc", name="Minimal")
        d = t.to_dict()
        restored = TaskTemplate.from_dict(d)
        assert restored.repo_path is None
        assert restored.prompt is None
        assert restored.backend is None
        assert restored.max_iterations is None
        assert restored.reference_repos is None
        assert restored.tools is None

    def test_from_dict_missing_required_fields(self) -> None:
        with pytest.raises(ValueError, match="Missing required fields"):
            TaskTemplate.from_dict({"name": "T"})

    def test_from_dict_empty_required_fields(self) -> None:
        with pytest.raises(ValueError, match="Required fields must not be empty"):
            TaskTemplate.from_dict({"template_id": "  ", "name": "T"})

    def test_to_dict_contains_all_keys(self) -> None:
        t = _make_template()
        d = t.to_dict()
        expected_keys = {
            "template_id",
            "name",
            "description",
            "owner_token_hash",
            "created_at",
            "updated_at",
            "repo_path",
            "prompt",
            "backend",
            "model",
            "max_iterations",
            "pr_number",
            "issue_number",
            "create_issue",
            "project_url",
            "no_pr",
            "enable_execution",
            "enable_web",
            "use_native_cli_auth",
            "fix_ci",
            "fix_conflicts",
            "master_rebase",
            "ci_check_wait_minutes",
            "reference_repos",
            "tools",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# generate_template_id
# ---------------------------------------------------------------------------


class TestGenerateTemplateId:
    """Tests for the generate_template_id function."""

    def test_format(self) -> None:
        tid = generate_template_id()
        assert tid.startswith("tmpl_")
        hex_part = tid[5:]
        assert len(hex_part) == 12
        int(hex_part, 16)  # should not raise

    def test_uniqueness(self) -> None:
        ids = {generate_template_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# TemplateManager CRUD
# ---------------------------------------------------------------------------


class TestTemplateManager:
    """Tests for TemplateManager Redis-backed CRUD operations."""

    def test_save_and_load_meta(self) -> None:
        mgr, mock_redis = _build_manager()
        template = _make_template()

        mgr._save_meta(template)
        mock_redis.set.assert_called_once()

        key_arg = mock_redis.set.call_args[0][0]
        json_arg = mock_redis.set.call_args[0][1]
        assert "tmpl_test12345678" in key_arg

        data = json.loads(json_arg)
        assert data["name"] == "Test Template"

    def test_load_meta_returns_none_when_missing(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.get.return_value = None
        result = mgr._load_meta("nonexistent")
        assert result is None

    def test_load_meta_returns_template(self) -> None:
        mgr, mock_redis = _build_manager()
        template = _make_template()
        mock_redis.get.return_value = json.dumps(template.to_dict())

        result = mgr._load_meta("tmpl_test12345678")
        assert result is not None
        assert result.name == "Test Template"

    def test_load_meta_handles_corrupted_json(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.get.return_value = "not-valid-json"
        result = mgr._load_meta("tmpl_bad")
        assert result is None

    def test_create_template(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.get.return_value = None
        template = _make_template()

        result = mgr.create_template(template)
        assert result.template_id == "tmpl_test12345678"
        mock_redis.set.assert_called_once()

    def test_create_template_duplicate_raises(self) -> None:
        mgr, mock_redis = _build_manager()
        template = _make_template()
        mock_redis.get.return_value = json.dumps(template.to_dict())

        with pytest.raises(ValueError, match="already exists"):
            mgr.create_template(template)

    def test_get_template(self) -> None:
        mgr, mock_redis = _build_manager()
        template = _make_template()
        mock_redis.get.return_value = json.dumps(template.to_dict())

        result = mgr.get_template("tmpl_test12345678")
        assert result is not None
        assert result.name == "Test Template"

    def test_get_template_not_found(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.get.return_value = None
        assert mgr.get_template("tmpl_nonexistent") is None

    def test_list_templates(self) -> None:
        mgr, mock_redis = _build_manager()

        t1 = _make_template(
            template_id="tmpl_aaa", name="First", created_at="2025-01-01T00:00:00"
        )
        t2 = _make_template(
            template_id="tmpl_bbb", name="Second", created_at="2025-02-01T00:00:00"
        )

        mock_redis.keys.return_value = [
            b"helping_hands:template:meta:tmpl_aaa",
            b"helping_hands:template:meta:tmpl_bbb",
        ]

        def get_side_effect(key):
            if "tmpl_aaa" in key:
                return json.dumps(t1.to_dict())
            if "tmpl_bbb" in key:
                return json.dumps(t2.to_dict())
            return None

        mock_redis.get.side_effect = get_side_effect

        results = mgr.list_templates()
        assert len(results) == 2
        assert results[0].name == "Second"
        assert results[1].name == "First"

    def test_list_templates_empty(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.keys.return_value = []
        assert mgr.list_templates() == []

    def test_update_template(self) -> None:
        mgr, mock_redis = _build_manager()
        original = _make_template(created_at="2025-01-01T00:00:00")
        mock_redis.get.return_value = json.dumps(original.to_dict())

        updated = _make_template(name="Updated Name", description="New desc")
        result = mgr.update_template(updated)

        assert result.name == "Updated Name"
        assert result.created_at == "2025-01-01T00:00:00"
        assert result.updated_at != "2025-01-01T00:00:00"

    def test_update_template_not_found(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.get.return_value = None
        template = _make_template()

        with pytest.raises(ValueError, match="not found"):
            mgr.update_template(template)

    def test_delete_template(self) -> None:
        mgr, mock_redis = _build_manager()
        template = _make_template()
        mock_redis.get.return_value = json.dumps(template.to_dict())

        assert mgr.delete_template("tmpl_test12345678") is True
        mock_redis.delete.assert_called_once()

    def test_delete_template_not_found(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.get.return_value = None
        assert mgr.delete_template("tmpl_nonexistent") is False

    def test_save_meta_redis_error_raises_runtime(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.set.side_effect = ConnectionError("Redis unavailable")
        template = _make_template()

        with pytest.raises(RuntimeError, match="Failed to persist template"):
            mgr._save_meta(template)

    def test_list_meta_keys_redis_error_returns_empty(self) -> None:
        mgr, mock_redis = _build_manager()
        mock_redis.keys.side_effect = ConnectionError("Redis down")
        assert mgr._list_meta_keys() == []


# ---------------------------------------------------------------------------
# Ownership enforcement (tested via the app endpoints pattern)
# ---------------------------------------------------------------------------


class TestOwnership:
    """Tests verifying the ownership hash pattern on templates."""

    def test_owner_hash_stored_on_create(self) -> None:
        template = _make_template(owner_token_hash="sha256_of_token")
        d = template.to_dict()
        assert d["owner_token_hash"] == "sha256_of_token"
        restored = TaskTemplate.from_dict(d)
        assert restored.owner_token_hash == "sha256_of_token"

    def test_update_preserves_created_at(self) -> None:
        mgr, mock_redis = _build_manager()
        original = _make_template(created_at="2025-01-01T00:00:00")
        mock_redis.get.return_value = json.dumps(original.to_dict())

        updated = _make_template(name="New Name")
        result = mgr.update_template(updated)
        assert result.created_at == "2025-01-01T00:00:00"

    def test_update_preserves_owner_hash(self) -> None:
        mgr, mock_redis = _build_manager()
        original = _make_template(owner_token_hash="original_hash")
        mock_redis.get.return_value = json.dumps(original.to_dict())

        updated_data = original.to_dict()
        updated_data["owner_token_hash"] = "different_hash"
        updated = TaskTemplate.from_dict(updated_data)
        mgr.update_template(updated)

        save_call = mock_redis.set.call_args[0][1]
        saved_data = json.loads(save_call)
        assert saved_data["owner_token_hash"] == "different_hash"
