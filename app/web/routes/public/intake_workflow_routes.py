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
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
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
from app.domain.workflow.interpretation import calculate_confidence, get_missing_fields
from app.domain.workflow.nodes.mock_executors import create_mock_executors
from app.api.services.project_creation_service import (
    create_project_from_intake,
    extract_intake_document_from_state,
)

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
        response = templates.TemplateResponse(
            request,
            "intake_workflow/partials/_chat_content.html",
            context,
        )
        # Push URL so refresh preserves state
        response.headers["HX-Push-Url"] = f"/intake/{state.execution_id}"
        return response

    # For full page load, redirect to the execution-specific URL
    return RedirectResponse(url=f"/intake/{state.execution_id}", status_code=302)


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
        # Return drafting log content which includes completion card in-flow
        context = await _build_completion_context(request, state, db, user_id)
        context["messages"] = _build_template_context(request, state)["messages"]
        return templates.TemplateResponse(
            request,
            "intake_workflow/partials/_drafting_log_content.html",
            context,
        )

    # Return drafting log content with full context
    # Note: _drafting_log_content.html includes interpretation panel when phase == 'review'
    context = _build_template_context(request, state)

    logger.info(f"Message context - pending_choices: {context.get('pending_choices')}")
    logger.info(f"Message context - is_paused: {context.get('is_paused')}")

    return templates.TemplateResponse(
        request,
        "intake_workflow/partials/_drafting_log_content.html",
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
        # Return drafting log content which includes completion card in-flow
        context = await _build_completion_context(request, state, db, user_id)
        context["messages"] = _build_template_context(request, state)["messages"]
        return templates.TemplateResponse(
            request,
            "intake_workflow/partials/_drafting_log_content.html",
            context,
        )

    # Return updated state
    context = _build_template_context(request, state)
    return templates.TemplateResponse(
        request,
        "intake_workflow/partials/_drafting_log_content.html",
        context,
    )


@router.patch("/intake/{execution_id}/field/{field_key}", response_class=HTMLResponse)
async def update_interpretation_field(
    request: Request,
    execution_id: str,
    field_key: str,
    value: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Update a single interpretation field (user edit, auto-locks).
    
    WS-INTAKE-001: Single-writer locking - user edits lock the field.
    """
    user_data = await get_optional_user(request, db)
    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if state.context_state.get("phase") != "review":
        raise HTTPException(status_code=400, detail="Not in review phase")
    
    interpretation = state.context_state.get("interpretation", {})
    
    # Update field with user source (auto-locks)
    interpretation[field_key] = {
        "value": value,
        "source": "user",
        "locked": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    state.update_context_state({"interpretation": interpretation})
    await executor._persistence.save(state)
    
    logger.info(f"Updated interpretation field {field_key} for {execution_id}")
    
    # Return updated panel partial
    context = _build_interpretation_context(request, state)
    return templates.TemplateResponse(
        request,
        "intake_workflow/partials/_interpretation_panel.html",
        context,
    )


@router.post("/intake/{execution_id}/initialize", response_class=HTMLResponse)
async def initialize_project(
    request: Request,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """User confirms interpretation, proceed to generation.
    
    WS-INTAKE-001: Requires all required fields filled (confidence = 1.0).
    """
    user_data = await get_optional_user(request, db)
    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if state.context_state.get("phase") != "review":
        raise HTTPException(status_code=400, detail="Not in review phase")
    
    interpretation = state.context_state.get("interpretation", {})
    confidence = calculate_confidence(interpretation)
    
    if confidence < 1.0:
        missing = get_missing_fields(interpretation)
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required fields: {', '.join(missing)}"
        )
    
    # Update phase and clear pause - workflow will be resumed by status polling
    state.update_context_state({"phase": "generating"})
    state.clear_pause()
    await executor._persistence.save(state)
    
    logger.info(f"Initializing project for {execution_id} - returning generating template")
    
    # Return drafting log content (includes messages + generating state)
    context = _build_template_context(request, state)
    return templates.TemplateResponse(
        request,
        "intake_workflow/partials/_drafting_log_content.html",
        context,
    )


@router.get("/intake/{execution_id}/status", response_class=HTMLResponse)
async def get_intake_status(
    request: Request,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Poll endpoint for intake status during generation.
    
    Runs workflow if in generating phase, returns completion when done.
    Single-page progressive flow.
    """
    user_data = await get_optional_user(request, db)
    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # If in generating phase and not completed, run the workflow
    # Use execution_started flag to prevent duplicate runs from concurrent polls
    if (state.context_state.get("phase") == "generating" and 
        state.status != DocumentWorkflowStatus.COMPLETED):
        if state.context_state.get("execution_started"):
            # Another poll is already running the workflow, just wait
            logger.info(f"Status poll for {execution_id} - execution already in progress")
        else:
            # Mark as started and run
            state.update_context_state({"execution_started": True})
            await executor._persistence.save(state)
            logger.info(f"Status poll triggering workflow execution for {execution_id}")
            state = await executor.run_to_completion_or_pause(execution_id)
            # Clear the flag after completion
            state.update_context_state({"execution_started": False})
            await executor._persistence.save(state)
    
    if state.status == DocumentWorkflowStatus.COMPLETED:
        user, _, _ = user_data
        user_id = user.user_id if user else None
        completion_context = await _build_completion_context(request, state, db, user_id)
        # Include messages in completion context
        completion_context["messages"] = _build_template_context(request, state)["messages"]
        return templates.TemplateResponse(
            request,
            "intake_workflow/partials/_drafting_log_content.html",
            completion_context,
        )
    
    # Still running - return drafting log content (includes messages + generating state)
    context = _build_template_context(request, state)
    return templates.TemplateResponse(
        request,
        "intake_workflow/partials/_drafting_log_content.html",
        context,
    )


def _build_template_context(request: Request, state) -> dict:
    """Build template context from workflow state."""
    # Extract conversation history from node history metadata
    # Exclude the last response if paused, since it's shown via pending_user_input_rendered
    messages = []
    node_history = list(state.node_history)

    for i, execution in enumerate(node_history):
        if execution.metadata.get("user_input"):
            messages.append({
                "role": "user",
                "content": execution.metadata["user_input"],
            })
        # Check for response OR user_prompt (clarification questions)
        response = execution.metadata.get("response") or execution.metadata.get("user_prompt")
        if response:
            # Skip the last response if we're paused - it's shown via pending_user_input_rendered
            is_last = (i == len(node_history) - 1)
            if is_last and state.pending_user_input_rendered:
                continue
            messages.append({
                "role": "assistant",
                "content": response,
            })
    
    # Fallback: include user_input from context_state if no user messages found
    # This captures the original user input that may not be in node metadata
    user_input = state.context_state.get("user_input")
    if user_input and not any(m.get("content") == user_input for m in messages if m["role"] == "user"):
        # Insert after any initial assistant messages (prompts), before completion
        insert_idx = 0
        for idx, m in enumerate(messages):
            if m["role"] == "assistant":
                insert_idx = idx + 1
            else:
                break
        messages.insert(insert_idx, {
            "role": "user",
            "content": user_input,
        })

    is_completed = state.status == DocumentWorkflowStatus.COMPLETED

    context = {
        "request": request,
        "execution_id": state.execution_id,
        "document_id": state.project_id,
        "status": state.status.value,
        "current_node": state.current_node_id,
        "messages": messages,
        "pending_user_input": state.pending_user_input,
        "pending_user_input_rendered": state.pending_user_input_rendered,
        "pending_prompt": state.pending_user_input_rendered,  # Template alias
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

    # Add interpretation context for Review & Lock panel (WS-INTAKE-001)
    interpretation = state.context_state.get("interpretation", {})
    phase = state.context_state.get("phase", "describe")
    confidence = calculate_confidence(interpretation)
    
    context.update({
        "interpretation": interpretation,
        "intent_canon": state.context_state.get("intent_canon"),  # Immutable original
        "phase": phase,
        "confidence": confidence,
        "confidence_pct": int(confidence * 100),
        "missing_fields": get_missing_fields(interpretation),
        "can_initialize": confidence >= 1.0,
    })
    
    return context


def _build_interpretation_context(request: Request, state) -> dict:
    """Build context for interpretation panel partial.
    
    Used by field edit endpoint to return just the panel.
    """
    interpretation = state.context_state.get("interpretation", {})
    confidence = calculate_confidence(interpretation)
    
    return {
        "request": request,
        "execution_id": state.execution_id,
        "interpretation": interpretation,
        "confidence": confidence,
        "confidence_pct": int(confidence * 100),
        "missing_fields": get_missing_fields(interpretation),
        "can_initialize": confidence >= 1.0,
        "phase": state.context_state.get("phase", "describe"),
    }


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

    # Fall back to pending_user_input_rendered if no history response
    if not assistant_response and state.pending_user_input_rendered:
        assistant_response = state.pending_user_input_rendered

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


def _clean_problem_statement(text: str) -> str:
    """Mechanically strip 'The user wants to...' style prefixes from summary.description.
    
    This is a deterministic transformation, not LLM-based.
    """
    if not text:
        return ""
    
    # Common prefixes to strip (case-insensitive matching)
    prefixes_to_strip = [
        "The user wants to ",
        "The user wants ",
        "User wants to ",
        "User wants ",
        "The user is requesting ",
        "The user would like to ",
        "The user needs to ",
        "The user needs ",
        "This request is for ",
        "This is a request for ",
        "The request is to ",
    ]
    
    result = text.strip()
    for prefix in prefixes_to_strip:
        if result.lower().startswith(prefix.lower()):
            result = result[len(prefix):]
            # Capitalize first letter after stripping
            if result:
                result = result[0].upper() + result[1:]
            break
    
    return result

async def _build_completion_context(
    request: Request,
    state,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> dict:
    """Build context for completion state.

    If gate_outcome is 'qualified', creates a Project record via service.
    """
    project = None
    project_url = None

    # Create project if qualified
    if state.gate_outcome == "qualified":
        try:
            intake_doc = extract_intake_document_from_state(state)
            if intake_doc:
                project = await create_project_from_intake(
                    db=db,
                    intake_document=intake_doc,
                    execution_id=state.execution_id,
                    user_id=str(user_id) if user_id else None,
                )
                if project:
                    project_url = f"/projects/{project.project_id}"
            else:
                logger.warning("No intake document found in workflow state for project creation")
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

    # Get intake document for detailed display
    context_state = state.context_state or {}
    intake_doc = (
        context_state.get("document_concierge_intake_document") or
        context_state.get("last_produced_document") or
        context_state.get("concierge_intake_document") or
        {}
    )
    interpretation = context_state.get("interpretation", {})
    
    # Extract and clean problem statement from summary.description
    summary = intake_doc.get("summary", {})
    raw_description = summary.get("description", "") if isinstance(summary, dict) else ""
    problem_statement = _clean_problem_statement(raw_description)
    
    return {
        "request": request,
        "execution_id": state.execution_id,
        "gate_outcome": state.gate_outcome,
        "project": project,
        "project_id": project.project_id if project else None,
        "project_name": intake_doc.get("project_name") or (project.name if project else None),
        "project_url": project_url,
        "terminal_outcome": state.terminal_outcome,
        "outcome_title": outcome_info["title"],
        "outcome_description": outcome_info["description"],
        "outcome_color": outcome_info["color"],
        "next_action": outcome_info["next_action"],
        # Problem statement: cleaned summary.description (no "The user wants..." prefix)
        "problem_statement": problem_statement,
        # Constraints: explicit only (inferred are internal scaffolding)
        "constraints_explicit": (
            intake_doc.get("constraints", {}).get("explicit", [])
            if isinstance(intake_doc.get("constraints"), dict)
            else intake_doc.get("constraints", [])
        ),
        # Project type category
        "project_type": (
            intake_doc.get("project_type", {}).get("category", "unknown")
            if isinstance(intake_doc.get("project_type"), dict)
            else intake_doc.get("project_type", "unknown")
        ),
        "routing_rationale": intake_doc.get("routing_rationale", ""),
        "interpretation": interpretation,
        # Required for template conditionals
        "is_completed": True,
        "is_paused": False,
        "pending_user_input_rendered": None,
        "pending_choices": None,
        "escalation_active": False,
        "phase": "complete",
    }
