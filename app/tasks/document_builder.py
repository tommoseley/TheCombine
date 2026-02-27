"""
Background document build runner.

Runs document builds as background tasks, updating the task registry
with progress. This decouples the build from the SSE stream.
"""
import json
import logging
from uuid import UUID

from app.tasks.registry import TaskStatus, update_task
from app.domain.services.document_builder import DocumentBuilder
from app.api.services.document_service import DocumentService
from app.api.services.role_prompt_service import RolePromptService
from app.api.routers.documents import PromptServiceAdapter
from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
from app.domain.services.llm_execution_logger import LLMExecutionLogger
from app.core.database import async_session_factory
# WS-INTAKE-SEP-003: Workflow-based builds
from app.domain.workflow.plan_executor import PlanExecutor
from app.domain.workflow.pg_state_persistence import PgStatePersistence
from app.domain.workflow.plan_registry import get_plan_registry
from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
from app.api.models.document import Document
from sqlalchemy import select, and_

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


# WS-INTAKE-SEP-003: Workflow-based document builds
# Maps document types to their workflow IDs
WORKFLOW_DOCUMENT_TYPES = {
    "project_discovery": "pm_discovery",
}


async def run_workflow_build(
    task_id: UUID,
    project_id: UUID,
    doc_type_id: str,
    correlation_id: UUID,
) -> None:
    """
    Run workflow-based document build in background.
    
    WS-INTAKE-SEP-003: For document types that have associated workflows,
    this runs the workflow to completion instead of using the old builder.
    
    Args:
        task_id: Task ID for status tracking
        project_id: Project UUID
        doc_type_id: Document type to build
        correlation_id: Correlation ID for logging
    """
    logger.info(f"[Workflow] Starting workflow build task {task_id} for {doc_type_id}")
    
    workflow_id = WORKFLOW_DOCUMENT_TYPES.get(doc_type_id)
    if not workflow_id:
        raise ValueError(f"No workflow defined for document type: {doc_type_id}")
    
    async with async_session_factory() as db:
        try:
            update_task(task_id, status=TaskStatus.RUNNING, progress=5, message="Loading workflow...")
            
            # Load input document (concierge_intake for pm_discovery)
            if doc_type_id == "project_discovery":
                intake_result = await db.execute(
                    select(Document).where(
                        and_(
                            Document.space_type == "project",
                            Document.space_id == project_id,
                            Document.doc_type_id == "concierge_intake",
                            Document.is_latest == True
                        )
                    )
                )
                intake_doc = intake_result.scalar_one_or_none()
                
                if not intake_doc:
                    # Fallback: try project_discovery with intake schema (legacy)
                    intake_result = await db.execute(
                        select(Document).where(
                            and_(
                                Document.space_type == "project",
                                Document.space_id == project_id,
                                Document.doc_type_id == "project_discovery",
                                Document.is_latest == True
                            )
                        )
                    )
                    intake_doc = intake_result.scalar_one_or_none()
                    
                if not intake_doc or not intake_doc.content:
                    update_task(
                        task_id,
                        status=TaskStatus.FAILED,
                        message="No intake document found",
                        error="Concierge Intake document required before generating Project Discovery"
                    )
                    return
                
                initial_context = {
                    "concierge_intake": intake_doc.content,
                    "project_id": str(project_id),
                    "user_input": intake_doc.content.get("summary", {}).get("user_statement", ""),
                }
            else:
                initial_context = {"project_id": str(project_id)}
            
            update_task(task_id, progress=10, message="Starting workflow execution...")
            
            # Create executor with LLM
            from app.domain.workflow.nodes.llm_executors import create_llm_executors
            from app.domain.workflow.thread_manager import ThreadManager
            from app.domain.workflow.outcome_recorder import OutcomeRecorder
            
            executors = await create_llm_executors(db)
            thread_manager = ThreadManager(db)
            outcome_recorder = OutcomeRecorder(db)
            
            executor = PlanExecutor(
                persistence=PgStatePersistence(db),
                plan_registry=get_plan_registry(),
                executors=executors,
                thread_manager=thread_manager,
                outcome_recorder=outcome_recorder,
            )
            
            # Start workflow execution
            state = await executor.start_execution(
                project_id=str(project_id),
                document_type=doc_type_id,
                initial_context=initial_context,
            )
            
            update_task(task_id, progress=20, message="Generating document...")
            
            # Run to completion
            state = await executor.run_to_completion_or_pause(state.execution_id)
            
            # Check outcome
            if state.status == DocumentWorkflowStatus.COMPLETED:
                # Get the produced document from workflow context
                produced_doc = state.context_state.get("last_produced_document")
                
                if produced_doc:
                    update_task(task_id, progress=80, message="Saving document...")
                    
                    # Create the document record
                    doc_service = DocumentService(db)
                    new_doc = await doc_service.create_document(
                        space_type="project",
                        space_id=project_id,
                        doc_type_id=doc_type_id,
                        title="Project Discovery",
                        summary=produced_doc.get("preliminary_summary", {}).get("problem_understanding", "")[:500],
                        content=produced_doc,
                        lifecycle_state="complete",
                    )
                    
                    update_task(
                        task_id,
                        status=TaskStatus.COMPLETE,
                        progress=100,
                        message="Document created successfully",
                        result={"document_id": str(new_doc.id)}
                    )
                    logger.info(f"[Workflow] Build complete: {task_id}, doc_id={new_doc.id}")
                else:
                    update_task(
                        task_id,
                        status=TaskStatus.FAILED,
                        message="Workflow completed but no document produced",
                        error="No document in workflow output"
                    )
            elif state.status == DocumentWorkflowStatus.PAUSED:
                update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message="Workflow paused unexpectedly",
                    error="Workflow requires user input (unexpected for this document type)"
                )
            else:
                update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Workflow ended with status: {state.status.value}",
                    error=state.terminal_outcome or "Unknown error"
                )
                
        except Exception as e:
            logger.exception(f"[Workflow] Build exception: {task_id}")
            update_task(
                task_id,
                status=TaskStatus.FAILED,
                progress=0,
                message=f"Error: {str(e)}",
                error=str(e)
            )