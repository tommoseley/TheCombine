"""JSON API router for Concierge Intake workflow.

Provides JSON endpoints for the React SPA intake experience.
Mirrors the HTMX flow in intake_workflow_routes.py but returns JSON.

Endpoints:
- POST /api/v1/intake/start - Start new intake workflow
- GET /api/v1/intake/{execution_id} - Get current state
- POST /api/v1/intake/{execution_id}/message - Submit user message
- PATCH /api/v1/intake/{execution_id}/field/{key} - Update interpretation field
- POST /api/v1/intake/{execution_id}/initialize - Lock fields, start generation
- GET /api/v1/intake/{execution_id}/events - SSE stream for generation progress
"""

import asyncio
import json
import logging
import uuid as uuid_module
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.config import USE_WORKFLOW_ENGINE_LLM
from app.auth.dependencies import require_auth
from app.auth.models import User
from app.domain.workflow.plan_executor import PlanExecutor
from app.domain.workflow.pg_state_persistence import PgStatePersistence
from app.domain.workflow.plan_registry import get_plan_registry
from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
from app.domain.workflow.interpretation import calculate_confidence, get_missing_fields
from app.domain.workflow.nodes.mock_executors import create_mock_executors
from app.api.services.project_creation_service import (
    create_project_from_intake,
    extract_intake_document_from_state,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])


# --- Request/Response Models ---


class InterpretationField(BaseModel):
    """A single interpretation field with metadata."""
    value: str
    source: str = "llm"
    locked: bool = False


class IntakeMessage(BaseModel):
    """A message in the intake conversation."""
    role: str  # "user" or "assistant"
    content: str


class IntakeStateResponse(BaseModel):
    """Response with full intake workflow state."""
    execution_id: str
    phase: str  # "describe", "review", "generating", "complete"
    messages: List[IntakeMessage]
    pending_prompt: Optional[str] = None
    pending_choices: Optional[List[str]] = None
    interpretation: Dict[str, InterpretationField] = {}
    confidence: float = 0.0
    missing_fields: List[str] = []
    can_initialize: bool = False
    gate_outcome: Optional[str] = None
    project: Optional[Dict[str, Any]] = None
    # Gate Profile fields (ADR-047)
    intake_classification: Optional[Dict[str, Any]] = None
    intake_gate_phase: Optional[str] = None


class StartIntakeResponse(BaseModel):
    """Response after starting intake."""
    execution_id: str
    phase: str
    pending_prompt: Optional[str] = None


class SubmitMessageRequest(BaseModel):
    """Request to submit a user message."""
    content: str = Field(..., min_length=1)


class UpdateFieldRequest(BaseModel):
    """Request to update an interpretation field."""
    value: str


class StatusResponse(BaseModel):
    """Response for status polling during generation."""
    execution_id: str
    phase: str
    is_complete: bool
    gate_outcome: Optional[str] = None
    project: Optional[Dict[str, Any]] = None


# --- Helpers ---


async def _get_executor(db: AsyncSession) -> PlanExecutor:
    """Get configured plan executor."""
    if USE_WORKFLOW_ENGINE_LLM:
        from app.domain.workflow.nodes.llm_executors import create_llm_executors
        from app.domain.workflow.thread_manager import ThreadManager
        from app.domain.workflow.outcome_recorder import OutcomeRecorder

        executors = await create_llm_executors(db)
        thread_manager = ThreadManager(db)
        outcome_recorder = OutcomeRecorder(db)

        return PlanExecutor(
            persistence=PgStatePersistence(db),
            plan_registry=get_plan_registry(),
            executors=executors,
            thread_manager=thread_manager,
            outcome_recorder=outcome_recorder,
            db_session=db,
        )
    else:
        return PlanExecutor(
            persistence=PgStatePersistence(db),
            plan_registry=get_plan_registry(),
            executors=create_mock_executors(),
            db_session=db,
        )


def _extract_messages(state) -> List[IntakeMessage]:
    """Extract conversation messages from workflow state.

    Messages are returned in chronological order (oldest first).
    The pending_user_input_rendered is included as the last assistant message
    to maintain consistent top-to-bottom conversation flow.
    """
    messages = []
    node_history = list(state.node_history)

    for i, execution in enumerate(node_history):
        if execution.metadata.get("user_input"):
            messages.append(IntakeMessage(
                role="user",
                content=execution.metadata["user_input"],
            ))
        response = execution.metadata.get("response") or execution.metadata.get("user_prompt")
        if response:
            messages.append(IntakeMessage(
                role="assistant",
                content=response,
            ))

    # Include user_input from context_state if not in messages
    user_input = state.context_state.get("user_input")
    if user_input and not any(m.content == user_input for m in messages if m.role == "user"):
        insert_idx = 0
        for idx, m in enumerate(messages):
            if m.role == "assistant":
                insert_idx = idx + 1
            else:
                break
        messages.insert(insert_idx, IntakeMessage(role="user", content=user_input))

    return messages


def _build_state_response(state, project: Optional[Dict[str, Any]] = None) -> IntakeStateResponse:
    """Build full state response from workflow state."""
    interpretation_raw = state.context_state.get("interpretation", {})
    interpretation = {}
    for key, val in interpretation_raw.items():
        if isinstance(val, dict):
            interpretation[key] = InterpretationField(
                value=val.get("value", ""),
                source=val.get("source", "llm"),
                locked=val.get("locked", False),
            )
        else:
            interpretation[key] = InterpretationField(value=str(val))

    phase = state.context_state.get("phase", "describe")
    if state.status == DocumentWorkflowStatus.COMPLETED:
        phase = "complete"

    confidence = calculate_confidence(interpretation_raw)
    missing = get_missing_fields(interpretation_raw)

    # Extract messages first
    messages = _extract_messages(state)

    # Don't show pending_prompt if it's already the last assistant message
    # This prevents duplication in the UI
    pending_prompt = state.pending_user_input_rendered
    if pending_prompt and messages:
        last_assistant = next(
            (m for m in reversed(messages) if m.role == "assistant"),
            None
        )
        if last_assistant and last_assistant.content == pending_prompt:
            pending_prompt = None

    return IntakeStateResponse(
        execution_id=state.execution_id,
        phase=phase,
        messages=messages,
        pending_prompt=pending_prompt,
        pending_choices=state.pending_choices,
        interpretation=interpretation,
        confidence=confidence,
        missing_fields=missing,
        can_initialize=confidence >= 1.0,
        gate_outcome=state.gate_outcome,
        project=project,
        # Gate Profile fields (ADR-047)
        intake_classification=state.context_state.get("intake_classification"),
        intake_gate_phase=state.context_state.get("intake_gate_phase"),
    )


# --- Endpoints ---


@router.post("/start", response_model=IntakeStateResponse)
async def start_intake(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> IntakeStateResponse:
    """Start a new intake workflow execution.

    Creates a workflow execution and runs to first pause (initial question).
    Returns full state including messages for consistent UI rendering.
    Requires authentication - user_id stored for project creation.
    """
    if not USE_WORKFLOW_ENGINE_LLM:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow engine not enabled. Set USE_WORKFLOW_ENGINE_LLM=true.",
        )

    project_id = f"intake-{uuid_module.uuid4().hex[:12]}"
    executor = await _get_executor(db)

    try:
        state = await executor.start_execution(
            project_id=project_id,
            document_type="concierge_intake",
            initial_context={},
        )
        state = await executor.run_to_completion_or_pause(state.execution_id)

        return _build_state_response(state)

    except Exception as e:
        logger.exception(f"Failed to start intake: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{execution_id}", response_model=IntakeStateResponse)
async def get_intake_state(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> IntakeStateResponse:
    """Get the current state of an intake workflow."""
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution not found: {execution_id}",
        )

    project = None
    if state.status == DocumentWorkflowStatus.COMPLETED and state.gate_outcome == "qualified":
        project = await _get_created_project(state, db, str(current_user.user_id))

    return _build_state_response(state, project)


@router.post("/{execution_id}/message", response_model=IntakeStateResponse)
async def submit_message(
    execution_id: str,
    request: SubmitMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> IntakeStateResponse:
    """Submit a user message to the intake workflow.

    Advances the workflow with the user's input.
    """
    executor = await _get_executor(db)

    try:
        state = await executor.submit_user_input(
            execution_id=execution_id,
            user_input=request.content,
        )
        state = await executor.run_to_completion_or_pause(execution_id)

    except Exception as e:
        logger.exception(f"Failed to process message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    project = None
    if state.status == DocumentWorkflowStatus.COMPLETED and state.gate_outcome == "qualified":
        project = await _get_created_project(state, db, str(current_user.user_id))

    return _build_state_response(state, project)


@router.patch("/{execution_id}/field/{field_key}", response_model=IntakeStateResponse)
async def update_field(
    execution_id: str,
    field_key: str,
    request: UpdateFieldRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> IntakeStateResponse:
    """Update a single interpretation field (user edit, auto-locks)."""
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    if state.context_state.get("phase") != "review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not in review phase",
        )

    interpretation = state.context_state.get("interpretation", {})
    interpretation[field_key] = {
        "value": request.value,
        "source": "user",
        "locked": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    state.update_context_state({"interpretation": interpretation})
    await executor._persistence.save(state)

    logger.info(f"Updated interpretation field {field_key} for {execution_id}")

    return _build_state_response(state)


@router.post("/{execution_id}/initialize", response_model=IntakeStateResponse)
async def initialize_project(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> IntakeStateResponse:
    """Confirm interpretation and proceed to generation phase.

    Requires all required fields to be filled (confidence = 1.0).
    """
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    if state.context_state.get("phase") != "review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not in review phase",
        )

    interpretation = state.context_state.get("interpretation", {})
    confidence = calculate_confidence(interpretation)

    if confidence < 1.0:
        missing = get_missing_fields(interpretation)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    # Update phase and clear pause
    state.update_context_state({"phase": "generating"})
    state.clear_pause()
    await executor._persistence.save(state)

    logger.info(f"Initialized project for {execution_id} - entering generating phase")

    return _build_state_response(state)


@router.get("/{execution_id}/events")
async def intake_events(
    request: Request,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> EventSourceResponse:
    """SSE stream for intake generation progress.

    Events:
    - started: Generation has begun
    - progress: Current node being processed
    - complete: Workflow finished, includes project info
    - error: Something went wrong

    Usage: Connect after calling /initialize, stream will run workflow
    and push updates until completion.
    """
    return EventSourceResponse(
        _intake_event_generator(request, execution_id, db, str(current_user.user_id))
    )


async def _intake_event_generator(
    request: Request,
    execution_id: str,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """Generate SSE events during intake workflow execution."""
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)

    if not state:
        yield {
            "event": "error",
            "data": json.dumps({"message": "Execution not found"}),
        }
        return

    # Send initial event
    yield {
        "event": "started",
        "data": json.dumps({
            "execution_id": execution_id,
            "phase": state.context_state.get("phase", "generating"),
            "current_node": state.current_node_id,
        }),
    }

    # Check if already complete
    if state.status == DocumentWorkflowStatus.COMPLETED:
        project = await _get_created_project(state, db, user_id)
        yield {
            "event": "complete",
            "data": json.dumps({
                "execution_id": execution_id,
                "gate_outcome": state.gate_outcome,
                "project": project,
            }),
        }
        return

    # Run workflow step by step, yielding progress
    try:
        last_node = state.current_node_id

        while state.status not in (
            DocumentWorkflowStatus.COMPLETED,
            DocumentWorkflowStatus.FAILED,
        ):
            # Check for client disconnect
            if await request.is_disconnected():
                logger.info(f"Client disconnected during intake {execution_id}")
                return

            # Execute one step
            state = await executor.execute_step(execution_id)

            # Yield progress if node changed
            if state.current_node_id != last_node:
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "current_node": state.current_node_id,
                        "previous_node": last_node,
                    }),
                }
                last_node = state.current_node_id

            # Small delay to prevent tight loop
            await asyncio.sleep(0.1)

        # Workflow complete - create project if qualified
        project = None
        if state.status == DocumentWorkflowStatus.COMPLETED and state.gate_outcome == "qualified":
            project = await _get_created_project(state, db, user_id)

        yield {
            "event": "complete",
            "data": json.dumps({
                "execution_id": execution_id,
                "gate_outcome": state.gate_outcome,
                "terminal_outcome": state.terminal_outcome,
                "project": project,
            }),
        }

    except Exception as e:
        logger.exception(f"Error during intake workflow: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"message": str(e)}),
        }


async def _get_created_project(
    state,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Get or create project from completed intake.

    Idempotent: checks if project already exists for this execution before creating.

    Args:
        state: Workflow execution state
        db: Database session
        user_id: Optional user ID for owner/created_by fields
    """
    from sqlalchemy import select
    from app.api.models.project import Project

    try:
        # First check if project already exists for this execution
        result = await db.execute(
            select(Project).where(
                Project.meta["workflow_execution_id"].astext == state.execution_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Found existing project {existing.project_id} for execution {state.execution_id}")
            return {
                "id": str(existing.id),
                "project_id": existing.project_id,
                "name": existing.name,
            }

        # No existing project, create one
        intake_doc = extract_intake_document_from_state(state)
        if intake_doc:
            project = await create_project_from_intake(
                db=db,
                intake_document=intake_doc,
                execution_id=state.execution_id,
                user_id=user_id,
            )
            if project:
                return {
                    "id": str(project.id),
                    "project_id": project.project_id,
                    "name": project.name,
                }
    except Exception as e:
        logger.exception(f"Failed to get/create project: {e}")
    return None
