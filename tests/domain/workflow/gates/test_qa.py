"""Tests for QA gate."""

import json
import pytest
import uuid

from app.domain.workflow.gates.qa import QAGate
from app.domain.workflow.step_state import QAResult, QAFinding


class TestQAGate:
    """Tests for QAGate."""
    
    @pytest.fixture
    def gate(self):
        """Create a gate instance."""
        return QAGate()
    
    def test_check_valid_dict_passes(self, gate):
        """Valid dict passes structural checks."""
        output = {"key": "value", "nested": {"a": 1}}
        
        result = gate.check(output, doc_type="unknown_type", strict=False)
        
        assert result.passed is True
        assert result.error_count == 0
    
    def test_check_valid_list_passes(self, gate):
        """Valid list passes structural checks."""
        output = [{"item": 1}, {"item": 2}]
        
        result = gate.check(output, doc_type="unknown_type", strict=False)
        
        assert result.passed is True
    
    def test_check_json_string_parsed(self, gate):
        """JSON string is parsed before validation."""
        output = '{"key": "value"}'
        
        result = gate.check(output, doc_type="unknown_type", strict=False)
        
        assert result.passed is True
    
    def test_check_invalid_json_fails(self, gate):
        """Invalid JSON string fails."""
        output = "not valid json {"
        
        result = gate.check(output, doc_type="unknown_type", strict=False)
        
        assert result.passed is False
        assert any("Invalid JSON" in f.message for f in result.findings)
    
    def test_check_null_fails(self, gate):
        """Null output fails."""
        result = gate.check(None, doc_type="unknown_type", strict=False)
        
        assert result.passed is False
        assert any("null" in f.message.lower() for f in result.findings)
    
    def test_check_empty_dict_warns(self, gate):
        """Empty dict produces warning (not error)."""
        result = gate.check({}, doc_type="unknown_type", strict=False)
        
        assert result.passed is True  # Warnings don't fail
        assert result.warning_count == 1
        assert any("empty" in f.message.lower() for f in result.findings)
    
    def test_check_empty_list_warns(self, gate):
        """Empty list produces warning."""
        result = gate.check([], doc_type="unknown_type", strict=False)
        
        assert result.passed is True
        assert result.warning_count == 1
    
    def test_check_primitive_fails(self, gate):
        """Primitive values (not dict/list) fail."""
        result = gate.check("just a string", doc_type="unknown_type", strict=False)
        
        # String is parsed as JSON, fails if not valid JSON object
        assert result.passed is False
    
    def test_check_with_schema_validates(self, gate):
        """Document with registered schema is validated."""
        # Use the clarification schema which exists
        valid_clarification = {
            "schema_version": "clarification_question_set.v1",
            "mode": "questions_only",
            "correlation_id": str(uuid.uuid4()),
            "question_set_kind": "discovery",
            "questions": [
                {
                    "id": "Q01",
                    "text": "What is the goal?",
                    "intent": "Understanding",
                    "priority": "must",
                    "answer_type": "free_text",
                    "required": True,
                }
            ],
            "qa": {
                "non_question_line_count": 0,
                "declarative_sentence_count": 0,
                "answer_leadin_count": 0,
                "all_questions_end_with_qmark": True,
            }
        }
        
        result = gate.check(valid_clarification, doc_type="clarification_questions")
        
        assert result.passed is True
        assert result.schema_used == "clarification_question_set.v1.json"
    
    def test_check_schema_violation_fails(self, gate):
        """Schema violation produces error."""
        invalid_clarification = {
            "schema_version": "clarification_question_set.v1",
            # Missing required fields
        }
        
        result = gate.check(invalid_clarification, doc_type="clarification_questions")
        
        assert result.passed is False
        assert result.error_count > 0
    
    def test_register_schema(self, gate):
        """Custom schema can be registered."""
        gate.register_schema("custom_doc", "custom_schema.json")
        
        assert gate.has_schema("custom_doc")
        assert "custom_doc" in gate.list_schemas()
    
    def test_has_schema_false_for_unknown(self, gate):
        """has_schema returns False for unregistered types."""
        assert gate.has_schema("completely_unknown") is False
    
    def test_result_to_dict(self, gate):
        """QAResult serializes to dict."""
        result = gate.check({"key": "value"}, doc_type="test", strict=False)
        
        d = result.to_dict()
        
        assert "passed" in d
        assert "error_count" in d
        assert "findings" in d
        assert isinstance(d["findings"], list)


class TestQAFinding:
    """Tests for QAFinding."""
    
    def test_finding_fields(self):
        """Finding has all expected fields."""
        finding = QAFinding(
            path="$.items[0]",
            message="Missing required field",
            severity="error",
            rule="required",
        )
        
        assert finding.path == "$.items[0]"
        assert finding.message == "Missing required field"
        assert finding.severity == "error"
        assert finding.rule == "required"


class TestQAResult:
    """Tests for QAResult."""
    
    def test_error_count(self):
        """error_count counts errors correctly."""
        result = QAResult(
            passed=False,
            findings=[
                QAFinding(path="a", message="err1", severity="error"),
                QAFinding(path="b", message="warn", severity="warning"),
                QAFinding(path="c", message="err2", severity="error"),
            ],
        )
        
        assert result.error_count == 2
        assert result.warning_count == 1
    
    def test_checked_at_auto_set(self):
        """checked_at is automatically set."""
        result = QAResult(passed=True)
        
        assert result.checked_at is not None