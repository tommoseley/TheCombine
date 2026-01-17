"""API router for Document Interaction Workflows (ADR-039).

Provides HTTP endpoints for:
- Starting document workflow executions
- Getting execution status
- Submitting user input for paused executions
- Handling escalation choices

This is the API layer that enables UI testing of the workflow engine.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.workflow.plan_executor import (
    PlanExecutor,
    PlanExecutorError,
)
from app.domain.workflow.pg_state_persistence import PgStatePersistence
from app.domain.workflow.plan_registry import PlanRegistry, get_plan_registry
from app.domain.workflow.plan_loader import PlanLoader
from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
from app.domain.workflow.nodes.mock_executors import create_mock_executors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document-workflows", tags=["document-workflows"])

# Load seed workflows at module initialization
_seed_workflows_loaded = False


def _load_seed_workflows():
    """Load seed workflow plans from seed/workflows/ directory."""
    global _seed_workflows_loaded
    if _seed_workflows_loaded:
        return

    registry = get_plan_registry()
    loader = PlanLoader()

    # Find seed workflows directory
    # Try multiple paths to handle different working directories
    possible_paths = [
        Path("seed/workflows"),
        Path(__file__).parent.parent.parent.parent.parent / "seed" / "workflows",
    ]

    seed_dir = None
    for path in possible_paths:
        if path.exists():
            seed_dir = path
            break

    if not seed_dir:
        logger.warning("Seed workflows directory not found")
        return

    # Load ADR-039 format workflow plans
    workflow_files = [
        "concierge_intake.v1.json",
    ]

    for filename in workflow_files:
        filepath = seed_dir / filename
        if filepath.exists():
            try:
                plan = loader.load(str(filepath))
                registry.register(plan)
                logger.info(f"Loaded workflow plan: {plan.workflow_id} ({plan.document_type})")
            except Exception as e:
                logger.error(f"Failed to load workflow {filename}: {e}")

    _seed_workflows_loaded = True
    logger.info(f"Loaded {len(registry.list_plans())} workflow plans")


# Load seed workflows when module is imported
_load_seed_workflows()


def get_executor(db: AsyncSession = Depends(get_db)) -> PlanExecutor:
    """Dependency to get the plan executor with PostgreSQL persistence."""
    return PlanExecutor(
        persistence=PgStatePersistence(db),
        plan_registry=get_plan_registry(),
        executors=create_mock_executors(),
    )


# --- Request/Response Models ---


class StartExecutionRequest(BaseModel):
    """Request to start a workflow execution."""

    document_id: str = Field(..., description="ID of the document to process")
    document_type: str = Field(
        ..., description="Type of document (determines workflow)"
    )
    initial_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional initial context data"
    )


class StartExecutionResponse(BaseModel):
    """Response after starting execution."""

    execution_id: str
    document_id: str
    document_type: str
    workflow_id: str
    status: str
    current_node_id: str


class ExecutionStatusResponse(BaseModel):
    """Response with execution status."""

    execution_id: str
    document_id: str
    document_type: str
    workflow_id: str
    status: str
    current_node_id: str
    terminal_outcome: Optional[str] = None
    gate_outcome: Optional[str] = None
    pending_user_input: bool = False
    pending_prompt: Optional[str] = None
    pending_choices: Optional[List[str]] = None
    escalation_active: bool = False
    escalation_options: List[str] = []
    step_count: int = 0
    created_at: str
    updated_at: str


class SubmitInputRequest(BaseModel):
    """Request to submit user input."""

    user_input: Optional[str] = Field(
        default=None, description="Free-text user input"
    )
    user_choice: Optional[str] = Field(
        default=None, description="Selected choice from options"
    )


class EscalationChoiceRequest(BaseModel):
    """Request to handle escalation choice."""

    choice: str = Field(..., description="Selected escalation option")


class ExecuteStepResponse(BaseModel):
    """Response after executing a step."""

    execution_id: str
    status: str
    current_node_id: str
    terminal_outcome: Optional[str] = None
    pending_user_input: bool = False
    pending_prompt: Optional[str] = None
    pending_choices: Optional[List[str]] = None
    escalation_active: bool = False
    escalation_options: List[str] = []


class WorkflowPlanSummary(BaseModel):
    """Summary of a workflow plan."""

    workflow_id: str
    name: str
    description: str
    document_type: str
    version: str


class ExecutionListItem(BaseModel):
    """Item in execution list response."""

    execution_id: str
    document_id: str
    document_type: str
    workflow_id: str
    status: str
    current_node_id: str
    terminal_outcome: Optional[str] = None
    pending_user_input: bool = False
    step_count: int = 0
    created_at: str
    updated_at: str


# --- Endpoints ---


@router.get("/executions", response_model=List[ExecutionListItem])
async def list_executions(
    status: Optional[str] = None,
    limit: int = 100,
    executor: PlanExecutor = Depends(get_executor),
) -> List[ExecutionListItem]:
    """List workflow executions.

    Query parameters:
    - status: Filter by status (running, paused, completed, failed, abandoned)
              Can be comma-separated for multiple statuses (e.g., "running,paused")
    - limit: Maximum number of results (default 100)

    Returns executions sorted by most recent first.
    """
    # Parse comma-separated status filter
    status_filter = None
    if status:
        status_filter = [s.strip() for s in status.split(",")]

    executions = await executor.list_executions(
        status_filter=status_filter,
        limit=limit,
    )

    return [ExecutionListItem(**ex) for ex in executions]


@router.post("/start", response_model=StartExecutionResponse)
async def start_execution(
    request: StartExecutionRequest,
    executor: PlanExecutor = Depends(get_executor),
) -> StartExecutionResponse:
    """Start a new workflow execution for a document.

    If an active execution already exists for this document,
    returns the existing execution instead of creating a new one.
    """
    try:
        state = await executor.start_execution(
            document_id=request.document_id,
            document_type=request.document_type,
            initial_context=request.initial_context,
        )

        return StartExecutionResponse(
            execution_id=state.execution_id,
            document_id=state.document_id,
            document_type=state.document_type,
            workflow_id=state.workflow_id,
            status=state.status.value,
            current_node_id=state.current_node_id,
        )

    except PlanExecutorError as e:
        logger.error(f"Failed to start execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: str,
    executor: PlanExecutor = Depends(get_executor),
) -> ExecutionStatusResponse:
    """Get the current status of a workflow execution."""
    status_data = await executor.get_execution_status(execution_id)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution not found: {execution_id}",
        )

    return ExecutionStatusResponse(**status_data)


@router.post("/executions/{execution_id}/step", response_model=ExecuteStepResponse)
async def execute_step(
    execution_id: str,
    executor: PlanExecutor = Depends(get_executor),
) -> ExecuteStepResponse:
    """Execute the next step in the workflow.

    This advances the workflow by executing the current node.
    If the node requires user input, the execution pauses.
    """
    try:
        state = await executor.execute_step(execution_id)

        return ExecuteStepResponse(
            execution_id=state.execution_id,
            status=state.status.value,
            current_node_id=state.current_node_id,
            terminal_outcome=state.terminal_outcome,
            pending_user_input=state.pending_user_input,
            pending_prompt=state.pending_prompt,
            pending_choices=state.pending_choices,
            escalation_active=state.escalation_active,
            escalation_options=state.escalation_options,
        )

    except PlanExecutorError as e:
        logger.error(f"Failed to execute step: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/executions/{execution_id}/run", response_model=ExecuteStepResponse)
async def run_to_completion(
    execution_id: str,
    executor: PlanExecutor = Depends(get_executor),
) -> ExecuteStepResponse:
    """Run the workflow until completion or pause.

    This repeatedly executes steps until:
    - The workflow completes (reaches terminal node)
    - The workflow pauses (requires user input)
    - The workflow fails
    """
    try:
        state = await executor.run_to_completion_or_pause(execution_id)

        return ExecuteStepResponse(
            execution_id=state.execution_id,
            status=state.status.value,
            current_node_id=state.current_node_id,
            terminal_outcome=state.terminal_outcome,
            pending_user_input=state.pending_user_input,
            pending_prompt=state.pending_prompt,
            pending_choices=state.pending_choices,
            escalation_active=state.escalation_active,
            escalation_options=state.escalation_options,
        )

    except PlanExecutorError as e:
        logger.error(f"Failed to run workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/executions/{execution_id}/input", response_model=ExecuteStepResponse)
async def submit_user_input(
    execution_id: str,
    request: SubmitInputRequest,
    executor: PlanExecutor = Depends(get_executor),
) -> ExecuteStepResponse:
    """Submit user input for a paused execution.

    This resumes a paused workflow by providing the requested input.
    """
    try:
        state = await executor.submit_user_input(
            execution_id=execution_id,
            user_input=request.user_input,
            user_choice=request.user_choice,
        )

        return ExecuteStepResponse(
            execution_id=state.execution_id,
            status=state.status.value,
            current_node_id=state.current_node_id,
            terminal_outcome=state.terminal_outcome,
            pending_user_input=state.pending_user_input,
            pending_prompt=state.pending_prompt,
            pending_choices=state.pending_choices,
            escalation_active=state.escalation_active,
            escalation_options=state.escalation_options,
        )

    except PlanExecutorError as e:
        logger.error(f"Failed to submit user input: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/executions/{execution_id}/escalation", response_model=ExecuteStepResponse
)
async def handle_escalation(
    execution_id: str,
    request: EscalationChoiceRequest,
    executor: PlanExecutor = Depends(get_executor),
) -> ExecuteStepResponse:
    """Handle an escalation choice (circuit breaker).

    When the circuit breaker trips (max retries exceeded), the user
    must choose how to proceed: retry, narrow scope, or abandon.
    """
    try:
        state = await executor.handle_escalation_choice(
            execution_id=execution_id,
            choice=request.choice,
        )

        return ExecuteStepResponse(
            execution_id=state.execution_id,
            status=state.status.value,
            current_node_id=state.current_node_id,
            terminal_outcome=state.terminal_outcome,
            pending_user_input=state.pending_user_input,
            pending_prompt=state.pending_prompt,
            pending_choices=state.pending_choices,
            escalation_active=state.escalation_active,
            escalation_options=state.escalation_options,
        )

    except PlanExecutorError as e:
        logger.error(f"Failed to handle escalation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/plans", response_model=List[WorkflowPlanSummary])
async def list_workflow_plans() -> List[WorkflowPlanSummary]:
    """List all available workflow plans."""
    registry = get_plan_registry()
    plans = registry.list_plans()

    return [
        WorkflowPlanSummary(
            workflow_id=plan.workflow_id,
            name=plan.name,
            description=plan.description,
            document_type=plan.document_type,
            version=plan.version,
        )
        for plan in plans
    ]


@router.get("/plans/{workflow_id}", response_model=WorkflowPlanSummary)
async def get_workflow_plan(workflow_id: str) -> WorkflowPlanSummary:
    """Get details of a specific workflow plan."""
    registry = get_plan_registry()
    plan = registry.get(workflow_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow plan not found: {workflow_id}",
        )

    return WorkflowPlanSummary(
        workflow_id=plan.workflow_id,
        name=plan.name,
        description=plan.description,
        document_type=plan.document_type,
        version=plan.version,
    )
