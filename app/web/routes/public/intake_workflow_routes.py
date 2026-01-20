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
from app.api.models.project import Project
from sqlalchemy import select, func
import json
import re
from app.domain.workflow.plan_registry import get_plan_registry
from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
from app.domain.workflow.nodes.mock_executors import create_mock_executors

logger = logging.getLogger(__name__)


# =============================================================================
# Project Creation Helpers
# =============================================================================

def _generate_project_id_prefix(project_name: str) -> str:
    """Generate 2-5 letter prefix from project name.
    
    Examples:
        "Legacy Inventory Replacement" -> "LIR"
        "Mobile App" -> "MA"
        "Customer Portal Redesign" -> "CPR"
    """
    # Extract words, take first letter of each
    words = re.findall(r'[A-Za-z]+', project_name)
    if not words:
        return "PRJ"
    
    # Take initials, max 5
    initials = ''.join(w[0].upper() for w in words[:5])
    
    # Ensure at least 2 characters
    if len(initials) < 2:
        initials = (initials + "X" * 2)[:2]
    
    return initials[:5]


async def _generate_unique_project_id(db: AsyncSession, project_name: str) -> str:
    """Generate unique project_id in format LIR-001.
    
    Finds the next available sequence number for the prefix.
    """
    prefix = _generate_project_id_prefix(project_name)
    
    # Find existing projects with this prefix
    pattern = f"{prefix}-%"
    result = await db.execute(
        select(Project.project_id)
        .where(Project.project_id.like(pattern))
        .order_by(Project.project_id.desc())
    )
    existing = result.scalars().all()
    
    if not existing:
        return f"{prefix}-001"
    
    # Extract highest number
    max_num = 0
    for pid in existing:
        try:
            num = int(pid.split('-')[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            continue
    
    return f"{prefix}-{max_num + 1:03d}"


async def _create_project_from_intake(
    db: AsyncSession,
    state,
    user_id: Optional[str] = None,
) -> Optional[Project]:
    """Create Project from completed intake workflow.
    
    Extracts project_name from the generated intake document in context_state.
    Returns None if creation fails or data is missing.
    """
    # Get the intake document from context_state
    context_state = state.context_state or {}
    
    # Debug: log what keys are in context_state
    logger.info(f"Context state keys: {list(context_state.keys())}")
    
    # Try multiple possible keys
    intake_doc = (
        context_state.get("document_concierge_intake_document") or
        context_state.get("last_produced_document") or
        context_state.get("concierge_intake_document")
    )
    
    if not intake_doc:
        # Try to find in node history metadata
        for execution in reversed(state.node_history):
            if execution.node_id == "generation":
                response = execution.metadata.get("response")
                if response:
                    try:
                        intake_doc = json.loads(response) if isinstance(response, str) else response
                        logger.info(f"Found intake doc in node history: {list(intake_doc.keys()) if isinstance(intake_doc, dict) else type(intake_doc)}")
                        break
                    except json.JSONDecodeError:
                        continue
    
    if not intake_doc:
        logger.warning("No intake document found in workflow state")
        logger.warning(f"Full context_state: {context_state}")
        return None
    
    # Extract project name
    project_name = intake_doc.get("project_name")
    if not project_name:
        # Fallback to summary description
        summary = intake_doc.get("summary", {})
        project_name = summary.get("description", "New Project")[:100]
    
    # Generate unique project_id with hyphen format (e.g., LIR-001)
    project_id = await _generate_unique_project_id(db, project_name)
    
    # Parse user_id to UUID if provided
    owner_uuid = uuid_module.UUID(user_id) if user_id else None
    
    # Create project using ORM
    project = Project(
        project_id=project_id,
        name=project_name,
        description=intake_doc.get("summary", {}).get("description"),
        status="active",
        icon="folder",
        owner_id=owner_uuid,
        organization_id=owner_uuid,
        created_by=str(user_id) if user_id else None,
        meta={
            "intake_document": intake_doc,
            "workflow_execution_id": state.execution_id,
        }
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    logger.info(f"Created project {project_id}: {project_name}")
    return project

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
    logger.info("=" * 80)
    logger.info("NEW /intake ROUTE CALLED - WORKFLOW ENGINE")
    logger.info("=" * 80)
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
            initial_context={"user_id": str(user.user_id)} if user else None,
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
    logger.info("=" * 80)
    logger.info("NEW /intake/{execution_id}/message CALLED - WORKFLOW ENGINE")
    logger.info(f"Execution ID: {execution_id}")
    logger.info(f"User content: {content[:100]}..." if len(content) > 100 else f"User content: {content}")
    logger.info("=" * 80)
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

    # Check if completed (workflow auto-completes after QA passes)
    if state.status == DocumentWorkflowStatus.COMPLETED:
        user, _, _ = user_data  # Unpack tuple (user, session, account)
        user_id = user.user_id if user else None
        context = await _build_completion_context(request, state, db, user_id)
        return templates.TemplateResponse(
            request,
            "intake_workflow/partials/_completion.html",
            context,
        )

    # Return message partial with updated state
    context = _build_message_context(request, state, content)

    logger.info(f"Message context - pending_choices: {context.get('pending_choices')}")
    logger.info(f"Message context - is_paused: {context.get('is_paused')}")

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
        # Submit user's selected option (ADR-037 compliant)
        state = await executor.submit_user_input(
            execution_id=execution_id,
            selected_option_id=choice,
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
        user, _, _ = user_data  # Unpack tuple (user, session, account)
        user_id = user.user_id if user else None
        context = await _build_completion_context(request, state, db, user_id)
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
    # Exclude the last response if paused, since it's shown via pending_prompt
    messages = []
    node_history = list(state.node_history)

    for i, execution in enumerate(node_history):
        if execution.metadata.get("user_input"):
            messages.append({
                "role": "user",
                "content": execution.metadata["user_input"],
            })
        if execution.metadata.get("response"):
            # Skip the last response if we're paused - it's shown via pending_prompt
            is_last = (i == len(node_history) - 1)
            if is_last and state.pending_user_input:
                continue
            messages.append({
                "role": "assistant",
                "content": execution.metadata["response"],
            })

    is_completed = state.status == DocumentWorkflowStatus.COMPLETED

    context = {
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
        "is_completed": is_completed,
        "is_paused": state.status == DocumentWorkflowStatus.PAUSED,
    }

    # Add completion display info if completed
    if is_completed:
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
            "blocked": {
                "title": "Blocked",
                "description": "The workflow could not complete due to validation issues.",
                "color": "yellow",
                "next_action": "Start Over",
            },
        }

        outcome_info = outcome_display.get(state.terminal_outcome or state.gate_outcome, {
            "title": "Complete",
            "description": "The intake workflow has completed.",
            "color": "gray",
            "next_action": None,
        })

        context.update({
            "outcome_title": outcome_info["title"],
            "outcome_description": outcome_info["description"],
            "outcome_color": outcome_info["color"],
            "next_action": outcome_info["next_action"],
        })

    return context


def _build_message_context(request: Request, state, user_message: str) -> dict:
    """Build context for message exchange partial.

    Note: user_message is NOT included in context because it's shown
    optimistically in the frontend before the request is sent.
    """
    # Find the most recent execution that has a response
    # (not just the last execution - qa/end nodes may not have responses)
    assistant_response = None
    if state.node_history:
        for execution in reversed(state.node_history):
            response = execution.metadata.get("response")
            if response:
                assistant_response = response
                break

    # Fall back to pending_prompt if no history response
    if not assistant_response and state.pending_prompt:
        assistant_response = state.pending_prompt

    logger.info(f"Message context - assistant_response: {assistant_response[:100] if assistant_response else None}...")
    logger.info(f"Message context - node_history count: {len(state.node_history)}")

    return {
        "request": request,
        "execution_id": state.execution_id,
        "user_message": None,  # Shown optimistically in frontend
        "assistant_response": assistant_response,
        "pending_choices": state.pending_choices,
        "is_paused": state.status == DocumentWorkflowStatus.PAUSED,
        "is_completed": state.status == DocumentWorkflowStatus.COMPLETED,
    }


async def _build_completion_context(
    request: Request,
    state,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> dict:
    """Build context for completion state.
    
    If gate_outcome is 'qualified', creates a Project record.
    """
    project = None
    project_url = None
    
    # Create project if qualified
    if state.gate_outcome == "qualified":
        try:
            project = await _create_project_from_intake(db, state, user_id)
            if project:
                project_url = f"/projects/{project.project_id}"
        except Exception as e:
            logger.exception(f"Failed to create project: {e}")
    
    outcome_display = {
        "qualified": {
            "title": "Project Created" if project else "Project Qualified",
            "description": f"Project {project.project_id} is ready for PM Discovery." if project else "Your project has been qualified and is ready for PM Discovery.",
            "color": "green",
            "next_action": "View Project" if project else "View Discovery Document",
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
        "project": project,
        "project_id": project.project_id if project else None,
        "project_url": project_url,
        "terminal_outcome": state.terminal_outcome,
        "outcome_title": outcome_info["title"],
        "outcome_description": outcome_info["description"],
        "outcome_color": outcome_info["color"],
        "next_action": outcome_info["next_action"],
    }
