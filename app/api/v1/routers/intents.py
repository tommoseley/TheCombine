"""Intent Intake API router.

Mechanical intake for IntentPackets — no LLM involvement.
IntentPackets are immutable once created. To revise, create a new one.

Endpoints:
- POST /api/v1/intents - Create and persist a new IntentPacket
- GET /api/v1/intents/{intent_id} - Retrieve an IntentPacket by document ID
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import require_auth
from app.auth.models import User
from app.api.models.document import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intents", tags=["intents"])


# --- Request/Response Models ---


class CreateIntentRequest(BaseModel):
    """Request to create an IntentPacket."""
    project_id: str = Field(..., description="Project UUID to associate the intent with")
    raw_intent: str = Field(..., min_length=1, description="Raw intent text from the user")
    constraints: Optional[str] = Field(None, description="Known constraints")
    success_criteria: Optional[str] = Field(None, description="What success looks like")
    context: Optional[str] = Field(None, description="Additional context")


class IntentResponse(BaseModel):
    """Response after creating or retrieving an IntentPacket."""
    intent_id: str
    project_id: str
    content: Dict[str, Any]
    created_at: Optional[str] = None


# --- Endpoints ---


@router.post("", status_code=status.HTTP_201_CREATED, response_model=IntentResponse)
async def create_intent(
    request: CreateIntentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> IntentResponse:
    """Create and persist a new IntentPacket.

    This is a mechanical write — no LLM involvement.
    The IntentPacket is immutable once created.
    """
    content = {
        "raw_intent": request.raw_intent,
        "constraints": request.constraints,
        "success_criteria": request.success_criteria,
        "context": request.context,
        "schema_version": "1.0.0",
    }

    doc = Document(
        space_type="project",
        space_id=UUID(request.project_id),
        doc_type_id="intent_packet",
        title=f"Intent: {request.raw_intent[:80]}",
        content=content,
        version=1,
        is_latest=True,
        status="complete",
        lifecycle_state="complete",
        created_by=str(current_user.user_id) if current_user else None,
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(f"Created IntentPacket {doc.id} for project {request.project_id}")

    return IntentResponse(
        intent_id=str(doc.id),
        project_id=request.project_id,
        content=content,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


@router.get("/{intent_id}", response_model=IntentResponse)
async def get_intent(
    intent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> IntentResponse:
    """Retrieve an IntentPacket by its document ID."""
    try:
        doc_uuid = UUID(intent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid intent_id format",
        )

    result = await db.execute(
        select(Document).where(
            Document.id == doc_uuid,
            Document.doc_type_id == "intent_packet",
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IntentPacket not found: {intent_id}",
        )

    return IntentResponse(
        intent_id=str(doc.id),
        project_id=str(doc.space_id),
        content=doc.content,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )
