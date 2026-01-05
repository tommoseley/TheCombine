"""API schema models."""

from app.api.v1.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    HealthResponse,
)
from app.api.v1.schemas.workflow import (
    ScopeResponse,
    DocumentTypeResponse,
    EntityTypeResponse,
    StepSummary,
    WorkflowSummary,
    WorkflowDetail,
    WorkflowListResponse,
)
from app.api.v1.schemas.execution import (
    StartWorkflowRequest,
    ClarificationQuestionResponse,
    ClarificationPending,
    AcceptancePending,
    StepProgress,
    IterationProgressResponse,
    ExecutionResponse,
    ExecutionSummary,
    ExecutionListResponse,
    AcceptanceRequest,
    ClarificationRequest,
    ExecutionEvent,
)


__all__ = [
    # Common
    "ErrorResponse",
    "PaginatedResponse",
    "HealthResponse",
    # Workflow
    "ScopeResponse",
    "DocumentTypeResponse",
    "EntityTypeResponse",
    "StepSummary",
    "WorkflowSummary",
    "WorkflowDetail",
    "WorkflowListResponse",
    # Execution
    "StartWorkflowRequest",
    "ClarificationQuestionResponse",
    "ClarificationPending",
    "AcceptancePending",
    "StepProgress",
    "IterationProgressResponse",
    "ExecutionResponse",
    "ExecutionSummary",
    "ExecutionListResponse",
    "AcceptanceRequest",
    "ClarificationRequest",
    "ExecutionEvent",
]
