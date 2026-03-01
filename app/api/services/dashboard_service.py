"""Dashboard service.

Provides dashboard data aggregation for the admin dashboard UI.
Used by both the API and web routes.
"""

import logging
from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.llm_logging import LLMRun
from app.domain.workflow import WorkflowStatus
from app.domain.workflow.plan_registry import PlanRegistry

logger = logging.getLogger(__name__)

# Default display timezone
DISPLAY_TZ = ZoneInfo('America/New_York')


def _sort_key_datetime(x):
    """Sort key that handles mixed timezone-aware/naive datetimes.

    Delegates to service_pure.sort_key_datetime for testability.
    """
    from app.api.services.service_pure import sort_key_datetime
    return sort_key_datetime(x)


async def get_dashboard_summary(
    db: AsyncSession,
    registry: PlanRegistry,
    execution_service,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get dashboard summary data.

    Returns:
        Dict with workflows, executions, stats, and today's date.
    """
    # Get workflows from registry
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
    query = (
        select(LLMRun)
        .where(LLMRun.artifact_type.isnot(None))
        .order_by(desc(LLMRun.started_at))
        .limit(20)
    )
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

    from app.api.services.service_pure import compute_dashboard_stats, format_execution_dates

    # Sort by started_at descending and take top N
    executions.sort(key=_sort_key_datetime, reverse=True)
    executions = executions[:limit]

    # Format dates for display
    format_execution_dates(executions, DISPLAY_TZ)

    # Calculate stats
    running = sum(1 for e in all_workflow_executions if e.status == WorkflowStatus.RUNNING)
    waiting = sum(
        1 for e in all_workflow_executions
        if e.status in (WorkflowStatus.WAITING_ACCEPTANCE, WorkflowStatus.WAITING_CLARIFICATION)
    )
    local_today = datetime.now(DISPLAY_TZ).date()
    doc_builds_today = len([
        r for r in llm_runs
        if r.started_at and r.started_at.astimezone(DISPLAY_TZ).date() == local_today
    ])

    stats = compute_dashboard_stats(len(workflows), running, waiting, doc_builds_today)

    return {
        "workflows": workflows,
        "executions": executions,
        "stats": stats,
        "today": datetime.now(DISPLAY_TZ).strftime("%Y-%m-%d"),
    }
