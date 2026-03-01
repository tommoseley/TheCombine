"""Interrupts API router (ADR-043 Phase 5).

Provides endpoints for resolving operator interrupts:
- POST /api/v1/interrupts/{id}/resolve - Submit resolution
- GET /api/v1/interrupts/{id} - Get interrupt details
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.workflow.interrupt_registry import InterruptRegistry, EscalationResolution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interrupts", tags=["interrupts"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ResolveInterruptRequest(BaseModel):
    """Request body for resolving an interrupt."""

    answers: Optional[Dict[str, Any]] = Field(
        None,
        description="Answers to PGC questions (key: question_id, value: answer)",
    )
    decision: Optional[str] = Field(
        None,
        description="Decision for audit review (approve, reject, escalate)",
    )
    notes: Optional[str] = Field(
        None,
        description="Operator notes for the resolution",
    )
    escalation_option: Optional[str] = Field(
        None,
        description="Selected escalation option if escalating",
    )


class EscalateInterruptRequest(BaseModel):
    """Request body for escalating an interrupt (ADR-043 Phase 8).

    Escalation acknowledges a halt without fixing the underlying issue.
    The document moves from Halted to Escalated state.
    """

    acknowledged_by: str = Field(
        ...,
        description="User ID or name acknowledging the escalation",
    )
    notes: Optional[str] = Field(
        None,
        description="Operator notes explaining the escalation decision",
    )


class InterruptResponse(BaseModel):
    """Response model for an interrupt."""

    id: str
    execution_id: str
    project_id: str
    document_type: str
    interrupt_type: str
    payload: Dict[str, Any]
    created_at: str
    resolved_at: Optional[str] = None
    resolution: Optional[Dict[str, Any]] = None
    current_node_id: Optional[str] = None
    workflow_id: Optional[str] = None


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/{interrupt_id}")
async def get_interrupt(
    interrupt_id: str,
    db: AsyncSession = Depends(get_db),
) -> InterruptResponse:
    """Get interrupt details by ID.

    Args:
        interrupt_id: The interrupt ID (same as execution_id)

    Returns:
        Interrupt details including payload for rendering UI
    """
    registry = InterruptRegistry(db)
    interrupt = await registry.get_interrupt(interrupt_id)

    if not interrupt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interrupt '{interrupt_id}' not found or already resolved",
        )

    return InterruptResponse(**interrupt.to_dict())


@router.post("/{interrupt_id}/resolve")
async def resolve_interrupt(
    interrupt_id: str,
    request: ResolveInterruptRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Resolve an interrupt and resume production.

    Clears the pause state and updates context with resolution.
    The workflow will resume on next execution tick.

    Args:
        interrupt_id: The interrupt ID to resolve
        request: Resolution data (answers, decision, notes)

    Returns:
        Success status and execution_id for tracking
    """
    registry = InterruptRegistry(db)

    # Build resolution dict from request
    from app.api.v1.services.pgc_pure import build_resolution_dict

    logger.info(f"Resolve request: answers={request.answers}, decision={request.decision}, notes={request.notes}")

    resolution = build_resolution_dict(
        answers=request.answers,
        decision=request.decision,
        notes=request.notes,
        escalation_option=request.escalation_option,
    )

    if not resolution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolution must include at least one of: answers, decision, notes, escalation_option",
        )

    # Get interrupt details BEFORE resolving (resolve clears pending_user_input,
    # which get_interrupt filters on, so it would return None after resolve)
    interrupt = await registry.get_interrupt(interrupt_id)
    project_id = interrupt.project_id if interrupt else None
    document_type = interrupt.document_type if interrupt else None

    # Resolve the interrupt
    success = await registry.resolve(interrupt_id, resolution)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interrupt '{interrupt_id}' not found or already resolved",
        )

    await db.commit()

    logger.info(f"Resolved interrupt {interrupt_id}")

    # Resume workflow execution
    final_state = None
    try:
        from app.domain.workflow.plan_executor import PlanExecutor
        from app.domain.workflow.pg_state_persistence import PgStatePersistence
        from app.domain.workflow.plan_registry import get_plan_registry
        from app.domain.workflow.nodes.llm_executors import create_llm_executors

        executors = await create_llm_executors(db)
        executor = PlanExecutor(
            persistence=PgStatePersistence(db),
            plan_registry=get_plan_registry(),
            executors=executors,
            db_session=db,
        )

        # Continue execution from where it was paused
        final_state = await executor.run_to_completion_or_pause(interrupt_id)
        logger.info(f"Resumed execution {interrupt_id}, now at node {final_state.current_node_id}, status={final_state.status}")
    except Exception as e:
        logger.error(f"Failed to resume execution after interrupt resolution: {e}")
        # Don't fail the request - interrupt is resolved, execution can be retried

    # Emit SSE events for UI update
    try:
        from app.api.v1.routers.production import publish_event

        if project_id:
            # Always emit interrupt_resolved
            await publish_event(
                project_id,
                "interrupt_resolved",
                {
                    "interrupt_id": interrupt_id,
                    "execution_id": interrupt_id,
                    "document_type": document_type,
                },
            )

            # If workflow completed, emit track_stabilized
            if final_state and final_state.terminal_outcome == "stabilized":
                await publish_event(
                    project_id,
                    "track_stabilized",
                    {
                        "execution_id": interrupt_id,
                        "document_type": document_type,
                        "outcome": "stabilized",
                    },
                )
                logger.info(f"Emitted track_stabilized event for {document_type}")
    except Exception as e:
        logger.warning(f"Failed to emit SSE events: {e}")

    return JSONResponse({
        "status": "resolved",
        "interrupt_id": interrupt_id,
        "execution_id": interrupt_id,
        "message": "Interrupt resolved, production will resume",
    })


@router.post("/{interrupt_id}/escalate")
async def escalate_interrupt(
    interrupt_id: str,
    request: EscalateInterruptRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Escalate an interrupt without resolving the underlying issue (ADR-043 Phase 8).

    This acknowledges a halt and moves the document to Escalated state.
    The underlying issue is NOT fixed - this is logged for compliance review.

    Args:
        interrupt_id: The interrupt ID to escalate
        request: Escalation acknowledgment details

    Returns:
        Success status with escalation details
    """
    from datetime import datetime, timezone

    registry = InterruptRegistry(db)

    # Get interrupt details first for SSE event
    interrupt = await registry.get_interrupt(interrupt_id)
    if not interrupt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interrupt '{interrupt_id}' not found or already resolved",
        )

    # Build escalation resolution
    escalation = EscalationResolution(
        acknowledged_by=request.acknowledged_by,
        acknowledged_at=datetime.now(timezone.utc),
        notes=request.notes,
    )

    # Perform escalation
    success = await registry.escalate(interrupt_id, escalation)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to escalate interrupt '{interrupt_id}'",
        )

    await db.commit()

    logger.warning(
        f"Escalated interrupt {interrupt_id} by {request.acknowledged_by}"
    )

    # Emit SSE event for UI update
    try:
        from app.api.v1.routers.production import publish_event

        await publish_event(
            interrupt.project_id,
            "document_escalated",
            {
                "interrupt_id": interrupt_id,
                "execution_id": interrupt_id,
                "document_type": interrupt.document_type,
                "acknowledged_by": request.acknowledged_by,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to emit document_escalated event: {e}")

    return JSONResponse({
        "status": "escalated",
        "interrupt_id": interrupt_id,
        "execution_id": interrupt_id,
        "acknowledged_by": request.acknowledged_by,
        "message": "Interrupt escalated, document moved to Escalated state",
    })
