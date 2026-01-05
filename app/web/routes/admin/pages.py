"""Page routes for UI."""

from typing import Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Default display timezone (Eastern Time for US)
DISPLAY_TZ = ZoneInfo('America/New_York')
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.domain.models.llm_logging import LLMRun, LLMRunInputRef, LLMRunOutputRef, LLMRunError, LLMContent
from app.api.models.project import Project
from uuid import UUID

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
from app.auth.dependencies import require_admin
from app.auth.models import User


router = APIRouter(prefix="/admin", tags=["admin-pages"], dependencies=[Depends(require_admin)])

templates = Jinja2Templates(directory="app/web/templates/admin")


def get_exec_service(
    persistence: StatePersistence = Depends(get_persistence),
) -> ExecutionService:
    """Get execution service via dependency injection."""
    return get_execution_service(persistence)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
    db: AsyncSession = Depends(get_db),
):
    """Render the dashboard page with unified workflow and document build activity."""
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
    
    executions = []
    
    # Get workflow executions
    all_workflow_executions = await execution_service.list_executions()
    for e in all_workflow_executions:
        executions.append({
            "execution_id": e.execution_id,
            "workflow_id": e.workflow_id,
            "project_id": e.project_id,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "started_at": e.started_at,
            "source": "workflow",
            "source_label": "Workflow",
        })
    
    # Get document builds
    query = select(LLMRun).where(LLMRun.artifact_type.isnot(None)).order_by(desc(LLMRun.started_at)).limit(20)
    result = await db.execute(query)
    llm_runs = result.scalars().all()
    
    for run in llm_runs:
        executions.append({
            "execution_id": str(run.id),
            "workflow_id": run.artifact_type,
            "project_id": str(run.project_id) if run.project_id else "-",
            "status": run.status.lower(),
            "started_at": run.started_at,
            "source": "document",
            "source_label": "Document Build",
        })
    
    # Sort by started_at descending and take top 10
    executions.sort(key=lambda x: x["started_at"] or "", reverse=True)
    executions = executions[:10]
    
    # Format dates for display (convert UTC to local timezone)
    for e in executions:
        if e["started_at"]:
            dt = e["started_at"]
            # Ensure timezone aware, then convert to display timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone(DISPLAY_TZ)
            e["started_at"] = local_dt.strftime("%Y-%m-%d %H:%M")
    
    # Calculate stats
    running = sum(1 for e in all_workflow_executions if e.status == WorkflowStatus.RUNNING)
    waiting = sum(1 for e in all_workflow_executions if e.status in (
        WorkflowStatus.WAITING_ACCEPTANCE,
        WorkflowStatus.WAITING_CLARIFICATION,
    ))
    local_today = datetime.now(DISPLAY_TZ).date()
    doc_builds_today = len([r for r in llm_runs if r.started_at and r.started_at.astimezone(DISPLAY_TZ).date() == local_today])
    
    stats = {
        "total_workflows": len(workflows),
        "running_executions": running,
        "waiting_action": waiting,
        "doc_builds_today": doc_builds_today,
    }
    
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "active_page": "dashboard",
            "workflows": workflows,
            "executions": executions,
            "stats": stats,
            "today": datetime.now(DISPLAY_TZ).strftime("%Y-%m-%d"),
            
        },
    )


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
        url=f"/admin/executions/{execution_id}",
        status_code=303,
    )


@router.get("/executions", response_class=HTMLResponse)
async def executions_list(
    request: Request,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
    db: AsyncSession = Depends(get_db),
):
    """Render executions list page with unified workflow executions and document builds."""
    # Parse date filters
    
    date_from_dt = None
    date_to_dt = None
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            pass
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)  # Include full day
        except ValueError:
            pass
    
    # Get workflows for filter dropdown
    workflow_ids = registry.list_ids()
    workflows = []
    for wf_id in workflow_ids:
        wf = registry.get(wf_id)
        workflows.append({
            "workflow_id": wf.workflow_id,
            "name": wf.name,
        })
    
    executions = []
    
    # Get workflow executions (unless filtered to documents only)
    if source != "documents":
        status_enum = None
        if status:
            try:
                status_enum = WorkflowStatus(status)
            except ValueError:
                pass
        
        all_executions = await execution_service.list_executions(
            workflow_id=workflow_id,
            status=status_enum,
        )
        
        for e in all_executions:
            # Apply date filter
            if date_from_dt and e.started_at and e.started_at.replace(tzinfo=None) < date_from_dt:
                continue
            if date_to_dt and e.started_at and e.started_at.replace(tzinfo=None) >= date_to_dt:
                continue
            executions.append({
                "execution_id": e.execution_id,
                "workflow_id": e.workflow_id,
                "project_id": e.project_id,
                "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
                "started_at": e.started_at,
                "source": "workflow",
                "source_label": "Workflow",
            })
    
    # Get document builds (unless filtered to workflows only)
    if source != "workflows":
        query = select(LLMRun).where(LLMRun.artifact_type.isnot(None)).order_by(desc(LLMRun.started_at)).limit(100)
        
        if status:
            query = query.where(LLMRun.status == status.upper())
        
        if date_from_dt:
            query = query.where(LLMRun.started_at >= date_from_dt)
        if date_to_dt:
            query = query.where(LLMRun.started_at < date_to_dt)
        
        result = await db.execute(query)
        llm_runs = result.scalars().all()
        
        for run in llm_runs:
            executions.append({
                "execution_id": str(run.id),
                "workflow_id": run.artifact_type,
                "project_id": str(run.project_id) if run.project_id else "-",
                "status": run.status.lower(),
                "started_at": run.started_at,
                "source": "document",
                "source_label": "Document Build",
            })
    
    # Sort by started_at descending
    executions.sort(key=lambda x: x["started_at"] or "", reverse=True)
    
    # Format dates for display (convert UTC to local timezone)
    for e in executions:
        if e["started_at"]:
            dt = e["started_at"]
            # Ensure timezone aware, then convert to display timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone(DISPLAY_TZ)
            e["started_at"] = local_dt.strftime("%Y-%m-%d %H:%M")
    
    # Check if HTMX request - return partial only
    is_htmx = request.headers.get("HX-Request") == "true"
    
    if is_htmx:
        return templates.TemplateResponse(
            request,
            "partials/execution_list.html",
            {
                "executions": executions,
            },
        )
    
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
                "source": source,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


async def resolve_content_ref(db: AsyncSession, content_ref: str) -> Optional[str]:
    """Resolve a content_ref like 'db://llm_content/{uuid}' to actual content."""
    if not content_ref or not content_ref.startswith("db://llm_content/"):
        return None
    try:
        content_id = UUID(content_ref.replace("db://llm_content/", ""))
        result = await db.execute(select(LLMContent).where(LLMContent.id == content_id))
        content = result.scalar_one_or_none()
        return content.content_text if content else None
    except Exception:
        return None


@router.get("/executions/{execution_id}", response_class=HTMLResponse)
async def execution_detail(
    request: Request,
    execution_id: str,
    registry: WorkflowRegistry = Depends(get_workflow_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
    db: AsyncSession = Depends(get_db),
):
    """Render execution detail page for workflows or document builds."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError
    
    # First try workflow execution
    try:
        state, context = await execution_service.get_execution(execution_id)
        
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
    except ExecutionNotFoundError:
        pass  # Try document build next
    
    # Try document build (LLMRun)
    try:
        run_id = UUID(execution_id)
        result = await db.execute(
            select(LLMRun)
            .where(LLMRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        
        if not run:
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
        
        # Get project info
        project_name = None
        if run.project_id:
            proj_result = await db.execute(select(Project).where(Project.id == run.project_id))
            project = proj_result.scalar_one_or_none()
            if project:
                project_name = project.name
        
        # Get inputs with content
        inputs_result = await db.execute(
            select(LLMRunInputRef).where(LLMRunInputRef.llm_run_id == run_id)
        )
        input_refs = inputs_result.scalars().all()
        
        inputs = []
        for ref in input_refs:
            content = await resolve_content_ref(db, ref.content_ref)
            inputs.append({
                "kind": ref.kind,
                "content": content,
                "size": len(content.encode('utf-8')) if content else 0,
                "redacted": ref.content_redacted,
            })
        
        # Get outputs with content
        outputs_result = await db.execute(
            select(LLMRunOutputRef).where(LLMRunOutputRef.llm_run_id == run_id)
        )
        output_refs = outputs_result.scalars().all()
        
        outputs = []
        for ref in output_refs:
            content = await resolve_content_ref(db, ref.content_ref)
            outputs.append({
                "kind": ref.kind,
                "content": content,
                "size": len(content.encode('utf-8')) if content else 0,
                "parse_status": ref.parse_status,
                "validation_status": ref.validation_status,
            })
        
        # Get errors
        errors_result = await db.execute(
            select(LLMRunError).where(LLMRunError.llm_run_id == run_id).order_by(LLMRunError.sequence)
        )
        errors = errors_result.scalars().all()
        
        error_list = [
            {
                "sequence": e.sequence,
                "stage": e.stage,
                "severity": e.severity,
                "error_code": e.error_code,
                "message": e.message,
                "details": e.details,
            }
            for e in errors
        ]
        
        # Calculate elapsed time
        elapsed_seconds = None
        if run.started_at and run.ended_at:
            elapsed_seconds = (run.ended_at - run.started_at).total_seconds()
        
        return templates.TemplateResponse(
            request,
            "pages/document_build_detail.html",
            {
                "active_page": "executions",
                "run": {
                    "id": str(run.id),
                    "correlation_id": str(run.correlation_id) if run.correlation_id else None,
                    "project_id": str(run.project_id) if run.project_id else None,
                    "project_name": project_name,
                    "artifact_type": run.artifact_type,
                    "role": run.role,
                    "model_provider": run.model_provider,
                    "model_name": run.model_name,
                    "prompt_id": run.prompt_id,
                    "prompt_version": run.prompt_version,
                    "status": run.status,
                    "started_at": run.started_at.astimezone(DISPLAY_TZ).strftime("%Y-%m-%d %H:%M:%S") if run.started_at else None,
                    "ended_at": run.ended_at.astimezone(DISPLAY_TZ).strftime("%Y-%m-%d %H:%M:%S") if run.ended_at else None,
                    "elapsed_seconds": elapsed_seconds,
                    "input_tokens": run.input_tokens,
                    "output_tokens": run.output_tokens,
                    "total_tokens": run.total_tokens,
                    "cost_usd": float(run.cost_usd) if run.cost_usd else None,
                    "primary_error_code": run.primary_error_code,
                    "primary_error_message": run.primary_error_message,
                    "metadata": run.run_metadata,
                },
                "inputs": inputs,
                "outputs": outputs,
                "errors": error_list,
            },
        )
    except ValueError:
        # Invalid UUID format
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
        url=f"/admin/executions/{execution_id}",
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
        return RedirectResponse(url=f"/admin/executions/{execution_id}", status_code=303)
    
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
    
    return RedirectResponse(url=f"/admin/executions/{execution_id}", status_code=303)


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
        return RedirectResponse(url=f"/admin/executions/{execution_id}", status_code=303)
    
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
    
    return RedirectResponse(url=f"/admin/executions/{execution_id}", status_code=303)
