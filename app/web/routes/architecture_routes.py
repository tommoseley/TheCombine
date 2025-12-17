"""
Architecture routes for The Combine UI
Handles architecture viewing and mentor operations
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .shared import templates, get_template
from app.api.services import project_service
from app.api.services.role_prompt_service import RolePromptService
from app.api.services.artifact_service import ArtifactService
from app.api.models import Artifact

router = APIRouter(tags=["architecture"])


async def get_artifact_by_path(db: AsyncSession, artifact_path: str):
    """Load an artifact by its path."""
    query = select(Artifact).where(Artifact.artifact_path == artifact_path)
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
    
    # Handle both dict and ORM object
    proj_id = project['project_id'] if isinstance(project, dict) else project.project_id
    
    # Load architecture artifacts
    preliminary = await get_artifact_by_path(
        db, f"{proj_id}/ARCH/DISCOVERY"
    )
    final = await get_artifact_by_path(
        db, f"{proj_id}/ARCH/FINAL"
    )
    
    # Extract content from artifacts
    preliminary_content = preliminary.content if preliminary else None
    final_content = final.content if final else None
    
    # Determine last updated
    last_updated = None
    if final:
        last_updated = final.updated_at.strftime('%b %d, %Y') if hasattr(final, 'updated_at') and final.updated_at else None
    elif preliminary:
        last_updated = preliminary.updated_at.strftime('%b %d, %Y') if hasattr(preliminary, 'updated_at') and preliminary.updated_at else None
    
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
    """Get preliminary architecture view specifically"""
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Handle both dict and ORM object
    proj_id = project['project_id'] if isinstance(project, dict) else project.project_id
    
    artifact = await get_artifact_by_path(
        db, f"{proj_id}/ARCH/DISCOVERY"
    )
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Preliminary architecture not found")
    
    context = {
        "request": request,
        "project": project,
        "artifact": artifact,
        "content": artifact.content,
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
    """Get final architecture view specifically"""
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Handle both dict and ORM object
    proj_id = project['project_id'] if isinstance(project, dict) else project.project_id
    proj_name = project['name'] if isinstance(project, dict) else project.name
    
    artifact = await get_artifact_by_path(
        db, f"{proj_id}/ARCH/FINAL"
    )
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Final architecture not found")
    
    # Build architecture object for the template
    architecture = {
        "project_name": proj_name,
        "architecture_uuid": str(artifact.id),
        "detailed_view": artifact.content
    }
    
    context = {
        "request": request,
        "project": project,
        "artifact": artifact,
        "architecture": architecture,
        "arch_type": "Final"
    }
    
    template = get_template(
        request,
        wrapper="pages/architecture_view.html",
        partial="pages/partials/_architecture_view_content.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.get("/artifacts/{artifact_id}", response_class=HTMLResponse)
async def get_artifact_detail(
    request: Request,
    artifact_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generic artifact viewer - routes to appropriate template based on artifact type/content.
    """
    query = select(Artifact).where(Artifact.id == artifact_id)
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    content = artifact.content or {}
    
    # Detect preliminary architecture by checking for preliminary_summary
    if artifact.artifact_type == "architecture" and "preliminary_summary" in content:
        template = get_template(
            request,
            wrapper="pages/preliminary_architecture.html",
            partial="pages/partials/_preliminary_architecture.html"
        )
        context = {
            "request": request,
            "artifact": artifact,
            "content": content,
        }
    # Detect final architecture
    elif artifact.artifact_type == "architecture" and "architecture_summary" in content:
        # Get project info for breadcrumbs
        project = await project_service.get_project_by_project_id(
            db, artifact.artifact_path.split("/")[0]
        )
        architecture = await project_service.get_architecture(db, str(project.id) if project else None)
        
        template = get_template(
            request,
            wrapper="pages/architecture_view.html",
            partial="pages/partials/_architecture_view_content.html"
        )
        context = {
            "request": request,
            "artifact": artifact,
            "architecture": architecture or {"detailed_view": content},
        }
    else:
        # Generic artifact view (fallback to JSON)
        template = get_template(
            request,
            wrapper="pages/artifact_view.html",
            partial="pages/partials/_artifact_view_content.html"
        )
        context = {
            "request": request,
            "artifact": artifact,
        }
    
    return templates.TemplateResponse(template, context)


@router.post("/projects/{project_id}/mentors/architect/preliminary")
async def start_preliminary_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Start preliminary (high-level) architecture mentor.
    Returns Server-Sent Events stream with progress updates.
    """
    from app.domain.mentors import ArchitectMentor
    
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create services for dependency injection
    prompt_service = RolePromptService(db)
    artifact_svc = ArtifactService(db)
    
    # Execute architect mentor (preliminary mode)
    mentor = ArchitectMentor(
        prompt_service=prompt_service,
        artifact_service=artifact_svc,
        model="claude-sonnet-4-20250514"
    )
    
    # Build request data with epic_content (for preliminary, we create from project info)
    request_data = {
        "epic_artifact_path": f"{project['project_id']}/ARCH/PRELIM",
        "epic_content": {
            "title": project['name'],
            "description": project['description'] or "",
            "objectives": [
                "Create high-level system architecture",
                "Identify major components",
                "Define technology recommendations",
                "Establish integration points"
            ]
        },
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 16384,
        "temperature": 0.5
    }
    
    return StreamingResponse(
        mentor.stream_execution(request_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.post("/projects/{project_id}/mentors/architect/detailed")
async def start_detailed_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Start detailed architecture mentor.
    Returns Server-Sent Events stream with progress updates.
    """
    from app.domain.mentors import ArchitectMentor
    
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create services for dependency injection
    prompt_service = RolePromptService(db)
    artifact_svc = ArtifactService(db)
    
    # Execute architect mentor (detailed mode - use Opus for deeper reasoning)
    mentor = ArchitectMentor(
        prompt_service=prompt_service,
        artifact_service=artifact_svc,
        model="claude-opus-4-20250514"
    )
    
    # Build request data with epic_content
    request_data = {
        "epic_artifact_path": f"{project['project_id']}/ARCH/FINAL",
        "epic_content": {
            "title": project['name'],
            "description": project['description'] or "",
            "objectives": [
                "Create detailed system architecture",
                "Define data models and schemas",
                "Specify API interfaces",
                "Address security considerations",
                "Plan scalability approach",
                "Justify technology stack",
                "Design deployment architecture"
            ]
        },
        "model": "claude-opus-4-20250514",
        "max_tokens": 16384,
        "temperature": 0.5
    }
    
    return StreamingResponse(
        mentor.stream_execution(request_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )