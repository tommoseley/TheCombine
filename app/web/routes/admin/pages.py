"""Page routes for UI."""

from typing import Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Default display timezone (Eastern Time for US)
DISPLAY_TZ = ZoneInfo('America/New_York')
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from app.core.database import get_db
from app.domain.models.llm_logging import LLMRun, LLMRunInputRef, LLMRunOutputRef, LLMRunError, LLMContent
from app.api.models.project import Project
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.v1.dependencies import get_persistence
from app.api.v1.routers.executions import get_execution_service
from app.api.v1.services.execution_service import ExecutionService
from app.domain.workflow import WorkflowStatus, StatePersistence
from app.domain.workflow.plan_registry import PlanRegistry, get_plan_registry
from app.auth.dependencies import require_admin
from app.auth.models import User


def _sort_key_datetime(x):
    """Sort key that handles mixed timezone-aware/naive datetimes."""
    dt = x.get("started_at")
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


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
    registry: PlanRegistry = Depends(get_plan_registry),
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
            "step_count": len(wf.nodes),
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
    executions.sort(key=_sort_key_datetime, reverse=True)
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
    registry: PlanRegistry = Depends(get_plan_registry),
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
            "version": wf.version,
            "step_count": len(wf.nodes),
            "doc_count": 1  # Single document type per plan,
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
    registry: PlanRegistry = Depends(get_plan_registry),
):
    """Render workflow detail page."""
    try:
        workflow = registry.get(workflow_id)
    except Exception:  # Plan not found
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
    registry: PlanRegistry = Depends(get_plan_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
):
    """Start a workflow and redirect to execution page."""
    try:
        workflow = registry.get(workflow_id)
    except Exception:  # Plan not found
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
    registry: PlanRegistry = Depends(get_plan_registry),
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

    # Get Document Workflow executions from workflow_executions table (unless filtered to documents only)
    if source != "documents":
        # Query workflow_executions table directly with user email join
        wf_query = """
            SELECT we.execution_id, we.workflow_id, we.document_id, we.status,
                   we.user_id, u.email as user_email,
                   (SELECT MIN(e.entry->>'timestamp') FROM jsonb_array_elements(we.execution_log) AS e(entry)
                    WHERE e.entry->>'timestamp' IS NOT NULL) as started_at
            FROM workflow_executions we
            LEFT JOIN users u ON we.user_id = u.user_id
            WHERE 1=1
        """
        params = {}

        if status:
            wf_query += " AND we.status = :status"
            params["status"] = status

        wf_query += " ORDER BY started_at DESC NULLS LAST LIMIT 100"

        result = await db.execute(text(wf_query), params)
        wf_executions = result.fetchall()

        for row in wf_executions:
            # Parse started_at from the query result
            started_at = None
            if row.started_at:
                try:
                    started_at = datetime.fromisoformat(row.started_at.replace('"', ''))
                except (ValueError, AttributeError):
                    pass

            # Apply date filter
            if date_from_dt and started_at and started_at.replace(tzinfo=None) < date_from_dt:
                continue
            if date_to_dt and started_at and started_at.replace(tzinfo=None) >= date_to_dt:
                continue

            executions.append({
                "execution_id": row.execution_id,
                "workflow_id": row.workflow_id,
                "project_id": row.document_id or "-",
                "status": row.status or "unknown",
                "started_at": started_at,
                "source": "workflow",
                "source_label": "Workflow",
                "user_email": row.user_email,
            })
    
    # Get document builds (unless filtered to workflows only)
    # Exclude LLM runs that belong to a workflow (they're bundled)
    if source != "workflows":
        query = select(LLMRun).where(
            LLMRun.artifact_type.isnot(None),
            LLMRun.workflow_execution_id.is_(None)  # Exclude bundled runs
        ).order_by(desc(LLMRun.started_at)).limit(100)

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
    executions.sort(key=_sort_key_datetime, reverse=True)
    
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


# ============================================================================
# LLM RUN DETAIL HELPERS
# ============================================================================

async def _get_project_name(db: AsyncSession, project_id: Optional[UUID]) -> Optional[str]:
    """Get project name from ID."""
    if not project_id:
        return None
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    return project.name if project else None


async def _get_llm_run_inputs(db: AsyncSession, run_id: UUID) -> list[dict]:
    """Get LLM run inputs with resolved content."""
    result = await db.execute(
        select(LLMRunInputRef).where(LLMRunInputRef.llm_run_id == run_id)
    )
    inputs = []
    for ref in result.scalars().all():
        content = await resolve_content_ref(db, ref.content_ref)
        inputs.append({
            "kind": ref.kind,
            "content": content,
            "size": len(content.encode('utf-8')) if content else 0,
            "redacted": ref.content_redacted,
        })
    return inputs


async def _get_llm_run_outputs(db: AsyncSession, run_id: UUID) -> list[dict]:
    """Get LLM run outputs with resolved content."""
    result = await db.execute(
        select(LLMRunOutputRef).where(LLMRunOutputRef.llm_run_id == run_id)
    )
    outputs = []
    for ref in result.scalars().all():
        content = await resolve_content_ref(db, ref.content_ref)
        outputs.append({
            "kind": ref.kind,
            "content": content,
            "size": len(content.encode('utf-8')) if content else 0,
            "parse_status": ref.parse_status,
            "validation_status": ref.validation_status,
        })
    return outputs


async def _get_llm_run_errors(db: AsyncSession, run_id: UUID) -> list[dict]:
    """Get LLM run errors."""
    result = await db.execute(
        select(LLMRunError).where(LLMRunError.llm_run_id == run_id).order_by(LLMRunError.sequence)
    )
    return [
        {
            "sequence": e.sequence,
            "stage": e.stage,
            "severity": e.severity,
            "error_code": e.error_code,
            "message": e.message,
            "details": e.details,
        }
        for e in result.scalars().all()
    ]


def _build_llm_run_vm(run: LLMRun, project_name: Optional[str]) -> dict:
    """Build view model dict for LLM run."""
    elapsed_seconds = None
    if run.started_at and run.ended_at:
        elapsed_seconds = (run.ended_at - run.started_at).total_seconds()
    
    return {
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
    }

@router.get("/executions/{execution_id}", response_class=HTMLResponse)
async def execution_detail(
    request: Request,
    execution_id: str,
    registry: PlanRegistry = Depends(get_plan_registry),
    execution_service: ExecutionService = Depends(get_exec_service),
    db: AsyncSession = Depends(get_db),
):
    """Render execution detail page for workflows or document builds."""
    from app.api.v1.services.execution_service import ExecutionNotFoundError
    
    # First try workflow execution
    try:
        state, context = await execution_service.get_execution(execution_id)
        
        try:
            workflow = registry.get(state.workflow_id)
            steps = workflow.nodes
        except Exception:  # Plan not found
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
            {"active_page": "executions", "execution": execution, "steps": steps},
        )
    except ExecutionNotFoundError:
        pass
    
    # Try document build (LLMRun) - first by UUID, then by workflow_execution_id
    run = None
    runs_by_workflow = []
    
    # Try as UUID (direct LLMRun lookup)
    try:
        run_id = UUID(execution_id)
        result = await db.execute(select(LLMRun).where(LLMRun.id == run_id))
        run = result.scalar_one_or_none()
    except ValueError:
        pass  # Not a UUID, try workflow_execution_id below
    
    # If not found by UUID, try by workflow_execution_id
    if not run:
        result = await db.execute(
            select(LLMRun)
            .where(LLMRun.workflow_execution_id == execution_id)
            .order_by(LLMRun.started_at)
        )
        runs_by_workflow = list(result.scalars().all())
        
        if runs_by_workflow:
            # Show workflow execution summary with all LLM runs
            first_run = runs_by_workflow[0]
            project_name = await _get_project_name(db, first_run.project_id) if first_run.project_id else None
            
            # Get document type from first run (should be consistent across workflow)
            document_type = first_run.artifact_type
            # Format for display: "project_discovery" -> "Project Discovery"
            document_type_display = document_type.replace("_", " ").title() if document_type else None
            
            run_vms = []
            for r in runs_by_workflow:
                run_vms.append(_build_llm_run_vm(r, project_name))
            
            return templates.TemplateResponse(
                request,
                "pages/workflow_execution_detail.html",
                {
                    "active_page": "executions",
                    "execution_id": execution_id,
                    "runs": run_vms,
                    "project_name": project_name,
                    "total_runs": len(run_vms),
                    "document_type": document_type_display,
                },
            )
    
    if not run:
        return templates.TemplateResponse(
            request, "pages/error.html",
            {"active_page": "executions", "error_code": 404, "error_message": f"Execution '{execution_id}' not found"},
            status_code=404,
        )
    
    # Single LLM run detail
    project_name = await _get_project_name(db, run.project_id)
    inputs = await _get_llm_run_inputs(db, run.id)
    outputs = await _get_llm_run_outputs(db, run.id)
    errors = await _get_llm_run_errors(db, run.id)
    run_vm = _build_llm_run_vm(run, project_name)
    
    return templates.TemplateResponse(
        request,
        "pages/document_build_detail.html",
        {"active_page": "executions", "run": run_vm, "inputs": inputs, "outputs": outputs, "errors": errors},
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
