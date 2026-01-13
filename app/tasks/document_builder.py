"""
Background document build runner.

Runs document builds as background tasks, updating the task registry
with progress. This decouples the build from the SSE stream.
"""
import asyncio
import json
import logging
from uuid import UUID

from app.tasks.registry import TaskInfo, TaskStatus, update_task
from app.domain.services.document_builder import DocumentBuilder
from app.api.services.document_service import DocumentService
from app.api.services.role_prompt_service import RolePromptService
from app.api.routers.documents import PromptServiceAdapter
from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
from app.domain.services.llm_execution_logger import LLMExecutionLogger
from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_document_build(
    task_id: UUID,
    project_id: UUID,
    project_description: str,
    doc_type_id: str,
    correlation_id: UUID,
) -> None:
    """
    Run document build in background.
    
    Creates its own database session (isolated from request).
    Updates task registry with progress.
    """
    logger.info(f"[Background] Starting build task {task_id} for {doc_type_id}")
    
    # Create isolated database session for this task
    async with async_session_factory() as db:
        try:
            update_task(task_id, status=TaskStatus.RUNNING, progress=5, message="Initializing...")
            
            # Create dependencies
            llm_repo = PostgresLLMLogRepository(db)
            llm_logger = LLMExecutionLogger(llm_repo)
            prompt_service = RolePromptService(db)
            prompt_adapter = PromptServiceAdapter(prompt_service)
            document_service = DocumentService(db)
            
            builder = DocumentBuilder(
                db=db,
                prompt_service=prompt_adapter,
                document_service=document_service,
                correlation_id=correlation_id,
                llm_logger=llm_logger,
            )
            
            # Run the build stream, capturing progress
            document_id = None
            async for sse_event in builder.build_stream(
                doc_type_id=doc_type_id,
                space_type='project',
                space_id=project_id,
                inputs={
                    "user_query": project_description,
                    "project_description": project_description,
                },
                options={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 16384,
                    "temperature": 0.5,
                }
            ):
                # Parse SSE event to extract progress
                progress_data = _parse_sse_event(sse_event)
                if progress_data:
                    status = progress_data.get("status", "")
                    message = progress_data.get("message", "")
                    progress = progress_data.get("progress", 0)
                    
                    if status == "complete":
                        document_id = progress_data.get("data", {}).get("document_id")
                        update_task(
                            task_id,
                            status=TaskStatus.COMPLETE,
                            progress=100,
                            message=message,
                            result={"document_id": document_id}
                        )
                        logger.info(f"[Background] Build complete: {task_id}, doc_id={document_id}")
                        return
                    
                    elif status == "error":
                        update_task(
                            task_id,
                            status=TaskStatus.FAILED,
                            progress=progress,
                            message=message,
                            error=message
                        )
                        logger.error(f"[Background] Build failed: {task_id} - {message}")
                        return
                    
                    else:
                        # Progress update
                        update_task(task_id, progress=progress, message=message)
            
            # If we get here without complete/error, something went wrong
            update_task(
                task_id,
                status=TaskStatus.FAILED,
                error="Build ended without completion status"
            )
            
        except Exception as e:
            logger.exception(f"[Background] Build exception: {task_id}")
            update_task(
                task_id,
                status=TaskStatus.FAILED,
                progress=0,
                message=f"Error: {str(e)}",
                error=str(e)
            )


def _parse_sse_event(sse_event: str) -> dict | None:
    """Parse SSE event string to extract data."""
    try:
        for line in sse_event.strip().split('\n'):
            if line.startswith('data: '):
                return json.loads(line[6:])
    except (json.JSONDecodeError, Exception):
        pass
    return None
