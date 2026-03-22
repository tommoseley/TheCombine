"""Rewind API router (ADR-063).

Provides endpoints for pipeline rewind, regeneration, and lineage:
- POST /api/v1/projects/{project_id}/rewind - Rewind pipeline to stage
- POST /api/v1/projects/{project_id}/regenerate/validate - Validate regeneration
- GET /api/v1/projects/{project_id}/lineage - Get lineage history
- GET /api/v1/projects/{project_id}/pipeline-status - Get pipeline status with staleness
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.models.pipeline_stage import PipelineStage
from app.domain.models.rewind_errors import RewindBlockedError
from app.domain.services.lineage_service import (
    InMemoryLineageRepository,
    LineageService,
)
from app.domain.services.rewind_service import (
    RewindRequest,
    RewindResult,
    RewindService,
)
from app.domain.services.regeneration_service import (
    RegenerationRequest,
    RegenerationResult,
    RegenerationService,
)
from app.persistence.repositories import InMemoryDocumentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["rewind"])


# ============================================================================
# Request/Response Models
# ============================================================================


class RewindRequestBody(BaseModel):
    """Request body for pipeline rewind."""

    rewind_to_stage: str = Field(
        ...,
        description="Pipeline stage to rewind to (CI, PD, TA, IP, WP, WS)",
    )
    reason: str = Field(
        ...,
        description="Reason for the rewind",
    )
    actor: str = Field(
        default="user",
        description="Who initiated the rewind",
    )


class RewindResponseBody(BaseModel):
    """Response for pipeline rewind."""

    success: bool
    rewind_to_stage: str
    affected_stages: List[str]
    affected_document_count: int
    stale_document_ids: List[str]
    lineage_event_id: str


class RegenerateValidateBody(BaseModel):
    """Request body to validate regeneration preconditions."""

    from_stage: str = Field(
        ...,
        description="Pipeline stage to regenerate from",
    )
    actor: str = Field(default="user")


class RegenerateValidateResponse(BaseModel):
    """Response for regeneration validation."""

    success: bool
    from_stage: str
    precondition_errors: List[str]
    message: str


class LineageEventResponse(BaseModel):
    """A single lineage event."""

    id: str
    project_id: str
    event_type: str
    rewind_to_stage: str
    reason: str
    actor: str
    affected_document_count: int
    created_at: str


class PipelineStageStatus(BaseModel):
    """Status of a single pipeline stage."""

    stage: str
    display_name: str
    doc_type_id: str
    has_current: bool
    has_stale: bool
    document_count: int


class PipelineStatusResponse(BaseModel):
    """Full pipeline status for a project."""

    project_id: str
    stages: List[PipelineStageStatus]
    has_stale_documents: bool
    earliest_stale_stage: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/{project_id}/rewind", response_model=RewindResponseBody)
async def rewind_pipeline(
    project_id: UUID,
    body: RewindRequestBody,
    db: AsyncSession = Depends(get_db),
):
    """Rewind pipeline to a specific stage, marking downstream artifacts stale."""
    # Validate stage — accept both short name (IP) and doc_type_id (implementation_plan)
    stage = None
    try:
        stage = PipelineStage[body.rewind_to_stage.upper()]
    except KeyError:
        try:
            stage = PipelineStage.from_doc_type_id(body.rewind_to_stage)
        except ValueError:
            valid = [f"{s.name} ({s.doc_type_id})" for s in PipelineStage]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{body.rewind_to_stage}'. Valid: {valid}",
            )

    # Build services with DB-backed repositories
    # For now, use a lightweight adapter pattern
    from app.api.v1.routers._rewind_wiring import build_rewind_service

    service = await build_rewind_service(db)

    request = RewindRequest(
        project_id=project_id,
        rewind_to_stage=stage,
        reason=body.reason,
        actor=body.actor,
    )

    result = await service.execute_rewind(request)

    return RewindResponseBody(
        success=result.success,
        rewind_to_stage=result.rewind_to_stage,
        affected_stages=result.affected_stages,
        affected_document_count=result.affected_document_count,
        stale_document_ids=[str(d) for d in result.stale_document_ids],
        lineage_event_id=str(result.lineage_event_id),
    )


@router.post(
    "/{project_id}/regenerate/validate",
    response_model=RegenerateValidateResponse,
)
async def validate_regeneration(
    project_id: UUID,
    body: RegenerateValidateBody,
    db: AsyncSession = Depends(get_db),
):
    """Validate preconditions for regeneration from a stage."""
    stage = None
    try:
        stage = PipelineStage[body.from_stage.upper()]
    except KeyError:
        try:
            stage = PipelineStage.from_doc_type_id(body.from_stage)
        except ValueError:
            valid = [f"{s.name} ({s.doc_type_id})" for s in PipelineStage]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{body.from_stage}'. Valid: {valid}",
            )

    from app.api.v1.routers._rewind_wiring import build_regeneration_service

    service = await build_regeneration_service(db)

    request = RegenerationRequest(
        project_id=project_id,
        from_stage=stage,
        actor=body.actor,
    )

    result = await service.validate_preconditions(request)

    return RegenerateValidateResponse(
        success=result.success,
        from_stage=result.from_stage,
        precondition_errors=result.precondition_errors,
        message=result.message,
    )


@router.get("/{project_id}/lineage", response_model=List[LineageEventResponse])
async def get_lineage(
    project_id: UUID,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get lineage history for a project."""
    from app.api.v1.routers._rewind_wiring import build_lineage_service

    service = await build_lineage_service(db)
    events = await service.get_project_history(project_id, event_type)

    return [
        LineageEventResponse(
            id=str(e.id),
            project_id=str(e.project_id),
            event_type=e.event_type,
            rewind_to_stage=e.rewind_to_stage,
            reason=e.reason,
            actor=e.actor,
            affected_document_count=len(e.affected_document_ids),
            created_at=e.created_at.isoformat(),
        )
        for e in events
    ]


@router.get(
    "/{project_id}/pipeline-status",
    response_model=PipelineStatusResponse,
)
async def get_pipeline_status(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get pipeline status showing current/stale state per stage."""
    from app.api.models.document import Document
    from sqlalchemy import select, and_, func

    stages_status = []
    has_stale = False
    earliest_stale = None

    for stage in PipelineStage.all_stages_ordered():
        # Count current docs at this stage
        current_q = select(func.count()).select_from(Document).where(
            and_(
                Document.space_type == "project",
                Document.space_id == project_id,
                Document.doc_type_id == stage.doc_type_id,
                Document.is_latest == True,
                Document.status.notin_(["stale", "archived"]),
            )
        )
        current_result = await db.execute(current_q)
        current_count = current_result.scalar() or 0

        # Count stale docs at this stage
        stale_q = select(func.count()).select_from(Document).where(
            and_(
                Document.space_type == "project",
                Document.space_id == project_id,
                Document.doc_type_id == stage.doc_type_id,
                Document.status == "stale",
            )
        )
        stale_result = await db.execute(stale_q)
        stale_count = stale_result.scalar() or 0

        has_stale_at_stage = stale_count > 0
        if has_stale_at_stage:
            has_stale = True
            if earliest_stale is None:
                earliest_stale = stage.name

        stages_status.append(
            PipelineStageStatus(
                stage=stage.name,
                display_name=stage.display_name,
                doc_type_id=stage.doc_type_id,
                has_current=current_count > 0,
                has_stale=has_stale_at_stage,
                document_count=current_count + stale_count,
            )
        )

    return PipelineStatusResponse(
        project_id=str(project_id),
        stages=stages_status,
        has_stale_documents=has_stale,
        earliest_stale_stage=earliest_stale,
    )
