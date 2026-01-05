"""Workflow domain module.

Provides workflow definition loading, validation, and execution.
"""

from app.domain.workflow.types import (
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
)
from app.domain.workflow.scope import ScopeHierarchy
from app.domain.workflow.validator import WorkflowValidator
from app.domain.workflow.models import (
    DocumentTypeConfig,
    EntityTypeConfig,
    InputReference,
    IterationConfig,
    ScopeConfig,
    Workflow,
    WorkflowStep,
)
from app.domain.workflow.loader import WorkflowLoader, WorkflowLoadError
from app.domain.workflow.registry import WorkflowRegistry, WorkflowNotFoundError
from app.domain.workflow.step_state import (
    ClarificationQuestion,
    QAFinding,
    QAResult,
    StepState,
    StepStatus,
)
from app.domain.workflow.prompt_loader import PromptLoader, PromptNotFoundError
from app.domain.workflow.input_resolver import (
    DocumentStore,
    InputResolver,
    InputResolutionResult,
    ResolvedInput,
)
from app.domain.workflow.gates import ClarificationGate, QAGate, AcceptanceGate
from app.domain.workflow.remediation import RemediationLoop, RemediationContext
from app.domain.workflow.step_executor import StepExecutor, ExecutionResult, LLMService
from app.domain.workflow.context import WorkflowContext, ScopeInstance
from app.domain.workflow.iteration import IterationHandler, IterationInstance
from app.domain.workflow.workflow_state import (
    WorkflowState,
    WorkflowStatus,
    IterationProgress,
    AcceptanceDecision,
)
from app.domain.workflow.workflow_executor import WorkflowExecutor, WorkflowExecutionResult
from app.domain.workflow.persistence import (
    StatePersistence,
    FileStatePersistence,
    InMemoryStatePersistence,
)


__all__ = [
    # Types
    "ValidationError",
    "ValidationErrorCode", 
    "ValidationResult",
    # Scope
    "ScopeHierarchy",
    # Validator
    "WorkflowValidator",
    # Models
    "DocumentTypeConfig",
    "EntityTypeConfig",
    "InputReference",
    "IterationConfig",
    "ScopeConfig",
    "Workflow",
    "WorkflowStep",
    # Loader
    "WorkflowLoader",
    "WorkflowLoadError",
    # Registry
    "WorkflowRegistry",
    "WorkflowNotFoundError",
    # Step State
    "ClarificationQuestion",
    "QAFinding",
    "QAResult",
    "StepState",
    "StepStatus",
    # Prompt Loader
    "PromptLoader",
    "PromptNotFoundError",
    # Input Resolver
    "DocumentStore",
    "InputResolver",
    "InputResolutionResult",
    "ResolvedInput",
    # Gates
    "ClarificationGate",
    "QAGate",
    "AcceptanceGate",
    # Remediation
    "RemediationLoop",
    "RemediationContext",
    # Step Executor
    "StepExecutor",
    "ExecutionResult",
    "LLMService",
    # Context
    "WorkflowContext",
    "ScopeInstance",
    # Iteration
    "IterationHandler",
    "IterationInstance",
    # Workflow State
    "WorkflowState",
    "WorkflowStatus",
    "IterationProgress",
    "AcceptanceDecision",
    # Workflow Executor
    "WorkflowExecutor",
    "WorkflowExecutionResult",
    # Persistence
    "StatePersistence",
    "FileStatePersistence",
    "InMemoryStatePersistence",
]
