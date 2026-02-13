"""Tests for step state model."""

import pytest
from datetime import datetime

from app.domain.workflow.step_state import (
    StepStatus,
    StepState,
    ClarificationQuestion,
    QAFinding,
    QAResult,
)


class TestStepStatus:
    """Tests for StepStatus enum."""
    
    def test_all_statuses_defined(self):
        """All expected statuses exist."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.EXECUTING.value == "executing"
        assert StepStatus.CLARIFYING.value == "clarifying"
        assert StepStatus.QA_CHECKING.value == "qa_checking"
        assert StepStatus.REMEDIATING.value == "remediating"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"


class TestQAResult:
    """Tests for QAResult."""
    
    def test_error_count(self):
        """error_count counts error-severity findings."""
        result = QAResult(
            passed=False,
            findings=[
                QAFinding(path="a", message="err1", severity="error"),
                QAFinding(path="b", message="warn1", severity="warning"),
                QAFinding(path="c", message="err2", severity="error"),
            ],
        )
        
        assert result.error_count == 2
        assert result.warning_count == 1
    
    def test_passed_result(self):
        """Passed result has no errors."""
        result = QAResult(passed=True, findings=[])
        
        assert result.passed
        assert result.error_count == 0


class TestStepState:
    """Tests for StepState."""
    
    def test_initial_state(self):
        """New state starts pending."""
        state = StepState(step_id="test_step")
        
        assert state.status == StepStatus.PENDING
        assert state.attempt == 0
        assert state.can_retry is True
        assert state.is_terminal is False
    
    def test_start_transitions_to_executing(self):
        """start() transitions to executing."""
        state = StepState(step_id="test_step")
        
        state.start()
        
        assert state.status == StepStatus.EXECUTING
        assert state.attempt == 1
        assert state.started_at is not None
    
    def test_request_clarification(self):
        """request_clarification() transitions to clarifying."""
        state = StepState(step_id="test_step")
        state.start()
        
        questions = [
            ClarificationQuestion(question_id="q1", question="What scope?")
        ]
        state.request_clarification(questions)
        
        assert state.status == StepStatus.CLARIFYING
        assert state.clarification_questions == questions
        assert state.is_waiting_for_human is True
    
    def test_provide_answers(self):
        """provide_answers() stores answers and resumes execution."""
        state = StepState(step_id="test_step")
        state.start()
        state.request_clarification([
            ClarificationQuestion(question_id="q1", question="What?")
        ])
        
        state.provide_answers({"q1": "Answer"})
        
        assert state.status == StepStatus.EXECUTING
        assert state.clarification_answers == {"q1": "Answer"}
    
    def test_qa_passed_completes(self):
        """Passing QA completes the step."""
        state = StepState(step_id="test_step")
        state.start()
        
        state.record_qa_result(QAResult(passed=True))
        
        assert state.status == StepStatus.COMPLETED
        assert state.is_terminal is True
        assert state.completed_at is not None
    
    def test_qa_failed_remediates_if_can_retry(self):
        """Failing QA enters remediation if retries available."""
        state = StepState(step_id="test_step", max_attempts=3)
        state.start()  # attempt 1
        
        state.record_qa_result(QAResult(
            passed=False,
            findings=[QAFinding(path="x", message="bad", severity="error")]
        ))
        
        assert state.status == StepStatus.REMEDIATING
        assert state.can_retry is True
    
    def test_qa_failed_exhausted_fails(self):
        """Failing QA after max attempts fails step."""
        state = StepState(step_id="test_step", max_attempts=1)
        state.start()  # attempt 1
        
        state.record_qa_result(QAResult(
            passed=False,
            findings=[QAFinding(path="x", message="bad", severity="error")]
        ))
        
        assert state.status == StepStatus.FAILED
        assert state.is_terminal is True
        assert "max attempts" in state.error
    
    def test_qa_history_tracks_all_attempts(self):
        """qa_history accumulates all QA results."""
        state = StepState(step_id="test_step", max_attempts=3)
        
        state.start()
        state.record_qa_result(QAResult(passed=False, findings=[
            QAFinding(path="a", message="err", severity="error")
        ]))
        
        state.start()  # attempt 2
        state.record_qa_result(QAResult(passed=True))
        
        assert len(state.qa_history) == 2
        assert state.qa_history[0].passed is False
        assert state.qa_history[1].passed is True
    
    def test_fail_sets_error(self):
        """fail() sets error message and details."""
        state = StepState(step_id="test_step")
        state.start()
        
        state.fail("Something broke", details={"code": 500})
        
        assert state.status == StepStatus.FAILED
        assert state.error == "Something broke"
        assert state.error_details == {"code": 500}
    
    def test_to_dict_serialization(self):
        """to_dict() produces serializable dict."""
        state = StepState(step_id="test_step")
        state.start()
        state.complete()
        
        d = state.to_dict()
        
        assert d["step_id"] == "test_step"
        assert d["status"] == "completed"
        assert d["attempt"] == 1
        assert d["started_at"] is not None
        assert d["completed_at"] is not None
        # duration_seconds removed from to_dict in favor of full serialization
    
    def test_duration_calculation(self):
        """duration_seconds calculates elapsed time."""
        state = StepState(step_id="test_step")
        state.started_at = datetime(2026, 1, 1, 12, 0, 0)
        state.completed_at = datetime(2026, 1, 1, 12, 0, 30)
        
        assert state.duration_seconds == 30.0
    
    def test_duration_none_if_not_complete(self):
        """duration_seconds is None if not completed."""
        state = StepState(step_id="test_step")
        state.start()
        
        assert state.duration_seconds is None
