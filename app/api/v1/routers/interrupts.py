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
    resolution: Dict[str, Any] = {}

    if request.answers:
        resolution["answers"] = request.answers

    if request.decision:
        resolution["decision"] = request.decision

    if request.notes:
        resolution["notes"] = request.notes

    if request.escalation_option:
        resolution["escalation_option"] = request.escalation_option

    if not resolution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolution must include at least one of: answers, decision, notes, escalation_option",
        )

    # Resolve the interrupt
    success = await registry.resolve(interrupt_id, resolution)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interrupt '{interrupt_id}' not found or already resolved",
        )

    await db.commit()

    logger.info(f"Resolved interrupt {interrupt_id}")

    # Emit SSE event for UI update
    try:
        from app.api.v1.routers.production import publish_event

        # Get interrupt details to find project_id
        interrupt = await registry.get_interrupt(interrupt_id)
        if interrupt:
            await publish_event(
                interrupt.project_id,
                "interrupt_resolved",
                {
                    "interrupt_id": interrupt_id,
                    "execution_id": interrupt_id,
                    "document_type": interrupt.document_type,
                },
            )
    except Exception as e:
        logger.warning(f"Failed to emit interrupt_resolved event: {e}")

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
