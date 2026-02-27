"""Unit tests for interpretation field management.

Tests the single-writer locking and confidence calculation logic.
"""

import pytest
from datetime import datetime

from app.domain.workflow.interpretation import (
    REQUIRED_FIELDS,
    calculate_confidence,
    get_missing_fields,
    create_field,
    update_field,
    can_initialize,
)


class TestCalculateConfidence:
    """Tests for confidence calculation."""
    
    def test_empty_interpretation_returns_zero(self):
        """Empty interpretation has 0% confidence."""
        assert calculate_confidence({}) == 0.0
    
    def test_one_of_three_fields_returns_one_third(self):
        """One filled field = 33% confidence."""
        interpretation = {
            "project_name": {"value": "Test Project", "source": "llm", "locked": False}
        }
        assert calculate_confidence(interpretation) == pytest.approx(1/3)
    
    def test_two_of_three_fields_returns_two_thirds(self):
        """Two filled fields = 67% confidence."""
        interpretation = {
            "project_name": {"value": "Test Project", "source": "llm", "locked": False},
            "project_type": {"value": "product", "source": "llm", "locked": False},
        }
        assert calculate_confidence(interpretation) == pytest.approx(2/3)
    
    def test_all_fields_filled_returns_one(self):
        """All filled fields = 100% confidence."""
        interpretation = {
            "project_name": {"value": "Test Project", "source": "llm", "locked": False},
            "project_type": {"value": "product", "source": "llm", "locked": False},
            "problem_statement": {"value": "Build something", "source": "llm", "locked": False},
        }
        assert calculate_confidence(interpretation) == 1.0
    
    def test_empty_value_not_counted(self):
        """Fields with empty string values are not counted."""
        interpretation = {
            "project_name": {"value": "", "source": "llm", "locked": False},
            "project_type": {"value": "product", "source": "llm", "locked": False},
        }
        assert calculate_confidence(interpretation) == pytest.approx(1/3)
    
    def test_none_value_not_counted(self):
        """Fields with None values are not counted."""
        interpretation = {
            "project_name": {"value": None, "source": "llm", "locked": False},
            "project_type": {"value": "product", "source": "llm", "locked": False},
        }
        assert calculate_confidence(interpretation) == pytest.approx(1/3)


class TestGetMissingFields:
    """Tests for missing field detection."""
    
    def test_empty_interpretation_returns_all_required(self):
        """Empty interpretation is missing all required fields."""
        missing = get_missing_fields({})
        assert set(missing) == set(REQUIRED_FIELDS)
    
    def test_partial_interpretation_returns_missing(self):
        """Partial interpretation returns only missing fields."""
        interpretation = {
            "project_name": {"value": "Test", "source": "llm", "locked": False},
        }
        missing = get_missing_fields(interpretation)
        assert "project_name" not in missing
        assert "project_type" in missing
        assert "problem_statement" in missing
    
    def test_complete_interpretation_returns_empty(self):
        """Complete interpretation has no missing fields."""
        interpretation = {
            "project_name": {"value": "Test", "source": "llm", "locked": False},
            "project_type": {"value": "product", "source": "llm", "locked": False},
            "problem_statement": {"value": "Goal", "source": "llm", "locked": False},
        }
        assert get_missing_fields(interpretation) == []
    
    def test_empty_value_counts_as_missing(self):
        """Fields with empty values are considered missing."""
        interpretation = {
            "project_name": {"value": "", "source": "llm", "locked": False},
        }
        assert "project_name" in get_missing_fields(interpretation)


class TestCreateField:
    """Tests for field creation."""
    
    def test_creates_field_with_value(self):
        """Field has correct value."""
        field = create_field("Test Value")
        assert field["value"] == "Test Value"
    
    def test_default_source_is_llm(self):
        """Default source is llm."""
        field = create_field("Test")
        assert field["source"] == "llm"
    
    def test_llm_source_not_locked(self):
        """LLM source fields are not locked."""
        field = create_field("Test", source="llm")
        assert field["locked"] is False
    
    def test_user_source_is_locked(self):
        """User source fields are auto-locked."""
        field = create_field("Test", source="user")
        assert field["locked"] is True
    
    def test_default_source_not_locked(self):
        """Default source fields are not locked."""
        field = create_field("Test", source="default")
        assert field["locked"] is False
    
    def test_has_updated_at_timestamp(self):
        """Field has updated_at timestamp."""
        field = create_field("Test")
        assert "updated_at" in field
        # Should be parseable as ISO format
        datetime.fromisoformat(field["updated_at"])


class TestUpdateField:
    """Tests for field updates with locking."""
    
    def test_updates_empty_field(self):
        """Can update a field that doesn't exist."""
        interpretation = {}
        result = update_field(interpretation, "project_name", "New Value")
        
        assert result is True
        assert interpretation["project_name"]["value"] == "New Value"
    
    def test_updates_unlocked_field(self):
        """Can update an unlocked field."""
        interpretation = {
            "project_name": {"value": "Old", "source": "llm", "locked": False}
        }
        result = update_field(interpretation, "project_name", "New")
        
        assert result is True
        assert interpretation["project_name"]["value"] == "New"
    
    def test_llm_cannot_update_locked_field(self):
        """LLM source cannot update a locked field."""
        interpretation = {
            "project_name": {"value": "User Value", "source": "user", "locked": True}
        }
        result = update_field(interpretation, "project_name", "LLM Value", source="llm")
        
        assert result is False
        assert interpretation["project_name"]["value"] == "User Value"
    
    def test_user_can_update_locked_field(self):
        """User source can update even a locked field."""
        interpretation = {
            "project_name": {"value": "Old User Value", "source": "user", "locked": True}
        }
        result = update_field(interpretation, "project_name", "New User Value", source="user")
        
        assert result is True
        assert interpretation["project_name"]["value"] == "New User Value"
    
    def test_user_update_sets_locked(self):
        """User updates auto-lock the field."""
        interpretation = {
            "project_name": {"value": "LLM Value", "source": "llm", "locked": False}
        }
        update_field(interpretation, "project_name", "User Value", source="user")
        
        assert interpretation["project_name"]["locked"] is True


class TestCanInitialize:
    """Tests for initialization check."""
    
    def test_empty_cannot_initialize(self):
        """Empty interpretation cannot initialize."""
        assert can_initialize({}) is False
    
    def test_partial_cannot_initialize(self):
        """Partial interpretation cannot initialize."""
        interpretation = {
            "project_name": {"value": "Test", "source": "llm", "locked": False},
            "project_type": {"value": "product", "source": "llm", "locked": False},
        }
        assert can_initialize(interpretation) is False
    
    def test_complete_can_initialize(self):
        """Complete interpretation can initialize."""
        interpretation = {
            "project_name": {"value": "Test", "source": "llm", "locked": False},
            "project_type": {"value": "product", "source": "llm", "locked": False},
            "problem_statement": {"value": "Goal", "source": "llm", "locked": False},
        }
        assert can_initialize(interpretation) is True