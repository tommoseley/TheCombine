"""
WS execution metrics service (WS-METRICS-001).

Business logic for:
- Creating and updating WS execution records
- Recording bug fixes
- Computing dashboard and scoreboard aggregations

Key design (follows LLMExecutionLogger pattern):
- Service commits at safe boundaries
- Repository handles storage (no commits)
- Enum validation happens in service, not repository
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from statistics import mean
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.domain.repositories.ws_metrics_repository import (
    WSMetricsRepository,
    WSExecutionRecord,
    WSBugFixRecord,
    VALID_STATUSES,
    VALID_PHASE_NAMES,
)

logger = logging.getLogger(__name__)


class InvalidStatusError(ValueError):
    """Raised when an invalid status value is provided."""
    pass


class InvalidPhaseNameError(ValueError):
    """Raised when an invalid phase name is provided."""
    pass


class WSMetricsService:
    """
    Centralized service for WS execution metrics.

    Transaction boundaries:
    - start_execution: commits after record created
    - update_execution: commits after update
    - complete_execution: commits after final update
    - record_phase: commits after phase appended
    - record_bug_fix: commits after bug fix created
    """

    def __init__(self, repo: WSMetricsRepository):
        self.repo = repo

    async def start_execution(
        self,
        ws_id: str,
        executor: str,
        wp_id: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> UUID:
        """Create a new WS execution record. Returns execution ID."""
        execution_id = uuid4()
        now = datetime.now(timezone.utc)

        record = WSExecutionRecord(
            id=execution_id,
            ws_id=ws_id,
            executor=executor,
            status="STARTED",
            started_at=now,
            wp_id=wp_id,
            scope_id=scope_id,
            phase_metrics={"phases": []},
            test_metrics={"written": 0, "passing": 0, "failing": 0, "skipped": 0},
            file_metrics={"created": [], "modified": [], "deleted": []},
            created_at=now,
        )

        try:
            await self.repo.insert_execution(record)
            await self.repo.commit()
            logger.info(f"[METRICS] Started WS execution {execution_id} for {ws_id}")
            return execution_id
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to start WS execution: {e}")
            raise

    async def update_execution(
        self,
        execution_id: UUID,
        status: Optional[str] = None,
        test_metrics: Optional[Dict[str, Any]] = None,
        file_metrics: Optional[Dict[str, Any]] = None,
        rework_cycles: Optional[int] = None,
        llm_calls: Optional[int] = None,
        llm_tokens_in: Optional[int] = None,
        llm_tokens_out: Optional[int] = None,
        llm_cost_usd: Optional[Decimal] = None,
    ) -> None:
        """Update fields on an existing execution."""
        fields: Dict[str, Any] = {}
        if status is not None:
            if status not in VALID_STATUSES:
                raise InvalidStatusError(
                    f"Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}"
                )
            fields["status"] = status
        if test_metrics is not None:
            fields["test_metrics"] = test_metrics
        if file_metrics is not None:
            fields["file_metrics"] = file_metrics
        if rework_cycles is not None:
            fields["rework_cycles"] = rework_cycles
        if llm_calls is not None:
            fields["llm_calls"] = llm_calls
        if llm_tokens_in is not None:
            fields["llm_tokens_in"] = llm_tokens_in
        if llm_tokens_out is not None:
            fields["llm_tokens_out"] = llm_tokens_out
        if llm_cost_usd is not None:
            fields["llm_cost_usd"] = llm_cost_usd

        if not fields:
            return

        try:
            await self.repo.update_execution(execution_id, **fields)
            await self.repo.commit()
            logger.info(f"[METRICS] Updated WS execution {execution_id}: {list(fields.keys())}")
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to update WS execution: {e}")
            raise

    async def complete_execution(
        self,
        execution_id: UUID,
        status: str,
        test_metrics: Optional[Dict[str, Any]] = None,
        file_metrics: Optional[Dict[str, Any]] = None,
        llm_calls: Optional[int] = None,
        llm_tokens_in: Optional[int] = None,
        llm_tokens_out: Optional[int] = None,
        llm_cost_usd: Optional[Decimal] = None,
    ) -> None:
        """Complete a WS execution with final metrics."""
        if status not in VALID_STATUSES:
            raise InvalidStatusError(
                f"Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}"
            )

        execution = await self.repo.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        now = datetime.now(timezone.utc)
        duration = int((now - execution.started_at).total_seconds())

        fields: Dict[str, Any] = {
            "status": status,
            "completed_at": now,
            "duration_seconds": duration,
        }
        if test_metrics is not None:
            fields["test_metrics"] = test_metrics
        if file_metrics is not None:
            fields["file_metrics"] = file_metrics
        if llm_calls is not None:
            fields["llm_calls"] = llm_calls
        if llm_tokens_in is not None:
            fields["llm_tokens_in"] = llm_tokens_in
        if llm_tokens_out is not None:
            fields["llm_tokens_out"] = llm_tokens_out
        if llm_cost_usd is not None:
            fields["llm_cost_usd"] = llm_cost_usd

        try:
            await self.repo.update_execution(execution_id, **fields)
            await self.repo.commit()
            logger.info(
                f"[METRICS] Completed WS execution {execution_id}: {status} "
                f"({duration}s)"
            )
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to complete WS execution: {e}")
            raise

    async def record_phase(
        self,
        execution_id: UUID,
        event_id: str,
        name: str,
        started_at: str,
        completed_at: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        result: Optional[str] = None,
        **extra_fields,
    ) -> None:
        """
        Append a phase event to an execution's phase_metrics.

        Idempotent: duplicate event_id is safely ignored.
        """
        if name not in VALID_PHASE_NAMES:
            raise InvalidPhaseNameError(
                f"Invalid phase name '{name}'. Must be one of: {sorted(VALID_PHASE_NAMES)}"
            )

        execution = await self.repo.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        phases = (execution.phase_metrics or {}).get("phases", [])

        # Idempotent: skip if event_id already exists
        for existing in phases:
            if existing.get("event_id") == event_id:
                logger.info(
                    f"[METRICS] Duplicate phase event {event_id} ignored for {execution_id}"
                )
                return

        phase_entry = {
            "event_id": event_id,
            "sequence": len(phases) + 1,
            "name": name,
            "started_at": started_at,
        }
        if completed_at is not None:
            phase_entry["completed_at"] = completed_at
        if duration_seconds is not None:
            phase_entry["duration_seconds"] = duration_seconds
        if result is not None:
            phase_entry["result"] = result
        phase_entry.update(extra_fields)

        phases.append(phase_entry)

        try:
            await self.repo.update_execution(
                execution_id, phase_metrics={"phases": phases}
            )
            await self.repo.commit()
            logger.info(
                f"[METRICS] Recorded phase '{name}' for execution {execution_id}"
            )
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to record phase: {e}")
            raise

    async def record_bug_fix(
        self,
        ws_execution_id: UUID,
        description: str,
        root_cause: str,
        test_name: str,
        fix_summary: str,
        autonomous: bool,
        scope_id: Optional[str] = None,
        files_modified: Optional[List[str]] = None,
    ) -> UUID:
        """Record a bug fix linked to a WS execution. Returns bug fix ID."""
        bug_fix_id = uuid4()
        now = datetime.now(timezone.utc)

        record = WSBugFixRecord(
            id=bug_fix_id,
            ws_execution_id=ws_execution_id,
            description=description,
            root_cause=root_cause,
            test_name=test_name,
            fix_summary=fix_summary,
            autonomous=autonomous,
            scope_id=scope_id,
            files_modified=files_modified,
            created_at=now,
        )

        try:
            await self.repo.insert_bug_fix(record)
            await self.repo.commit()
            logger.info(
                f"[METRICS] Recorded bug fix {bug_fix_id} "
                f"for execution {ws_execution_id}"
            )
            return bug_fix_id
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to record bug fix: {e}")
            raise

    async def get_execution_detail(self, execution_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a single execution with linked bug fixes."""
        execution = await self.repo.get_execution(execution_id)
        if execution is None:
            return None

        bug_fixes = await self.repo.get_bug_fixes_for_execution(execution_id)

        return {
            "execution": execution,
            "bug_fixes": bug_fixes,
        }

    async def get_dashboard(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Compute aggregated dashboard metrics."""
        executions = await self.repo.list_executions(since=since, until=until)
        bug_fixes = await self.repo.list_bug_fixes(since=since, until=until)

        completed = [e for e in executions if e.status == "COMPLETED"]
        durations = [e.duration_seconds for e in completed if e.duration_seconds is not None]

        total_tests = sum(
            (e.test_metrics or {}).get("written", 0) for e in executions
        )
        total_cost = sum(
            float(e.llm_cost_usd or 0) for e in executions
        )
        autonomous_fixes = sum(1 for bf in bug_fixes if bf.autonomous)
        rework_avg = (
            mean(e.rework_cycles for e in completed) if completed else 0
        )

        return {
            "total_ws_completed": len(completed),
            "average_duration_seconds": mean(durations) if durations else 0,
            "total_tests_written": total_tests,
            "total_bugs_fixed_autonomously": autonomous_fixes,
            "total_llm_cost_usd": total_cost,
            "rework_cycle_average": rework_avg,
            "cost_per_ws": (total_cost / len(completed)) if completed else 0,
        }

    async def get_scoreboard(
        self,
        window: str = "7d",
    ) -> Dict[str, Any]:
        """
        Compute demo-ready scoreboard summary.

        Window: 24h, 7d, 30d, 90d, all.
        """
        now = datetime.now(timezone.utc)
        since = _parse_window(window, now)

        executions = await self.repo.list_executions(since=since)
        bug_fixes = await self.repo.list_bug_fixes(since=since)

        total_runs = len(executions)
        completed = [e for e in executions if e.status == "COMPLETED"]
        success_rate = (len(completed) / total_runs) if total_runs > 0 else 0

        durations = sorted(
            [e.duration_seconds for e in completed if e.duration_seconds is not None]
        )
        avg_duration = mean(durations) if durations else 0
        p95_duration = _percentile(durations, 95) if durations else 0

        first_pass = sum(1 for e in completed if e.rework_cycles == 0)
        first_pass_rate = (first_pass / len(completed)) if completed else 0

        total_cost = sum(float(e.llm_cost_usd or 0) for e in executions)
        cost_per_ws = (total_cost / len(completed)) if completed else 0

        autonomous_fixes = sum(1 for bf in bug_fixes if bf.autonomous)

        return {
            "window": window,
            "total_runs": total_runs,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "p95_duration_seconds": p95_duration,
            "first_pass_rate": first_pass_rate,
            "total_llm_cost_usd": total_cost,
            "cost_per_completed_ws": cost_per_ws,
            "autonomous_bug_fix_count": autonomous_fixes,
        }

    async def get_cost_summary(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """LLM cost breakdown by WS."""
        executions = await self.repo.list_executions(since=since, until=until)

        by_ws: Dict[str, float] = {}
        for e in executions:
            cost = float(e.llm_cost_usd or 0)
            by_ws[e.ws_id] = by_ws.get(e.ws_id, 0) + cost

        total = sum(by_ws.values())

        return {
            "total_llm_cost_usd": total,
            "by_ws": by_ws,
            "execution_count": len(executions),
        }


def _parse_window(window: str, now: datetime) -> Optional[datetime]:
    """Parse window string to a since datetime."""
    if window == "all":
        return None
    mapping = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    delta = mapping.get(window)
    if delta is None:
        raise ValueError(f"Invalid window '{window}'. Must be one of: 24h, 7d, 30d, 90d, all")
    return now - delta


def _percentile(sorted_values: List[int], pct: int) -> float:
    """Compute percentile from a sorted list."""
    if not sorted_values:
        return 0
    n = len(sorted_values)
    k = (pct / 100) * (n - 1)
    f = int(k)
    c = f + 1
    if c >= n:
        return float(sorted_values[-1])
    d = k - f
    return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])
