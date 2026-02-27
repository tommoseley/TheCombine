"""
Document routes for The Combine UI - Simplified
Returns document content only, targeting #document-content

DEPRECATED: These routes are deprecated in favor of /view/{document_type}
See WS-ADR-034-DOCUMENT-VIEWER for migration details.
Removal scheduled for future WS.
"""


from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.config import USE_LEGACY_TEMPLATES
from ..shared import templates
from app.api.services import project_service
from app.api.models import Document
from app.api.models.project import Project
from app.api.models.document_type import DocumentType

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

# Background task infrastructure
import asyncio
from uuid import uuid4
from app.tasks import (
    TaskStatus,
    TaskInfo,
    get_task,
    set_task,
    find_task,
    run_document_build,
    run_workflow_build,
    WORKFLOW_DOCUMENT_TYPES,
)

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
    lifecycle_state: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> HTMLResponse | None:
    """
    Attempt to render using new RenderModel + Fragment system.
    Returns None if rendering fails (triggers fallback to old templates).
    """
    logger.info(f"_render_with_new_viewer: Starting render for {document_type}")
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
            lifecycle_state=lifecycle_state,
            title=title,
            subtitle=description,
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
            "document_data": document_data,  # For command buttons
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
        import traceback
        logger.error(f"New viewer failed for {document_type}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


# ============================================================================
# DOCUMENT TYPE CONFIG (fallback if not in database)
# ============================================================================

DOCUMENT_CONFIG = {
    "concierge_intake": {
        "title": "Concierge Intake",
        "icon": "clipboard-check",
        "template": "public/pages/partials/_concierge_intake_content.html",
        # No view_docdef - uses legacy template
    },
    "project_discovery": {
        "title": "Project Discovery",
        "icon": "compass",
        "template": "public/pages/partials/_project_discovery_content.html",
        # NOTE: view_docdef removed - intake format uses different schema than ProjectDiscovery docdef
    },
    "technical_architecture": {
        "title": "Technical Architecture",
        "icon": "building",
        "template": "public/pages/partials/_technical_architecture_content.html",
        "view_docdef": "ArchitecturalSummaryView",  # ADR-034: New viewer docdef
    },
}


# ============================================================================
# HELPERS
# ============================================================================

async def _get_project_with_icon(db: AsyncSession, project_id: str) -> dict | None:
    """Get project with icon field via ORM.
    
    Handles both UUID (id column) and string (project_id column) lookups.
    """
    # Try UUID lookup first
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
    except (ValueError, TypeError):
        # Not a UUID, try string lookup
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )
    project = result.scalar_one_or_none()
    if not project:
        return None
    
    return {
        "id": str(project.id),
        "name": project.name,
        "project_id": project.project_id,
        "description": project.description,
        "icon": project.icon or "folder",
    }


async def _get_document_type(db: AsyncSession, doc_type_id: str) -> dict | None:
    """Get document type configuration via ORM."""
    result = await db.execute(
        select(DocumentType).where(
            and_(
                DocumentType.doc_type_id == doc_type_id,
                DocumentType.is_active == True
            )
        )
    )
    doc_type = result.scalar_one_or_none()
    if not doc_type:
        return None
    
    return {
        "doc_type_id": doc_type.doc_type_id,
        "name": doc_type.name,
        "description": doc_type.description,
        "icon": doc_type.icon,
        "required_inputs": doc_type.required_inputs or [],
        "optional_inputs": doc_type.optional_inputs or [],
        "view_docdef": doc_type.view_docdef,
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

async def _check_missing_dependencies(
    db: AsyncSession,
    proj_uuid: UUID,
    doc_type: dict
) -> list[str]:
    """Check which required input documents are missing."""
    missing = []
    if doc_type and doc_type.get("required_inputs"):
        for req_doc_type in doc_type["required_inputs"]:
            req_doc = await _get_document_by_type(db, proj_uuid, req_doc_type)
            if not req_doc:
                missing.append(req_doc_type)
    return missing

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
    
    proj_uuid = UUID(project["id"])
    
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
    # Phase 1 (WS-DOCUMENT-SYSTEM-CLEANUP): Prefer DB value, fallback to DOCUMENT_CONFIG
    view_docdef = (doc_type.get("view_docdef") if doc_type else None) or fallback_config.get("view_docdef")
    # Skip new viewer for project_discovery - intake workflow uses different schema than ProjectDiscovery docdef
    if doc_type_id == "project_discovery":
        view_docdef = None
    if document and view_docdef and document.content:
        logger.info(f"Attempting new viewer for {doc_type_id} -> {view_docdef}")
        response = await _render_with_new_viewer(
            request=request,
            db=db,
            document_type=view_docdef,
            document_data=document.content,
            project=project,
            is_htmx=is_htmx,
            lifecycle_state=getattr(document, 'lifecycle_state', None),
            title=doc_type_name,
            description=doc_type_description,
        )
        if response:
            return response
        # Phase 6 (WS-DOCUMENT-SYSTEM-CLEANUP): Feature flag controls fallback behavior
        if not USE_LEGACY_TEMPLATES:
            logger.warning(
                f"LEGACY_TEMPLATE_FALLBACK_BLOCKED: New viewer failed for {doc_type_id}, "
                f"USE_LEGACY_TEMPLATES=False. Set USE_LEGACY_TEMPLATES=true to enable fallback."
            )
            # Continue to legacy path for now - in future, return error template
        else:
            logger.info(f"Falling back to legacy templates for {doc_type_id} (USE_LEGACY_TEMPLATES=True)")
    
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
        # Check if dependencies are met before allowing build
        missing_deps = await _check_missing_dependencies(db, proj_uuid, doc_type)
        logger.info(f"Missing deps for {doc_type_id}: {missing_deps}")
        context["is_blocked"] = len(missing_deps) > 0
        context["missing_dependencies"] = missing_deps
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
    Start document build as background task.
    Returns task_id for status polling.
    
    ADR-010: Integrated LLM execution logging via background task.
    """
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    proj_uuid = UUID(project['id']) if isinstance(project.get('id'), str) else project.get('id')
    
    # Check for existing active task
    existing_task = find_task(proj_uuid, doc_type_id)
    if existing_task:
        logger.info(f"Returning existing task {existing_task.task_id} for {doc_type_id}")
        return {"task_id": str(existing_task.task_id), "status": existing_task.status.value}
    
    # Create new task
    task_id = uuid4()
    # Middleware stores correlation_id as string; ensure we have a UUID for downstream use
    raw_correlation_id = getattr(request.state, "correlation_id", None)
    if raw_correlation_id:
        correlation_id = UUID(raw_correlation_id) if isinstance(raw_correlation_id, str) else raw_correlation_id
    else:
        correlation_id = uuid4()
    
    task_info = TaskInfo(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0,
        message="Starting...",
        project_id=proj_uuid,
        doc_type_id=doc_type_id,
    )
    set_task(task_info)
    
    logger.info(f"[Background] Created task {task_id} for {doc_type_id}")
    
    # Start background task (fire and forget)
    # WS-INTAKE-SEP-003: Use workflow build for document types with workflows
    if doc_type_id in WORKFLOW_DOCUMENT_TYPES:
        logger.info(f"[Background] Using workflow build for {doc_type_id}")
        asyncio.create_task(
            run_workflow_build(
                task_id=task_id,
                project_id=proj_uuid,
                doc_type_id=doc_type_id,
                correlation_id=correlation_id,
            )
        )
    else:
        asyncio.create_task(
            run_document_build(
                task_id=task_id,
                project_id=proj_uuid,
                project_description=project.get('description', ''),
                doc_type_id=doc_type_id,
                correlation_id=correlation_id,
            )
        )
    
    return {"task_id": str(task_id), "status": "pending"}


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Get status of a background task.
    Used by frontend to poll for build completion.
    """
    try:
        tid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task_id")
    
    task = get_task(tid)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "progress": task.progress,
        "message": task.message,
        "result": task.result,
        "error": task.error,
    }










