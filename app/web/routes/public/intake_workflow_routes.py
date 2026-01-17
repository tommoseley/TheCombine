"""
Intake Workflow Routes - Document Interaction Workflow UI (ADR-039).

Adapter pattern for the workflow-based intake flow. Bridges the existing
UI framework with the workflow engine.

Entry point: /intake
- Creates workflow execution and serves chat UI
- Handles user input via workflow executor
- Displays workflow state and gate outcomes

Feature Flag: USE_WORKFLOW_ENGINE_LLM
- When enabled, /start redirects to /intake
- When disabled, /intake shows "coming soon" message
"""

import logging
import uuid as uuid_module
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import USE_WORKFLOW_ENGINE_LLM
from app.auth.dependencies import get_optional_user
from app.web.routes.shared import templates
from app.domain.workflow.plan_executor import PlanExecutor
from app.domain.workflow.pg_state_persistence import PgStatePersistence
from app.domain.workflow.plan_registry import get_plan_registry
from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
from app.domain.workflow.nodes.mock_executors import create_mock_executors

logger = logging.getLogger(__name__)

router = APIRouter(tags=["intake-workflow-ui"])


def _is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


async def _get_executor(db: AsyncSession) -> PlanExecutor:
    """Get configured plan executor."""
    if USE_WORKFLOW_ENGINE_LLM:
        # Real LLM executors - import here to avoid circular dependency
        from app.domain.workflow.nodes.llm_executors import create_llm_executors
        from app.domain.workflow.thread_manager import ThreadManager
        from app.domain.workflow.outcome_recorder import OutcomeRecorder

        executors = await create_llm_executors(db)
        thread_manager = ThreadManager(db)
        outcome_recorder = OutcomeRecorder(db)

        return PlanExecutor(
            persistence=PgStatePersistence(db),
            plan_registry=get_plan_registry(),
            executors=executors,
            thread_manager=thread_manager,
            outcome_recorder=outcome_recorder,
        )
    else:
        # Mock executors for testing
        return PlanExecutor(
            persistence=PgStatePersistence(db),
            plan_registry=get_plan_registry(),
            executors=create_mock_executors(),
        )


@router.get("/intake", response_class=HTMLResponse)
async def start_intake_workflow(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Entry point for workflow-based intake.

    Creates a new workflow execution and serves the intake UI.
    """
    # Check authentication
    user_data = await get_optional_user(request, db)

    if not user_data:
        return RedirectResponse(url="/web/static/public/login.html", status_code=302)

    user, _, _ = user_data

    # Check feature flag
    if not USE_WORKFLOW_ENGINE_LLM:
        context = {
            "request": request,
            "feature_enabled": False,
            "message": "Workflow-based intake is not yet enabled. Set USE_WORKFLOW_ENGINE_LLM=true to enable.",
        }
        if _is_htmx_request(request):
            return templates.TemplateResponse(
                request,
                "intake_workflow/partials/_not_enabled.html",
                context,
            )
        return templates.TemplateResponse(
            request,
            "intake_workflow/not_enabled.html",
            context,
        )

    # Create document ID for this intake
    document_id = f"intake-{uuid_module.uuid4().hex[:12]}"

    # Get executor and start workflow
    executor = await _get_executor(db)

    try:
        state = await executor.start_execution(
            document_id=document_id,
            document_type="concierge_intake",
        )

        # Run to first pause (clarification questions)
        state = await executor.run_to_completion_or_pause(state.execution_id)

    except Exception as e:
        logger.exception(f"Failed to start workflow: {e}")
        context = {
            "request": request,
            "error": str(e),
        }
        return templates.TemplateResponse(
            request,
            "intake_workflow/error.html",
            context,
        )

    # Build context for template
    context = _build_template_context(request, state)

    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request,
            "intake_workflow/partials/_chat_content.html",
            context,
        )

    return templates.TemplateResponse(
        request,
        "intake_workflow/chat.html",
        context,
    )


@router.get("/intake/{execution_id}", response_class=HTMLResponse)
async def get_intake_workflow(
    request: Request,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Resume or view an existing workflow execution.
    """
    user_data = await get_optional_user(request, db)
    if not user_data:
        return RedirectResponse(url="/web/static/public/login.html", status_code=302)

    executor = await _get_executor(db)
    status = await executor.get_execution_status(execution_id)

    if not status:
        context = {"request": request, "error": "Workflow not found"}
        return templates.TemplateResponse(
            request,
            "intake_workflow/error.html",
            context,
        )

    # Load full state
    state = await executor._persistence.load(execution_id)
    context = _build_template_context(request, state)

    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request,
            "intake_workflow/partials/_chat_content.html",
            context,
        )

    return templates.TemplateResponse(
        request,
        "intake_workflow/chat.html",
        context,
    )


@router.post("/intake/{execution_id}/message", response_class=HTMLResponse)
async def submit_intake_message(
    request: Request,
    execution_id: str,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit user message to the workflow.

    Advances the workflow with user input and returns the response.
    """
    user_data = await get_optional_user(request, db)
    if not user_data:
        return HTMLResponse(
            '<div class="p-4 bg-red-100 text-red-800 rounded">Please log in to continue.</div>',
            status_code=401,
        )

    executor = await _get_executor(db)

    try:
        # Submit user input
        state = await executor.submit_user_input(
            execution_id=execution_id,
            user_input=content,
        )

        # Run to next pause or completion
        state = await executor.run_to_completion_or_pause(execution_id)

    except Exception as e:
        logger.exception(f"Failed to process message: {e}")
        return HTMLResponse(
            f'<div class="p-4 bg-red-100 text-red-800 rounded">Error: {str(e)}</div>',
            status_code=500,
        )

    # Return message partial with updated state
    context = _build_message_context(request, state, content)

    return templates.TemplateResponse(
        request,
        "intake_workflow/partials/_message_exchange.html",
        context,
    )


@router.post("/intake/{execution_id}/choice", response_class=HTMLResponse)
async def submit_intake_choice(
    request: Request,
    execution_id: str,
    choice: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit user choice (gate selection) to the workflow.
    """
    user_data = await get_optional_user(request, db)
    if not user_data:
        return HTMLResponse(
            '<div class="p-4 bg-red-100 text-red-800 rounded">Please log in to continue.</div>',
            status_code=401,
        )

    executor = await _get_executor(db)

    try:
        # Submit user choice
        state = await executor.submit_user_input(
            execution_id=execution_id,
            user_choice=choice,
        )

        # Run to next pause or completion
        state = await executor.run_to_completion_or_pause(execution_id)

    except Exception as e:
        logger.exception(f"Failed to process choice: {e}")
        return HTMLResponse(
            f'<div class="p-4 bg-red-100 text-red-800 rounded">Error: {str(e)}</div>',
            status_code=500,
        )

    # Check if completed
    if state.status == DocumentWorkflowStatus.COMPLETED:
        context = _build_completion_context(request, state)
        return templates.TemplateResponse(
            request,
            "intake_workflow/partials/_completion.html",
            context,
        )

    # Return updated state
    context = _build_template_context(request, state)
    return templates.TemplateResponse(
        request,
        "intake_workflow/partials/_workflow_state.html",
        context,
    )


def _build_template_context(request: Request, state) -> dict:
    """Build template context from workflow state."""
    # Extract conversation history from node history metadata
    messages = []
    for execution in state.node_history:
        if execution.metadata.get("user_input"):
            messages.append({
                "role": "user",
                "content": execution.metadata["user_input"],
            })
        if execution.metadata.get("response"):
            messages.append({
                "role": "assistant",
                "content": execution.metadata["response"],
            })

    return {
        "request": request,
        "execution_id": state.execution_id,
        "document_id": state.document_id,
        "status": state.status.value,
        "current_node": state.current_node_id,
        "messages": messages,
        "pending_user_input": state.pending_user_input,
        "pending_prompt": state.pending_prompt,
        "pending_choices": state.pending_choices,
        "escalation_active": state.escalation_active,
        "escalation_options": state.escalation_options,
        "gate_outcome": state.gate_outcome,
        "terminal_outcome": state.terminal_outcome,
        "is_completed": state.status == DocumentWorkflowStatus.COMPLETED,
        "is_paused": state.status == DocumentWorkflowStatus.PAUSED,
    }


def _build_message_context(request: Request, state, user_message: str) -> dict:
    """Build context for message exchange partial."""
    # Get last assistant response from metadata
    assistant_response = None
    if state.node_history:
        last_execution = state.node_history[-1]
        assistant_response = last_execution.metadata.get("response")

    return {
        "request": request,
        "execution_id": state.execution_id,
        "user_message": user_message,
        "assistant_response": assistant_response or state.pending_prompt,
        "pending_choices": state.pending_choices,
        "is_paused": state.status == DocumentWorkflowStatus.PAUSED,
        "is_completed": state.status == DocumentWorkflowStatus.COMPLETED,
    }


def _build_completion_context(request: Request, state) -> dict:
    """Build context for completion state."""
    outcome_display = {
        "qualified": {
            "title": "Project Qualified",
            "description": "Your project has been qualified and is ready for PM Discovery.",
            "color": "green",
            "next_action": "View Discovery Document",
        },
        "not_ready": {
            "title": "Not Ready",
            "description": "Additional information is needed before proceeding.",
            "color": "yellow",
            "next_action": "Start Over",
        },
        "out_of_scope": {
            "title": "Out of Scope",
            "description": "This request is outside the scope of The Combine.",
            "color": "gray",
            "next_action": None,
        },
        "redirect": {
            "title": "Redirected",
            "description": "This request has been redirected to a different engagement type.",
            "color": "blue",
            "next_action": None,
        },
    }

    outcome_info = outcome_display.get(state.gate_outcome, {
        "title": "Complete",
        "description": "The intake workflow has completed.",
        "color": "gray",
        "next_action": None,
    })

    return {
        "request": request,
        "execution_id": state.execution_id,
        "gate_outcome": state.gate_outcome,
        "terminal_outcome": state.terminal_outcome,
        "outcome_title": outcome_info["title"],
        "outcome_description": outcome_info["description"],
        "outcome_color": outcome_info["color"],
        "next_action": outcome_info["next_action"],
    }
