"""Rewind API router (ADR-063, ADR-067).

Provides endpoints for pipeline rewind, regeneration, lineage, and timeline:
- POST /api/v1/projects/{project_id}/rewind - Rewind pipeline to stage
- POST /api/v1/projects/{project_id}/regenerate/validate - Validate regeneration
- GET /api/v1/projects/{project_id}/lineage - Get lineage history
- GET /api/v1/projects/{project_id}/pipeline-status - Get pipeline status with staleness
- GET /api/v1/projects/{project_id}/timeline - Full project history timeline (ADR-067)
- POST /api/v1/projects/{project_id}/restore - Restore lineage path (ADR-067)
- POST /api/v1/projects/{project_id}/archive-thread - Archive rewind thread (ADR-067)
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["rewind"])


# ============================================================================
# Request/Response Models
# ============================================================================


class RewindRequestBody(BaseModel):
    """Request body for pipeline rewind.

    ADR-069: The reason field is the living correction brief.
    It serves as both the audit narrative AND the binding authority
    for regeneration. Dual-written to lineage event + authority record.
    Pre-populated from authority store on subsequent rewinds.
    """

    rewind_to_stage: str = Field(
        ...,
        description="Pipeline stage to rewind to (CI, PD, TA, IP, WP, WS)",
    )
    reason: str = Field(
        ...,
        description="Correction brief — what's wrong and what must change. "
        "Dual-written: audit log + binding authority for regeneration.",
    )
    actor: str = Field(
        default="user",
        description="Who initiated the rewind",
    )
    applies_to_stages: Optional[List[str]] = Field(
        default=None,
        description="Pipeline stages this correction applies to (default: rewound-to stage only). "
        "Accepts both short codes (TA) and doc_type_ids (technical_architecture).",
    )


class RewindResponseBody(BaseModel):
    """Response for pipeline rewind."""

    success: bool
    rewind_to_stage: str
    affected_stages: List[str]
    affected_document_count: int
    stale_document_ids: List[str]
    lineage_event_id: str
    correction_record_id: str


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


class CorrectionResponse(BaseModel):
    """Response for current correction at a stage (ADR-069 pre-population)."""

    stage: str
    text: str
    applies_to_stages: List[str]
    authority_record_id: str
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
    from app.domain.models.pipeline_stage import PipelineStage
    from app.domain.services.rewind_service import RewindRequest

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

    # Cancel any paused/running executions for affected document types
    # (prevents stale PGC questions from appearing after rewind)
    from app.api.models.workflow_execution import WorkflowExecution
    from app.domain.services.rewind_impact_evaluator import get_affected_doc_type_ids
    from sqlalchemy import update, and_

    affected_doc_types = get_affected_doc_type_ids(stage)
    if affected_doc_types:
        cancel_result = await db.execute(
            update(WorkflowExecution)
            .where(
                and_(
                    WorkflowExecution.project_id == project_id,
                    WorkflowExecution.workflow_id.in_(affected_doc_types),
                    WorkflowExecution.status.in_(["paused", "running"]),
                )
            )
            .values(
                status="failed",
                pending_user_input=False,
                terminal_outcome="cancelled_by_rewind",
            )
        )
        cancelled_count = cancel_result.rowcount
        if cancelled_count > 0:
            logger.info(
                "Rewind cancelled %d in-progress executions for project %s",
                cancelled_count,
                project_id,
            )
        await db.commit()

    # ADR-069: Reason is the living correction brief — always dual-written
    # to both lineage event (audit) and authority record (binding for regeneration).
    from app.domain.repositories.authority_repository import PostgresAuthorityRepository
    from app.domain.services.authority_service import AuthorityService

    auth_repo = PostgresAuthorityRepository(db)
    auth_service = AuthorityService(auth_repo)

    # Normalize applies_to_stages: accept doc_type_ids and convert to canonical stage names
    raw_applies_to = body.applies_to_stages or [stage.name]
    applies_to = []
    invalid_stages = []
    for s in raw_applies_to:
        try:
            applies_to.append(PipelineStage[s.upper()].name)
        except KeyError:
            try:
                applies_to.append(PipelineStage.from_doc_type_id(s).name)
            except ValueError:
                invalid_stages.append(s)
    if invalid_stages:
        valid = [f"{ps.name} ({ps.doc_type_id})" for ps in PipelineStage]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid applies_to_stages: {invalid_stages}. Valid: {valid}",
        )
    # Deduplicate (e.g., if client sends both 'TA' and 'technical_architecture')
    applies_to = list(dict.fromkeys(applies_to))
    if not applies_to:
        applies_to = [stage.name]

    correction_record = await auth_service.record_authority(
        project_id=project_id,
        authority_type="operator_correction",
        stage=stage.name,
        key=f"correction:{stage.name}",
        value={
            "text": body.reason.strip(),
            "applies_to_stages": applies_to,
            "rewind_event_id": str(result.lineage_event_id),
        },
        source_execution_id=result.lineage_event_id,
        lineage_path_id=result.lineage_event_id,
        actor="operator",
    )
    correction_record_id = str(correction_record.id)
    await db.commit()

    logger.info(
        "Rewind correction brief persisted: project=%s, stage=%s, record=%s",
        project_id, stage.name, correction_record_id,
    )

    return RewindResponseBody(
        success=result.success,
        rewind_to_stage=result.rewind_to_stage,
        affected_stages=result.affected_stages,
        affected_document_count=result.affected_document_count,
        stale_document_ids=[str(d) for d in result.stale_document_ids],
        lineage_event_id=str(result.lineage_event_id),
        correction_record_id=correction_record_id,
    )


@router.get(
    "/{project_id}/corrections/{stage}",
    response_model=CorrectionResponse,
)
async def get_correction(
    project_id: UUID,
    stage: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current correction for a (project, stage) pair.

    Used by the UI to pre-populate the correction field on subsequent
    rewinds (ADR-069 §3.2). Returns 404 if no correction exists.

    Accepts both short stage names (TA) and doc_type_ids (technical_architecture).
    """
    from app.domain.models.pipeline_stage import PipelineStage
    from app.domain.repositories.authority_repository import PostgresAuthorityRepository
    from app.domain.services.authority_service import AuthorityService

    # Normalize: accept both short name (TA) and doc_type_id (technical_architecture)
    canonical_stage = stage.upper()
    try:
        PipelineStage[canonical_stage]
    except KeyError:
        try:
            canonical_stage = PipelineStage.from_doc_type_id(stage).name
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage '{stage}'")

    auth_repo = PostgresAuthorityRepository(db)
    auth_service = AuthorityService(auth_repo)

    record = await auth_service.get_current_correction(project_id, canonical_stage)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No correction for stage '{stage}'")

    value = record.value if isinstance(record.value, dict) else {}
    return CorrectionResponse(
        stage=record.stage,
        text=value.get("text", ""),
        applies_to_stages=value.get("applies_to_stages", [record.stage]),
        authority_record_id=str(record.id),
        created_at=record.created_at.isoformat() if record.created_at else "",
    )


class CorrectionUpdateBody(BaseModel):
    """Request body for updating a pending correction before regeneration."""

    text: str = Field(..., description="Updated correction brief text")
    applies_to_stages: Optional[List[str]] = Field(
        default=None, description="Updated stage applicability"
    )


@router.patch(
    "/{project_id}/corrections/{stage}",
    response_model=CorrectionResponse,
)
async def update_correction(
    project_id: UUID,
    stage: str,
    body: CorrectionUpdateBody,
    db: AsyncSession = Depends(get_db),
):
    """Update a pending correction before regeneration (ADR-069).

    Allows the operator to refine the correction brief without
    triggering another rewind. Creates a new authority record
    (superseding the current one) for audit traceability.

    Accepts both short stage names (TA) and doc_type_ids.
    """
    from app.domain.models.pipeline_stage import PipelineStage
    from app.domain.repositories.authority_repository import PostgresAuthorityRepository
    from app.domain.services.authority_service import AuthorityService

    # Normalize stage
    canonical_stage = stage.upper()
    try:
        PipelineStage[canonical_stage]
    except KeyError:
        try:
            canonical_stage = PipelineStage.from_doc_type_id(stage).name
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage '{stage}'")

    auth_repo = PostgresAuthorityRepository(db)
    auth_service = AuthorityService(auth_repo)

    # Must have an existing correction to update
    existing = await auth_service.get_current_correction(project_id, canonical_stage)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"No correction for stage '{stage}' to update")

    # Preserve rewind_event_id from the original correction
    existing_value = existing.value if isinstance(existing.value, dict) else {}
    rewind_event_id = existing_value.get("rewind_event_id", str(existing.source_execution_id))

    # Normalize applies_to_stages
    raw_applies_to = body.applies_to_stages or existing_value.get("applies_to_stages", [canonical_stage])
    applies_to = []
    for s in raw_applies_to:
        try:
            applies_to.append(PipelineStage[s.upper()].name)
        except KeyError:
            try:
                applies_to.append(PipelineStage.from_doc_type_id(s).name)
            except ValueError:
                pass  # drop invalid values silently on update
    applies_to = list(dict.fromkeys(applies_to)) or [canonical_stage]

    # Create new record (supersedes existing via record_authority)
    new_record = await auth_service.record_authority(
        project_id=project_id,
        authority_type="operator_correction",
        stage=canonical_stage,
        key=f"correction:{canonical_stage}",
        value={
            "text": body.text.strip(),
            "applies_to_stages": applies_to,
            "rewind_event_id": rewind_event_id,
        },
        source_execution_id=existing.source_execution_id,
        lineage_path_id=existing.lineage_path_id,
        actor="operator",
    )
    await db.commit()

    return CorrectionResponse(
        stage=new_record.stage,
        text=new_record.value.get("text", ""),
        applies_to_stages=new_record.value.get("applies_to_stages", [canonical_stage]),
        authority_record_id=str(new_record.id),
        created_at=new_record.created_at.isoformat() if new_record.created_at else "",
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
    from app.domain.models.pipeline_stage import PipelineStage
    from app.domain.services.regeneration_service import RegenerationRequest

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
    from app.domain.models.pipeline_stage import PipelineStage
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


# ============================================================================
# Timeline (ADR-067)
# ============================================================================


@router.get("/{project_id}/timeline")
async def get_project_timeline(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full project history timeline — documents + lineage events.

    Returns a chronological list of all document versions and lineage events
    for a project. Excludes archived documents per ADR-067.
    """
    from sqlalchemy import select
    from app.api.models.document import Document
    from app.api.v1.dependencies import resolve_project as _resolve_project

    project = await _resolve_project(project_id, db)
    project_uuid = project.id

    # Get all document versions (exclude archived per ADR-067)
    result = await db.execute(
        select(Document).where(
            Document.space_type == "project",
            Document.space_id == project_uuid,
            Document.status != "archived",
        ).order_by(Document.created_at)
    )
    docs = result.scalars().all()

    # Get lineage events
    from app.api.models.lineage_event import LineageEventModel
    events_result = await db.execute(
        select(LineageEventModel).where(
            LineageEventModel.project_id == project_uuid,
        ).order_by(LineageEventModel.created_at)
    )
    events = events_result.scalars().all()

    # Build timeline entries
    timeline = []

    for doc in docs:
        entry = {
            "type": "document",
            "id": str(doc.id),
            "doc_type_id": doc.doc_type_id,
            "display_id": doc.display_id,
            "version": doc.version,
            "title": doc.title,
            "is_latest": doc.is_latest,
            "is_stale": doc.is_stale,
            "lifecycle_state": doc.lifecycle_state,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "parent_document_id": str(doc.parent_document_id) if doc.parent_document_id else None,
        }
        # WS/WP hierarchy: include parent_wp_id for grouping in timeline graph
        content = doc.content if isinstance(doc.content, dict) else {}
        if doc.doc_type_id == "work_statement" and content.get("parent_wp_id"):
            entry["parent_wp_id"] = content["parent_wp_id"]
        timeline.append(entry)

    for evt in events:
        timeline.append({
            "type": "event",
            "id": str(evt.id),
            "event_type": evt.event_type,
            "rewind_to_stage": evt.rewind_to_stage,
            "reason": evt.reason,
            "actor": evt.actor,
            "affected_document_count": len(evt.affected_document_ids or []),
            "affected_document_ids": [str(aid) for aid in (evt.affected_document_ids or [])],
            "created_at": evt.created_at.isoformat() if evt.created_at else None,
        })

    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("created_at") or "")

    # Authoritative active document IDs — the frontend should use this
    # instead of heuristically guessing the active thread
    active_doc_ids = [str(doc.id) for doc in docs if doc.is_latest]

    from fastapi.responses import JSONResponse
    return JSONResponse({
        "project_id": project_id,
        "entry_count": len(timeline),
        "active_document_ids": active_doc_ids,
        "timeline": timeline,
    })


# ============================================================================
# Restore Preview + Action (ADR-067)
# ============================================================================


class RestoreRequestBody(BaseModel):
    checkpoint_id: str = Field(..., description="Document ID to restore as checkpoint")
    reason: str = Field(default="Operator restore", description="Reason for restore")


@router.post("/{project_id}/restore")
async def restore_checkpoint(
    project_id: str,
    body: RestoreRequestBody,
    db: AsyncSession = Depends(get_db),
):
    """Restore a lineage path to active state.

    Computes the path from checkpoint, demotes ALL currently active docs
    (not just matching keys), then promotes the path documents.
    Per ADR-067: restore switches the authoritative path globally.
    """
    from app.domain.services.lineage_path_service import (
        compute_lineage_path_from_db,
        PathDocument,
    )
    from app.domain.services.restore_preview_service import evaluate_restore_preview
    from sqlalchemy import select
    from app.api.models.document import Document
    from app.api.models.lineage_event import LineageEventModel
    from app.api.v1.dependencies import resolve_project as _resolve_project
    from datetime import datetime, timezone as tz

    project = await _resolve_project(project_id, db)
    project_uuid = project.id

    try:
        checkpoint_uuid = UUID(body.checkpoint_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid checkpoint_id format")

    # Compute the path
    path = await compute_lineage_path_from_db(db, project_uuid, checkpoint_uuid)
    if path is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Get ALL current is_latest docs for preview and demotion
    current_result = await db.execute(
        select(Document).where(
            Document.space_type == "project",
            Document.space_id == project_uuid,
            Document.is_latest == True,  # noqa: E712
        )
    )
    current_orm_docs = current_result.scalars().all()
    current_docs = [
        PathDocument(
            id=d.id, doc_type_id=d.doc_type_id,
            display_id=d.display_id or "", version=d.version,
            title=d.title or "", is_latest=d.is_latest,
            is_stale=d.is_stale, lifecycle_state=d.lifecycle_state or "complete",
            created_at=d.created_at, parent_document_id=d.parent_document_id,
        )
        for d in current_orm_docs
    ]

    # Preview
    preview = evaluate_restore_preview(path, current_docs)

    # Execute restore: demote ALL current docs not in the path
    path_ids = {d.id for d in path.documents}
    demoted_ids = []

    # Re-query for mutation (scalars consumed above)
    demote_result = await db.execute(
        select(Document).where(
            Document.space_type == "project",
            Document.space_id == project_uuid,
            Document.is_latest == True,  # noqa: E712
        )
    )
    for doc_orm in demote_result.scalars().all():
        if doc_orm.id not in path_ids:
            doc_orm.is_latest = False
            doc_orm.is_stale = True
            demoted_ids.append(str(doc_orm.id))

    # Promote path docs that aren't already is_latest
    activated_ids = []
    for path_doc in path.documents:
        if not path_doc.is_latest:
            promote_result = await db.execute(
                select(Document).where(Document.id == path_doc.id)
            )
            promote_orm = promote_result.scalar_one_or_none()
            if promote_orm:
                promote_orm.is_latest = True
                promote_orm.is_stale = False
                activated_ids.append(str(promote_orm.id))

    # Record restore event
    from uuid import uuid4
    restore_event = LineageEventModel(
        id=uuid4(),
        project_id=project_uuid,
        event_type="restore",
        rewind_to_stage=path.checkpoint_doc_type,
        reason=body.reason,
        actor="operator",
        affected_document_ids=activated_ids + demoted_ids,
        created_at=datetime.now(tz.utc),
    )
    db.add(restore_event)

    await db.commit()

    from fastapi.responses import JSONResponse
    return JSONResponse({
        "status": "restored",
        "checkpoint_id": body.checkpoint_id,
        "activated": len(activated_ids),
        "demoted": len(demoted_ids),
        "restore_event_id": str(restore_event.id),
        "preview": preview.to_dict(),
    })


# ============================================================================
# Thread Archive (ADR-067)
# ============================================================================


class ArchiveThreadBody(BaseModel):
    event_id: str = Field(..., description="Root rewind event ID of the thread to archive")
    reason: str = Field(default="Operator archive", description="Reason for archiving")


@router.post("/{project_id}/archive-thread")
async def archive_thread(
    project_id: str,
    body: ArchiveThreadBody,
    db: AsyncSession = Depends(get_db),
):
    """Archive a rewind thread (soft-delete with audit stub).

    Identifies thread documents by lineage membership: documents whose
    parent_document_id chain traces to the set of documents affected by
    the root rewind event. Marks them as archived (status='archived',
    is_latest=False) and records an archive event.
    Per ADR-067: archived threads do not appear in normal navigation.
    """
    from sqlalchemy import select
    from app.api.models.lineage_event import LineageEventModel
    from app.api.models.document import Document
    from app.api.v1.dependencies import resolve_project as _resolve_project
    from datetime import datetime, timezone as tz

    project = await _resolve_project(project_id, db)
    project_uuid = project.id

    try:
        event_uuid = UUID(body.event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    # Find the root rewind event
    result = await db.execute(
        select(LineageEventModel).where(
            LineageEventModel.id == event_uuid,
            LineageEventModel.project_id == project_uuid,
        )
    )
    root_event = result.scalar_one_or_none()
    if not root_event:
        raise HTTPException(status_code=404, detail="Rewind event not found")

    # Find documents belonging to this thread via lineage membership.
    # Thread docs = documents whose parent_document_id traces to a document
    # that was invalidated by the root rewind event.
    # The affected_document_ids on the rewind event are the docs that were
    # marked stale. Documents created AFTER the rewind with parent_document_id
    # pointing to the stale set are the thread's descendants.
    affected_ids = set()
    for aid in (root_event.affected_document_ids or []):
        try:
            affected_ids.add(UUID(aid) if isinstance(aid, str) else aid)
        except (ValueError, TypeError):
            pass

    # Get all project documents
    all_docs_result = await db.execute(
        select(Document).where(
            Document.space_type == "project",
            Document.space_id == project_uuid,
        )
    )
    all_docs = all_docs_result.scalars().all()

    # Build parent lookup and find thread members:
    # documents created after the rewind whose parent chain traces to
    # the rewind-affected set or to other thread members
    thread_doc_ids: set = set()
    docs_by_id = {d.id: d for d in all_docs}

    # Seed: documents created after the rewind with parent in affected set
    for doc in all_docs:
        if (doc.created_at and root_event.created_at
                and doc.created_at >= root_event.created_at
                and doc.parent_document_id in affected_ids):
            thread_doc_ids.add(doc.id)

    # Expand: documents whose parent is already in the thread
    changed = True
    while changed:
        changed = False
        for doc in all_docs:
            if doc.id not in thread_doc_ids and doc.parent_document_id in thread_doc_ids:
                thread_doc_ids.add(doc.id)
                changed = True

    thread_docs = [d for d in all_docs if d.id in thread_doc_ids]

    # Safety: cannot archive if any thread doc is currently is_latest
    active_in_thread = [d for d in thread_docs if d.is_latest]
    if active_in_thread:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot archive: {len(active_in_thread)} documents in this thread are currently active",
        )

    # Mark thread documents as archived
    archived_ids = []
    for doc in thread_docs:
        doc.status = "archived"
        doc.is_latest = False
        doc.is_stale = True
        archived_ids.append(str(doc.id))

    # Record archive event
    from uuid import uuid4
    archive_event = LineageEventModel(
        id=uuid4(),
        project_id=project_uuid,
        event_type="archive",
        rewind_to_stage=root_event.rewind_to_stage,
        reason=f"Thread archived: {body.reason}",
        actor="operator",
        affected_document_ids=archived_ids,
        created_at=datetime.now(tz.utc),
    )
    db.add(archive_event)

    await db.commit()

    from fastapi.responses import JSONResponse
    return JSONResponse({
        "status": "archived",
        "thread_root_event_id": body.event_id,
        "archive_event_id": str(archive_event.id),
        "documents_archived": len(archived_ids),
    })
