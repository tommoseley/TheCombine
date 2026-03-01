"""
Tests for architecture_spec pure functions -- WS-CRAP-004.

Tests extracted pure functions: normalize_quality_attributes,
transform_architecture_spec.
"""

from app.domain.handlers.architecture_spec_handler import (
    normalize_quality_attributes,
    transform_architecture_spec,
)


# =========================================================================
# normalize_quality_attributes
# =========================================================================


class TestNormalizeQualityAttributes:
    """Tests for normalize_quality_attributes pure function."""

    def test_dict_passthrough(self):
        qa = {"performance": ["< 200ms response time"]}
        assert normalize_quality_attributes(qa) == qa

    def test_list_with_name_and_acceptance_criteria(self):
        qa = [
            {"name": "Performance", "acceptance_criteria": ["< 200ms"]},
            {"name": "Security", "acceptance_criteria": ["OWASP compliant"]},
        ]
        result = normalize_quality_attributes(qa)
        assert result == {
            "performance": ["< 200ms"],
            "security": ["OWASP compliant"],
        }

    def test_list_with_name_and_criteria_fallback(self):
        qa = [{"name": "Scalability", "criteria": ["1000 concurrent users"]}]
        result = normalize_quality_attributes(qa)
        assert result == {"scalability": ["1000 concurrent users"]}

    def test_list_with_spaces_in_name(self):
        qa = [{"name": "Response Time", "acceptance_criteria": ["fast"]}]
        result = normalize_quality_attributes(qa)
        assert "response_time" in result

    def test_list_item_without_name_skipped(self):
        qa = [
            {"name": "Valid", "acceptance_criteria": ["ok"]},
            {"description": "no name field"},
        ]
        result = normalize_quality_attributes(qa)
        assert len(result) == 1
        assert "valid" in result

    def test_non_dict_item_in_list_skipped(self):
        qa = [
            {"name": "Valid", "acceptance_criteria": ["ok"]},
            "just a string",
        ]
        result = normalize_quality_attributes(qa)
        assert len(result) == 1

    def test_none_returns_empty_dict(self):
        assert normalize_quality_attributes(None) == {}

    def test_string_returns_empty_dict(self):
        assert normalize_quality_attributes("some string") == {}

    def test_int_returns_empty_dict(self):
        assert normalize_quality_attributes(42) == {}

    def test_empty_list_returns_empty_dict(self):
        assert normalize_quality_attributes([]) == {}

    def test_empty_dict_passthrough(self):
        assert normalize_quality_attributes({}) == {}


# =========================================================================
# transform_architecture_spec
# =========================================================================


class TestTransformArchitectureSpec:
    """Tests for transform_architecture_spec pure function."""

    def test_ensures_array_fields_exist(self):
        data = {}
        result = transform_architecture_spec(data)
        assert result["components"] == []
        assert result["data_models"] == []
        assert result["api_interfaces"] == []
        assert result["workflows"] == []
        assert result["risks"] == []
        assert result["open_questions"] == []

    def test_legacy_data_model_migration(self):
        data = {"data_model": [{"name": "User"}]}
        result = transform_architecture_spec(data)
        assert result["data_models"] == [{"name": "User"}]
        assert "data_model" not in result

    def test_legacy_interfaces_migration(self):
        data = {"interfaces": [{"name": "REST API"}]}
        result = transform_architecture_spec(data)
        assert result["api_interfaces"] == [{"name": "REST API"}]
        assert "interfaces" not in result

    def test_no_migration_if_canonical_exists(self):
        data = {
            "data_model": [{"name": "Old"}],
            "data_models": [{"name": "New"}],
        }
        result = transform_architecture_spec(data)
        # data_models already existed, so data_model is NOT migrated
        assert result["data_models"] == [{"name": "New"}]

    def test_quality_attributes_normalized(self):
        data = {
            "quality_attributes": [
                {"name": "Performance", "acceptance_criteria": ["fast"]},
            ]
        }
        result = transform_architecture_spec(data)
        assert result["quality_attributes"] == {"performance": ["fast"]}

    def test_missing_architecture_summary_added(self):
        data = {}
        result = transform_architecture_spec(data)
        assert result["architecture_summary"] == {}

    def test_string_architecture_summary_converted(self):
        data = {"architecture_summary": "A microservices architecture"}
        result = transform_architecture_spec(data)
        assert result["architecture_summary"] == {
            "title": "Architecture Overview",
            "refined_description": "A microservices architecture",
        }

    def test_dict_architecture_summary_preserved(self):
        data = {
            "architecture_summary": {
                "title": "My Arch",
                "refined_description": "Custom description",
            }
        }
        result = transform_architecture_spec(data)
        assert result["architecture_summary"]["title"] == "My Arch"

    def test_existing_array_fields_preserved(self):
        data = {
            "components": [{"name": "API"}],
            "data_models": [{"name": "User"}],
        }
        result = transform_architecture_spec(data)
        assert result["components"] == [{"name": "API"}]
        assert result["data_models"] == [{"name": "User"}]

    def test_mutates_input(self):
        """transform_architecture_spec mutates input by design."""
        data = {}
        result = transform_architecture_spec(data)
        assert result is data
