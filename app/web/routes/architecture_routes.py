"""
Architecture routes for The Combine UI - Document-centric version.
Handles architecture viewing and document building.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from database import get_db
from .shared import templates, get_template
from app.api.services import project_service
from app.api.services.role_prompt_service import RolePromptService
from app.api.services.document_service import DocumentService
from app.api.models import Document

router = APIRouter(tags=["architecture"])


async def get_document_by_type(
    db: AsyncSession, 
    space_id: UUID, 
    doc_type_id: str
) -> Document | None:
    """Load the latest document of a type for a project."""
    query = (
        select(Document)
        .where(Document.space_type == 'project')
        .where(Document.space_id == space_id)
        .where(Document.doc_type_id == doc_type_id)
        .where(Document.is_latest == True)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


@router.get("/projects/{project_id}/architecture", response_class=HTMLResponse)
async def get_project_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get architecture summary view - aggregates Discovery and Final"""
    # First get the project
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get project UUID
    proj_uuid = UUID(project['id']) if isinstance(project.get('id'), str) else project.get('id')
    
    # Load architecture documents
    preliminary = await get_document_by_type(db, proj_uuid, 'project_discovery')
    final = await get_document_by_type(db, proj_uuid, 'architecture_spec')
    
    # Extract content from documents
    preliminary_content = preliminary.content if preliminary else None
    final_content = final.content if final else None
    
    # Determine last updated
    last_updated = None
    if final:
        last_updated = final.updated_at.strftime('%b %d, %Y') if final.updated_at else None
    elif preliminary:
        last_updated = preliminary.updated_at.strftime('%b %d, %Y') if preliminary.updated_at else None
    
    context = {
        "request": request,
        "project": project,
        "has_preliminary": preliminary is not None,
        "has_final": final is not None,
        "preliminary_content": preliminary_content,
        "final_content": final_content,
        "last_updated": last_updated,
    }
    
    template = get_template(
        request,
        wrapper="pages/architecture_summary.html",
        partial="pages/partials/_architecture_summary.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/projects/{project_id}/architecture/preliminary", response_class=HTMLResponse)
async def get_preliminary_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get preliminary architecture (project discovery) view"""
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    proj_uuid = UUID(project['id']) if isinstance(project.get('id'), str) else project.get('id')
    
    document = await get_document_by_type(db, proj_uuid, 'project_discovery')
    
    if not document:
        raise HTTPException(status_code=404, detail="Project discovery not found")
    
    context = {
        "request": request,
        "project": project,
        "document": document,
        "artifact": document,  # For template compatibility
        "content": document.content,
    }
    
    template = get_template(
        request,
        wrapper="pages/preliminary_architecture.html",
        partial="pages/partials/_preliminary_architecture.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/projects/{project_id}/architecture/final", response_class=HTMLResponse)
async def get_final_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get final architecture (architecture spec) view"""
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    proj_uuid = UUID(project['id']) if isinstance(project.get('id'), str) else project.get('id')
    proj_name = project['name'] if isinstance(project, dict) else project.name
    
    document = await get_document_by_type(db, proj_uuid, 'architecture_spec')
    
    if not document:
        raise HTTPException(status_code=404, detail="Architecture spec not found")
    
    # Build architecture object for the template
    architecture = {
        "project_name": proj_name,
        "architecture_uuid": str(document.id),
        "detailed_view": document.content
    }
    
    context = {
        "request": request,
        "project": project,
        "document": document,
        "artifact": document,  # For template compatibility
        "architecture": architecture,
        "arch_type": "Final"
    }
    
    template = get_template(
        request,
        wrapper="pages/architecture_view.html",
        partial="pages/partials/_architecture_view_content.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def get_document_detail(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generic document viewer - routes to appropriate template based on document type.
    """
    doc_uuid = UUID(document_id)
    document = await db.get(Document, doc_uuid)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    content = document.content or {}
    
    # Get handler for rendering
    from app.domain.handlers import get_handler
    from app.domain.registry.loader import get_document_config
    
    try:
        config = await get_document_config(db, document.doc_type_id)
        handler = get_handler(config["handler_id"])
        rendered_html = handler.render(content)
    except Exception as e:
        import logging
        logging.error(f"Error rendering document: {e}")
        rendered_html = f"<pre>{content}</pre>"
    
    # Get project info for breadcrumbs
    project = None
    if document.space_type == 'project':
        project = await project_service.get_project_by_uuid(db, str(document.space_id))
    
    template = get_template(
        request,
        wrapper="pages/document_view.html",
        partial="pages/partials/_document_view_content.html"
    )
    
    context = {
        "request": request,
        "document": document,
        "project": project,
        "content": content,
        "rendered_html": rendered_html,
    }
    
    return templates.TemplateResponse(template, context)


# ============================================================================
# DOCUMENT BUILDING (replaces mentor routes)
# ============================================================================

@router.post("/projects/{project_id}/documents/{doc_type_id}/build")
async def build_document(
    request: Request,
    project_id: str,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Build a document using the document-centric pipeline.
    Returns Server-Sent Events stream with progress updates.
    """
    from app.domain.services.document_builder import DocumentBuilder
    from app.api.routers.documents import PromptServiceAdapter
    
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    proj_uuid = UUID(project['id']) if isinstance(project.get('id'), str) else project.get('id')
    
    # Create builder with dependencies
    prompt_service = RolePromptService(db)
    prompt_adapter = PromptServiceAdapter(prompt_service)
    document_service = DocumentService(db)
    
    builder = DocumentBuilder(
        db=db,
        prompt_service=prompt_adapter,
        document_service=document_service,
    )
    
    return StreamingResponse(
        builder.build_stream(
            doc_type_id=doc_type_id,
            space_type='project',
            space_id=proj_uuid,
            inputs={
                "user_query": project.get('description', ''),
                "project_description": project.get('description', ''),
            },
            options={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 16384,
                "temperature": 0.5,
            }
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ============================================================================
# DEPRECATED: Old mentor routes - redirect to new document routes
# ============================================================================

@router.post("/projects/{project_id}/mentors/architect/preliminary")
async def start_preliminary_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    DEPRECATED: Use /projects/{project_id}/documents/project_discovery/build instead.
    Redirects to new document-centric endpoint.
    """
    return await build_document(request, project_id, "project_discovery", db)


@router.post("/projects/{project_id}/mentors/architect/detailed")
async def start_detailed_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    DEPRECATED: Use /projects/{project_id}/documents/architecture_spec/build instead.
    Redirects to new document-centric endpoint.
    """
    return await build_document(request, project_id, "architecture_spec", db)