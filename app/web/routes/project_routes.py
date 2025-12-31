"""
Project routes for The Combine UI - With User Ownership
Handles different User model ID field names (id, user_id, uuid, etc.)
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from uuid import UUID
import logging

from app.core.database import get_db
from .shared import templates
from app.api.services import project_service
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
    """
    Get the user's ID, handling different field names.
    The User model might use 'id', 'user_id', 'uuid', or other field names.
    """
    # Try common field names
    for field_name in ['id', 'user_id', 'uuid', 'pk']:
        if hasattr(user, field_name):
            value = getattr(user, field_name)
            # Convert to string if it's a UUID
            return str(value) if value else None
    
    # If we can't find the ID, raise a helpful error
    available_attrs = [attr for attr in dir(user) if not attr.startswith('_')]
    raise AttributeError(
        f"User model has no 'id' attribute. Available attributes: {available_attrs}. "
        f"Please update _get_user_id() in project_routes.py to use the correct field."
    )


async def _get_project_with_icon(db: AsyncSession, project_id: str, user: User) -> dict | None:
    """Get project with icon AND archive state - VERIFY OWNERSHIP."""
    user_id = _get_user_id(user)
    
    result = await db.execute(
        text("""
            SELECT id, name, project_id, description, icon, 
                   created_at, updated_at, owner_id,
                   archived_at, archived_by, archived_reason
            FROM projects 
            WHERE id = :project_id AND owner_id = :user_id
        """),
        {"project_id": project_id, "user_id": user_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    return {
        "id": str(row.id),
        "name": row.name,
        "project_id": row.project_id,
        "description": row.description,
        "icon": row.icon or "folder",
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "archived_at": row.archived_at,
        "archived_by": str(row.archived_by) if row.archived_by else None,
        "archived_reason": row.archived_reason,
        "is_archived": row.archived_at is not None,  # Computed convenience field
    }


def _is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


def _get_htmx_target(request: Request) -> str | None:
    """Get the HTMX target element."""
    return request.headers.get("HX-Target")


# ============================================================================
# STATIC ROUTES (must come BEFORE parameterized routes)
# ============================================================================

@router.get("/new", response_class=HTMLResponse)
async def new_project_form(
    request: Request,
    current_user: User = Depends(require_auth)
):
    """Display form for creating a new project."""
    return templates.TemplateResponse("pages/partials/_project_new_content.html", {
        "request": request,
        "project": None,
        "mode": "create"
    })

@router.get("/list", response_class=HTMLResponse)
async def get_project_list(
    request: Request,
    current_user: User = Depends(require_auth),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get list of projects for sidebar - USER'S PROJECTS ONLY."""
    user_id = _get_user_id(current_user)
    
    if search:
        result = await db.execute(
            text("""
                SELECT id, name, project_id, icon, archived_at FROM projects
                WHERE owner_id = :user_id 
                AND (name ILIKE :search OR project_id ILIKE :search)
                ORDER BY archived_at NULLS FIRST, name ASC
            """),
            {"user_id": user_id, "search": f"%{search}%"}
        )
    else:
        result = await db.execute(
            text("""
                SELECT id, name, project_id, icon, archived_at FROM projects 
                WHERE owner_id = :user_id
                ORDER BY archived_at NULLS FIRST, name ASC
            """),
            {"user_id": user_id}
        )
    
    rows = result.fetchall()
    projects = [
        {
            "id": str(row.id), 
            "name": row.name, 
            "project_id": row.project_id, 
            "icon": row.icon or "folder",
            "is_archived": row.archived_at is not None  # Add this line
        }
        for row in rows
    ]
    
    return templates.TemplateResponse("components/project_list.html", {
        "request": request,
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
    """Get project tree with documents for accordion sidebar navigation - USER'S PROJECTS ONLY."""
    user_id = _get_user_id(current_user)
    
    # Get ONLY user's projects - WITH ARCHIVE STATUS
    result = await db.execute(
        text("""
            SELECT id, name, project_id, icon, archived_at FROM projects
            WHERE owner_id = :user_id
            ORDER BY archived_at NULLS FIRST, name ASC
            LIMIT :limit OFFSET :offset
        """),
        {"user_id": user_id, "limit": limit, "offset": offset}
    )
    
    rows = result.fetchall()
    projects = []
    
    for row in rows:
        project_id = str(row.id)
        project_uuid = UUID(project_id)
        is_archived = row.archived_at is not None  # Calculate once
        
        # Get document statuses for this project
        document_statuses = await document_status_service.get_project_document_statuses(db, project_uuid)
        
        # Calculate status summary
        status_summary = {
            "ready": 0,
            "stale": 0,
            "blocked": 0,
            "waiting": 0,
            "needs_acceptance": 0
        }
        
        # Convert DocumentStatus objects to dicts
        documents = []
        for doc in document_statuses:
            if hasattr(doc, 'readiness'):
                readiness = doc.readiness
                acceptance_state = getattr(doc, 'acceptance_state', None)
                documents.append({
                    "doc_type_id": doc.doc_type_id,
                    "title": doc.title,
                    "icon": doc.icon,
                    "readiness": readiness,
                    "acceptance_state": acceptance_state,
                    "subtitle": getattr(doc, 'subtitle', None)
                })
            else:
                readiness = doc.get("readiness", "waiting")
                acceptance_state = doc.get("acceptance_state")
                documents.append(doc)
            
            # # Count statuses
            # if acceptance_state == "needs_acceptance":
            #     status_summary["needs_acceptance"] += 1
            # elif acceptance_state == "rejected":
            #     status_summary["blocked"] += 1
            # elif readiness in status_summary:
            #     status_summary[readiness] += 1
        
        projects.append({
            "id": project_id,
            "name": row.name,
            "project_id": row.project_id,
            "icon": row.icon or "folder",
            "documents": documents,
            "status_summary": status_summary,
            "is_archived": is_archived  # Add this line
        })
    
    return templates.TemplateResponse("components/project_list.html", {
        "request": request,
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
    """Create a new project - SET OWNER."""
    user_id = _get_user_id(current_user)
    
    try:
        # Create project with owner_id and organization_id
        # For individual users: organization_id = user_id
        result = await db.execute(
            text("""
                INSERT INTO projects (id, project_id, name, description, icon, owner_id, organization_id, created_by, created_at, updated_at)
                VALUES (gen_random_uuid(), :project_id, :name, :description, :icon, :owner_id, :organization_id, :created_by, NOW(), NOW())
                RETURNING id
            """),
            {
                "project_id": name.strip().upper().replace(" ", "_")[:20],
                "name": name.strip(),
                "description": description.strip(),
                "icon": icon,
                "owner_id": user_id,
                "organization_id": user_id,  # Individual user = own org
                "created_by": user_id
            }
        )
        await db.commit()
        
        row = result.fetchone()
        project_id = str(row.id)
        
        return templates.TemplateResponse(
            "components/alerts/success.html",
            {
                "request": request,
                "title": "Project Created",
                "message": f'Project "{name}" has been created.',
            },
            headers={"HX-Redirect": f"/projects/{project_id}"}
        )
        
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        return templates.TemplateResponse("components/alerts/error.html", {
            "request": request,
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
    """Archive a project - TRANSACTIONAL STATE + AUDIT."""
    user_id = _get_user_id(current_user)
    
    try:
        # Verify ownership and not already archived
        result = await db.execute(
            text("""
                SELECT archived_at 
                FROM projects 
                WHERE id = :project_id AND owner_id = :user_id
            """),
            {"project_id": project_id, "user_id": user_id}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        if row.archived_at is not None:
            raise HTTPException(status_code=400, detail="Project is already archived")
        
        # Update project state
        result = await db.execute(
            text("""
                UPDATE projects 
                SET archived_at = NOW(),
                    archived_by = :user_id,
                    archived_reason = :reason,
                    updated_at = NOW()
                WHERE id = :project_id AND owner_id = :user_id
            """),
            {
                "project_id": project_id,
                "user_id": user_id,
                "reason": reason.strip() if reason else None
            }
        )
        
        # Only audit if update succeeded
        if result.rowcount > 0:
            await audit_service.log_event(
                db=db,
                project_id=UUID(project_id),
                action='ARCHIVED',
                actor_user_id=UUID(user_id),
                reason=reason.strip() if reason else None,
                metadata={
                    'client': 'web',
                    'ui_source': 'edit_modal'
                },
                correlation_id=request.headers.get('X-Request-ID')
            )
        
        # Commit the transaction
        await db.commit()
        
        return templates.TemplateResponse(
            "components/alerts/success.html",
            {
                "request": request,
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
        return templates.TemplateResponse("components/alerts/error.html", {
            "request": request,
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
    """Unarchive a project - RESTORE FULL ACCESS + AUDIT."""
    user_id = _get_user_id(current_user)
    
    try:
        # Verify ownership and currently archived
        result = await db.execute(
            text("""
                SELECT archived_at 
                FROM projects 
                WHERE id = :project_id AND owner_id = :user_id
            """),
            {"project_id": project_id, "user_id": user_id}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        if row.archived_at is None:
            raise HTTPException(status_code=400, detail="Project is not archived")
        
        # Clear archive state
        result = await db.execute(
            text("""
                UPDATE projects 
                SET archived_at = NULL,
                    archived_by = NULL,
                    archived_reason = NULL,
                    updated_at = NOW()
                WHERE id = :project_id AND owner_id = :user_id
            """),
            {
                "project_id": project_id,
                "user_id": user_id
            }
        )
        
        # Only audit if update succeeded
        if result.rowcount > 0:
            await audit_service.log_event(
                db=db,
                project_id=UUID(project_id),
                action='UNARCHIVED',
                actor_user_id=UUID(user_id),
                metadata={
                    'client': 'web',
                    'ui_source': 'edit_modal'
                },
                correlation_id=request.headers.get('X-Request-ID')
            )
        
        # Commit the transaction
        await db.commit()
        
        return templates.TemplateResponse(
            "components/alerts/success.html",
            {
                "request": request,
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
        return templates.TemplateResponse("components/alerts/error.html", {
            "request": request,
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
    """Get project view - VERIFY OWNERSHIP."""
    project = await _get_project_with_icon(db, project_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    project_uuid = UUID(project_id)
    document_statuses = await document_status_service.get_project_document_statuses(db, project_uuid)
    
    context = {
        "request": request,
        "project": project,
        "document_statuses": document_statuses,
        "active_doc_type": None,
    }
    
    # HTMX request - return just the document container partial
    if _is_htmx_request(request):
        return templates.TemplateResponse("pages/partials/_document_container.html", context)
    
    # Full page request - return page with base.html
    return templates.TemplateResponse("pages/project_detail.html", context)


@router.put("/{project_id}", response_class=HTMLResponse)
async def update_project(
    request: Request,
    project_id: str,
    _: None = Depends(verify_project_not_archived),  # ← ARCHIVE PROTECTION
    current_user: User = Depends(require_auth),
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form("folder"),
    db: AsyncSession = Depends(get_db)
):
    """Update project - VERIFY OWNERSHIP."""
    user_id = _get_user_id(current_user)
    
    # Verify ownership first
    project = await _get_project_with_icon(db, project_id, current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    await db.execute(
        text("""
            UPDATE projects 
            SET name = :name, description = :description, icon = :icon, updated_at = NOW()
            WHERE id = :project_id AND owner_id = :user_id
        """),
        {
            "name": name.strip(),
            "description": description.strip(),
            "icon": icon,
            "project_id": project_id,
            "user_id": user_id
        }
    )
    await db.commit()
    
    project = await _get_project_with_icon(db, project_id, current_user)
    project_uuid = UUID(project_id)
    document_statuses = await document_status_service.get_project_document_statuses(db, project_uuid)
    
    return templates.TemplateResponse(
        "pages/partials/_project_overview.html",
        {
            "request": request,
            "project": project,
            "document_statuses": document_statuses,
        },
        headers={"HX-Trigger": "refreshProjectList"}
    )