"""Step execution state model.

Tracks the state of a step as it progresses through execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class StepStatus(Enum):
    """Status of a step in execution."""
    
    PENDING = "pending"           # Not yet started
    EXECUTING = "executing"       # LLM call in progress
    CLARIFYING = "clarifying"     # Waiting for human clarification
    QA_CHECKING = "qa_checking"   # Running QA validation
    REMEDIATING = "remediating"   # Retrying after QA failure
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"             # Exhausted retries or unrecoverable error


@dataclass
class ClarificationQuestion:
    """A single clarification question per ADR-024."""
    
    question_id: str
    question: str
    context: Optional[str] = None
    options: Optional[List[str]] = None  # For multiple-choice
    required: bool = True


@dataclass
class QAFinding:
    """A single QA finding."""
    
    path: str           # JSON path to the issue
    message: str        # Description of the issue
    severity: str       # "error" or "warning"
    rule: Optional[str] = None  # Which rule was violated


@dataclass
class QAResult:
    """Result of QA gate check."""
    
    passed: bool
    findings: List[QAFinding] = field(default_factory=list)
    checked_at: Optional[datetime] = None
    schema_used: Optional[str] = None
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now(timezone.utc)
    
    @property
    def error_count(self) -> int:
        """Count of error-severity findings."""
        return sum(1 for f in self.findings if f.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """Count of warning-severity findings."""
        return sum(1 for f in self.findings if f.severity == "warning")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "schema_used": self.schema_used,
            "findings": [
                {
                    "path": f.path,
                    "message": f.message,
                    "severity": f.severity,
                    "rule": f.rule,
                }
                for f in self.findings
            ],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QAResult":
        """Restore from dictionary."""
        findings = [
            QAFinding(
                path=f["path"],
                message=f["message"],
                severity=f.get("severity", "error"),
                rule=f.get("rule"),
            )
            for f in data.get("findings", [])
        ]
        result = cls(
            passed=data["passed"],
            findings=findings,
            schema_used=data.get("schema_used"),
        )
        if data.get("checked_at"):
            result.checked_at = datetime.fromisoformat(data["checked_at"])
        return result


@dataclass
class StepState:
    """Execution state for a single step.
    
    Tracks progress, attempts, artifacts, and timing.
    """
    
    step_id: str
    status: StepStatus = StepStatus.PENDING
    
    # Retry tracking
    attempt: int = 0
    max_attempts: int = 3
    
    # Clarification state
    clarification_questions: Optional[List[ClarificationQuestion]] = None
    clarification_answers: Optional[Dict[str, str]] = None
    
    # Output artifact
    output_document: Optional[Dict[str, Any]] = None
    raw_llm_response: Optional[str] = None
    
    # QA state
    qa_result: Optional[QAResult] = None
    qa_history: List[QAResult] = field(default_factory=list)  # All attempts
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error tracking
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    def start(self) -> None:
        """Mark step as started."""
        self.status = StepStatus.EXECUTING
        self.started_at = datetime.now(timezone.utc)
        self.attempt += 1
    
    def request_clarification(self, questions: List[ClarificationQuestion]) -> None:
        """Transition to clarifying state."""
        self.status = StepStatus.CLARIFYING
        self.clarification_questions = questions
    
    def provide_answers(self, answers: Dict[str, str]) -> None:
        """Record clarification answers."""
        self.clarification_answers = answers
        self.status = StepStatus.EXECUTING
    
    def record_qa_result(self, result: QAResult) -> None:
        """Record QA result."""
        self.qa_result = result
        self.qa_history.append(result)
        
        if result.passed:
            self.complete()
        elif self.can_retry:
            self.status = StepStatus.REMEDIATING
        else:
            self.fail("QA failed after max attempts")
    
    def complete(self) -> None:
        """Mark step as completed successfully."""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
    
    def fail(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.error = error
        self.error_details = details
        self.completed_at = datetime.now(timezone.utc)
    
    @property
    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.attempt < self.max_attempts
    
    @property
    def is_terminal(self) -> bool:
        """Check if step is in a terminal state."""
        return self.status in (StepStatus.COMPLETED, StepStatus.FAILED)
    
    @property
    def is_waiting_for_human(self) -> bool:
        """Check if step is waiting for human input."""
        return self.status == StepStatus.CLARIFYING
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "clarification_questions": [
                {"id": q.id, "text": q.text, "context": q.context, "priority": q.priority}
                for q in self.clarification_questions
            ] if self.clarification_questions else [],
            "clarification_answers": self.clarification_answers or {},
            "qa_history": [r.to_dict() for r in self.qa_history],
            "output_document": self.output_document,
            "raw_llm_response": self.raw_llm_response,
            "error": self.error,
            "error_details": self.error_details,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepState":
        """Restore from dictionary."""
        state = cls(
            step_id=data["step_id"],
            max_attempts=data.get("max_attempts", 3),
        )
        state.status = StepStatus(data["status"])
        state.attempt = data.get("attempt", 1)
        state.clarification_questions = [
            ClarificationQuestion(
                id=q["id"], text=q["text"], 
                context=q.get("context"), priority=q.get("priority", "medium")
            )
            for q in data.get("clarification_questions", [])
        ]
        state.clarification_answers = data.get("clarification_answers", {})
        state.qa_history = [QAResult.from_dict(r) for r in data.get("qa_history", [])]
        if state.qa_history:
            state.qa_result = state.qa_history[-1]
        state.output_document = data.get("output_document")
        state.raw_llm_response = data.get("raw_llm_response")
        state.error = data.get("error")
        state.error_details = data.get("error_details")
        if data.get("started_at"):
            state.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            state.completed_at = datetime.fromisoformat(data["completed_at"])
        return state