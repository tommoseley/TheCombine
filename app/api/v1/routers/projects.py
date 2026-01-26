"""Projects API router.

Provides RESTful API for project management:
- GET /api/v1/projects - List projects
- POST /api/v1/projects - Create project
- POST /api/v1/projects/from-intake - Create project from intake workflow
- GET /api/v1/projects/{id} - Get project details
- GET /api/v1/projects/{id}/tree - Get project with documents
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.project import Project
from app.api.services.document_status_service import document_status_service
from app.api.services.project_creation_service import (
    generate_unique_project_id,
    create_project_from_intake as create_project_from_intake_service,
)
from app.core.database import get_db

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


# =============================================================================
# Helper Functions
# =============================================================================

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
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    search: Optional[str] = Query(None, description="Search term for name/project_id"),
    owner_id: Optional[str] = Query(None, description="Filter by owner"),
    include_archived: bool = Query(False, description="Include archived projects"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """List projects with optional filtering."""
    query = select(Project).where(Project.deleted_at.is_(None))

    if not include_archived:
        query = query.where(Project.archived_at.is_(None))

    if owner_id:
        try:
            owner_uuid = UUID(owner_id)
            query = query.where(Project.owner_id == owner_uuid)
        except ValueError:
            pass

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
    owner_id: Optional[str] = Query(None, description="Owner user ID"),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project."""
    project_id = await generate_unique_project_id(db, request.name)

    owner_uuid = None
    if owner_id:
        try:
            owner_uuid = UUID(owner_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid owner_id format",
            )

    project = Project(
        project_id=project_id,
        name=request.name.strip(),
        description=request.description.strip() if request.description else None,
        icon=request.icon,
        owner_id=owner_uuid,
        organization_id=owner_uuid,
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
) -> ProjectResponse:
    """Create a project from completed intake workflow.

    Extracts project_name from the intake document and creates both
    the Project and the concierge_intake Document.
    """
    project = await create_project_from_intake_service(
        db=db,
        intake_document=request.intake_document,
        execution_id=request.execution_id,
        user_id=request.user_id,
    )

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

    return ProjectTreeResponse(
        project=_project_to_response(project),
        documents=documents,
        intake_content=intake_content,
    )
