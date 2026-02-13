"""Tests for output parsing and validation."""

import pytest
import json

from app.llm.output_parser import (
    OutputValidator,
    ValidationResult,
    ValidationError,
    ClarificationDetector,
    ClarificationResult,
    ClarificationQuestion,
    OutputParser,
)


class TestOutputValidator:
    """Tests for OutputValidator."""
    
    def test_validate_passes_valid_data(self):
        """Valid data passes validation."""
        validator = OutputValidator()
        data = {"name": "Test", "value": 42}
        
        result = validator.validate(data)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_required_fields_present(self):
        """Required fields present passes."""
        validator = OutputValidator()
        data = {"name": "Test", "value": 42}
        
        result = validator.validate(data, required_fields=["name", "value"])
        
        assert result.valid is True
    
    def test_validate_required_fields_missing(self):
        """Missing required field fails."""
        validator = OutputValidator()
        data = {"name": "Test"}
        
        result = validator.validate(data, required_fields=["name", "value"])
        
        assert result.valid is False
        assert any("value" in e.field for e in result.errors)
    
    def test_validate_required_field_null(self):
        """Null required field fails."""
        validator = OutputValidator()
        data = {"name": None}
        
        result = validator.validate(data, required_fields=["name"])
        
        assert result.valid is False
    
    def test_validate_required_field_empty_string(self):
        """Empty string required field fails."""
        validator = OutputValidator()
        data = {"name": "   "}
        
        result = validator.validate(data, required_fields=["name"])
        
        assert result.valid is False
    
    def test_validate_schema_type_string(self):
        """Validates string type."""
        validator = OutputValidator()
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}}
        }
        
        # Valid
        result = validator.validate({"name": "Test"}, schema=schema)
        assert result.valid is True
        
        # Invalid
        result = validator.validate({"name": 123}, schema=schema)
        assert result.valid is False
    
    def test_validate_schema_type_integer(self):
        """Validates integer type."""
        validator = OutputValidator()
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}}
        }
        
        result = validator.validate({"count": "not a number"}, schema=schema)
        assert result.valid is False
    
    def test_validate_schema_required(self):
        """Validates schema required fields."""
        validator = OutputValidator()
        schema = {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            }
        }
        
        result = validator.validate({"id": 1}, schema=schema)
        assert result.valid is False
        assert any("name" in e.message for e in result.errors)
    
    def test_validate_string_min_length(self):
        """Validates string minLength."""
        validator = OutputValidator()
        schema = {
            "type": "object",
            "properties": {"code": {"type": "string", "minLength": 3}}
        }
        
        result = validator.validate({"code": "AB"}, schema=schema)
        assert result.valid is False
    
    def test_validate_array_min_items(self):
        """Validates array minItems."""
        validator = OutputValidator()
        schema = {
            "type": "object",
            "properties": {"items": {"type": "array", "minItems": 2}}
        }
        
        result = validator.validate({"items": [1]}, schema=schema)
        assert result.valid is False


class TestClarificationDetector:
    """Tests for ClarificationDetector."""
    
    def test_no_clarification_needed(self):
        """Normal response doesn't need clarification."""
        detector = ClarificationDetector()
        
        result = detector.detect('{"status": "complete", "data": [1, 2, 3]}')
        
        assert result.needs_clarification is False
        assert len(result.questions) == 0
    
    def test_detects_need_more_information(self):
        """Detects 'need more information' pattern."""
        detector = ClarificationDetector()
        
        result = detector.detect("I need more information about the requirements.")
        
        assert result.needs_clarification is True
    
    def test_detects_clarify_request(self):
        """Detects 'could you clarify' pattern."""
        detector = ClarificationDetector()
        
        result = detector.detect("Could you please clarify the scope?")
        
        assert result.needs_clarification is True
    
    def test_detects_before_proceed(self):
        """Detects 'before I can proceed' pattern."""
        detector = ClarificationDetector()
        
        result = detector.detect("Before I can proceed, I need to know the budget.")
        
        assert result.needs_clarification is True
    
    def test_detects_unclear(self):
        """Detects 'unclear' pattern."""
        detector = ClarificationDetector()
        
        result = detector.detect("The requirements are unclear.")
        
        assert result.needs_clarification is True
    
    def test_extracts_questions(self):
        """Extracts questions from response."""
        detector = ClarificationDetector()
        text = """I need some clarification:
1. What is the target audience?
2. What is the budget?
"""
        
        result = detector.detect(text)
        
        assert result.needs_clarification is True
        assert len(result.questions) >= 1


class TestOutputParser:
    """Tests for combined OutputParser."""
    
    def test_parse_valid_json(self):
        """Parses valid JSON successfully."""
        parser = OutputParser()
        response = '{"name": "Test", "value": 42}'
        
        parse_result, validation, clarification = parser.parse(response)
        
        assert parse_result.success is True
        assert parse_result.data["name"] == "Test"
        assert validation.valid is True
    
    def test_parse_with_required_fields(self):
        """Validates required fields."""
        parser = OutputParser()
        response = '{"name": "Test"}'
        
        parse_result, validation, _ = parser.parse(
            response, 
            required_fields=["name", "value"]
        )
        
        assert parse_result.success is True
        assert validation.valid is False
    
    def test_parse_clarification_stops_early(self):
        """Clarification needed stops parsing."""
        parser = OutputParser()
        response = "I need more information. What is the scope?"
        
        parse_result, validation, clarification = parser.parse(response)
        
        assert parse_result.success is False
        assert clarification.needs_clarification is True
    
    def test_parse_skip_clarification_check(self):
        """Can skip clarification check."""
        parser = OutputParser()
        response = '{"question": "What is this?"}'
        
        parse_result, validation, clarification = parser.parse(
            response,
            check_clarification=False,
        )
        
        assert parse_result.success is True
        assert clarification is None
    
    def test_parse_invalid_json(self):
        """Handles invalid JSON."""
        parser = OutputParser()
        response = "This is not JSON at all."
        
        parse_result, validation, _ = parser.parse(
            response,
            check_clarification=False,
        )
        
        assert parse_result.success is False
        assert validation.valid is False
    
    def test_parse_with_schema(self):
        """Validates against schema."""
        parser = OutputParser()
        schema = {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "integer"}}
        }
        response = '{"id": "not-an-int"}'
        
        parse_result, validation, _ = parser.parse(
            response,
            schema=schema,
            check_clarification=False,
        )
        
        assert parse_result.success is True  # JSON valid
        assert validation.valid is False  # Schema invalid
