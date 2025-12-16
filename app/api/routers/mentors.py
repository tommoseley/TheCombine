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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from database import get_db
from app.api.services.role_prompt_service import RolePromptService
from app.api.services.artifact_service import ArtifactService
from app.api.models import Artifact
from app.api.repositories import ProjectRepository
from app.api.utils.id_generators import generate_epic_id, generate_story_id

# Import mentor classes and request models
from app.domain.mentors import (
    PMMentor,
    ArchitectMentor,
    BAMentor,
    DeveloperMentor,
)
from app.domain.mentors.pm_mentor import PMRequest
from app.domain.mentors.architect_mentor import ArchitectRequest
from app.domain.mentors.ba_mentor import BARequest
from app.domain.mentors.dev_mentor import DeveloperRequest


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
# ARTIFACT LOADING HELPERS (kept in API layer)
# ============================================================================

async def load_epic_content(db: AsyncSession, epic_artifact_path: str) -> Dict[str, Any]:
    """
    Load epic content from database.
    
    This stays in the API layer because it requires database access.
    """
    query = (
        select(Artifact)
        .where(Artifact.artifact_path == epic_artifact_path)
        .where(Artifact.artifact_type == "epic")
    )
    
    result = await db.execute(query)
    epic_artifact = result.scalar_one_or_none()
    
    if not epic_artifact:
        raise ValueError(f"Epic not found at path: {epic_artifact_path}")
    
    return epic_artifact.content or {}


async def load_architecture_content(db: AsyncSession, architecture_artifact_path: str) -> Dict[str, Any]:
    """
    Load architecture content from database.
    
    This stays in the API layer because it requires database access.
    """
    query = (
        select(Artifact)
        .where(Artifact.artifact_path == architecture_artifact_path)
        .where(Artifact.artifact_type == "architecture")
    )
    
    result = await db.execute(query)
    arch_artifact = result.scalar_one_or_none()
    
    if not arch_artifact:
        raise ValueError(f"Architecture not found at path: {architecture_artifact_path}")
    
    return arch_artifact.content or {}


async def load_story_content(db: AsyncSession, story_artifact_path: str) -> Dict[str, Any]:
    """
    Load story content from database.
    
    This stays in the API layer because it requires database access.
    """
    query = (
        select(Artifact)
        .where(Artifact.artifact_path == story_artifact_path)
        .where(Artifact.artifact_type == "story")
    )
    
    result = await db.execute(query)
    story_artifact = result.scalar_one_or_none()
    
    if not story_artifact:
        raise ValueError(f"Story not found at path: {story_artifact_path}")
    
    return story_artifact.content or {}


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
    
    Returns Server-Sent Events with progress updates.
    """
    # Create ID generator function that closes over db
    async def epic_id_generator(project_id: str) -> str:
        return await generate_epic_id(db, project_id)
    
    # Ensure project exists
    project_repo = ProjectRepository(db)
    await project_repo.ensure_exists(request.project_id)
    
    # Create mentor with injected dependencies
    mentor = PMMentor(
        prompt_service=prompt_service,
        artifact_service=artifact_service,
        id_generator=epic_id_generator
    )
    
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
    
    Returns Server-Sent Events with progress updates.
    """
    # Load epic content (API layer responsibility)
    try:
        epic_content = await load_epic_content(db, request.epic_artifact_path)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load epic: {str(e)}")
    
    # Create mentor with injected dependencies
    mentor = ArchitectMentor(
        prompt_service=prompt_service,
        artifact_service=artifact_service
    )
    
    # Add epic content to request data
    request_data = request.dict()
    request_data["epic_content"] = epic_content
    
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
    
    Returns Server-Sent Events with progress updates.
    """
    # Load epic and architecture content (API layer responsibility)
    try:
        epic_content = await load_epic_content(db, request.epic_artifact_path)
        architecture_content = await load_architecture_content(db, request.architecture_artifact_path)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load artifacts: {str(e)}")
    
    # Create ID generator function that closes over db and epic path
    async def story_id_generator(epic_id: str) -> str:
        return await generate_story_id(db, request.epic_artifact_path)
    
    # Create mentor with injected dependencies
    mentor = BAMentor(
        prompt_service=prompt_service,
        artifact_service=artifact_service,
        id_generator=story_id_generator
    )
    
    # Add content to request data
    request_data = request.dict()
    request_data["epic_content"] = epic_content
    request_data["architecture_content"] = architecture_content
    
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
    
    Returns Server-Sent Events with progress updates.
    """
    # Load story and architecture content (API layer responsibility)
    try:
        story_content = await load_story_content(db, request.story_artifact_path)
        
        # Extract epic path from story path (e.g., "PROJ/E001/S001" -> "PROJ/E001")
        path_parts = request.story_artifact_path.split("/")
        if len(path_parts) == 3:
            epic_path = f"{path_parts[0]}/{path_parts[1]}"
            architecture_content = await load_architecture_content(db, epic_path)
        else:
            architecture_content = {}
            
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load artifacts: {str(e)}")
    
    # Create mentor with injected dependencies
    mentor = DeveloperMentor(
        prompt_service=prompt_service,
        artifact_service=artifact_service
    )
    
    # Add content to request data
    request_data = request.dict()
    request_data["story_content"] = story_content
    request_data["architecture_content"] = architecture_content
    
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