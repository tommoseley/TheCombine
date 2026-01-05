"""
Document Status Web Routes (ADR-007)

UI routes for document-centric project pages.
These routes serve the templates with document status data.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.models.document import Document
from app.api.models.project import Project
from app.api.services.document_status_service import document_status_service

router = APIRouter(tags=["ui"])

# Templates - adjust path as needed for your project structure
templates = Jinja2Templates(directory="app/web/templates")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


async def get_project_or_404(db: AsyncSession, project_id: UUID) -> Project:
    """Get project by ID or raise 404."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# =============================================================================
# PROJECT DETAIL ROUTES
# =============================================================================

@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Project detail page with document-centric sidebar.
    
    Returns full page or partial based on HX-Request header.
    """
    # Get project
    project = await get_project_or_404(db, project_id)
    
    # Get document statuses for sidebar
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_id
    )
    
    context = {
            "project": project,
        "document_statuses": document_statuses,
        "active_doc_type": None,
        "active_document": None,
        "doc_status": None,
    }
    
    # Choose template based on request type
    template = (
        "public/pages/partials/_project_content.html" if is_htmx_request(request)
        else "public/pages/project_detail.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/projects/{project_id}/documents/{doc_type_id}", response_class=HTMLResponse)
async def project_document_detail(
    request: Request,
    project_id: UUID,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Document detail view within project context.
    
    Shows specific document type with its status and content.
    """
    # Get project
    project = await get_project_or_404(db, project_id)
    
    # Get all document statuses for sidebar
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_id
    )
    
    # Find the specific document status
    doc_status = next(
        (s for s in document_statuses if s.doc_type_id == doc_type_id),
        None
    )
    
    if not doc_status:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    # Get the actual document if it exists
    active_document = None
    if doc_status.document_id:
        result = await db.execute(
            select(Document).where(Document.id == doc_status.document_id)
        )
        active_document = result.scalar_one_or_none()
    
    context = {
            "project": project,
        "document_statuses": document_statuses,
        "active_doc_type": doc_type_id,
        "active_document": active_document,
        "doc_status": doc_status,
    }
    
    # Choose template based on request type
    template = (
        "public/pages/partials/_project_content.html" if is_htmx_request(request)
        else "public/pages/project_detail.html"
    )
    
    return templates.TemplateResponse(template, context)


# =============================================================================
# SIDEBAR REFRESH ROUTES
# =============================================================================

@router.get("/projects/{project_id}/document-statuses", response_class=HTMLResponse)
async def get_document_statuses_partial(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns just the document status list for sidebar refresh.
    
    Used by HTMX to refresh status indicators without full page reload.
    """
    # Get project
    project = await get_project_or_404(db, project_id)
    
    # Get document statuses
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_id
    )
    
    context = {
            "project": project,
        "document_statuses": document_statuses,
        "active_doc_type": None,
    }
    
    return templates.TemplateResponse(
        "public/components/sidebar/document_status_list.html",
        context
    )


# =============================================================================
# MODAL ROUTES
# =============================================================================

@router.get(
    "/projects/{project_id}/documents/{doc_type_id}/reject-modal",
    response_class=HTMLResponse
)
async def get_reject_modal(
    request: Request,
    project_id: UUID,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the reject document modal HTML.
    
    Used by HTMX to load the modal into #modal-container.
    """
    # Get project
    project = await get_project_or_404(db, project_id)
    
    # Get document status
    doc_status = await document_status_service.get_document_status(
        db, doc_type_id, "project", project_id
    )
    
    if not doc_status:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    if not doc_status.document_id:
        raise HTTPException(status_code=400, detail="Document does not exist")
    
    # Get actual document
    result = await db.execute(
        select(Document).where(Document.id == doc_status.document_id)
    )
    document = result.scalar_one_or_none()
    
    context = {
            "project": project,
        "doc_status": doc_status,
        "document": document,
    }
    
    return templates.TemplateResponse("public/components/reject_modal.html", context)


# =============================================================================
# ACTION ROUTES (trigger document generation)
# =============================================================================

@router.post(
    "/projects/{project_id}/documents/{doc_type_id}/build",
    response_class=HTMLResponse
)
async def build_document(
    request: Request,
    project_id: UUID,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger document generation for a document type.
    
    This route would integrate with your mentor/generation system.
    For now, returns the updated document detail view.
    """
    # Get project
    project = await get_project_or_404(db, project_id)
    
    # Get document status
    doc_status = await document_status_service.get_document_status(
        db, doc_type_id, "project", project_id
    )
    
    if not doc_status:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    if not doc_status.can_build:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot build: {doc_status.subtitle or 'not ready'}"
        )
    
    # TODO: Integrate with actual document generation system
    # This would typically:
    # 1. Call the appropriate mentor/handler
    # 2. Create the document
    # 3. Return the updated view
    #
    # For now, we just redirect back to the document detail
    
    # Get all document statuses for sidebar
    document_statuses = await document_status_service.get_project_document_statuses(
        db, project_id
    )
    
    # Refresh the doc_status after potential changes
    doc_status = await document_status_service.get_document_status(
        db, doc_type_id, "project", project_id
    )
    
    # Get the document if it was created
    active_document = None
    if doc_status and doc_status.document_id:
        result = await db.execute(
            select(Document).where(Document.id == doc_status.document_id)
        )
        active_document = result.scalar_one_or_none()
    
    context = {
            "project": project,
        "document_statuses": document_statuses,
        "active_doc_type": doc_type_id,
        "active_document": active_document,
        "doc_status": doc_status,
    }
    
    return templates.TemplateResponse(
        "public/pages/partials/_project_content.html",
        context
    )