"""
Unified Mentor Routes - Streaming endpoints for all mentors

All mentors use Server-Sent Events for real-time progress updates.

Endpoints:
- POST /api/mentors/pm/execute-stream - Create epic with streaming progress
- POST /api/mentors/architect/execute-stream - Create architecture with streaming progress
- POST /api/mentors/ba/execute-stream - Create user stories with streaming progress
- POST /api/mentors/developer/execute-stream - Create implementation with streaming progress
- GET /api/mentors/health - Health check for all mentors
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.combine.services.role_prompt_service import RolePromptService
from app.combine.services.artifact_service import ArtifactService
from app.combine.mentors.pm_mentor import PMMentor, PMRequest
from app.combine.mentors.architect_mentor import ArchitectMentor, ArchitectRequest
from app.combine.mentors.ba_mentor import BAMentor, BARequest
from app.combine.mentors.dev_mentor import DeveloperMentor, DeveloperRequest


router = APIRouter(prefix="/api/mentors", tags=["mentors"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_prompt_service(db: AsyncSession = Depends(get_db)) -> RolePromptService:
    """Get role prompt service instance"""
    return RolePromptService(db)


async def get_artifact_service(db: AsyncSession = Depends(get_db)) -> ArtifactService:
    """Get artifact service instance"""
    return ArtifactService(db)


# ============================================================================
# PM MENTOR ROUTES
# ============================================================================

@router.post("/pm/execute-stream")
async def execute_pm_stream(
    request: PMRequest,
    db: AsyncSession = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_prompt_service),
    artifact_service: ArtifactService = Depends(get_artifact_service)
):
    """
    Stream PM Mentor execution with progress updates.
    
    Request Body:
        {
            "user_query": "Build a user authentication system...",
            "project_id": "AUTH",
            "model": "claude-sonnet-4-20250514",  // optional
            "max_tokens": 4096,  // optional
            "temperature": 0.7  // optional
        }
    
    Returns Server-Sent Events:
        - "📋 Reading PM instructions" (10%)
        - "🔍 Loading epic schema" (20%)
        - "🤖 Analyzing your request" (30%)
        - "✨ Crafting epic definition" (50%)
        - "💭 Building epic structure" (70%)
        - "🔧 Parsing epic JSON" (80%)
        - "✅ Validating epic completeness" (85%)
        - "💾 Saving epic to project" (95%)
        - "🎉 Epic created successfully!" (100%)
    
    Final Event:
        {
            "status": "complete",
            "message": "🎉 PM task completed!",
            "progress": 100,
            "data": {
                "project_id": "AUTH",
                "epic_id": "E001",
                "epic_path": "AUTH/E001",
                "artifact_id": "...",
                "title": "User Authentication System",
                "tokens": {
                    "input": 1234,
                    "output": 2345,
                    "total": 3579
                }
            }
        }
    """
    mentor = PMMentor(db, prompt_service, artifact_service)
    
    return StreamingResponse(
        mentor.stream_execution(request.dict()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ============================================================================
# ARCHITECT MENTOR ROUTES
# ============================================================================

@router.post("/architect/execute-stream")
async def execute_architect_stream(
    request: ArchitectRequest,
    db: AsyncSession = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_prompt_service),
    artifact_service: ArtifactService = Depends(get_artifact_service)
):
    """
    Stream Architect Mentor execution with progress updates.
    
    Request Body:
        {
            "epic_artifact_path": "AUTH/E001",
            "model": "claude-sonnet-4-20250514",  // optional
            "max_tokens": 8192,  // optional (higher for architecture)
            "temperature": 0.5  // optional
        }
    
    Returns Server-Sent Events:
        - "📋 Reading architecture guidelines" (8%)
        - "🔍 Loading architecture schema" (12%)
        - "📖 Loading epic context" (20%)
        - "🤖 Analyzing epic requirements" (28%)
        - "✨ Designing system architecture" (40%)
        - "💭 Defining components and interfaces" (55%)
        - "🗄️ Creating data models" (70%)
        - "🔧 Parsing architecture JSON" (82%)
        - "✅ Validating architecture completeness" (88%)
        - "💾 Saving architecture" (95%)
        - "🎉 Architecture created successfully!" (100%)
    
    Final Event:
        {
            "status": "complete",
            "message": "🎉 ARCHITECT task completed!",
            "progress": 100,
            "data": {
                "epic_artifact_path": "AUTH/E001",
                "architecture_artifact_path": "AUTH/E001",
                "artifact_id": "...",
                "project_id": "AUTH",
                "epic_id": "E001",
                "title": "Architecture for E001",
                "tokens": {
                    "input": 2345,
                    "output": 5678,
                    "total": 8023
                }
            }
        }
    """
    mentor = ArchitectMentor(db, prompt_service, artifact_service)
    
    # Load epic content before streaming
    try:
        epic_content = await mentor._load_epic_content(request.epic_artifact_path)
        
        # Add epic content to request data
        request_data = request.dict()
        request_data["epic_content"] = epic_content
        
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load epic: {str(e)}")
    
    return StreamingResponse(
        mentor.stream_execution(request_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )



# ============================================================================
# BA MENTOR ROUTES
# ============================================================================

@router.post("/ba/execute-stream")
async def execute_ba_stream(
    request: BARequest,
    db: AsyncSession = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_prompt_service),
    artifact_service: ArtifactService = Depends(get_artifact_service)
):
    """
    Stream BA Mentor execution with progress updates.
    
    Request Body:
        {
            "epic_artifact_path": "AUTH/E001",
            "architecture_artifact_path": "AUTH/E001",
            "model": "claude-sonnet-4-20250514",  // optional
            "max_tokens": 8192,  // optional
            "temperature": 0.6  // optional
        }
    
    Returns Server-Sent Events:
        - "📋 Reading BA guidelines" (8%)
        - "🔍 Loading story schema" (12%)
        - "📖 Loading epic context" (18%)
        - "🏗️ Loading architecture context" (24%)
        - "🤖 Analyzing requirements" (30%)
        - "✨ Breaking down into stories" (45%)
        - "💭 Defining acceptance criteria" (60%)
        - "📝 Adding technical details" (75%)
        - "🔧 Parsing stories JSON" (82%)
        - "✅ Validating story structure" (88%)
        - "💾 Creating story artifacts" (95%)
        - "🎉 Stories created successfully!" (100%)
    
    Final Event:
        {
            "status": "complete",
            "message": "🎉 BA task completed!",
            "progress": 100,
            "data": {
                "epic_artifact_path": "AUTH/E001",
                "architecture_artifact_path": "AUTH/E001",
                "stories_created": [
                    {
                        "artifact_path": "AUTH/E001/S001",
                        "artifact_id": "...",
                        "title": "User Registration",
                        "story_id": "S001"
                    },
                    ...
                ],
                "project_id": "AUTH",
                "epic_id": "E001",
                "total_stories": 5,
                "tokens": {
                    "input": 3456,
                    "output": 6789,
                    "total": 10245
                }
            }
        }
    """
    mentor = BAMentor(db, prompt_service, artifact_service)
    
    # Load epic and architecture content before streaming
    try:
        epic_content = await mentor._load_epic_content(request.epic_artifact_path)
        architecture_content = await mentor._load_architecture_content(request.architecture_artifact_path)
        
        # Add content to request data
        request_data = request.dict()
        request_data["epic_content"] = epic_content
        request_data["architecture_content"] = architecture_content
        
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load artifacts: {str(e)}")
    
    return StreamingResponse(
        mentor.stream_execution(request_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ============================================================================
# DEVELOPER MENTOR ROUTES
# ============================================================================

@router.post("/developer/execute-stream")
async def execute_developer_stream(
    request: DeveloperRequest,
    db: AsyncSession = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_prompt_service),
    artifact_service: ArtifactService = Depends(get_artifact_service)
):
    """
    Stream Developer Mentor execution with progress updates.
    
    Request Body:
        {
            "story_artifact_path": "AUTH/E001/S001",
            "model": "claude-sonnet-4-20250514",  // optional
            "max_tokens": 16384,  // optional (very high for code)
            "temperature": 0.3  // optional (low for deterministic code)
        }
    
    Returns Server-Sent Events:
        - "📋 Reading development guidelines" (5%)
        - "🔍 Loading code schema" (8%)
        - "📖 Loading story context" (12%)
        - "🏗️ Loading architecture context" (18%)
        - "🤖 Analyzing technical requirements" (25%)
        - "✨ Planning implementation approach" (32%)
        - "💻 Writing production code" (48%)
        - "🧪 Adding unit tests" (62%)
        - "📝 Creating documentation" (76%)
        - "🔧 Parsing code artifacts" (84%)
        - "✅ Validating code structure" (90%)
        - "💾 Saving implementation" (95%)
        - "🎉 Code ready for review!" (100%)
    
    Final Event:
        {
            "status": "complete",
            "message": "🎉 DEVELOPER task completed!",
            "progress": 100,
            "data": {
                "story_artifact_path": "AUTH/E001/S001",
                "code_artifacts_created": [
                    {
                        "artifact_path": "AUTH/E001/S001",
                        "artifact_id": "...",
                        "title": "Implementation: User Registration",
                        "file_path": "src/auth/registration.py"
                    },
                    ...
                ],
                "project_id": "AUTH",
                "epic_id": "E001",
                "story_id": "S001",
                "total_files": 8,
                "tokens": {
                    "input": 5678,
                    "output": 12345,
                    "total": 18023
                }
            }
        }
    """
    mentor = DeveloperMentor(db, prompt_service, artifact_service)
    
    # Load story and architecture content before streaming
    try:
        story_content = await mentor._load_story_content(request.story_artifact_path)
        
        # Extract epic path from story path (e.g., "PROJ/E001/S001" -> "PROJ/E001")
        path_parts = request.story_artifact_path.split("/")
        if len(path_parts) == 3:
            epic_path = f"{path_parts[0]}/{path_parts[1]}"
            architecture_content = await mentor._load_architecture_content(epic_path)
        else:
            architecture_content = {}
        
        # Add content to request data
        request_data = request.dict()
        request_data["story_content"] = story_content
        request_data["architecture_content"] = architecture_content
        
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load artifacts: {str(e)}")
    
    return StreamingResponse(
        mentor.stream_execution(request_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Health check for mentor system
    
    Returns:
        {
            "status": "healthy",
            "mentors": ["pm", "architect", "ba", "developer"],
            "version": "1.0.0"
        }
    """
    return {
        "status": "healthy",
        "mentors": ["pm", "architect", "ba", "developer"],
        "version": "1.0.0"
    }