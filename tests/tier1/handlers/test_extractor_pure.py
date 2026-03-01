"""
Tests for extractor pure functions -- WS-CRAP-004.

Tests extracted pure functions: extract_jsonpath, extract_fields.
"""

import pytest

from app.api.services.mech_handlers.extractor import (
    extract_jsonpath,
    extract_fields,
)
from app.api.services.mech_handlers.base import TransformError


# =========================================================================
# extract_jsonpath
# =========================================================================


class TestExtractJsonpath:
    """Tests for extract_jsonpath pure function."""

    def test_simple_field(self):
        source = {"name": "test"}
        assert extract_jsonpath(source, "$.name") == "test"

    def test_nested_field(self):
        source = {"a": {"b": {"c": 42}}}
        assert extract_jsonpath(source, "$.a.b.c") == 42

    def test_no_match_returns_none(self):
        source = {"name": "test"}
        assert extract_jsonpath(source, "$.missing") is None

    def test_multiple_matches_returns_list(self):
        source = {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
        result = extract_jsonpath(source, "$.items[*].id")
        assert result == [1, 2, 3]

    def test_single_array_match(self):
        source = {"items": [{"id": 1}]}
        result = extract_jsonpath(source, "$.items[0].id")
        assert result == 1

    def test_invalid_jsonpath_raises(self):
        with pytest.raises(TransformError, match="Invalid JSONPath"):
            extract_jsonpath({}, "$[invalid")

    def test_root_object(self):
        source = {"name": "test"}
        result = extract_jsonpath(source, "$")
        assert result == {"name": "test"}

    def test_array_field(self):
        source = {"tags": ["a", "b", "c"]}
        result = extract_jsonpath(source, "$.tags")
        assert result == ["a", "b", "c"]


# =========================================================================
# extract_fields
# =========================================================================


class TestExtractFields:
    """Tests for extract_fields pure function."""

    def test_basic_extraction(self):
        source = {"name": "test", "value": 42}
        field_paths = [
            {"path": "$.name", "as": "project_name"},
            {"path": "$.value", "as": "count"},
        ]
        result = extract_fields(source, field_paths)
        assert result == {"project_name": "test", "count": 42}

    def test_missing_field_returns_none(self):
        source = {"name": "test"}
        field_paths = [
            {"path": "$.name", "as": "project_name"},
            {"path": "$.missing", "as": "absent"},
        ]
        result = extract_fields(source, field_paths)
        assert result["project_name"] == "test"
        assert result["absent"] is None

    def test_invalid_jsonpath_returns_none(self):
        source = {"name": "test"}
        field_paths = [
            {"path": "$[invalid", "as": "bad"},
        ]
        result = extract_fields(source, field_paths)
        assert result["bad"] is None

    def test_missing_path_or_as_skipped(self):
        source = {"name": "test"}
        field_paths = [
            {"path": "$.name"},  # missing "as"
            {"as": "result"},  # missing "path"
            {},  # both missing
        ]
        result = extract_fields(source, field_paths)
        assert result == {}

    def test_empty_field_paths(self):
        source = {"name": "test"}
        result = extract_fields(source, [])
        assert result == {}

    def test_nested_extraction(self):
        source = {
            "project": {
                "summary": "hello",
                "constraints": ["a", "b"],
            }
        }
        field_paths = [
            {"path": "$.project.summary", "as": "summary"},
            {"path": "$.project.constraints", "as": "constraints"},
        ]
        result = extract_fields(source, field_paths)
        assert result["summary"] == "hello"
        assert result["constraints"] == ["a", "b"]
