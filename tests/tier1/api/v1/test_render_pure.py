"""Tests for render model pure functions -- WS-CRAP-002.

Tests extracted pure functions: unwrap_raw_envelope, normalize_document_keys,
repair_truncated_json, resolve_display_title, inject_ia_config,
build_fallback_render_model, build_spawned_children, build_document_metadata_dict.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.api.v1.services.render_pure import (
    build_document_metadata_dict,
    build_fallback_render_model,
    build_spawned_children,
    inject_ia_config,
    unwrap_raw_envelope,
    normalize_document_keys,
    repair_truncated_json,
    resolve_display_title,
)


# =========================================================================
# unwrap_raw_envelope
# =========================================================================


class TestUnwrapRawEnvelope:
    """Tests for unwrap_raw_envelope pure function."""

    def test_non_dict_passthrough(self):
        assert unwrap_raw_envelope("hello") == "hello"
        assert unwrap_raw_envelope(42) == 42
        assert unwrap_raw_envelope(None) is None

    def test_dict_without_raw_flag(self):
        data = {"key": "value"}
        assert unwrap_raw_envelope(data) is data

    def test_dict_with_raw_false(self):
        data = {"raw": False, "content": "something"}
        assert unwrap_raw_envelope(data) is data

    def test_dict_without_content_key(self):
        data = {"raw": True, "other": "stuff"}
        assert unwrap_raw_envelope(data) is data

    def test_non_string_content(self):
        data = {"raw": True, "content": {"already": "parsed"}}
        assert unwrap_raw_envelope(data) is data

    def test_valid_json_content(self):
        data = {"raw": True, "content": '{"name": "Test"}'}
        result = unwrap_raw_envelope(data)
        assert result == {"name": "Test"}

    def test_json_with_code_fences(self):
        data = {"raw": True, "content": '```json\n{"name": "Test"}\n```'}
        result = unwrap_raw_envelope(data)
        assert result == {"name": "Test"}

    def test_json_with_code_fences_no_newline(self):
        data = {"raw": True, "content": '```{"name": "Test"}```'}
        result = unwrap_raw_envelope(data)
        assert result == {"name": "Test"}

    def test_truncated_json_repaired(self):
        data = {"raw": True, "content": '{"name": "Test", "items": [1, 2'}
        result = unwrap_raw_envelope(data)
        assert isinstance(result, dict)
        assert result["name"] == "Test"
        assert result["items"] == [1, 2]

    def test_completely_invalid_json(self):
        data = {"raw": True, "content": "not json at all"}
        result = unwrap_raw_envelope(data)
        # Returns original data when parsing fails completely
        assert result is data

    def test_whitespace_handling(self):
        data = {"raw": True, "content": '  \n{"name": "Test"}\n  '}
        result = unwrap_raw_envelope(data)
        assert result == {"name": "Test"}


# =========================================================================
# normalize_document_keys
# =========================================================================


class TestNormalizeDocumentKeys:
    """Tests for normalize_document_keys pure function."""

    def test_data_models_alias(self):
        data = {"data_models": [{"name": "User"}]}
        result = normalize_document_keys(data)
        assert result["data_model"] == [{"name": "User"}]

    def test_data_models_no_overwrite(self):
        data = {"data_models": [{"name": "Old"}], "data_model": [{"name": "Existing"}]}
        result = normalize_document_keys(data)
        assert result["data_model"] == [{"name": "Existing"}]

    def test_api_interfaces_alias(self):
        data = {"api_interfaces": [{"name": "REST"}]}
        result = normalize_document_keys(data)
        assert result["interfaces"] == [{"name": "REST"}]

    def test_api_interfaces_no_overwrite(self):
        data = {"api_interfaces": [{"name": "Old"}], "interfaces": [{"name": "Existing"}]}
        result = normalize_document_keys(data)
        assert result["interfaces"] == [{"name": "Existing"}]

    def test_risks_alias(self):
        data = {"risks": [{"name": "Risk1"}]}
        result = normalize_document_keys(data)
        assert result["identified_risks"] == [{"name": "Risk1"}]

    def test_risks_no_overwrite(self):
        data = {"risks": [{"name": "New"}], "identified_risks": [{"name": "Existing"}]}
        result = normalize_document_keys(data)
        assert result["identified_risks"] == [{"name": "Existing"}]

    def test_quality_attributes_dict_to_list(self):
        data = {
            "quality_attributes": {
                "performance": ["< 200ms response"],
                "security": ["OWASP compliant"],
            }
        }
        result = normalize_document_keys(data)
        qa = result["quality_attributes"]
        assert isinstance(qa, list)
        assert len(qa) == 2
        names = [item["name"] for item in qa]
        assert "Performance" in names
        assert "Security" in names

    def test_quality_attributes_underscore_title(self):
        data = {
            "quality_attributes": {
                "response_time": ["fast"],
            }
        }
        result = normalize_document_keys(data)
        assert result["quality_attributes"][0]["name"] == "Response Time"

    def test_quality_attributes_list_passthrough(self):
        data = {"quality_attributes": [{"name": "Perf", "acceptance_criteria": ["fast"]}]}
        result = normalize_document_keys(data)
        assert isinstance(result["quality_attributes"], list)

    def test_quality_attributes_non_list_values_skipped(self):
        data = {
            "quality_attributes": {
                "performance": ["fast"],
                "note": "not a list",
            }
        }
        result = normalize_document_keys(data)
        qa = result["quality_attributes"]
        assert len(qa) == 1

    def test_empty_dict_passthrough(self):
        data = {}
        result = normalize_document_keys(data)
        assert result == {}

    def test_mutates_input(self):
        data = {"data_models": [{"name": "User"}]}
        result = normalize_document_keys(data)
        assert result is data


# =========================================================================
# repair_truncated_json
# =========================================================================


class TestRepairTruncatedJson:
    """Tests for repair_truncated_json pure function."""

    def test_valid_json_returns_none(self):
        assert repair_truncated_json('{"name": "test"}') is None

    def test_empty_string_returns_none(self):
        assert repair_truncated_json("") is None

    def test_closes_open_brace(self):
        result = repair_truncated_json('{"name": "test"')
        assert result == {"name": "test"}

    def test_closes_open_bracket(self):
        result = repair_truncated_json('[1, 2, 3')
        assert result == [1, 2, 3]

    def test_closes_nested_structures(self):
        result = repair_truncated_json('{"items": [1, 2')
        assert result is not None
        assert result["items"] == [1, 2]

    def test_trailing_comma_stripped(self):
        result = repair_truncated_json('{"a": 1, "b": 2,')
        assert result is not None
        assert result == {"a": 1, "b": 2}

    def test_deeply_nested(self):
        result = repair_truncated_json('{"a": {"b": {"c": [1')
        assert result is not None
        assert result["a"]["b"]["c"] == [1]

    def test_string_with_brackets_ignored(self):
        result = repair_truncated_json('{"text": "hello [world"')
        assert result is not None
        assert result["text"] == "hello [world"

    def test_aggressive_trimming_fallback(self):
        # Last line is incomplete key-value, triggers aggressive trim
        result = repair_truncated_json('{"a": 1,\n"b": "incom')
        assert result is not None
        assert result["a"] == 1

    def test_completely_broken_returns_none(self):
        assert repair_truncated_json("not json {[}") is None

    def test_single_open_brace(self):
        # "{" has open brace, closes to "{}" which parses as empty dict
        assert repair_truncated_json("{") == {}

    def test_escape_in_string(self):
        result = repair_truncated_json('{"text": "say \\"hello\\""')
        assert result is not None
        assert result["text"] == 'say "hello"'

    def test_array_of_objects(self):
        result = repair_truncated_json('[{"a": 1}, {"b": 2')
        assert result is not None
        assert len(result) == 2


# =========================================================================
# resolve_display_title
# =========================================================================


class TestResolveDisplayTitle:
    """Tests for resolve_display_title pure function."""

    def test_uses_document_title(self):
        assert resolve_display_title("My Title", {}) == "My Title"

    def test_none_title_uses_data(self):
        assert resolve_display_title(None, {"title": "From Data"}) == "From Data"

    def test_underscore_title_uses_data(self):
        result = resolve_display_title("my_doc_type", {"title": "From Data"})
        assert result == "From Data"

    def test_underscore_title_humanized(self):
        result = resolve_display_title("technical_architecture", {})
        assert result == "Technical Architecture"

    def test_architecture_summary_title(self):
        data = {"architecture_summary": {"title": "Arch Title"}}
        result = resolve_display_title(None, data)
        assert result == "Arch Title"

    def test_non_dict_data(self):
        result = resolve_display_title(None, "string data")
        assert result == ""

    def test_underscore_name_humanized_with_title(self):
        result = resolve_display_title("my_document", {})
        # replace("_"," ") -> "my document", replace(" Document","") only matches capital D
        # so result is "my document".title() -> "My Document"
        assert result == "My Document"

    def test_empty_returns_empty_string(self):
        assert resolve_display_title(None, None) == ""


# =========================================================================
# inject_ia_config
# =========================================================================


class TestInjectIaConfig:
    """Tests for inject_ia_config pure function."""

    def test_injects_rendering_config(self):
        d = {}
        inject_ia_config(d, {"css": "dark"}, None)
        assert d["rendering_config"] == {"css": "dark"}
        assert "information_architecture" not in d

    def test_injects_ia_config(self):
        d = {}
        inject_ia_config(d, None, {"version": 2, "sections": []})
        assert d["information_architecture"] == {"version": 2, "sections": []}
        assert "rendering_config" not in d

    def test_injects_both(self):
        d = {}
        inject_ia_config(d, {"css": "dark"}, {"version": 2})
        assert d["rendering_config"] == {"css": "dark"}
        assert d["information_architecture"] == {"version": 2}

    def test_none_values_no_injection(self):
        d = {"existing": True}
        inject_ia_config(d, None, None)
        assert "rendering_config" not in d
        assert "information_architecture" not in d
        assert d["existing"] is True

    def test_mutates_in_place(self):
        d = {}
        inject_ia_config(d, {"k": "v"}, None)
        assert d["rendering_config"] == {"k": "v"}


# =========================================================================
# build_fallback_render_model
# =========================================================================


class TestBuildFallbackRenderModel:
    """Tests for build_fallback_render_model pure function."""

    def test_basic_structure(self):
        result = build_fallback_render_model(
            document_id="abc-123",
            doc_type_id="project_discovery",
            title="Project Discovery",
            metadata={"version": 1},
            raw_content={"summary": "test"},
        )
        assert result["render_model_version"] == "1.0"
        assert result["schema_id"] == "schema:RenderModelV1"
        assert result["document_id"] == "abc-123"
        assert result["document_type"] == "project_discovery"
        assert result["title"] == "Project Discovery"
        assert result["sections"] == []
        assert result["metadata"] == {"version": 1}
        assert result["raw_content"] == {"summary": "test"}

    def test_empty_title(self):
        result = build_fallback_render_model("id", "dt", "", {}, None)
        assert result["title"] == ""

    def test_metadata_passed_through(self):
        meta = {"fallback": True, "reason": "no_view_docdef"}
        result = build_fallback_render_model("id", "dt", "T", meta, {})
        assert result["metadata"]["fallback"] is True
        assert result["metadata"]["reason"] == "no_view_docdef"


# =========================================================================
# build_spawned_children
# =========================================================================


class TestBuildSpawnedChildren:
    """Tests for build_spawned_children pure function."""

    def _mock_child(self, instance_id, content, title, doc_type_id):
        cd = MagicMock()
        cd.instance_id = instance_id
        cd.content = content
        cd.title = title
        cd.doc_type_id = doc_type_id
        return cd

    def test_empty_list(self):
        result = build_spawned_children([])
        assert result == {"count": 0, "items": []}

    def test_single_child_with_dict_content(self):
        cd = self._mock_child(
            instance_id="epic-1",
            content={"epic_id": "E-001", "name": "Epic One"},
            title="Epic Title",
            doc_type_id="epic",
        )
        result = build_spawned_children([cd])
        assert result["count"] == 1
        item = result["items"][0]
        assert item["instance_id"] == "epic-1"
        assert item["epic_id"] == "E-001"
        assert item["name"] == "Epic One"
        assert item["title"] == "Epic Title"
        assert item["doc_type_id"] == "epic"

    def test_child_with_non_dict_content(self):
        cd = self._mock_child(
            instance_id="child-1",
            content="plain string",
            title="Fallback Title",
            doc_type_id="story",
        )
        result = build_spawned_children([cd])
        item = result["items"][0]
        assert item["epic_id"] == ""
        assert item["name"] == "Fallback Title"

    def test_child_content_missing_name_uses_title(self):
        cd = self._mock_child(
            instance_id="child-2",
            content={"epic_id": "E-002"},
            title="Title Fallback",
            doc_type_id="epic",
        )
        result = build_spawned_children([cd])
        assert result["items"][0]["name"] == "Title Fallback"

    def test_multiple_children(self):
        children = [
            self._mock_child("c1", {"epic_id": "E1", "name": "N1"}, "T1", "epic"),
            self._mock_child("c2", {"epic_id": "E2", "name": "N2"}, "T2", "epic"),
        ]
        result = build_spawned_children(children)
        assert result["count"] == 2
        assert len(result["items"]) == 2


# =========================================================================
# build_document_metadata_dict
# =========================================================================


class TestBuildDocumentMetadataDict:
    """Tests for build_document_metadata_dict pure function."""

    def test_basic_fields(self):
        result = build_document_metadata_dict(
            doc_type_id="project_discovery",
            doc_type_name="Project Discovery",
            display_id="PD-001",
            version=3,
            lifecycle_state="complete",
            created_at=None,
            updated_at=None,
            created_by="admin",
        )
        assert result["document_type"] == "project_discovery"
        assert result["document_type_name"] == "Project Discovery"
        assert result["display_id"] == "PD-001"
        assert result["version"] == 3
        assert result["lifecycle_state"] == "complete"
        assert result["created_at"] is None
        assert result["updated_at"] is None
        assert result["created_by"] == "admin"
        assert "execution_id" not in result

    def test_with_execution_id(self):
        result = build_document_metadata_dict(
            doc_type_id="dt",
            doc_type_name=None,
            display_id=None,
            version=1,
            lifecycle_state=None,
            created_at=None,
            updated_at=None,
            created_by=None,
            execution_id=42,
        )
        assert result["execution_id"] == 42

    def test_datetime_isoformat(self):
        dt = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = build_document_metadata_dict(
            doc_type_id="dt",
            doc_type_name=None,
            display_id=None,
            version=1,
            lifecycle_state=None,
            created_at=dt,
            updated_at=dt,
            created_by=None,
        )
        assert result["created_at"] == "2026-03-01T12:00:00+00:00"
        assert result["updated_at"] == "2026-03-01T12:00:00+00:00"

    def test_none_doc_type_name(self):
        result = build_document_metadata_dict(
            doc_type_id="dt",
            doc_type_name=None,
            display_id=None,
            version=1,
            lifecycle_state=None,
            created_at=None,
            updated_at=None,
            created_by=None,
        )
        assert result["document_type_name"] is None

    def test_execution_id_none_omitted(self):
        result = build_document_metadata_dict(
            doc_type_id="dt",
            doc_type_name=None,
            display_id=None,
            version=1,
            lifecycle_state=None,
            created_at=None,
            updated_at=None,
            created_by=None,
            execution_id=None,
        )
        assert "execution_id" not in result
