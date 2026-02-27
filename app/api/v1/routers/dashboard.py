"""Dashboard API router.

Provides API endpoints for dashboard data:
- GET /api/v1/dashboard/summary - Dashboard summary with stats
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.services.dashboard_service import get_dashboard_summary
from app.api.v1.dependencies import get_persistence
from app.api.v1.routers.executions import get_execution_service
from app.api.v1.services.execution_service import ExecutionService
from app.core.database import get_db
from app.domain.workflow import StatePersistence
from app.domain.workflow.plan_registry import PlanRegistry, get_plan_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# =============================================================================
# Response Models
# =============================================================================

class WorkflowSummary(BaseModel):
    """Summary of a workflow definition."""
    workflow_id: str
    name: str
    step_count: int


class ExecutionSummary(BaseModel):
    """Summary of a recent execution."""
    execution_id: str
    workflow_id: str
    project_id: str
    status: str
    started_at_formatted: Optional[str] = None
    started_at_iso: Optional[str] = None
    source: str
    source_label: str


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_workflows: int
    running_executions: int
    waiting_action: int
    doc_builds_today: int


class DashboardSummaryResponse(BaseModel):
    """Response model for dashboard summary."""
    workflows: List[WorkflowSummary]
    executions: List[ExecutionSummary]
    stats: DashboardStats
    today: str


# =============================================================================
# Dependencies
# =============================================================================

def _get_exec_service(
    persistence: StatePersistence = Depends(get_persistence),
) -> ExecutionService:
    """Get execution service via dependency injection."""
    return get_execution_service(persistence)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    limit: int = Query(10, ge=1, le=100, description="Max recent executions to return"),
    registry: PlanRegistry = Depends(get_plan_registry),
    execution_service: ExecutionService = Depends(_get_exec_service),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    """Get dashboard summary data.

    Returns:
        Summary including workflows, recent executions, and stats.
    """
    data = await get_dashboard_summary(
        db=db,
        registry=registry,
        execution_service=execution_service,
        limit=limit,
    )

    return DashboardSummaryResponse(
        workflows=[WorkflowSummary(**w) for w in data["workflows"]],
        executions=[ExecutionSummary(**e) for e in data["executions"]],
        stats=DashboardStats(**data["stats"]),
        today=data["today"],
    )
