"""Page routes for UI."""

from typing import Optional

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.v1.dependencies import get_workflow_registry, get_persistence
from app.api.v1.routers.executions import get_execution_service
from app.api.v1.services.execution_service import ExecutionService
from app.domain.workflow import (
    WorkflowRegistry,
    WorkflowStatus,
    WorkflowNotFoundError,
    StatePersistence,
)


router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory="app/ui/templates")


def get_exec_service(
    persistence: StatePersistence = Depends(get_persistence),
) -> ExecutionService:
    """Get execution service via dependency injection."""
    return get_execution_service(persistence)


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Render the dashboard page."""
    # Get workflows for shortcuts
    workflow_ids = registry.list_ids()
    workflows = []
    for wf_id in workflow_ids:
        wf = registry.get(wf_id)
        workflows.append({
            "workflow_id": wf.workflow_id,
            "name": wf.name,
            "step_count": len(wf.steps),
        })
    
    # Get recent executions
    all_executions = await execution_service.list_executions()
    executions = [
        {
            "execution_id": e.execution_id,
            "workflow_id": e.workflow_id,
            "project_id": e.project_id,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "started_at": e.started_at.strftime("%Y-%m-%d %H:%M") if e.started_at else None,
        }
        for e in all_executions[:10]
    ]
    
    # Calculate stats
    running = sum(1 for e in all_executions if e.status == WorkflowStatus.RUNNING)
    waiting = sum(1 for e in all_executions if e.status in (
        WorkflowStatus.WAITING_ACCEPTANCE,
        WorkflowStatus.WAITING_CLARIFICATION,
    ))
    
    stats = {
        "total_workflows": len(workflows),
        "running_executions": running,
        "waiting_action": waiting,
        "completed_today": 0,
    }
    
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "active_page": "dashboard",
            "workflows": workflows,
            "executions": executions,
            "stats": stats,
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alias(
    request: Request,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Alias for dashboard."""
    return await dashboard(request, registry, execution_service)


@router.get("/workflows", response_class=HTMLResponse)
async def workflows_list(
    request: Request,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
):
    """Render workflows list page."""
    workflow_ids = registry.list_ids()
    workflows = []
    for wf_id in workflow_ids:
        wf = registry.get(wf_id)
        workflows.append({
            "workflow_id": wf.workflow_id,
            "name": wf.name,
            "description": wf.description,
            "revision": wf.revision,
            "step_count": len(wf.steps),
            "doc_count": len(wf.document_types),
        })
    
    return templates.TemplateResponse(
        request,
        "pages/workflows.html",
        {
            "active_page": "workflows",
            "workflows": workflows,
        },
    )


@router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
async def workflow_detail(
    request: Request,
    workflow_id: str,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
):
    """Render workflow detail page."""
    try:
        workflow = registry.get(workflow_id)
    except WorkflowNotFoundError:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "workflows",
                "error_code": 404,
                "error_message": f"Workflow '{workflow_id}' not found",
            },
            status_code=404,
        )
    
    return templates.TemplateResponse(
        request,
        "pages/workflow_detail.html",
        {
            "active_page": "workflows",
            "workflow": workflow,
        },
    )


@router.post("/workflows/{workflow_id}/start")
async def start_workflow_ui(
    request: Request,
    workflow_id: str,
    project_id: str = Form(default="proj_new"),
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Start a workflow and redirect to execution page."""
    try:
        workflow = registry.get(workflow_id)
    except WorkflowNotFoundError:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "workflows",
                "error_code": 404,
                "error_message": f"Workflow '{workflow_id}' not found",
            },
            status_code=404,
        )
    
    execution_id, state = await execution_service.start_execution(
        workflow=workflow,
        project_id=project_id,
    )
    
    return RedirectResponse(
        url=f"/executions/{execution_id}",
        status_code=303,
    )


@router.get("/executions", response_class=HTMLResponse)
async def executions_list(
    request: Request,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Render executions list page."""
    # Get workflows for filter dropdown
    workflow_ids = registry.list_ids()
    workflows = []
    for wf_id in workflow_ids:
        wf = registry.get(wf_id)
        workflows.append({
            "workflow_id": wf.workflow_id,
            "name": wf.name,
        })
    
    # Convert status string to enum
    status_enum = None
    if status:
        try:
            status_enum = WorkflowStatus(status)
        except ValueError:
            pass
    
    # Get executions
    all_executions = await execution_service.list_executions(
        workflow_id=workflow_id,
        status=status_enum,
    )
    
    executions = [
        {
            "execution_id": e.execution_id,
            "workflow_id": e.workflow_id,
            "project_id": e.project_id,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "started_at": e.started_at.strftime("%Y-%m-%d %H:%M") if e.started_at else None,
        }
        for e in all_executions
    ]
    
    return templates.TemplateResponse(
        request,
        "pages/executions.html",
        {
            "active_page": "executions",
            "workflows": workflows,
            "executions": executions,
            "filters": {
                "workflow_id": workflow_id,
                "status": status,
            },
        },
    )


@router.get("/executions/{execution_id}", response_class=HTMLResponse)
async def execution_detail(
    request: Request,
    execution_id: str,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Render execution detail page."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError
    
    try:
        state, context = await execution_service.get_execution(execution_id)
    except ExecutionNotFoundError:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "executions",
                "error_code": 404,
                "error_message": f"Execution '{execution_id}' not found",
            },
            status_code=404,
        )
    
    # Get workflow for step info
    try:
        workflow = registry.get(state.workflow_id)
        steps = workflow.steps
    except WorkflowNotFoundError:
        steps = []
    
    execution = {
        "execution_id": execution_id,
        "workflow_id": state.workflow_id,
        "project_id": state.project_id,
        "status": state.status.value if hasattr(state.status, 'value') else str(state.status),
        "current_step_id": state.current_step_id,
        "completed_steps": list(state.completed_steps),
        "pending_acceptance": state.pending_acceptance,
        "pending_clarification_step_id": state.pending_clarification_step_id,
        "started_at": state.started_at.strftime("%Y-%m-%d %H:%M") if state.started_at else None,
        "completed_at": state.completed_at.strftime("%Y-%m-%d %H:%M") if state.completed_at else None,
        "error": state.error,
    }
    
    return templates.TemplateResponse(
        request,
        "pages/execution_detail.html",
        {
            "active_page": "executions",
            "execution": execution,
            "steps": steps,
        },
    )


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution_ui(
    request: Request,
    execution_id: str,
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Cancel execution and redirect back to detail page."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError, InvalidExecutionStateError
    
    try:
        await execution_service.cancel_execution(execution_id)
    except (ExecutionNotFoundError, InvalidExecutionStateError):
        pass  # Ignore errors, just redirect back
    
    return RedirectResponse(
        url=f"/executions/{execution_id}",
        status_code=303,
    )


@router.get("/executions/{execution_id}/acceptance", response_class=HTMLResponse)
async def acceptance_form(
    request: Request,
    execution_id: str,
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Render acceptance form page."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError
    
    try:
        state, context = await execution_service.get_execution(execution_id)
    except ExecutionNotFoundError:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "executions",
                "error_code": 404,
                "error_message": f"Execution '{execution_id}' not found",
            },
            status_code=404,
        )
    
    # Check if actually waiting for acceptance
    if state.status != WorkflowStatus.WAITING_ACCEPTANCE:
        return RedirectResponse(url=f"/executions/{execution_id}", status_code=303)
    
    # Try to get document content from context
    document_content = None
    if context and state.pending_acceptance:
        doc = context.get_document(state.pending_acceptance, state.pending_acceptance_scope_id or state.project_id)
        if doc:
            document_content = doc
    
    execution = {
        "execution_id": execution_id,
        "workflow_id": state.workflow_id,
        "pending_acceptance": state.pending_acceptance,
    }
    
    return templates.TemplateResponse(
        request,
        "pages/acceptance_form.html",
        {
            "active_page": "executions",
            "execution": execution,
            "document_content": document_content,
        },
    )


@router.post("/executions/{execution_id}/acceptance")
async def submit_acceptance_ui(
    request: Request,
    execution_id: str,
    accepted: str = Form(...),
    comment: str = Form(default=""),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Submit acceptance decision."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError, InvalidExecutionStateError
    
    try:
        await execution_service.submit_acceptance(
            execution_id=execution_id,
            accepted=(accepted.lower() == "true"),
            comment=comment if comment else None,
        )
    except (ExecutionNotFoundError, InvalidExecutionStateError):
        pass
    
    return RedirectResponse(url=f"/executions/{execution_id}", status_code=303)


@router.get("/executions/{execution_id}/clarification", response_class=HTMLResponse)
async def clarification_form(
    request: Request,
    execution_id: str,
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Render clarification form page."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError
    
    try:
        state, context = await execution_service.get_execution(execution_id)
    except ExecutionNotFoundError:
        return templates.TemplateResponse(
            request,
            "pages/error.html",
            {
                "active_page": "executions",
                "error_code": 404,
                "error_message": f"Execution '{execution_id}' not found",
            },
            status_code=404,
        )
    
    # Check if actually waiting for clarification
    if state.status != WorkflowStatus.WAITING_CLARIFICATION:
        return RedirectResponse(url=f"/executions/{execution_id}", status_code=303)
    
    execution = {
        "execution_id": execution_id,
        "workflow_id": state.workflow_id,
        "pending_clarification_step_id": state.pending_clarification_step_id,
    }
    
    # Questions would come from the step that needs clarification
    # For now, we use a generic form
    questions = []
    
    return templates.TemplateResponse(
        request,
        "pages/clarification_form.html",
        {
            "active_page": "executions",
            "execution": execution,
            "questions": questions,
        },
    )


@router.post("/executions/{execution_id}/clarification")
async def submit_clarification_ui(
    request: Request,
    execution_id: str,
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Submit clarification answers."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError, InvalidExecutionStateError
    
    # Parse form data to extract answers
    form_data = await request.form()
    answers = {}
    for key, value in form_data.items():
        if key.startswith("answers[") and key.endswith("]"):
            answer_key = key[8:-1]  # Extract key from answers[key]
            answers[answer_key] = value
    
    try:
        await execution_service.submit_clarification(
            execution_id=execution_id,
            answers=answers,
        )
    except (ExecutionNotFoundError, InvalidExecutionStateError):
        pass
    
    return RedirectResponse(url=f"/executions/{execution_id}", status_code=303)
