"""
Debug and test routes for The Combine UI
These routes help diagnose issues during development
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .shared import templates

router = APIRouter(tags=["debug"])


@router.get("/test-template", response_class=HTMLResponse)
async def test_template(request: Request):
    """Test if basic template rendering works"""
    return """
    <div style="padding: 20px; border: 2px solid green; margin: 20px;">
        <h1>✓ Plain HTML works!</h1>
        <p>If you see this, FastAPI can return HTML.</p>
    </div>
    """


@router.get("/test-template-engine", response_class=HTMLResponse)
async def test_template_engine(request: Request):
    """Test if Jinja2 template engine works"""
    try:
        return templates.TemplateResponse(
            "pages/project_detail.html",
            {
                "request": request,
                "project": {
                    "id": "test-123",
                    "project_id": "TEST",
                    "name": "Test Project",
                    "description": "Testing templates"
                },
                "high_level_architecture": None,
                "detailed_architecture": None,
                "epics": []
            }
        )
    except Exception as e:
        import traceback
        return f"""
        <div style="padding: 20px; border: 2px solid red; margin: 20px;">
            <h1>✗ Template Error</h1>
            <pre>{str(e)}</pre>
            <h2>Traceback:</h2>
            <pre>{traceback.format_exc()}</pre>
        </div>
        """


@router.get("/test-db", response_class=HTMLResponse)
async def test_db(request: Request, db: AsyncSession = Depends(get_db)):
    """Test if database works"""
    try:
        from sqlalchemy import select, text
        from app.combine.models import Project
        
        # Test 1: Simple query
        result = await db.execute(text("SELECT 1"))
        test_val = result.scalar()
        
        # Test 2: Get first project
        query = select(Project).limit(1)
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if project:
            project_info = f"Found project: {project.name} (id={project.id})"
        else:
            project_info = "No projects in database"
        
        return f"""
        <div style="padding: 20px; border: 2px solid green;">
            <h1>✓ Database Works!</h1>
            <p>Test query result: {test_val}</p>
            <p>{project_info}</p>
        </div>
        """
    except Exception as e:
        import traceback
        return f"""
        <div style="padding: 20px; border: 2px solid red;">
            <h1>✗ Database Error</h1>
            <pre>{str(e)}</pre>
            <pre>{traceback.format_exc()}</pre>
        </div>
        """