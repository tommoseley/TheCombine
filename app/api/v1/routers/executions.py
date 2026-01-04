"""Execution management endpoints."""

from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.dependencies import (
    get_workflow_registry,
    get_persistence,
)
from app.api.v1.schemas import (
    AcceptanceRequest,
    ClarificationRequest,
    StartWorkflowRequest,
    ExecutionResponse,
    ExecutionSummary,
    ExecutionListResponse,
    StepProgress,
    IterationProgressResponse,
    AcceptancePending,
    ClarificationPending,
    ErrorResponse,
)
from app.api.v1.services.execution_service import (
    ExecutionService,
    ExecutionNotFoundError,
    InvalidExecutionStateError,
)
from app.domain.workflow import (
    WorkflowRegistry,
    WorkflowNotFoundError,
    WorkflowStatus,
    StatePersistence,
    InMemoryStatePersistence,
)


router = APIRouter(tags=["executions"])


# Singleton execution service - stored at module level
_execution_service: Optional[ExecutionService] = None


def get_execution_service(
    persistence: StatePersistence = Depends(get_persistence),
) -> ExecutionService:
    """Get shared execution service instance."""
    global _execution_service
    if _execution_service is None:
        _execution_service = ExecutionService(persistence=persistence)
    return _execution_service


def reset_execution_service() -> None:
    """Reset execution service (for testing)."""
    global _execution_service
    _execution_service = None


def _state_to_response(execution_id: str, state) -> ExecutionResponse:
    """Convert WorkflowState to ExecutionResponse."""
    # Build step progress dict
    step_progress = {}
    for step_id, step_state in state.step_states.items():
        step_progress[step_id] = StepProgress(
            step_id=step_id,
            status=step_state.status.value if hasattr(step_state.status, 'value') else str(step_state.status),
            started_at=getattr(step_state, 'started_at', None),
            completed_at=getattr(step_state, 'completed_at', None),
            attempt=getattr(step_state, 'attempt', 1),
        )
    
    # Build iteration progress dict
    iteration_progress = {}
    for step_id, iter_prog in state.iteration_progress.items():
        iteration_progress[step_id] = IterationProgressResponse(
            step_id=step_id,
            total=iter_prog.total,
            completed=iter_prog.completed,
            current_index=iter_prog.current_index,
        )
    
    # Build pending acceptance info
    pending_acceptance = None
    if state.pending_acceptance:
        pending_acceptance = AcceptancePending(
            doc_type=state.pending_acceptance,
            scope_id=getattr(state, 'pending_acceptance_scope_id', None),
        )
    
    # Build pending clarification info
    pending_clarification = None
    if hasattr(state, 'pending_clarification') and state.pending_clarification:
        pending_clarification = ClarificationPending(
            step_id=state.pending_clarification.get('step_id', ''),
            questions=[],
        )
    
    return ExecutionResponse(
        execution_id=execution_id,
        workflow_id=state.workflow_id,
        project_id=state.project_id,
        status=state.status.value if hasattr(state.status, 'value') else str(state.status),
        current_step_id=state.current_step_id,
        completed_steps=list(state.completed_steps),
        step_progress=step_progress,
        iteration_progress=iteration_progress,
        pending_acceptance=pending_acceptance,
        pending_clarification=pending_clarification,
        started_at=getattr(state, 'started_at', None),
        completed_at=getattr(state, 'completed_at', None),
        error=getattr(state, 'error', None),
    )


@router.post(
    "/workflows/{workflow_id}/start",
    response_model=ExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start workflow execution",
    description="Start a new execution of the specified workflow.",
    responses={
        404: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def start_workflow(
    workflow_id: str,
    request: StartWorkflowRequest,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    """Start a new workflow execution."""
    try:
        workflow = registry.get(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WORKFLOW_NOT_FOUND",
                "message": f"Workflow '{workflow_id}' not found",
            },
        )
    
    execution_id, state = await execution_service.start_execution(
        workflow=workflow,
        project_id=request.project_id,
        initial_context=request.initial_context,
    )
    
    return _state_to_response(execution_id, state)


@router.get(
    "/executions",
    response_model=ExecutionListResponse,
    summary="List executions",
    description="List workflow executions with optional filters.",
)
async def list_executions(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecutionListResponse:
    """List workflow executions."""
    status_enum = None
    if status_filter:
        try:
            status_enum = WorkflowStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_STATUS",
                    "message": f"Invalid status: {status_filter}",
                },
            )
    
    executions = await execution_service.list_executions(
        workflow_id=workflow_id,
        project_id=project_id,
        status=status_enum,
    )
    
    summaries = [
        ExecutionSummary(
            execution_id=e.execution_id,
            workflow_id=e.workflow_id,
            project_id=e.project_id,
            status=e.status.value if hasattr(e.status, 'value') else str(e.status),
            started_at=e.started_at,
            completed_at=e.completed_at,
        )
        for e in executions
    ]
    
    return ExecutionListResponse(
        executions=summaries,
        total=len(summaries),
    )


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="Get execution status",
    description="Get detailed status of a workflow execution.",
    responses={
        404: {"model": ErrorResponse, "description": "Execution not found"},
    },
)
async def get_execution(
    execution_id: str,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    """Get execution status."""
    try:
        state, context = await execution_service.get_execution(execution_id)
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXECUTION_NOT_FOUND",
                "message": f"Execution '{execution_id}' not found",
            },
        )
    
    return _state_to_response(execution_id, state)


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=ExecutionResponse,
    summary="Cancel execution",
    description="Cancel a running workflow execution.",
    responses={
        404: {"model": ErrorResponse, "description": "Execution not found"},
        409: {"model": ErrorResponse, "description": "Cannot cancel in current state"},
    },
)
async def cancel_execution(
    execution_id: str,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    """Cancel a workflow execution."""
    try:
        state = await execution_service.cancel_execution(execution_id)
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXECUTION_NOT_FOUND",
                "message": f"Execution '{execution_id}' not found",
            },
        )
    except InvalidExecutionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INVALID_STATE",
                "message": str(e),
            },
        )
    
    return _state_to_response(execution_id, state)


@router.post(
    "/executions/{execution_id}/acceptance",
    response_model=ExecutionResponse,
    summary="Submit acceptance decision",
    description="Submit acceptance or rejection for a pending document.",
    responses={
        404: {"model": ErrorResponse, "description": "Execution not found"},
        409: {"model": ErrorResponse, "description": "Not waiting for acceptance"},
    },
)
async def submit_acceptance(
    execution_id: str,
    request: AcceptanceRequest,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    """Submit acceptance decision."""
    try:
        state = await execution_service.submit_acceptance(
            execution_id=execution_id,
            accepted=request.accepted,
            comment=request.comment,
            decided_by="user",  # Would come from auth in production
        )
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXECUTION_NOT_FOUND",
                "message": f"Execution '{execution_id}' not found",
            },
        )
    except InvalidExecutionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INVALID_STATE",
                "message": str(e),
            },
        )
    
    return _state_to_response(execution_id, state)


@router.post(
    "/executions/{execution_id}/clarification",
    response_model=ExecutionResponse,
    summary="Submit clarification answers",
    description="Submit answers to clarification questions.",
    responses={
        404: {"model": ErrorResponse, "description": "Execution not found"},
        409: {"model": ErrorResponse, "description": "Not waiting for clarification"},
    },
)
async def submit_clarification(
    execution_id: str,
    request: ClarificationRequest,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    """Submit clarification answers."""
    try:
        state = await execution_service.submit_clarification(
            execution_id=execution_id,
            answers=request.answers,
        )
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXECUTION_NOT_FOUND",
                "message": f"Execution '{execution_id}' not found",
            },
        )
    except InvalidExecutionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INVALID_STATE",
                "message": str(e),
            },
        )
    
    return _state_to_response(execution_id, state)


@router.post(
    "/executions/{execution_id}/resume",
    response_model=ExecutionResponse,
    summary="Resume execution",
    description="Resume a paused workflow execution.",
    responses={
        404: {"model": ErrorResponse, "description": "Execution not found"},
        409: {"model": ErrorResponse, "description": "Cannot resume in current state"},
    },
)
async def resume_execution(
    execution_id: str,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    """Resume paused execution."""
    try:
        state = await execution_service.resume_execution(execution_id)
    except ExecutionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXECUTION_NOT_FOUND",
                "message": f"Execution '{execution_id}' not found",
            },
        )
    except InvalidExecutionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INVALID_STATE",
                "message": str(e),
            },
        )
    
    return _state_to_response(execution_id, state)
