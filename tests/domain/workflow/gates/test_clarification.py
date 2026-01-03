"""Tests for clarification gate."""

import json
import pytest
import uuid

from app.domain.workflow.gates.clarification import (
    ClarificationGate,
    ClarificationQuestion,
    ClarificationResult,
)


class TestClarificationGate:
    """Tests for ClarificationGate."""
    
    @pytest.fixture
    def gate(self):
        """Create a gate instance."""
        return ClarificationGate()
    
    @pytest.fixture
    def valid_question_set(self):
        """Create a valid clarification question set."""
        return {
            "schema_version": "clarification_question_set.v1",
            "mode": "questions_only",
            "correlation_id": str(uuid.uuid4()),
            "question_set_kind": "discovery",
            "questions": [
                {
                    "id": "Q01",
                    "text": "What is the primary goal of this project?",
                    "intent": "Understanding the core objective",
                    "priority": "must",
                    "answer_type": "free_text",
                    "required": True,
                    "blocking": True,
                }
            ],
            "qa": {
                "non_question_line_count": 0,
                "declarative_sentence_count": 0,
                "answer_leadin_count": 0,
                "all_questions_end_with_qmark": True,
            }
        }
    
    def test_check_no_clarification(self, gate):
        """Normal response without clarification returns needs_clarification=False."""
        response = "Here is a regular document with no questions."
        
        result = gate.check(response)
        
        assert result.needs_clarification is False
        assert len(result.questions) == 0
    
    def test_check_detects_clarification(self, gate, valid_question_set):
        """Response with valid question set detected."""
        response = json.dumps(valid_question_set)
        
        result = gate.check(response)
        
        assert result.needs_clarification is True
        assert len(result.questions) == 1
        assert result.questions[0].id == "Q01"
    
    def test_check_extracts_from_markdown(self, gate, valid_question_set):
        """Question set in markdown code block extracted."""
        response = f"```json\n{json.dumps(valid_question_set)}\n```"
        
        result = gate.check(response)
        
        assert result.needs_clarification is True
        assert len(result.questions) == 1
    
    def test_check_invalid_schema_reports_errors(self, gate):
        """Invalid question set reports validation errors."""
        invalid = {
            "schema_version": "clarification_question_set.v1",
            "mode": "questions_only",
            # Missing required fields
        }
        response = json.dumps(invalid)
        
        result = gate.check(response)
        
        assert result.needs_clarification is True  # Tried to clarify
        assert len(result.questions) == 0  # But failed
        assert len(result.validation_errors) > 0
    
    def test_check_parses_all_question_fields(self, gate):
        """All question fields are parsed correctly."""
        question_set = {
            "schema_version": "clarification_question_set.v1",
            "mode": "questions_only",
            "correlation_id": str(uuid.uuid4()),
            "question_set_kind": "discovery",
            "questions": [
                {
                    "id": "CHOICE_Q",
                    "text": "Which option do you prefer?",
                    "intent": "Determining preference",
                    "priority": "should",
                    "answer_type": "single_choice",
                    "required": False,
                    "blocking": False,
                    "choices": [
                        {"value": "a", "label": "Option A"},
                        {"value": "b", "label": "Option B"},
                    ],
                    "default": "a",
                }
            ],
            "qa": {
                "non_question_line_count": 0,
                "declarative_sentence_count": 0,
                "answer_leadin_count": 0,
                "all_questions_end_with_qmark": True,
            }
        }
        
        result = gate.check(json.dumps(question_set))
        
        assert result.needs_clarification is True
        q = result.questions[0]
        assert q.id == "CHOICE_Q"
        assert q.priority == "should"
        assert q.answer_type == "single_choice"
        assert q.required is False
        assert q.blocking is False
        assert len(q.choices) == 2
        assert q.default == "a"
    
    def test_validate_questions_only_passes_valid(self, gate, valid_question_set):
        """Valid questions-only response passes."""
        violations = gate.validate_questions_only(valid_question_set)
        
        assert len(violations) == 0
    
    def test_validate_questions_only_catches_wrong_mode(self, gate, valid_question_set):
        """Wrong mode is caught."""
        valid_question_set["mode"] = "mixed"
        
        violations = gate.validate_questions_only(valid_question_set)
        
        assert any("Mode must be" in v for v in violations)
    
    def test_validate_questions_only_catches_declarative(self, gate, valid_question_set):
        """Declarative sentences are caught."""
        valid_question_set["qa"]["declarative_sentence_count"] = 3
        
        violations = gate.validate_questions_only(valid_question_set)
        
        assert any("declarative_sentence_count" in v for v in violations)
    
    def test_validate_questions_only_catches_bad_qmark(self, gate, valid_question_set):
        """Questions not ending with ? are caught."""
        valid_question_set["qa"]["all_questions_end_with_qmark"] = False
        
        violations = gate.validate_questions_only(valid_question_set)
        
        assert any("all_questions_end_with_qmark" in v for v in violations)
    
    def test_get_blocking_questions(self, gate):
        """get_blocking_questions filters correctly."""
        questions = [
            ClarificationQuestion(
                id="Q1", text="?", intent="", priority="must",
                answer_type="free_text", required=True, blocking=True
            ),
            ClarificationQuestion(
                id="Q2", text="?", intent="", priority="could",
                answer_type="free_text", required=False, blocking=False
            ),
            ClarificationQuestion(
                id="Q3", text="?", intent="", priority="should",
                answer_type="free_text", required=True, blocking=True
            ),
        ]
        
        blocking = gate.get_blocking_questions(questions)
        
        assert len(blocking) == 2
        assert all(q.blocking and q.required for q in blocking)