"""Execution-related API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StartWorkflowRequest(BaseModel):
    """Request to start a new workflow execution."""
    
    project_id: str = Field(..., description="Unique project identifier")
    initial_context: Optional[Dict[str, Any]] = Field(
        None, description="Initial documents/data to seed the workflow"
    )
    
    model_config = {"json_schema_extra": {
        "example": {
            "project_id": "proj_12345",
            "initial_context": {"user_input": "Build a todo app"}
        }
    }}


class ClarificationQuestionResponse(BaseModel):
    """A clarification question requiring user answer."""
    
    id: str
    text: str
    context: Optional[str] = None
    priority: str = "medium"


class ClarificationPending(BaseModel):
    """Info about pending clarification."""
    
    step_id: str
    questions: List[ClarificationQuestionResponse]


class AcceptancePending(BaseModel):
    """Info about pending acceptance decision."""
    
    doc_type: str
    scope_id: Optional[str] = None
    document_preview: Optional[Dict[str, Any]] = None


class StepProgress(BaseModel):
    """Progress info for a step."""
    
    step_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt: int = 1


class IterationProgressResponse(BaseModel):
    """Progress through an iteration."""
    
    step_id: str
    total: int
    completed: int
    current_index: int


class ExecutionResponse(BaseModel):
    """Full execution status response."""
    
    execution_id: str
    workflow_id: str
    project_id: str
    status: str = Field(..., description="pending|running|waiting_acceptance|waiting_clarification|completed|failed|cancelled")
    current_step_id: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    step_progress: Dict[str, StepProgress] = Field(default_factory=dict)
    iteration_progress: Dict[str, IterationProgressResponse] = Field(default_factory=dict)
    pending_acceptance: Optional[AcceptancePending] = None
    pending_clarification: Optional[ClarificationPending] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    model_config = {"json_schema_extra": {
        "example": {
            "execution_id": "exec_abc123",
            "workflow_id": "software_product_development",
            "project_id": "proj_12345",
            "status": "running",
            "current_step_id": "discovery",
            "completed_steps": [],
            "step_progress": {},
            "iteration_progress": {},
            "pending_acceptance": None,
            "pending_clarification": None,
            "started_at": "2026-01-03T12:00:00Z",
            "completed_at": None,
            "error": None
        }
    }}


class ExecutionSummary(BaseModel):
    """Brief execution info for list responses."""
    
    execution_id: str
    workflow_id: str
    project_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExecutionListResponse(BaseModel):
    """Response for list executions endpoint."""
    
    executions: List[ExecutionSummary]
    total: int


class AcceptanceRequest(BaseModel):
    """Request to submit acceptance decision."""
    
    accepted: bool = Field(..., description="Whether to accept or reject")
    comment: Optional[str] = Field(None, description="Optional comment explaining decision")
    
    model_config = {"json_schema_extra": {
        "example": {
            "accepted": True,
            "comment": "Looks good, approved"
        }
    }}


class ClarificationRequest(BaseModel):
    """Request to submit clarification answers."""
    
    answers: Dict[str, str] = Field(..., description="Map of question_id to answer text")
    
    model_config = {"json_schema_extra": {
        "example": {
            "answers": {
                "q1": "The target users are small business owners",
                "q2": "Budget is $50,000"
            }
        }
    }}


class ExecutionEvent(BaseModel):
    """WebSocket event for execution updates."""
    
    event_type: str = Field(..., description="step_started|step_completed|waiting_acceptance|waiting_clarification|completed|failed")
    execution_id: str
    step_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
