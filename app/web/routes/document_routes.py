"""
Document routes for The Combine UI - Simplified
Returns document content only, targeting #document-content
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from database import get_db
from .shared import templates
from app.api.services import project_service
from app.api.services.document_status_service import document_status_service
from app.api.services.role_prompt_service import RolePromptService
from app.api.services.document_service import DocumentService
from app.api.models import Document

router = APIRouter(tags=["documents"])


# ============================================================================
# DOCUMENT TYPE CONFIG
# ============================================================================

DOCUMENT_CONFIG = {
    "project_discovery": {
        "title": "Project Discovery",
        "icon": "compass",
        "template": "pages/partials/_project_discovery_content.html",
    },
    "epic_backlog": {
        "title": "Epic Backlog",
        "icon": "layers",
        "template": "pages/partials/_epic_backlog_content.html",
    },
    "technical_architecture": {
        "title": "Technical Architecture",
        "icon": "building",
        "template": "pages/partials/_technical_architecture_content.html",
    },
    "architecture_spec": {
        "title": "Architecture Specification",
        "icon": "landmark",
        "template": "pages/partials/_architecture_spec_content.html",
    },
}


# ============================================================================
# HELPERS
# ============================================================================

async def _get_project_with_icon(db: AsyncSession, project_id: str) -> dict | None:
    """Get project with icon field."""
    result = await db.execute(
        text("""
            SELECT id, name, project_id, description, icon
            FROM projects WHERE id = :project_id
        """),
        {"project_id": project_id}
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
    }


async def _get_document_by_type(db: AsyncSession, space_id: UUID, doc_type_id: str) -> Document | None:
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


# ============================================================================
# DOCUMENT VIEWS - Return content only (targets #document-content)
# ============================================================================

@router.get("/projects/{project_id}/documents/{doc_type_id}", response_class=HTMLResponse)
async def get_document(
    request: Request,
    project_id: str,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get document content.
    Returns just the document content partial - targets #document-content.
    """
    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    proj_uuid = UUID(project_id)
    
    # Get document config
    config = DOCUMENT_CONFIG.get(doc_type_id, {
        "title": doc_type_id.replace("_", " ").title(),
        "icon": "file-text",
        "template": "pages/partials/_document_not_found.html",
    })
    
    # Try to load the document
    document = await _get_document_by_type(db, proj_uuid, doc_type_id)
    
    if not document:
        # Return not found state
        return templates.TemplateResponse(
            "pages/partials/_document_not_found.html",
            {
                "request": request,
                "project": project,
                "doc_type_id": doc_type_id,
                "document_title": config["title"],
                "document_icon": config["icon"],
                "is_blocked": False,
            }
        )
    
    # Return document content
    return templates.TemplateResponse(
        config["template"],
        {
            "request": request,
            "project": project,
            "document": document,
            "artifact": document,  # For template compatibility
            "content": document.content,
        }
    )


# ============================================================================
# DOCUMENT BUILDING
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