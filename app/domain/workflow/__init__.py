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

# ADR-039: Document Interaction Workflow Plans
from app.domain.workflow.plan_models import (
    WorkflowPlan,
    Node,
    NodeType,
    Edge,
    EdgeKind,
    EdgeCondition,
    ConditionOperator,
    OutcomeMapping,
    ThreadOwnership,
    CircuitBreaker,
    Governance,
)
from app.domain.workflow.plan_validator import PlanValidator, PlanValidationError
from app.domain.workflow.plan_loader import PlanLoader, PlanLoadError
from app.domain.workflow.plan_registry import (
    PlanRegistry,
    PlanNotFoundError,
    get_plan_registry,
)
from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)
from app.domain.workflow.outcome_mapper import OutcomeMapper, OutcomeMapperError
from app.domain.workflow.edge_router import EdgeRouter, EdgeRoutingError
from app.domain.workflow.plan_executor import (
    PlanExecutor,
    PlanExecutorError,
    InMemoryStatePersistence as PlanStatePersistence,
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
    # ADR-039: Plan Models
    "WorkflowPlan",
    "Node",
    "NodeType",
    "Edge",
    "EdgeKind",
    "EdgeCondition",
    "ConditionOperator",
    "OutcomeMapping",
    "ThreadOwnership",
    "CircuitBreaker",
    "Governance",
    # ADR-039: Plan Loading
    "PlanValidator",
    "PlanValidationError",
    "PlanLoader",
    "PlanLoadError",
    "PlanRegistry",
    "PlanNotFoundError",
    "get_plan_registry",
    # ADR-039: Document Workflow State
    "DocumentWorkflowState",
    "DocumentWorkflowStatus",
    "NodeExecution",
    # ADR-039: Routing
    "OutcomeMapper",
    "OutcomeMapperError",
    "EdgeRouter",
    "EdgeRoutingError",
    # ADR-039: Plan Executor
    "PlanExecutor",
    "PlanExecutorError",
    "PlanStatePersistence",
]
