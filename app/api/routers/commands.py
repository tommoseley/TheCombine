"""
Command endpoints for thread observation and document operations.
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
# PHASE 7 (WS-DOCUMENT-SYSTEM-CLEANUP): Canonical Document Commands
# =============================================================================
# All document commands under /api/commands/documents/{doc_type_id}
# Pattern: POST /api/commands/documents/{doc_type_id}/{action}
# Response: JSON with task_id
# =============================================================================

class DocumentBuildRequest(BaseModel):
    """Request to build a document."""
    project_id: str
    user_query: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = 4096
    temperature: Optional[float] = 0.7


class DocumentBuildResponse(BaseModel):
    """Response from document build command."""
    status: str  # "queued" | "started" | "completed" | "error"
    task_id: str
    doc_type_id: str
    document_id: Optional[str] = None
    message: Optional[str] = None


class MarkStaleRequest(BaseModel):
    """Request to mark a document as stale."""
    project_id: str


class MarkStaleResponse(BaseModel):
    """Response from mark-stale command."""
    status: str  # "marked" | "already_stale" | "not_found"
    task_id: str
    doc_type_id: str
    document_id: Optional[str] = None
    downstream_marked: int = 0


@router.post("/documents/{doc_type_id}/build", response_model=DocumentBuildResponse)
async def build_document_command(
    doc_type_id: str,
    request: DocumentBuildRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Build a document (canonical command route).
    
    Phase 7 (WS-DOCUMENT-SYSTEM-CLEANUP): Canonical endpoint for document building.
    Returns task_id for async tracking.
    
    Pattern: POST /api/commands/documents/{doc_type_id}/build
    """
    from uuid import uuid4
    from app.domain.services.document_builder import DocumentBuilder
    from app.api.services.role_prompt_service import RolePromptService
    from app.api.services.document_service import DocumentService
    from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
    from app.domain.services.llm_execution_logger import LLMExecutionLogger
    
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    # Generate task_id for tracking
    task_id = str(uuid4())
    
    logger.info(f"[Phase7] Build command: doc_type={doc_type_id}, project={request.project_id}, task={task_id}")
    
    # Set up services
    llm_repo = PostgresLLMLogRepository(db)
    llm_logger = LLMExecutionLogger(llm_repo)
    role_prompt_service = RolePromptService(db)
    document_service = DocumentService(db)
    
    # Create prompt adapter
    class PromptAdapter:
        def __init__(self, svc):
            self.svc = svc
        
        async def get_prompt_and_schema(self, role_name, task_name):
            from app.api.services.role_prompt_service import PromptNotFoundError
            try:
                composed = await self.svc.get_composed_prompt(role_name, task_name)
            except PromptNotFoundError:
                raise ValueError(f"No prompt found for {role_name}/{task_name}")
            prompt_text, prompt_id = await self.svc.build_prompt(role_name, task_name)
            schema = composed.expected_schema or {}
            return prompt_text, str(prompt_id), schema
    
    prompt_adapter = PromptAdapter(role_prompt_service)
    
    builder = DocumentBuilder(
        db=db,
        prompt_service=prompt_adapter,
        document_service=document_service,
        correlation_id=UUID(task_id),
        llm_logger=llm_logger,
    )
    
    # Check buildability
    can_build, missing = await builder.can_build(doc_type_id, "project", project_uuid)
    
    if not can_build:
        return DocumentBuildResponse(
            status="error",
            task_id=task_id,
            doc_type_id=doc_type_id,
            message=f"Cannot build: missing dependencies {missing}"
        )
    
    # Execute build (synchronous for now - async queueing in future)
    result = await builder.build(
        doc_type_id=doc_type_id,
        space_type="project",
        space_id=project_uuid,
        inputs={
            "user_query": request.user_query,
        },
        model=request.model,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )
    
    if not result.success:
        return DocumentBuildResponse(
            status="error",
            task_id=task_id,
            doc_type_id=doc_type_id,
            message=result.error
        )
    
    await db.commit()
    
    return DocumentBuildResponse(
        status="completed",
        task_id=task_id,
        doc_type_id=doc_type_id,
        document_id=result.document_id,
        message=f"Built {doc_type_id}: {result.title}"
    )


@router.post("/documents/{doc_type_id}/mark-stale", response_model=MarkStaleResponse)
async def mark_stale_command(
    doc_type_id: str,
    request: MarkStaleRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a document as stale (canonical command route).
    
    Phase 7 (WS-DOCUMENT-SYSTEM-CLEANUP): Canonical endpoint for marking stale.
    Also propagates staleness to downstream documents per ADR-036.
    
    Pattern: POST /api/commands/documents/{doc_type_id}/mark-stale
    """
    from uuid import uuid4
    from app.domain.services.staleness_service import StalenessService
    
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    # Generate task_id for tracking
    task_id = str(uuid4())
    
    logger.info(f"[Phase7] Mark-stale command: doc_type={doc_type_id}, project={request.project_id}, task={task_id}")
    
    doc_service = DocumentService(db)
    staleness_service = StalenessService(db)
    
    # Get the document
    document = await doc_service.get_latest(
        space_type="project",
        space_id=project_uuid,
        doc_type_id=doc_type_id
    )
    
    if not document:
        return MarkStaleResponse(
            status="not_found",
            task_id=task_id,
            doc_type_id=doc_type_id,
            message=f"No {doc_type_id} found for project"
        )
    
    # Check if already stale
    if document.lifecycle_state == "stale":
        return MarkStaleResponse(
            status="already_stale",
            task_id=task_id,
            doc_type_id=doc_type_id,
            document_id=str(document.id),
            downstream_marked=0
        )
    
    # Mark as stale
    document.mark_stale()
    
    # Propagate to downstream documents
    downstream_count = await staleness_service.propagate_staleness(document)
    
    await db.commit()
    
    logger.info(f"[Phase7] Marked {doc_type_id} stale, propagated to {downstream_count} downstream docs")
    
    return MarkStaleResponse(
        status="marked",
        task_id=task_id,
        doc_type_id=doc_type_id,
        document_id=str(document.id),
        downstream_marked=downstream_count
    )