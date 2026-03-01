"""Projects API router.

Provides RESTful API for project management:
- GET /api/v1/projects - List projects
- POST /api/v1/projects - Create project
- POST /api/v1/projects/from-intake - Create project from intake workflow
- GET /api/v1/projects/{id} - Get project details
- GET /api/v1/projects/{id}/tree - Get project with documents
"""

import copy
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.document_type import DocumentType
from app.api.models.project import Project
from app.api.services.document_status_service import document_status_service
from app.api.services.project_creation_service import (
    generate_unique_project_id,
    create_project_from_intake as create_project_from_intake_service,
)
from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.schema_registry_service import SchemaRegistryService
from app.core.database import get_db
from app.auth.dependencies import require_auth
from app.auth.models import User
from app.domain.workflow.interrupt_registry import InterruptRegistry
from app.domain.services.render_model_builder import (
    RenderModelBuilder,
    DocDefNotFoundError,
)
from app.api.models.workflow_instance import WorkflowInstance
from app.api.models.pgc_answer import PGCAnswer
from app.api.models.workflow_execution import WorkflowExecution
from app.api.services.admin_workbench_service import get_admin_workbench_service
from app.api.services.workflow_instance_service import WorkflowInstanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ProjectCreateRequest(BaseModel):
    """Request body for creating a project."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    icon: str = Field(default="folder", max_length=50)


class ProjectFromIntakeRequest(BaseModel):
    """Request body for creating a project from intake workflow."""
    execution_id: str = Field(..., description="Workflow execution ID")
    intake_document: Dict[str, Any] = Field(..., description="Intake document content")
    user_id: Optional[str] = Field(None, description="Owner user ID")
    workflow_id: Optional[str] = Field(None, description="Source POW to assign (optional)")
    workflow_version: Optional[str] = Field(None, description="Source POW version (required if workflow_id set)")


class ProjectUpdateRequest(BaseModel):
    """Request body for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Partial metadata merge")


class ProjectResponse(BaseModel):
    """Response model for a project."""
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    icon: str = "folder"
    status: str = "active"
    owner_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_archived: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ProjectListResponse(BaseModel):
    """Response model for project list."""
    projects: List[ProjectResponse]
    total: int
    offset: int
    limit: int


class ProjectTreeResponse(BaseModel):
    """Response model for project with documents."""
    project: ProjectResponse
    documents: List[Dict[str, Any]]
    intake_content: Optional[Dict[str, Any]] = None
    has_workflow: bool = False
    workflow_status: Optional[str] = None


# -- Workflow Instance models (ADR-046) --

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
# Helper Functions
# =============================================================================

def _get_workflow_instance_service() -> WorkflowInstanceService:
    """Get WorkflowInstanceService with singleton workbench dependency."""
    return WorkflowInstanceService(get_admin_workbench_service())


async def _resolve_project(project_id: str, db: AsyncSession) -> Project:
    """Resolve a project by UUID or project_id. Raises 404 if not found."""
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.deleted_at.is_(None),
            )
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(
                Project.project_id == project_id,
                Project.deleted_at.is_(None),
            )
        )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


def _project_to_response(project: Project) -> ProjectResponse:
    """Convert Project ORM object to response model."""
    return ProjectResponse(
        id=str(project.id),
        project_id=project.project_id,
        name=project.name or "",
        description=project.description,
        icon=project.icon or "folder",
        status=project.status or "active",
        owner_id=str(project.owner_id) if project.owner_id else None,
        created_at=project.created_at.isoformat() if project.created_at else None,
        updated_at=project.updated_at.isoformat() if project.updated_at else None,
        is_archived=project.archived_at is not None,
        metadata=project.meta,
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    search: Optional[str] = Query(None, description="Search term for name/project_id"),
    include_archived: bool = Query(False, description="Include archived projects"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ProjectListResponse:
    """List projects for the current user."""
    query = select(Project).where(Project.deleted_at.is_(None))

    # Filter by current user's projects
    query = query.where(Project.owner_id == current_user.user_id)

    if not include_archived:
        query = query.where(Project.archived_at.is_(None))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Project.name.ilike(search_pattern),
                Project.project_id.ilike(search_pattern),
            )
        )

    # Get total count
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(Project.archived_at.nulls_first(), Project.name.asc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectListResponse(
        projects=[_project_to_response(p) for p in projects],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ProjectResponse:
    """Create a new project for the current user."""
    project_id = await generate_unique_project_id(db, request.name)

    project = Project(
        project_id=project_id,
        name=request.name.strip(),
        description=request.description.strip() if request.description else None,
        icon=request.icon,
        owner_id=current_user.user_id,
        organization_id=current_user.user_id,
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Created project {project_id}: {request.name}")
    return _project_to_response(project)


@router.post("/from-intake", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_from_intake(
    request: ProjectFromIntakeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ProjectResponse:
    """Create a project from completed intake workflow.

    Extracts project_name from the intake document and creates both
    the Project and the concierge_intake Document. Optionally assigns
    a workflow instance if workflow_id is provided.
    """
    project = await create_project_from_intake_service(
        db=db,
        intake_document=request.intake_document,
        execution_id=request.execution_id,
        user_id=str(current_user.user_id),
    )

    # Optionally assign a workflow instance (ADR-046 Phase 6)
    if request.workflow_id and request.workflow_version:
        try:
            service = _get_workflow_instance_service()
            await service.create_instance(
                db=db,
                project_id=project.id,
                workflow_id=request.workflow_id,
                version=request.workflow_version,
                changed_by=current_user.email,
            )
            logger.info(
                f"Assigned workflow {request.workflow_id} v{request.workflow_version} "
                f"to project {project.project_id}"
            )
        except ValueError as e:
            logger.warning(f"Could not assign workflow to new project: {e}")

    return _project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Get project by ID (UUID or project_id)."""
    # Try UUID first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
    except ValueError:
        # Fall back to project_id
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    return _project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update project properties (name, description, icon)."""
    # Try UUID first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.deleted_at.is_(None),
            )
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(
                Project.project_id == project_id,
                Project.deleted_at.is_(None),
            )
        )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Update provided fields
    if request.name is not None:
        project.name = request.name.strip()
    if request.description is not None:
        project.description = request.description.strip() if request.description else None
    if request.icon is not None:
        project.icon = request.icon
    if request.metadata is not None:
        current = dict(project.meta or {})
        current.update(request.metadata)
        project.meta = current

    await db.commit()
    await db.refresh(project)

    logger.info(f"Updated project {project.project_id}")
    return _project_to_response(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Archive a project (soft hide, reversible)."""
    # Try UUID first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.deleted_at.is_(None),
            )
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(
                Project.project_id == project_id,
                Project.deleted_at.is_(None),
            )
        )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    if project.archived_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is already archived",
        )

    project.archived_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Archived project {project.project_id}")
    return _project_to_response(project)


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Restore an archived project."""
    # Try UUID first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.deleted_at.is_(None),
            )
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(
                Project.project_id == project_id,
                Project.deleted_at.is_(None),
            )
        )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    if not project.archived_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not archived",
        )

    project.archived_at = None
    await db.commit()
    await db.refresh(project)

    logger.info(f"Unarchived project {project.project_id}")
    return _project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a project (not reversible through API)."""
    # Try UUID first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.deleted_at.is_(None),
            )
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(
                Project.project_id == project_id,
                Project.deleted_at.is_(None),
            )
        )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    project.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Deleted project {project.project_id}")


@router.get("/{project_id}/tree", response_model=ProjectTreeResponse)
async def get_project_tree(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectTreeResponse:
    """Get project with documents and status."""
    # Try UUID first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )

    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Get document statuses
    document_statuses = await document_status_service.get_project_document_statuses(db, project.id)

    documents = []
    for doc in document_statuses:
        if hasattr(doc, 'readiness'):
            documents.append({
                "doc_type_id": doc.doc_type_id,
                "title": doc.title,
                "icon": doc.icon,
                "readiness": doc.readiness,
                "acceptance_state": getattr(doc, 'acceptance_state', None),
                "subtitle": getattr(doc, 'subtitle', None),
            })
        else:
            documents.append(doc)

    # Get intake content
    intake_content = None
    intake_result = await db.execute(
        select(Document).where(
            and_(
                Document.space_type == "project",
                Document.space_id == project.id,
                Document.doc_type_id == "concierge_intake",
                Document.is_latest == True,
            )
        )
    )
    intake_doc = intake_result.scalar_one_or_none()
    if intake_doc and intake_doc.content:
        intake_content = intake_doc.content
    else:
        # Fallback to project_discovery
        discovery_result = await db.execute(
            select(Document).where(
                and_(
                    Document.space_type == "project",
                    Document.space_id == project.id,
                    Document.doc_type_id == "project_discovery",
                    Document.is_latest == True,
                )
            )
        )
        discovery_doc = discovery_result.scalar_one_or_none()
        if discovery_doc and discovery_doc.content:
            intake_content = discovery_doc.content

    # Check workflow instance assignment (ADR-046 Phase 6)
    wf_result = await db.execute(
        select(WorkflowInstance.status).where(
            WorkflowInstance.project_id == project.id,
        )
    )
    wf_row = wf_result.one_or_none()
    has_workflow = wf_row is not None
    workflow_status = wf_row[0] if wf_row else None

    return ProjectTreeResponse(
        project=_project_to_response(project),
        documents=documents,
        intake_content=intake_content,
        has_workflow=has_workflow,
        workflow_status=workflow_status,
    )


@router.get("/{project_id}/interrupts")
async def get_project_interrupts(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get pending operator interrupts for a project.

    Returns list of interrupts requiring operator action:
    - Clarification requests (PGC nodes)
    - Audit reviews (QA failures)
    - Constraint conflicts
    - Escalations (circuit breaker)

    Used by Production Line UI to show pending actions.
    """
    registry = InterruptRegistry(db)
    interrupts = await registry.get_pending(project_id)
    return [i.to_dict() for i in interrupts]


@router.get("/{project_id}/documents/{doc_type_id}")
async def get_project_document(
    project_id: str,
    doc_type_id: str,
    instance_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get document content for a project.

    Returns the full document content as JSON for the SPA viewer.
    When instance_id is provided, filters to that specific instance
    (needed for multi-instance doc types like epics).
    """
    # Try UUID first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )

    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Get the latest document of this type
    query = (
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == doc_type_id)
        .where(Document.is_latest == True)
    )
    if instance_id:
        query = query.where(Document.instance_id == instance_id)
    doc_result = await db.execute(query)
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_type_id}' not found for project",
        )

    return {
        "id": str(document.id),
        "doc_type_id": document.doc_type_id,
        "title": document.title,
        "content": document.content,
        "summary": document.summary,
        "version": document.version,
        "status": document.status,
        "lifecycle_state": document.lifecycle_state if document.lifecycle_state else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "accepted_at": document.accepted_at.isoformat() if document.accepted_at else None,
        "accepted_by": document.accepted_by,
    }


@router.get("/{project_id}/documents/{doc_type_id}/render-model")
async def get_document_render_model(
    project_id: str,
    doc_type_id: str,
    instance_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get RenderModel for a document.

    Returns the data-driven RenderModel structure that can be used
    by any frontend (React, HTMX, etc.) to render the document.

    The RenderModel includes:
    - sections: Ordered list of sections with blocks
    - metadata: Document metadata and schema info
    - title/subtitle: Display information

    When instance_id is provided, filters to that specific instance
    (needed for multi-instance doc types like epics).
    """
    # Get project
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )

    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Get the document
    doc_query = (
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == doc_type_id)
        .where(Document.is_latest == True)
    )
    if instance_id:
        doc_query = doc_query.where(Document.instance_id == instance_id)
    doc_result = await db.execute(doc_query)
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_type_id}' not found for project",
        )

    if not document.content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_type_id}' has no content",
        )

    # Get the DocumentType to find view_docdef
    doc_type_result = await db.execute(
        select(DocumentType).where(DocumentType.doc_type_id == doc_type_id)
    )
    doc_type = doc_type_result.scalar_one_or_none()

    # Load package from combine-config (authoritative source for rendering config)
    _package = None
    try:
        from app.config.package_loader import get_package_loader
        _package = get_package_loader().get_document_type(doc_type_id)
    except Exception:
        pass  # combine-config lookup is best-effort

    # combine-config is authoritative for view_docdef; DB is legacy fallback
    if _package:
        view_docdef = _package.view_docdef
    else:
        view_docdef = doc_type.view_docdef if doc_type else None

    # Helper: build common metadata dict for all response paths
    async def _build_doc_metadata() -> Dict[str, Any]:
        meta: Dict[str, Any] = {
            "document_type": doc_type_id,
            "document_type_name": doc_type.name if doc_type else None,
            "version": document.version,
            "lifecycle_state": document.lifecycle_state,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "created_by": document.created_by,
        }
        # Look up the workflow execution that produced this document
        exec_id = None
        for query in [
            select(WorkflowExecution.execution_id)
            .where(WorkflowExecution.project_id == project.id)
            .where(WorkflowExecution.workflow_id == doc_type_id)
            .where(WorkflowExecution.status == "completed")
            .order_by(WorkflowExecution.execution_id.desc())
            .limit(1),
            select(WorkflowExecution.execution_id)
            .where(WorkflowExecution.project_id == project.id)
            .where(WorkflowExecution.workflow_id == doc_type_id)
            .order_by(WorkflowExecution.execution_id.desc())
            .limit(1),
            select(WorkflowExecution.execution_id)
            .where(WorkflowExecution.document_id == str(document.id))
            .order_by(WorkflowExecution.execution_id.desc())
            .limit(1),
        ]:
            result = await db.execute(query)
            exec_id = result.scalar_one_or_none()
            if exec_id:
                break
        if exec_id:
            meta["execution_id"] = exec_id
        return meta

    # Helper: inject IA config from package.yaml (ADR-054) into any response dict
    def _inject_ia_config(response_dict: Dict[str, Any]) -> None:
        if _package:
            if _package.rendering:
                response_dict["rendering_config"] = _package.rendering
            if _package.information_architecture:
                response_dict["information_architecture"] = _package.information_architecture

    # Unwrap document content if stored in raw envelope format
    from app.api.v1.services.render_pure import unwrap_raw_envelope
    document_data = unwrap_raw_envelope(document.content)
    if document_data is document.content and isinstance(document_data, dict) and document_data.get("raw"):
        logger.warning(f"Failed to parse raw content JSON for {doc_type_id}")

    # Apply handler transform at render time (computed fields like associated_risks)
    if isinstance(document_data, dict):
        try:
            from app.domain.handlers.registry import handler_exists, get_handler
            if handler_exists(doc_type_id):
                _handler = get_handler(doc_type_id)
                document_data = _handler.transform(document_data)
        except Exception:
            pass  # Handler transform is best-effort at render time

    # Snapshot for IA-driven rendering (schema-canonical names).
    # The docdef normalization below may reverse field names for the old
    # RenderModel builder; raw_content must keep canonical names for the
    # IA block renderer in the SPA.
    ia_raw_content = copy.deepcopy(document_data) if isinstance(document_data, dict) else document_data

    if not view_docdef:
        # No view_docdef configured - return raw content wrapped in basic structure
        meta = await _build_doc_metadata()
        meta["fallback"] = True
        meta["reason"] = "no_view_docdef"
        result = {
            "render_model_version": "1.0",
            "schema_id": "schema:RenderModelV1",
            "document_id": str(document.id),
            "document_type": doc_type_id,
            "title": document.title or doc_type_id,
            "sections": [],
            "metadata": meta,
            "raw_content": ia_raw_content,
        }
        _inject_ia_config(result)
        return result

    # Normalize LLM output keys to match docdef source pointers
    if isinstance(document_data, dict):
        from app.api.v1.services.render_pure import normalize_document_keys
        normalize_document_keys(document_data)

    # Build the RenderModel
    try:
        docdef_service = DocumentDefinitionService(db)
        component_service = ComponentRegistryService(db)
        schema_service = SchemaRegistryService(db)

        builder = RenderModelBuilder(
            docdef_service=docdef_service,
            component_service=component_service,
            schema_service=schema_service,
        )

        # Determine best title
        from app.api.v1.services.render_pure import resolve_display_title
        display_title = resolve_display_title(document.title, document_data)

        render_model = await builder.build(
            document_def_id=view_docdef,
            document_data=document_data,
            document_id=str(document.id),
            title=display_title,
            lifecycle_state=document.lifecycle_state,
        )

        result_dict = render_model.to_dict()

        # Always include raw_content so SPA can use IA-driven rendering
        # even when DocDef sections are incomplete (e.g. workflows)
        result_dict["raw_content"] = ia_raw_content

        # Inject rendering config from package.yaml (ADR-054)
        _inject_ia_config(result_dict)

        # Inject document metadata for header display
        doc_meta = await _build_doc_metadata()
        meta = result_dict.setdefault("metadata", {})
        meta.update(doc_meta)

        # Query spawned child documents for this document
        child_result = await db.execute(
            select(Document)
            .where(Document.parent_document_id == document.id)
            .where(Document.is_latest == True)
        )
        child_docs = child_result.scalars().all()
        if child_docs:
            meta["spawned_children"] = {
                "count": len(child_docs),
                "items": [
                    {
                        "instance_id": cd.instance_id,
                        "epic_id": cd.content.get("epic_id", "") if isinstance(cd.content, dict) else "",
                        "name": cd.content.get("name", cd.title) if isinstance(cd.content, dict) else cd.title,
                        "title": cd.title,
                        "doc_type_id": cd.doc_type_id,
                    }
                    for cd in child_docs
                ],
            }

        return result_dict

    except DocDefNotFoundError as e:
        logger.warning(f"DocDef not found for {doc_type_id}: {e}")
        # Return fallback with raw content (unwrapped) and IA config
        meta = await _build_doc_metadata()
        meta["fallback"] = True
        meta["reason"] = "docdef_not_found"
        meta["view_docdef"] = view_docdef
        result = {
            "render_model_version": "1.0",
            "schema_id": "schema:RenderModelV1",
            "document_id": str(document.id),
            "document_type": doc_type_id,
            "title": display_title or doc_type_id,
            "sections": [],
            "metadata": meta,
            "raw_content": ia_raw_content,
        }
        _inject_ia_config(result)
        return result
    except Exception as e:
        logger.error(f"Failed to build RenderModel for {doc_type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build render model: {str(e)}",
        )


@router.get("/{project_id}/documents/{doc_type_id}/pgc")
async def get_document_pgc_context(
    project_id: str,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get PGC (Pre-Generation Clarification) context for a document.

    Returns the PGC questions (with why_it_matters rationale) and the
    operator's answers. Checks two sources:
    1. pgc_answers table (newer executions)
    2. workflow_executions.context_state (older executions)
    """
    project = await _resolve_project(project_id, db)

    # Source 1: pgc_answers table (newer format)
    result = await db.execute(
        select(PGCAnswer)
        .where(PGCAnswer.project_id == project.id)
        .where(PGCAnswer.workflow_id == doc_type_id)
        .order_by(PGCAnswer.created_at.desc())
        .limit(1)
    )
    pgc_answer = result.scalar_one_or_none()

    if pgc_answer:
        clarifications = _build_pgc_from_answers_table(pgc_answer)
        return {
            "clarifications": clarifications,
            "has_pgc": True,
            "execution_id": pgc_answer.execution_id,
            "created_at": pgc_answer.created_at.isoformat() if pgc_answer.created_at else None,
        }

    # Source 2: workflow_executions context_state (older format)
    we_result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.project_id == project.id)
        .where(WorkflowExecution.document_type == doc_type_id)
        .where(WorkflowExecution.status == "completed")
        .order_by(WorkflowExecution.execution_id.desc())
        .limit(1)
    )
    execution = we_result.scalar_one_or_none()

    if execution and execution.context_state:
        clarifications = _build_pgc_from_context_state(execution.context_state)
        if clarifications:
            return {
                "clarifications": clarifications,
                "has_pgc": True,
                "execution_id": execution.execution_id,
                "created_at": None,
            }

    return {"clarifications": [], "has_pgc": False}


def _repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to repair truncated JSON from LLM output."""
    from app.api.v1.services.render_pure import repair_truncated_json
    return repair_truncated_json(text)


def _build_pgc_from_answers_table(pgc_answer: PGCAnswer) -> List[Dict[str, Any]]:
    """Build clarifications from pgc_answers table (newer format)."""
    from app.api.v1.services.pgc_pure import build_pgc_from_answers
    return build_pgc_from_answers(pgc_answer.questions or [], pgc_answer.answers or {})


def _build_pgc_from_context_state(context_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build clarifications from workflow execution context_state (older format)."""
    from app.api.v1.services.pgc_pure import build_pgc_from_context_state
    return build_pgc_from_context_state(context_state)


def _resolve_answer_label(question: Dict[str, Any], user_answer: Any) -> Optional[str]:
    """Resolve human-readable answer label from question choices."""
    from app.api.v1.services.pgc_pure import resolve_answer_label
    return resolve_answer_label(question, user_answer)


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
    project = await _resolve_project(project_id, db)
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
    project = await _resolve_project(project_id, db)
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
    project = await _resolve_project(project_id, db)
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
    project = await _resolve_project(project_id, db)
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
    project = await _resolve_project(project_id, db)
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
    project = await _resolve_project(project_id, db)
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


# =============================================================================
# Work Packages
# =============================================================================

class WorkPackageResponse(BaseModel):
    """Response model for a governed work package."""
    id: str
    wp_id: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    state: Optional[str] = None
    ws_count: int = 0
    provenance: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


@router.get("/{project_id}/work-packages")
async def list_work_packages(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> List[WorkPackageResponse]:
    """List governed work packages for a project."""
    project = await _resolve_project(project_id, db)

    result = await db.execute(
        select(Document)
        .where(Document.space_type == 'project')
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == 'work_package')
        .where(Document.is_latest == True)
        .order_by(Document.created_at)
    )
    docs = result.scalars().all()

    # Count work statements per WP
    ws_counts: Dict[str, int] = {}
    if docs:
        ws_result = await db.execute(
            select(Document)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id == 'work_statement')
            .where(Document.is_latest == True)
        )
        for ws in ws_result.scalars().all():
            parent = (ws.content or {}).get('parent_wp_id', '')
            if parent:
                ws_counts[parent] = ws_counts.get(parent, 0) + 1

    return [
        WorkPackageResponse(
            id=str(doc.id),
            wp_id=doc.instance_id or str(doc.id)[:8],
            title=(doc.content or {}).get('title'),
            name=(doc.content or {}).get('name', doc.instance_id),
            state=(doc.content or {}).get('state', 'ready'),
            ws_count=ws_counts.get(str(doc.id), 0),
            provenance=(doc.content or {}).get('provenance'),
            created_at=doc.created_at.isoformat() if doc.created_at else None,
        )
        for doc in docs
    ]


@router.post("/{project_id}/work-packages/generate")
async def generate_work_packages(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Dict[str, Any]:
    """Trigger LLM generation of governed work packages from IP candidates + TA."""
    project = await _resolve_project(project_id, db)

    # Placeholder: In a future WS, this will invoke the work_package_handler
    # to decompose IP candidates into governed WPs with TA bindings.
    logger.info(
        "Work package generation requested for project %s by %s",
        project.id, current_user.email,
    )

    return {
        "status": "accepted",
        "message": "Work package generation is not yet implemented. "
                   "This endpoint will invoke the WP handler in a future release.",
    }


@router.get("/{project_id}/work-packages/{wp_id}/work-statements")
async def list_work_statements(
    project_id: str,
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> List[Dict[str, Any]]:
    """List work statements for a governed work package."""
    project = await _resolve_project(project_id, db)

    result = await db.execute(
        select(Document)
        .where(Document.space_type == 'project')
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == 'work_statement')
        .where(Document.is_latest == True)
    )
    ws_docs = result.scalars().all()

    # Filter to WSs belonging to this WP
    statements = []
    for doc in ws_docs:
        content = doc.content or {}
        parent = content.get('parent_wp_id', '')
        if parent == wp_id or str(doc.id).startswith(wp_id):
            statements.append({
                "id": str(doc.id),
                "ws_id": doc.instance_id or str(doc.id)[:8],
                "title": content.get('title'),
                "state": content.get('state', 'ready'),
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            })

    return statements


@router.post("/{project_id}/work-packages/{wp_id}/work-statements/generate")
async def generate_work_statements(
    project_id: str,
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Dict[str, Any]:
    """Trigger LLM decomposition of a work package into work statements."""
    project = await _resolve_project(project_id, db)

    logger.info(
        "Work statement generation requested for WP %s in project %s by %s",
        wp_id, project.id, current_user.email,
    )

    return {
        "status": "accepted",
        "message": "Work statement generation is not yet implemented. "
                   "This endpoint will invoke the WS handler in a future release.",
    }
