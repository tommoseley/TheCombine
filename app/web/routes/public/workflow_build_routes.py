"""
Workflow-based document build routes.

For document types with PGC workflows (e.g., project_discovery),
provides interactive build flow with question/answer UI.

WS-PGC-UX-001: PGC Questions UI Integration
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import Document
from app.api.models.project import Project
from app.core.database import get_db
from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
from app.domain.workflow.nodes.llm_executors import create_llm_executors
from app.domain.workflow.outcome_recorder import OutcomeRecorder
from app.domain.workflow.pg_state_persistence import PgStatePersistence
from app.domain.workflow.plan_executor import PlanExecutor
from app.domain.workflow.plan_registry import get_plan_registry
from app.domain.workflow.thread_manager import ThreadManager
from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
from app.api.models.pgc_answer import PGCAnswer
from ..shared import templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workflow-build"])


def _is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"

# Document types that use workflow builds (have PGC)
WORKFLOW_BUILD_TYPES = {"project_discovery"}


async def _get_project_with_icon(db: AsyncSession, project_id: str) -> Optional[dict]:
    """Get project with icon field via ORM."""
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
    except (ValueError, TypeError):
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


async def _get_intake_document(db: AsyncSession, project_uuid: UUID) -> Optional[Document]:
    """Load concierge_intake document for project."""
    result = await db.execute(
        select(Document).where(
            and_(
                Document.space_type == "project",
                Document.space_id == project_uuid,
                Document.doc_type_id == "concierge_intake",
                Document.is_latest == True
            )
        )
    )
    return result.scalar_one_or_none()


async def _create_executor(db: AsyncSession) -> PlanExecutor:
    """Create a PlanExecutor with all dependencies."""
    executors = await create_llm_executors(db)
    thread_manager = ThreadManager(db)
    outcome_recorder = OutcomeRecorder(db)

    return PlanExecutor(
        persistence=PgStatePersistence(db),
        plan_registry=get_plan_registry(),
        executors=executors,
        thread_manager=thread_manager,
        outcome_recorder=outcome_recorder,
        db_session=db,
    )


def _parse_pgc_form(form) -> Dict[str, Any]:
    """Parse form data into answers dict.

    Handles:
    - answers[QUESTION_ID] = "value" (single value)
    - answers[QUESTION_ID][] = ["a", "b"] (multi-select)
    - answers[QUESTION_ID] = "true"/"false" (yes/no)
    """
    answers = {}
    multi_values = {}

    # Log raw form data for debugging
    raw_items = list(form.multi_items())
    logger.info(f"PGC form raw items: {raw_items}")

    for key, value in raw_items:
        if key.startswith("answers["):
            if key.endswith("[]"):
                q_id = key[8:-3]  # answers[X][] -> X (8 chars prefix, 3 chars suffix)
                if q_id not in multi_values:
                    multi_values[q_id] = []
                multi_values[q_id].append(value)
                logger.debug(f"PGC form multi-choice: {q_id} += {value!r}")
            else:
                q_id = key[8:-1]  # answers[X] -> X (8 chars prefix, 1 char suffix)
                if value == "true":
                    answers[q_id] = True
                elif value == "false":
                    answers[q_id] = False
                else:
                    answers[q_id] = value
                logger.debug(f"PGC form single: {q_id} = {value!r}")

    answers.update(multi_values)
    logger.info(f"PGC form parsed answers: {answers}")
    return answers


def _estimate_progress(state) -> int:
    """Estimate progress percentage based on workflow state."""
    node_progress = {
        "pgc": 10,
        "generation": 50,
        "qa": 80,
        "persist": 95,
        "end": 100,
    }
    return node_progress.get(state.current_node_id, 30)


def _get_status_message(state) -> str:
    """Get human-readable status message."""
    node_messages = {
        "pgc": "Preparing questions...",
        "generation": "Generating document...",
        "qa": "Validating quality...",
        "persist": "Saving document...",
        "end": "Completing...",
    }
    return node_messages.get(state.current_node_id, "Processing...")


# Document type config
DOC_TYPE_CONFIG = {
    "project_discovery": {
        "name": "Project Discovery",
        "icon": "compass",
    }
}


def _render_workflow_state(
    request: Request,
    state,
    project: dict,
    doc_type_id: str,
) -> HTMLResponse:
    """Render appropriate partial based on workflow state.
    
    For HTMX requests, returns just the partial.
    For direct navigation, returns full page with layout.
    """
    config = DOC_TYPE_CONFIG.get(doc_type_id, {"name": doc_type_id, "icon": "file-text"})
    is_htmx = _is_htmx_request(request)

    context = {
        "request": request,
        "project": project,
        "project_id": project["id"],
        "execution_id": state.execution_id,
        "doc_type_id": doc_type_id,
        "doc_type_name": config["name"],
        "doc_type_icon": config["icon"],
        "is_htmx": is_htmx,
    }

    logger.info(f"Rendering workflow state: status={state.status}, pending_input={state.pending_user_input}, has_payload={state.pending_user_input_payload is not None}")

    if state.status == DocumentWorkflowStatus.COMPLETED:
        context["workflow_state"] = "complete"
        template = "public/pages/partials/_workflow_build_container.html" if is_htmx else "public/pages/workflow_build_page.html"
        return templates.TemplateResponse(template, context)

    if state.status == DocumentWorkflowStatus.FAILED:
        context["workflow_state"] = "failed"
        context["error_message"] = state.terminal_outcome or "Unknown error"
        template = "public/pages/partials/_workflow_build_container.html" if is_htmx else "public/pages/workflow_build_page.html"
        return templates.TemplateResponse(template, context)

    # Check PAUSED status explicitly
    if state.status == DocumentWorkflowStatus.PAUSED:
        if state.pending_user_input_payload:
            questions = state.pending_user_input_payload.get("questions", [])
            if questions:
                context["workflow_state"] = "paused_pgc"
                context["questions"] = questions
                context["pending_user_input_payload"] = state.pending_user_input_payload
                template = "public/pages/partials/_workflow_build_container.html" if is_htmx else "public/pages/workflow_build_page.html"
                return templates.TemplateResponse(template, context)
        
        # Paused but no payload/questions - stale execution, need to regenerate
        logger.warning(f"Execution {state.execution_id} is paused but has no questions payload - stale state")
        context["workflow_state"] = "failed"
        context["error_message"] = "Previous workflow session expired. Please try again."
        template = "public/pages/partials/_workflow_build_container.html" if is_htmx else "public/pages/workflow_build_page.html"
        return templates.TemplateResponse(template, context)

    # Running state (PENDING or RUNNING)
    context["workflow_state"] = "running"
    context["progress"] = _estimate_progress(state)
    context["status_message"] = _get_status_message(state)
    template = "public/pages/partials/_workflow_build_container.html" if is_htmx else "public/pages/workflow_build_page.html"
    return templates.TemplateResponse(template, context)


@router.post("/projects/{project_id}/workflows/{doc_type_id}/start", response_class=HTMLResponse)
async def start_workflow_build(
    request: Request,
    project_id: str,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    Start workflow-based document build.

    Returns:
    - PGC questions partial if workflow pauses
    - Generating partial if workflow runs without pause
    - Complete partial if workflow finishes immediately
    """
    if doc_type_id not in WORKFLOW_BUILD_TYPES:
        raise HTTPException(400, f"{doc_type_id} does not use workflow builds")

    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    proj_uuid = UUID(project["id"])

    intake = await _get_intake_document(db, proj_uuid)
    if not intake:
        raise HTTPException(400, "Concierge Intake required before generating Project Discovery")

    executor = await _create_executor(db)

    correlation_id = getattr(request.state, "correlation_id", None) or uuid4()
    document_id = f"{doc_type_id}-{correlation_id.hex[:12] if hasattr(correlation_id, 'hex') else str(correlation_id)[:12]}"

    state = await executor.start_execution(
        project_id=str(proj_uuid),
        document_type=doc_type_id,
        initial_context={
            "concierge_intake": intake.content,
            "project_id": str(proj_uuid),
        },
    )

    state = await executor.run_to_completion_or_pause(state.execution_id)

    return _render_workflow_state(request, state, project, doc_type_id)


@router.post("/projects/{project_id}/workflows/{execution_id}/pgc-answers", response_class=HTMLResponse)
async def submit_pgc_answers(
    request: Request,
    project_id: str,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    Submit PGC answers and resume workflow.

    Form data: answers[QUESTION_ID] = value
    """
    form = await request.form()
    answers = _parse_pgc_form(form)

    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    proj_uuid = UUID(project["id"])

    # Load current state to get questions for persistence
    persistence = PgStatePersistence(db)
    current_state = await persistence.load(execution_id)
    if not current_state:
        raise HTTPException(404, "Workflow execution not found")

    # Persist PGC answers (WS-PGC-VALIDATION-001 Phase 2)
    if current_state.pending_user_input_payload:
        questions = current_state.pending_user_input_payload.get("questions", [])
        schema_ref = current_state.pending_user_input_schema_ref or "schema://clarification_question_set.v2"

        pgc_repo = PGCAnswerRepository(db)
        pgc_answer = PGCAnswer(
            execution_id=execution_id,
            workflow_id=current_state.workflow_id,
            project_id=proj_uuid,
            pgc_node_id=current_state.current_node_id,
            schema_ref=schema_ref,
            questions=questions,
            answers=answers,
        )
        await pgc_repo.add(pgc_answer)
        await db.commit()
        logger.info(f"Persisted PGC answers for execution {execution_id}")

    # Resume workflow
    executor = await _create_executor(db)
    state = await executor.submit_user_input(
        execution_id=execution_id,
        user_input=answers,
    )

    state = await executor.run_to_completion_or_pause(execution_id)

    # Determine document type from state
    doc_type_id = state.document_type or "project_discovery"

    return _render_workflow_state(request, state, project, doc_type_id)


@router.get("/projects/{project_id}/workflows/{execution_id}/status", response_class=HTMLResponse)
async def get_workflow_status(
    request: Request,
    project_id: str,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    Poll endpoint for workflow status during generation.

    Used by HTMX to check progress and update UI.
    """
    project = await _get_project_with_icon(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    persistence = PgStatePersistence(db)
    state = await persistence.load(execution_id)

    if not state:
        raise HTTPException(404, "Workflow not found")

    doc_type_id = state.document_type or "project_discovery"

    return _render_workflow_state(request, state, project, doc_type_id)

