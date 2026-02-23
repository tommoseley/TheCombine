"""
In-memory implementation for Tier-1 tests (WS-METRICS-001).

Real storage semantics, queryable, no DB dependency.
Follows InMemoryLLMLogRepository pattern.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime
from dataclasses import replace

from app.domain.repositories.ws_metrics_repository import (
    WSExecutionRecord,
    WSBugFixRecord,
)


class InMemoryWSMetricsRepository:
    """
    In-memory repository with real storage semantics.

    For Tier-1 tests: verifies persisted, queryable data.
    """

    def __init__(self):
        self._executions: Dict[UUID, WSExecutionRecord] = {}
        self._bug_fixes: Dict[UUID, WSBugFixRecord] = {}

        self._pending_executions: Dict[UUID, WSExecutionRecord] = {}
        self._pending_bug_fixes: Dict[UUID, WSBugFixRecord] = {}
        self._pending_execution_updates: Dict[UUID, Dict[str, Any]] = {}

    async def insert_execution(self, record: WSExecutionRecord) -> None:
        self._pending_executions[record.id] = record

    async def get_execution(self, execution_id: UUID) -> Optional[WSExecutionRecord]:
        return self._executions.get(execution_id)

    async def update_execution(self, execution_id: UUID, **fields) -> None:
        if execution_id not in self._pending_execution_updates:
            self._pending_execution_updates[execution_id] = {}
        self._pending_execution_updates[execution_id].update(fields)

    async def list_executions(
        self,
        wp_id: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[WSExecutionRecord]:
        results = list(self._executions.values())
        if wp_id is not None:
            results = [r for r in results if r.wp_id == wp_id]
        if status is not None:
            results = [r for r in results if r.status == status]
        if since is not None:
            results = [r for r in results if r.started_at >= since]
        if until is not None:
            results = [r for r in results if r.started_at <= until]
        return sorted(results, key=lambda r: r.started_at, reverse=True)

    async def insert_bug_fix(self, record: WSBugFixRecord) -> None:
        self._pending_bug_fixes[record.id] = record

    async def get_bug_fixes_for_execution(self, execution_id: UUID) -> List[WSBugFixRecord]:
        return [
            bf for bf in self._bug_fixes.values()
            if bf.ws_execution_id == execution_id
        ]

    async def list_bug_fixes(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[WSBugFixRecord]:
        results = list(self._bug_fixes.values())
        if since is not None:
            results = [r for r in results if r.created_at and r.created_at >= since]
        if until is not None:
            results = [r for r in results if r.created_at and r.created_at <= until]
        return results

    async def commit(self) -> None:
        self._executions.update(self._pending_executions)
        self._pending_executions.clear()

        for exec_id, updates in self._pending_execution_updates.items():
            if exec_id in self._executions:
                self._executions[exec_id] = replace(self._executions[exec_id], **updates)
        self._pending_execution_updates.clear()

        self._bug_fixes.update(self._pending_bug_fixes)
        self._pending_bug_fixes.clear()

    async def rollback(self) -> None:
        self._pending_executions.clear()
        self._pending_bug_fixes.clear()
        self._pending_execution_updates.clear()
