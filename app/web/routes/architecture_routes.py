"""
Architecture routes for The Combine UI
Handles architecture viewing and mentor operations
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .shared import templates, get_template
from app.api.services import project_service, artifact_service

router = APIRouter(tags=["architecture"])


@router.get("/projects/{project_id}/architecture", response_class=HTMLResponse)
async def get_project_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get architecture view"""
    architecture = await project_service.get_architecture(db, project_id)
    
    context = {
        "request": request,
        "architecture": architecture
    }
    
    template = get_template(
        request,
        wrapper="pages/architecture_view.html",
        partial="pages/partials/_architecture_view_content.html"
    )
    
    return templates.TemplateResponse(template, context)


@router.post("/projects/{project_id}/mentors/architect/preliminary", response_class=HTMLResponse)
async def start_preliminary_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Start preliminary (high-level) architecture mentor
    Returns updated project page
    """
    from app.domain.mentors import ArchitectMentor
    
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Execute architect mentor (preliminary mode)
    mentor = ArchitectMentor(preferred_model="claude-sonnet-4-20250514")
    
    prompt = f"""Create a high-level preliminary architecture for this project:

Project: {project['name']}
Description: {project['description']}

Provide:
1. System overview (2-3 paragraphs)
2. Major components (3-5 key systems)
3. Technology recommendations
4. Integration points

Keep it high-level and strategic, not detailed implementation.
"""
    
    result = await mentor.execute(prompt, project['project_id'])
    
    # Save architecture artifact using service
    artifact_path = f"{project['project_id']}/architecture/preliminary"
    
    await artifact_service.create_artifact(
        db=db,
        artifact_path=artifact_path,
        artifact_type='architecture',
        title='Preliminary Architecture',
        content={'architecture': result.get('architecture', '')},
        created_by='architect_mentor'
    )
    
    # Reload page to show architecture
    return RedirectResponse(
        url=f"/ui/projects/{project_id}",
        status_code=303
    )


@router.post("/projects/{project_id}/mentors/architect/detailed", response_class=HTMLResponse)
async def start_detailed_architecture(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Start detailed architecture mentor
    Returns updated project page
    """
    from app.domain.mentors import ArchitectMentor
    
    project = await project_service.get_project_by_uuid(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Execute architect mentor (detailed mode)
    mentor = ArchitectMentor(preferred_model="claude-opus-4-20250514")
    
    prompt = f"""Create a detailed technical architecture for this project:

Project: {project['name']}
Description: {project['description']}

Provide comprehensive technical details including:
1. Detailed system architecture
2. Data models and schemas
3. API specifications
4. Security considerations
5. Scalability approach
6. Technology stack with justifications
7. Deployment architecture
"""
    
    result = await mentor.execute(prompt, project['project_id'])
    
    # Save architecture artifact using service
    artifact_path = f"{project['project_id']}/architecture/detailed"
    
    await artifact_service.create_artifact(
        db=db,
        artifact_path=artifact_path,
        artifact_type='architecture',
        title='Detailed Architecture',
        content={'architecture': result.get('architecture', '')},
        created_by='architect_mentor'
    )
    
    # Reload page
    return RedirectResponse(
        url=f"/ui/projects/{project_id}",
        status_code=303
    )