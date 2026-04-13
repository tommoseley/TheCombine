"""Project workflow instance sub-router (ADR-046).

Handles workflow instance CRUD, drift detection, history, and completion.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import require_auth
from app.auth.models import User
from app.api.services.admin_workbench_service import get_admin_workbench_service
from app.api.services.workflow_instance_service import WorkflowInstanceService
from app.api.v1.routers.projects_common import resolve_project

logger = logging.getLogger(__name__)

router = APIRouter(tags=["project-workflows"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateWorkflowInstanceRequest(BaseModel):
    """Request to assign a workflow to a project."""
    workflow_id: str = Field(..., description="Source POW identifier in combine-config")
    version: str = Field(..., description="Source POW version")


class UpdateWorkflowInstanceRequest(BaseModel):
    """Request to update the effective workflow."""
    effective_workflow: Dict[str, Any] = Field(..., description="Full definition snapshot")


class WorkflowInstanceResponse(BaseModel):
    """Response model for a workflow instance."""
    id: str
    project_id: str
    base_workflow_ref: Dict[str, Any]
    effective_workflow: Dict[str, Any]
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DriftResponse(BaseModel):
    """Computed drift between instance and source."""
    base_workflow_id: str
    base_version: str
    steps_added: List[str]
    steps_removed: List[str]
    steps_reordered: bool
    metadata_changed: bool
    is_drifted: bool


class HistoryEntry(BaseModel):
    """Single audit trail entry."""
    id: str
    change_type: str
    change_detail: Optional[Dict[str, Any]] = None
    changed_at: Optional[str] = None
    changed_by: Optional[str] = None


class WorkflowHistoryResponse(BaseModel):
    """Paginated audit trail."""
    entries: List[HistoryEntry]
    total: int


# =============================================================================
# Private helpers
# =============================================================================

def _get_workflow_instance_service() -> WorkflowInstanceService:
    """Get WorkflowInstanceService with singleton workbench dependency."""
    return WorkflowInstanceService(get_admin_workbench_service())


# =============================================================================
# Workflow Instance Endpoints (ADR-046)
# =============================================================================

@router.post(
    "/{project_id}/workflow",
    response_model=WorkflowInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_instance(
    project_id: str,
    request: CreateWorkflowInstanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> WorkflowInstanceResponse:
    """Create a workflow instance by snapshotting a source POW."""
    project = await resolve_project(project_id, db)
    service = _get_workflow_instance_service()

    try:
        instance = await service.create_instance(
            db=db,
            project_id=project.id,
            workflow_id=request.workflow_id,
            version=request.version,
            changed_by=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return WorkflowInstanceResponse(
        id=str(instance.id),
        project_id=str(instance.project_id),
        base_workflow_ref=instance.base_workflow_ref,
        effective_workflow=instance.effective_workflow,
        status=instance.status,
        created_at=instance.created_at.isoformat() if instance.created_at else None,
        updated_at=instance.updated_at.isoformat() if instance.updated_at else None,
    )


@router.get("/{project_id}/workflow", response_model=WorkflowInstanceResponse)
async def get_workflow_instance(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> WorkflowInstanceResponse:
    """Get the current effective workflow for a project."""
    project = await resolve_project(project_id, db)
    service = _get_workflow_instance_service()

    instance = await service.get_instance(db, project.id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workflow assigned to this project",
        )

    return WorkflowInstanceResponse(
        id=str(instance.id),
        project_id=str(instance.project_id),
        base_workflow_ref=instance.base_workflow_ref,
        effective_workflow=instance.effective_workflow,
        status=instance.status,
        created_at=instance.created_at.isoformat() if instance.created_at else None,
        updated_at=instance.updated_at.isoformat() if instance.updated_at else None,
    )


@router.put("/{project_id}/workflow", response_model=WorkflowInstanceResponse)
async def update_workflow_instance(
    project_id: str,
    request: UpdateWorkflowInstanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> WorkflowInstanceResponse:
    """Update the effective workflow of a project's instance."""
    project = await resolve_project(project_id, db)
    service = _get_workflow_instance_service()

    try:
        instance = await service.update_instance(
            db=db,
            project_id=project.id,
            effective_workflow=request.effective_workflow,
            changed_by=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return WorkflowInstanceResponse(
        id=str(instance.id),
        project_id=str(instance.project_id),
        base_workflow_ref=instance.base_workflow_ref,
        effective_workflow=instance.effective_workflow,
        status=instance.status,
        created_at=instance.created_at.isoformat() if instance.created_at else None,
        updated_at=instance.updated_at.isoformat() if instance.updated_at else None,
    )


@router.get("/{project_id}/workflow/drift", response_model=DriftResponse)
async def get_workflow_drift(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> DriftResponse:
    """Compute drift between instance and its source POW."""
    project = await resolve_project(project_id, db)
    service = _get_workflow_instance_service()

    try:
        drift = await service.compute_drift(db, project.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return DriftResponse(
        base_workflow_id=drift.base_workflow_id,
        base_version=drift.base_version,
        steps_added=drift.steps_added,
        steps_removed=drift.steps_removed,
        steps_reordered=drift.steps_reordered,
        metadata_changed=drift.metadata_changed,
        is_drifted=drift.is_drifted,
    )


@router.get("/{project_id}/workflow/history", response_model=WorkflowHistoryResponse)
async def get_workflow_history(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> WorkflowHistoryResponse:
    """Get audit trail for a project's workflow instance."""
    project = await resolve_project(project_id, db)
    service = _get_workflow_instance_service()

    try:
        entries, total = await service.get_history(
            db, project.id, limit=limit, offset=offset
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return WorkflowHistoryResponse(
        entries=[
            HistoryEntry(
                id=str(e.id),
                change_type=e.change_type,
                change_detail=e.change_detail,
                changed_at=e.changed_at.isoformat() if e.changed_at else None,
                changed_by=e.changed_by,
            )
            for e in entries
        ],
        total=total,
    )


@router.post("/{project_id}/workflow/complete", response_model=WorkflowInstanceResponse)
async def complete_workflow_instance(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> WorkflowInstanceResponse:
    """Mark the workflow instance as completed."""
    project = await resolve_project(project_id, db)
    service = _get_workflow_instance_service()

    try:
        instance = await service.complete_instance(
            db, project.id, changed_by=current_user.email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return WorkflowInstanceResponse(
        id=str(instance.id),
        project_id=str(instance.project_id),
        base_workflow_ref=instance.base_workflow_ref,
        effective_workflow=instance.effective_workflow,
        status=instance.status,
        created_at=instance.created_at.isoformat() if instance.created_at else None,
        updated_at=instance.updated_at.isoformat() if instance.updated_at else None,
    )
