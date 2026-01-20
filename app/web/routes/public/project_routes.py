"""
Project routes for The Combine UI - With User Ownership
Uses SQLAlchemy ORM instead of raw SQL.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from ..shared import templates
from app.api.models.project import Project
from app.api.services.document_status_service import document_status_service
from app.auth.dependencies import require_auth
from app.auth.models import User

from app.core.audit_service import audit_service
from app.core.dependencies.archive import verify_project_not_archived

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_user_id(user: User) -> str:
    """Get the user's ID as string."""
    for field_name in ['id', 'user_id', 'uuid', 'pk']:
        if hasattr(user, field_name):
            value = getattr(user, field_name)
            return str(value) if value else None
    
    available_attrs = [attr for attr in dir(user) if not attr.startswith('_')]
    raise AttributeError(
        f"User model has no 'id' attribute. Available: {available_attrs}"
    )


def _get_user_uuid(user: User) -> UUID:
    """Get user ID as UUID object."""
    return UUID(_get_user_id(user))


def _project_to_dict(project: Project) -> dict:
    """Convert Project ORM object to dict for templates."""
    return {
        "id": str(project.id),
        "name": project.name,
        "project_id": project.project_id,
        "description": project.description,
        "icon": project.icon or "folder",
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "owner_id": str(project.owner_id) if project.owner_id else None,
        "archived_at": project.archived_at,
        "archived_by": str(project.archived_by) if project.archived_by else None,
        "archived_reason": project.archived_reason,
        "is_archived": project.archived_at is not None,
    }


def _get_project_id_condition(project_id: str):
    """Get the appropriate WHERE condition for project lookup.
    
    Handles both UUID (id column) and string (project_id column).
    """
    try:
        project_uuid = UUID(project_id)
        return Project.id == project_uuid
    except (ValueError, TypeError):
        return Project.project_id == project_id


async def _get_project_with_icon(db: AsyncSession, project_id: str, user: User) -> dict | None:
    """Get project with ownership check via ORM.
    
    Handles both UUID (id column) and string (project_id column) lookups.
    """
    user_uuid = _get_user_uuid(user)
    
    result = await db.execute(
        select(Project).where(
            and_(
                _get_project_id_condition(project_id),
                Project.owner_id == user_uuid
            )
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        return None
    
    return _project_to_dict(project)


def _is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"

# ============================================================================
# STATIC ROUTES (must come BEFORE parameterized routes)
# ============================================================================

@router.get("/new", response_class=HTMLResponse)
async def new_project_form(
    request: Request,
    current_user: User = Depends(require_auth)
):
    """Redirect to intake flow."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/start", status_code=302)


@router.get("/list", response_class=HTMLResponse)
async def get_project_list(
    request: Request,
    current_user: User = Depends(require_auth),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get list of projects for sidebar via ORM."""
    user_uuid = _get_user_uuid(current_user)
    
    query = select(Project).where(Project.owner_id == user_uuid)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Project.name.ilike(search_pattern),
                Project.project_id.ilike(search_pattern)
            )
        )
    
    query = query.order_by(Project.archived_at.nulls_first(), Project.name.asc())
    
    result = await db.execute(query)
    rows = result.scalars().all()
    
    projects = [
        {
            "id": str(row.id), 
            "name": row.name, 
            "project_id": row.project_id, 
            "icon": row.icon or "folder",
            "is_archived": row.archived_at is not None
        }
        for row in rows
    ]
    
    return templates.TemplateResponse(request, "public/components/project_list.html", {
        "projects": projects
    })


@router.get("/tree", response_class=HTMLResponse)
async def get_project_tree(
    request: Request,
    current_user: User = Depends(require_auth),
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get project tree with documents via ORM."""
    user_uuid = _get_user_uuid(current_user)
    
    query = (
        select(Project)
        .where(Project.owner_id == user_uuid)
        .order_by(Project.archived_at.nulls_first(), Project.name.asc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(query)
    rows = result.scalars().all()
    
    projects = []
    
    for row in rows:
        project_uuid = row.id
        is_archived = row.archived_at is not None
        
        document_statuses = await document_status_service.get_project_document_statuses(db, project_uuid)
        
        status_summary = {"ready": 0, "stale": 0, "blocked": 0, "waiting": 0, "needs_acceptance": 0}
        
        documents = []
        for doc in document_statuses:
            if hasattr(doc, 'readiness'):
                documents.append({
                    "doc_type_id": doc.doc_type_id,
                    "title": doc.title,
                    "icon": doc.icon,
                    "readiness": doc.readiness,
                    "acceptance_state": getattr(doc, 'acceptance_state', None),
                    "subtitle": getattr(doc, 'subtitle', None)
                })
            else:
                documents.append(doc)
        
        projects.append({
            "id": str(project_uuid),
            "name": row.name,
            "project_id": row.project_id,
            "icon": row.icon or "folder",
            "documents": documents,
            "status_summary": status_summary,
            "is_archived": is_archived
        })
    
    return templates.TemplateResponse(request, "public/components/project_list.html", {
        "projects": projects
    })

@router.post("/create", response_class=HTMLResponse)
async def create_project_handler(
    request: Request,
    current_user: User = Depends(require_auth),
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("folder"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project via ORM (legacy route)."""
    user_uuid = _get_user_uuid(current_user)
    user_id = _get_user_id(current_user)
    
    try:
        project = Project(
            project_id=name.strip().upper().replace(" ", "_")[:20],
            name=name.strip(),
            description=description.strip(),
            icon=icon,
            owner_id=user_uuid,
            organization_id=user_uuid,
            created_by=user_id,
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        return templates.TemplateResponse(request, "public/components/alerts/success.html", {
                "title": "Project Created",
                "message": f'Project "{name}" has been created.',
            },
            headers={"HX-Redirect": f"/projects/{project.project_id}"}
        )
        
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        return templates.TemplateResponse(request, "public/components/alerts/error.html", {
            "title": "Error Creating Project",
            "message": str(e)
        })


@router.post("/{project_id}/archive", response_class=HTMLResponse)
async def archive_project(
    request: Request,
    project_id: str,
    current_user: User = Depends(require_auth),
    reason: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Archive a project via ORM."""
    user_uuid = _get_user_uuid(current_user)
    
    try:
        result = await db.execute(
            select(Project).where(
                and_(_get_project_id_condition(project_id), Project.owner_id == user_uuid)
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        if project.archived_at is not None:
            raise HTTPException(status_code=400, detail="Project is already archived")
        
        project.archived_at = datetime.now(timezone.utc)
        project.archived_by = user_uuid
        project.archived_reason = reason.strip() if reason else None
        
        await audit_service.log_event(
            db=db,
            project_id=project.id,
            action='ARCHIVED',
            actor_user_id=user_uuid,
            reason=reason.strip() if reason else None,
            metadata={'client': 'web', 'ui_source': 'edit_modal'},
            correlation_id=request.headers.get('X-Request-ID')
        )
        
        await db.commit()
        
        return templates.TemplateResponse(request, "public/components/alerts/success.html", {
                "title": "Project Archived",
                "message": "The project has been archived and is now read-only.",
            },
            headers={"HX-Redirect": f"/projects/{project_id}", "HX-Trigger": "refreshProjectList"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving project: {e}", exc_info=True)
        await db.rollback()
        return templates.TemplateResponse(request, "public/components/alerts/error.html", {
            "title": "Error Archiving Project",
            "message": str(e)
        })

@router.post("/{project_id}/unarchive", response_class=HTMLResponse)
async def unarchive_project(
    request: Request,
    project_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Unarchive a project via ORM."""
    user_uuid = _get_user_uuid(current_user)
    
    try:
        result = await db.execute(
            select(Project).where(
                and_(_get_project_id_condition(project_id), Project.owner_id == user_uuid)
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        if project.archived_at is None:
            raise HTTPException(status_code=400, detail="Project is not archived")
        
        project.archived_at = None
        project.archived_by = None
        project.archived_reason = None
        
        await audit_service.log_event(
            db=db,
            project_id=project.id,
            action='UNARCHIVED',
            actor_user_id=user_uuid,
            metadata={'client': 'web', 'ui_source': 'edit_modal'},
            correlation_id=request.headers.get('X-Request-ID')
        )
        
        await db.commit()
        
        return templates.TemplateResponse(request, "public/components/alerts/success.html", {
                "title": "Project Unarchived",
                "message": "The project has been restored and is now fully editable.",
            },
            headers={"HX-Redirect": f"/projects/{project_id}", "HX-Trigger": "refreshProjectList"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unarchiving project: {e}", exc_info=True)
        await db.rollback()
        return templates.TemplateResponse(request, "public/components/alerts/error.html", {
            "title": "Error Unarchiving Project",
            "message": str(e)
        })


# ============================================================================
# PARAMETERIZED ROUTES (must come AFTER static routes)
# ============================================================================

@router.get("/{project_id}", response_class=HTMLResponse)
async def get_project(
    request: Request,
    project_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get project view via ORM."""
    project = await _get_project_with_icon(db, project_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    project_uuid = UUID(project["id"])
    document_statuses = await document_status_service.get_project_document_statuses(db, project_uuid)
    
    context = {
        "request": request,
        "project": project,
        "document_statuses": document_statuses,
        "active_doc_type": None,
    }
    
    if _is_htmx_request(request):
        return templates.TemplateResponse(request, "public/pages/partials/_document_container.html", context)
    
    return templates.TemplateResponse(request, "public/pages/project_detail.html", context)


@router.put("/{project_id}", response_class=HTMLResponse)
async def update_project(
    request: Request,
    project_id: str,
    _: None = Depends(verify_project_not_archived),
    current_user: User = Depends(require_auth),
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("folder"),
    db: AsyncSession = Depends(get_db)
):
    """Update project via ORM."""
    user_uuid = _get_user_uuid(current_user)
    
    result = await db.execute(
        select(Project).where(
            and_(_get_project_id_condition(project_id), Project.owner_id == user_uuid)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    project.name = name.strip()
    project.description = description.strip()
    project.icon = icon
    
    await db.commit()
    await db.refresh(project)
    
    project_dict = _project_to_dict(project)
    document_statuses = await document_status_service.get_project_document_statuses(db, project.id)
    
    return templates.TemplateResponse(request, "public/pages/partials/_project_overview.html", {
            "project": project_dict,
            "document_statuses": document_statuses,
        },
        headers={"HX-Trigger": "refreshProjectList"}
    )