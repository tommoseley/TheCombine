"""
Story Backlog Commands - Command endpoints for story backlog operations.

WS-STORY-BACKLOG-COMMANDS-SLICE-1: Init command for creating StoryBacklog from EpicBacklog.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/commands", tags=["commands"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class StoryBacklogInitRequest(BaseModel):
    """Request to initialize StoryBacklog from EpicBacklog."""
    project_id: str


class DocumentRef(BaseModel):
    """Reference to a document."""
    document_type: str
    params: dict


class StoryBacklogInitResponse(BaseModel):
    """Response from StoryBacklog init."""
    status: str  # "created" | "exists"
    document_id: str
    document_ref: DocumentRef
    summary: dict


# =============================================================================
# STORY BACKLOG COMMANDS
# =============================================================================

@router.post("/story-backlog/init", response_model=StoryBacklogInitResponse)
async def init_story_backlog(
    request: StoryBacklogInitRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize StoryBacklog from EpicBacklog.
    
    Copies epics from EpicBacklog with empty stories arrays.
    Idempotent: returns existing StoryBacklog if already initialized.
    
    WS-STORY-BACKLOG-COMMANDS-SLICE-1
    """
    project_id = request.project_id
    
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    doc_service = DocumentService(db)
    
    # Check if StoryBacklog already exists
    existing = await doc_service.get_latest(
        space_type="project",
        space_id=project_uuid,
        doc_type_id="story_backlog"
    )
    
    if existing:
        logger.info(f"StoryBacklog already exists for project {project_id}")
        return StoryBacklogInitResponse(
            status="exists",
            document_id=str(existing.id),
            document_ref=DocumentRef(
                document_type="StoryBacklog",
                params={"project_id": project_id}
            ),
            summary={
                "epics_initialized": len(existing.content.get("epics", [])),
                "stories_existing": sum(
                    len(e.get("stories", []))
                    for e in existing.content.get("epics", [])
                )
            }
        )
    
    # Load EpicBacklog
    epic_backlog = await doc_service.get_latest(
        space_type="project",
        space_id=project_uuid,
        doc_type_id="epic_backlog"
    )
    
    if not epic_backlog:
        raise HTTPException(
            status_code=404,
            detail="EpicBacklog not found for project. Build Epic Backlog first."
        )
    
    if not epic_backlog.content:
        raise HTTPException(
            status_code=422,
            detail="EpicBacklog has no content"
        )
    
    source_epics = epic_backlog.content.get("epics", [])
    if not source_epics:
        raise HTTPException(
            status_code=422,
            detail="EpicBacklog contains no epics"
        )
    
    # Build StoryBacklog content
    story_backlog_epics = []
    for epic in source_epics:
        story_backlog_epics.append({
            "epic_id": epic.get("epic_id") or epic.get("id") or f"epic-{len(story_backlog_epics)+1}",
            "name": epic.get("title") or epic.get("name") or "Untitled Epic",
            "intent": epic.get("description") or epic.get("intent") or "",
            "mvp_phase": epic.get("mvp_phase") or epic.get("phase") or "mvp",
            "stories": []  # Empty - to be populated by generate-epic
        })
    
    # Get project name if available
    project_name = epic_backlog.content.get("project_name", "")
    
    story_backlog_content = {
        "project_id": project_id,
        "project_name": project_name,
        "source_epic_backlog_ref": {
            "document_type": "EpicBacklog",
            "params": {"project_id": project_id}
        },
        "epics": story_backlog_epics
    }
    
    # Create StoryBacklog document
    new_doc = await doc_service.create_document(
        space_type="project",
        space_id=project_uuid,
        doc_type_id="story_backlog",
        title="Story Backlog",
        content=story_backlog_content,
        summary=f"Story backlog with {len(story_backlog_epics)} epics",
        created_by="story-backlog-init",
        created_by_type="builder"
    )
    
    await db.commit()
    
    logger.info(f"Created StoryBacklog for project {project_id} with {len(story_backlog_epics)} epics")
    
    return StoryBacklogInitResponse(
        status="created",
        document_id=str(new_doc.id),
        document_ref=DocumentRef(
            document_type="StoryBacklog",
            params={"project_id": project_id}
        ),
        summary={
            "epics_initialized": len(story_backlog_epics),
            "stories_existing": 0
        }
    )



# =============================================================================
# WS-STORY-BACKLOG-COMMANDS-SLICE-2: Generate endpoints
# =============================================================================

class GenerateEpicRequest(BaseModel):
    """Request to generate stories for a single epic."""
    project_id: str
    epic_id: str


class GenerateEpicResponse(BaseModel):
    """Response from generate-epic."""
    status: str
    epic_id: str
    summary: dict
    thread_id: Optional[str] = None  # ADR-035: Thread reference
    stories: Optional[list] = None  # The generated story summaries for immediate rendering
    error: Optional[str] = None


class GenerateAllRequest(BaseModel):
    """Request to generate stories for all epics."""
    project_id: str


class GenerateAllResponse(BaseModel):
    """Response from generate-all."""
    status: str
    summary: dict
    thread_id: Optional[str] = None  # ADR-035: Parent thread reference
    errors: Optional[list] = None


@router.post("/story-backlog/generate-epic", response_model=GenerateEpicResponse)
async def generate_epic_stories(
    request: GenerateEpicRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate stories for a single epic.
    
    Calls LLM, stores StoryDetail documents, projects summaries to StoryBacklog.
    
    WS-STORY-BACKLOG-COMMANDS-SLICE-2
    """
    from app.domain.services.story_backlog_service import StoryBacklogService
    from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
    from app.domain.services.llm_execution_logger import LLMExecutionLogger
    
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    # ADR-010: Create LLM logger for telemetry
    llm_repo = PostgresLLMLogRepository(db)
    llm_logger = LLMExecutionLogger(llm_repo)
    
    service = StoryBacklogService(db, llm_logger=llm_logger)
    result = await service.generate_epic_stories(project_uuid, request.epic_id)
    
    if result.status == "error" and "not found" in (result.error or "").lower():
        raise HTTPException(status_code=404, detail=result.error)
    
    return GenerateEpicResponse(
        status=result.status,
        epic_id=result.epic_id,
        summary={
            "stories_generated": result.stories_generated,
            "stories_written": result.stories_written
        },
        thread_id=str(result.thread_id) if result.thread_id else None,
        stories=result.stories,
        error=result.error
    )


@router.post("/story-backlog/generate-all", response_model=GenerateAllResponse)
async def generate_all_stories(
    request: GenerateAllRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate stories for all epics in the StoryBacklog.
    
    Calls generate-epic for each epic sequentially.
    
    WS-STORY-BACKLOG-COMMANDS-SLICE-2
    """
    from app.domain.services.story_backlog_service import StoryBacklogService
    from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
    from app.domain.services.llm_execution_logger import LLMExecutionLogger
    
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    # ADR-010: Create LLM logger for telemetry
    llm_repo = PostgresLLMLogRepository(db)
    llm_logger = LLMExecutionLogger(llm_repo)
    
    service = StoryBacklogService(db, llm_logger=llm_logger)
    result = await service.generate_all_stories(project_uuid)
    
    if result.status == "error" and result.errors:
        if "not found" in result.errors[0].lower():
            raise HTTPException(status_code=404, detail=result.errors[0])
    
    return GenerateAllResponse(
        status=result.status,
        summary={
            "epics_processed": result.epics_processed,
            "total_stories_generated": result.total_stories_generated
        },
        thread_id=str(result.thread_id) if result.thread_id else None,
        errors=result.errors
    )






# =============================================================================
# WS-ADR-035: Thread Observation Endpoints
# =============================================================================

class ThreadStatusResponse(BaseModel):
    """Response from thread status query."""
    thread_id: str
    kind: str
    status: str
    target_ref: dict
    created_at: str
    closed_at: Optional[str] = None
    child_summary: Optional[dict] = None


class ActiveThreadsResponse(BaseModel):
    """Response from active threads query."""
    threads: list


@router.get("/threads/{thread_id}", response_model=ThreadStatusResponse)
async def get_thread_status(
    thread_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get status of a specific thread."""
    from app.domain.services.thread_execution_service import ThreadExecutionService
    
    try:
        thread_uuid = UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
    
    service = ThreadExecutionService(db)
    thread = await service.get_thread(thread_uuid)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get child summary if this is an orchestration thread
    child_summary = None
    if thread.kind.endswith("_all"):
        child_summary = await service.get_child_summary(thread_uuid)
    
    return ThreadStatusResponse(
        thread_id=str(thread.id),
        kind=thread.kind,
        status=thread.status.value,
        target_ref=thread.target_ref,
        created_at=thread.created_at.isoformat(),
        closed_at=thread.closed_at.isoformat() if thread.closed_at else None,
        child_summary=child_summary,
    )


@router.get("/projects/{project_id}/threads", response_model=ActiveThreadsResponse)
async def get_active_threads(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all active threads for a project."""
    from app.domain.services.thread_execution_service import ThreadExecutionService
    
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    service = ThreadExecutionService(db)
    threads = await service.get_active_threads("project", project_uuid)
    
    return ActiveThreadsResponse(
        threads=[
            {
                "thread_id": str(t.id),
                "kind": t.kind,
                "status": t.status.value,
                "target_ref": t.target_ref,
                "created_at": t.created_at.isoformat(),
            }
            for t in threads
        ]
    )


# =============================================================================
# WS-STORY-BACKLOG-COMMANDS-SLICE-3: Streaming generate-all endpoint
# =============================================================================

@router.post("/story-backlog/generate-all-stream")
async def generate_all_stories_stream(
    request: GenerateAllRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate stories for all epics with SSE streaming.
    
    Returns results as each epic completes (parallel execution, streaming output).
    """
    from fastapi.responses import StreamingResponse
    from app.domain.services.story_backlog_service import StoryBacklogService
    from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
    from app.domain.services.llm_execution_logger import LLMExecutionLogger
    
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    # ADR-010: Create LLM logger for telemetry
    llm_repo = PostgresLLMLogRepository(db)
    llm_logger = LLMExecutionLogger(llm_repo)
    
    service = StoryBacklogService(db, llm_logger=llm_logger)
    
    return StreamingResponse(
        service.generate_all_stories_stream(project_uuid),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


