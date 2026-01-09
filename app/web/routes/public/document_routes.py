"""
Document routes for The Combine UI - Simplified
Returns document content only, targeting #document-content

DEPRECATED: These routes are deprecated in favor of /view/{document_type}
See WS-ADR-034-DOCUMENT-VIEWER for migration details.
Removal scheduled for future WS.
"""

import warnings

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from ..shared import templates
from app.api.services import project_service
from app.api.services.document_status_service import document_status_service
from app.api.services.role_prompt_service import RolePromptService
from app.api.services.document_service import DocumentService
from app.api.models import Document

# ADR-030: BFF imports
from app.web.bff import get_epic_backlog_vm
from app.web.template_helpers import create_preloaded_fragment_renderer

# ADR-034: New viewer imports
from app.api.services.document_definition_service import DocumentDefinitionService
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.schema_registry_service import SchemaRegistryService
from app.api.services.fragment_registry_service import FragmentRegistryService
from app.domain.services.render_model_builder import (
    RenderModelBuilder,
    DocDefNotFoundError,
)
from .view_routes import FragmentRenderer

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


# ============================================================================
# ADR-034: NEW VIEWER RENDERING
# ============================================================================

async def _render_with_new_viewer(
    request: Request,
    db: AsyncSession,
    document_type: str,
    document_data: dict,
    project: dict,
    is_htmx: bool,
) -> HTMLResponse | None:
    """
    Attempt to render using new RenderModel + Fragment system.
    Returns None if rendering fails (triggers fallback to old templates).
    """
    try:
        # Build services
        docdef_service = DocumentDefinitionService(db)
        component_service = ComponentRegistryService(db)
        schema_service = SchemaRegistryService(db)
        fragment_service = FragmentRegistryService(db)
        
        # Build RenderModel
        builder = RenderModelBuilder(
            docdef_service=docdef_service,
            component_service=component_service,
            schema_service=schema_service,
        )
        
        render_model = await builder.build(
            document_def_id=document_type,
            document_data=document_data,
        )
        
        # Preload fragments
        fragment_renderer = FragmentRenderer(
            component_service=component_service,
            fragment_service=fragment_service,
        )
        await fragment_renderer.preload(render_model)
        
        # Render
        context = {
            "request": request,
            "render_model": render_model,
            "fragment_renderer": fragment_renderer,
            "project": project,
        }
        
        if is_htmx:
            return templates.TemplateResponse(
                "public/partials/_document_viewer_content.html",
                context,
            )
        else:
            return templates.TemplateResponse(
                "public/pages/document_viewer_page.html",
                context,
            )
            
    except DocDefNotFoundError:
        logger.warning(f"No docdef found for {document_type}, falling back to old template")
        return None
    except Exception as e:
        logger.error(f"New viewer failed for {document_type}: {e}, falling back to old template")
        return None


# ============================================================================
# DOCUMENT TYPE CONFIG (fallback if not in database)
# ============================================================================

DOCUMENT_CONFIG = {
    "project_discovery": {
        "title": "Project Discovery",
        "icon": "compass",
        "template": "public/pages/partials/_project_discovery_content.html",
        "view_docdef": "ProjectDiscovery",  # ADR-034: New viewer docdef
    },
    "epic_backlog": {
        "title": "Epic Backlog",
        "icon": "layers",
        "template": "public/pages/partials/_epic_backlog_content.html",
        "view_docdef": "EpicBacklogView",  # ADR-034: New viewer docdef
    },
    "technical_architecture": {
        "title": "Technical Architecture",
        "icon": "building",
        "template": "public/pages/partials/_technical_architecture_content.html",
        "view_docdef": "ArchitecturalSummaryView",  # ADR-034: New viewer docdef
    },
    "story_backlog": {
        "title": "Story Backlog",
        "icon": "list-checks",
        "template": "public/pages/partials/_story_backlog_content.html",
        "view_docdef": "StoryBacklogView",  # ADR-034: New viewer docdef
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


async def _get_document_type(db: AsyncSession, doc_type_id: str) -> dict | None:
    """Get document type configuration from database."""
    result = await db.execute(
        text("""
            SELECT doc_type_id, name, description, icon, required_inputs, optional_inputs
            FROM document_types 
            WHERE doc_type_id = :doc_type_id AND is_active = true
        """),
        {"doc_type_id": doc_type_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    return {
        "doc_type_id": row.doc_type_id,
        "name": row.name,
        "description": row.description,
        "icon": row.icon,
        "required_inputs": row.required_inputs or [],
        "optional_inputs": row.optional_inputs or [],
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
    Returns partial for HTMX requests, full page for browser refresh.
    
    DEPRECATED: Use GET /view/{document_type}?params instead.
    This route will be removed in a future release.
    """
    # Log deprecation warning
    logger.warning(
        f"DEPRECATED: /projects/{project_id}/documents/{doc_type_id} - "
        f"Use /view/{{document_type}} instead"
    )
    
    logger.info(f"Looking for document: doc_type_id={doc_type_id}, space_id={project_id}")
    
    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    proj_uuid = UUID(project_id)
    
    # Get document type from database
    doc_type = await _get_document_type(db, doc_type_id)
    
    # Fallback to static config if not in database
    fallback_config = DOCUMENT_CONFIG.get(doc_type_id, {
        "title": doc_type_id.replace("_", " ").title(),
        "icon": "file-text",
        "template": "public/pages/partials/_document_not_found.html",
    })
    
    # Merge database config with fallback
    doc_type_name = doc_type["name"] if doc_type else fallback_config["title"]
    doc_type_icon = doc_type["icon"] if doc_type and doc_type["icon"] else fallback_config["icon"]
    doc_type_description = doc_type["description"] if doc_type else None
    template_path = fallback_config.get("template", "public/pages/partials/_document_not_found.html")
    
    # Try to load the document
    document = await _get_document_by_type(db, proj_uuid, doc_type_id)
    
    logger.info(f"Document found: {document is not None}")
    
    # Check if this is an HTMX request (partial) or full page request (browser refresh)
    is_htmx = request.headers.get("HX-Request") == "true"
    
    # ADR-034: Try new viewer if view_docdef is configured and document exists
    view_docdef = fallback_config.get("view_docdef")
    if document and view_docdef and document.content:
        logger.info(f"Attempting new viewer for {doc_type_id} -> {view_docdef}")
        response = await _render_with_new_viewer(
            request=request,
            db=db,
            document_type=view_docdef,
            document_data=document.content,
            project=project,
            is_htmx=is_htmx,
        )
        if response:
            return response
        # Fall through to old templates if new viewer fails
    
    # ADR-030: BFF handling for epic_backlog (legacy path)
    if doc_type_id == "epic_backlog":
        vm = await get_epic_backlog_vm(
            db=db,
            project_id=proj_uuid,
            project_name=project["name"],
            base_url="",
        )
        
        # ADR-033: Fragment rendering is a web channel concern
        # Preload fragment templates while in async context
        fragment_renderer = await create_preloaded_fragment_renderer(
            db, 
            type_ids=['OpenQuestionV1']
        )
        
        context = {
            "request": request,
            "project": project,
            "vm": vm,
            "fragment_renderer": fragment_renderer,
        }
        partial_template = "public/pages/partials/_epic_backlog_content.html"
        
        if is_htmx:
            return templates.TemplateResponse(partial_template, context)
        else:
            context["content_template"] = partial_template
            return templates.TemplateResponse("public/pages/document_page.html", context)
    
    # Build context for other document types
    context = {
        "request": request,
            "project": project,
        "doc_type_id": doc_type_id,
        "doc_type_name": doc_type_name,
        "doc_type_icon": doc_type_icon,
        "doc_type_description": doc_type_description,
    }
    
    if not document:
        context["is_blocked"] = False
        partial_template = "public/pages/partials/_document_not_found.html"
    else:
        context["document"] = document
        context["artifact"] = document  # For template compatibility
        context["content"] = document.content
        partial_template = template_path
    
    # Return partial for HTMX, full page for browser
    if is_htmx:
        return templates.TemplateResponse(partial_template, context)
    else:
        # Wrap in full page layout
        context["content_template"] = partial_template
        return templates.TemplateResponse("public/pages/document_page.html", context)


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
    
    ADR-010: Integrated LLM execution logging.
    """
    from app.domain.services.document_builder import DocumentBuilder
    from app.api.routers.documents import PromptServiceAdapter
    from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
    from app.domain.services.llm_execution_logger import LLMExecutionLogger
    
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    proj_uuid = UUID(project['id']) if isinstance(project.get('id'), str) else project.get('id')
    
    # ADR-010: Get correlation_id from request state (set by middleware)
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(f"[ADR-010] Web route build_document - correlation_id={correlation_id}")
    
    # ADR-010: Create LLM logger
    llm_repo = PostgresLLMLogRepository(db)
    llm_logger = LLMExecutionLogger(llm_repo)
    logger.info(f"[ADR-010] Created LLMExecutionLogger for web route")
    
    # Create builder with dependencies
    prompt_service = RolePromptService(db)
    prompt_adapter = PromptServiceAdapter(prompt_service)
    document_service = DocumentService(db)
    
    builder = DocumentBuilder(
        db=db,
        prompt_service=prompt_adapter,
        document_service=document_service,
        correlation_id=correlation_id,  # ADR-010
        llm_logger=llm_logger,  # ADR-010
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





