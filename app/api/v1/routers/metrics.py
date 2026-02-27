"""WS execution metrics API endpoints (WS-METRICS-001)."""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.repositories.postgres_ws_metrics_repository import (
    PostgresWSMetricsRepository,
)
from app.domain.services.ws_metrics_service import (
    WSMetricsService,
    InvalidStatusError,
    InvalidPhaseNameError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


async def get_metrics_service(db: AsyncSession = Depends(get_db)) -> WSMetricsService:
    """Get metrics service backed by PostgreSQL."""
    repo = PostgresWSMetricsRepository(db)
    return WSMetricsService(repo)


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class WSExecutionStartRequest(BaseModel):
    ws_id: str = Field(..., description="Work Statement identifier")
    executor: str = Field(..., description="Who is executing (claude_code, human, subagent)")
    wp_id: Optional[str] = Field(None, description="Parent Work Package identifier")
    scope_id: Optional[str] = Field(None, description="Scope/tenant ID (reserved for v2)")


class WSExecutionUpdateRequest(BaseModel):
    status: Optional[str] = None
    test_metrics: Optional[Dict[str, Any]] = None
    file_metrics: Optional[Dict[str, Any]] = None
    rework_cycles: Optional[int] = None
    llm_calls: Optional[int] = None
    llm_tokens_in: Optional[int] = None
    llm_tokens_out: Optional[int] = None
    llm_cost_usd: Optional[float] = None


class PhaseEventRequest(BaseModel):
    event_id: str = Field(..., description="Unique event ID for idempotency")
    name: str = Field(..., description="Phase name: failing_tests, implement, verify, do_no_harm_audit")
    started_at: str = Field(..., description="ISO 8601 timestamp")
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    result: Optional[str] = None


class WSExecutionCompleteRequest(BaseModel):
    status: str = Field(..., description="Final status")
    test_metrics: Optional[Dict[str, Any]] = None
    file_metrics: Optional[Dict[str, Any]] = None
    llm_calls: Optional[int] = None
    llm_tokens_in: Optional[int] = None
    llm_tokens_out: Optional[int] = None
    llm_cost_usd: Optional[float] = None


class BugFixRequest(BaseModel):
    ws_execution_id: str = Field(..., description="UUID of parent WS execution")
    description: str
    root_cause: str
    test_name: str
    fix_summary: str
    autonomous: bool = False
    scope_id: Optional[str] = None
    files_modified: Optional[List[str]] = None


class WSExecutionResponse(BaseModel):
    id: str
    ws_id: str
    executor: str
    status: str
    started_at: str
    wp_id: Optional[str] = None
    scope_id: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    phase_metrics: Optional[Dict[str, Any]] = None
    test_metrics: Optional[Dict[str, Any]] = None
    file_metrics: Optional[Dict[str, Any]] = None
    rework_cycles: int = 0
    llm_calls: int = 0
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    llm_cost_usd: Optional[float] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/ws-execution", status_code=status.HTTP_201_CREATED)
async def create_ws_execution(
    request: WSExecutionStartRequest,
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Start a new WS execution record."""
    exec_id = await service.start_execution(
        ws_id=request.ws_id,
        executor=request.executor,
        wp_id=request.wp_id,
        scope_id=request.scope_id,
    )
    return {"id": str(exec_id)}


@router.put("/ws-execution/{execution_id}")
async def update_ws_execution(
    execution_id: str,
    request: WSExecutionUpdateRequest,
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Update an existing WS execution."""
    try:
        cost = Decimal(str(request.llm_cost_usd)) if request.llm_cost_usd is not None else None
        await service.update_execution(
            execution_id=UUID(execution_id),
            status=request.status,
            test_metrics=request.test_metrics,
            file_metrics=request.file_metrics,
            rework_cycles=request.rework_cycles,
            llm_calls=request.llm_calls,
            llm_tokens_in=request.llm_tokens_in,
            llm_tokens_out=request.llm_tokens_out,
            llm_cost_usd=cost,
        )
        return {"status": "updated"}
    except InvalidStatusError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ws-execution/{execution_id}/phase")
async def record_phase(
    execution_id: str,
    request: PhaseEventRequest,
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Record a phase event for a WS execution."""
    try:
        await service.record_phase(
            execution_id=UUID(execution_id),
            event_id=request.event_id,
            name=request.name,
            started_at=request.started_at,
            completed_at=request.completed_at,
            duration_seconds=request.duration_seconds,
            result=request.result,
        )
        return {"status": "recorded"}
    except InvalidPhaseNameError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ws-execution/{execution_id}/complete")
async def complete_ws_execution(
    execution_id: str,
    request: WSExecutionCompleteRequest,
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Complete a WS execution with final metrics."""
    try:
        cost = Decimal(str(request.llm_cost_usd)) if request.llm_cost_usd is not None else None
        await service.complete_execution(
            execution_id=UUID(execution_id),
            status=request.status,
            test_metrics=request.test_metrics,
            file_metrics=request.file_metrics,
            llm_calls=request.llm_calls,
            llm_tokens_in=request.llm_tokens_in,
            llm_tokens_out=request.llm_tokens_out,
            llm_cost_usd=cost,
        )
        return {"status": "completed"}
    except InvalidStatusError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bug-fix", status_code=status.HTTP_201_CREATED)
async def record_bug_fix(
    request: BugFixRequest,
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Record a bug fix linked to a WS execution."""
    bf_id = await service.record_bug_fix(
        ws_execution_id=UUID(request.ws_execution_id),
        description=request.description,
        root_cause=request.root_cause,
        test_name=request.test_name,
        fix_summary=request.fix_summary,
        autonomous=request.autonomous,
        scope_id=request.scope_id,
        files_modified=request.files_modified,
    )
    return {"id": str(bf_id)}


@router.get("/ws-executions")
async def list_ws_executions(
    wp_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    service: WSMetricsService = Depends(get_metrics_service),
):
    """List WS executions with optional filters."""
    repo = service.repo
    executions = await repo.list_executions(wp_id=wp_id, status=status_filter)
    return {
        "executions": [
            {
                "id": str(e.id),
                "ws_id": e.ws_id,
                "wp_id": e.wp_id,
                "executor": e.executor,
                "status": e.status,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "duration_seconds": e.duration_seconds,
                "rework_cycles": e.rework_cycles,
                "llm_cost_usd": float(e.llm_cost_usd) if e.llm_cost_usd else None,
            }
            for e in executions
        ]
    }


@router.get("/ws-executions/{execution_id}")
async def get_ws_execution(
    execution_id: str,
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Get a single WS execution with linked bug fixes."""
    detail = await service.get_execution_detail(UUID(execution_id))
    if detail is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    e = detail["execution"]
    return {
        "id": str(e.id),
        "ws_id": e.ws_id,
        "wp_id": e.wp_id,
        "scope_id": e.scope_id,
        "executor": e.executor,
        "status": e.status,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "duration_seconds": e.duration_seconds,
        "phase_metrics": e.phase_metrics,
        "test_metrics": e.test_metrics,
        "file_metrics": e.file_metrics,
        "rework_cycles": e.rework_cycles,
        "llm_calls": e.llm_calls,
        "llm_tokens_in": e.llm_tokens_in,
        "llm_tokens_out": e.llm_tokens_out,
        "llm_cost_usd": float(e.llm_cost_usd) if e.llm_cost_usd else None,
        "bug_fixes": [
            {
                "id": str(bf.id),
                "description": bf.description,
                "root_cause": bf.root_cause,
                "test_name": bf.test_name,
                "fix_summary": bf.fix_summary,
                "autonomous": bf.autonomous,
                "files_modified": bf.files_modified,
            }
            for bf in detail["bug_fixes"]
        ],
    }


@router.get("/dashboard")
async def get_dashboard(
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Get aggregated dashboard metrics."""
    return await service.get_dashboard()


@router.get("/cost-summary")
async def get_cost_summary(
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Get LLM cost breakdown by WS."""
    return await service.get_cost_summary()


@router.get("/scoreboard")
async def get_scoreboard(
    window: str = Query("7d", description="Time window: 24h, 7d, 30d, 90d, all"),
    service: WSMetricsService = Depends(get_metrics_service),
):
    """Get demo-ready scoreboard summary."""
    try:
        return await service.get_scoreboard(window=window)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
