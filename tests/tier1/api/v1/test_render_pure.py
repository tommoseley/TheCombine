"""Tests for render model pure functions -- WS-CRAP-002.

Tests extracted pure functions: unwrap_raw_envelope, normalize_document_keys,
repair_truncated_json, resolve_display_title.
"""

from app.api.v1.services.render_pure import (
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
