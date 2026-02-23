"""
PostgreSQL implementation for WS execution metrics (WS-METRICS-001).

IMPORTANT: Does NOT commit. Caller owns transaction.
Follows PostgresLLMLogRepository pattern.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.domain.repositories.ws_metrics_repository import (
    WSExecutionRecord,
    WSBugFixRecord,
)

logger = logging.getLogger(__name__)


class PostgresWSMetricsRepository:
    """PostgreSQL repository via ORM. Does NOT commit internally."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def insert_execution(self, record: WSExecutionRecord) -> None:
        from app.domain.models.ws_metrics import WSExecution

        row = WSExecution(
            id=record.id,
            ws_id=record.ws_id,
            wp_id=record.wp_id,
            scope_id=record.scope_id,
            executor=record.executor,
            status=record.status,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_seconds=record.duration_seconds,
            phase_metrics=record.phase_metrics,
            test_metrics=record.test_metrics,
            file_metrics=record.file_metrics,
            rework_cycles=record.rework_cycles,
            llm_calls=record.llm_calls,
            llm_tokens_in=record.llm_tokens_in,
            llm_tokens_out=record.llm_tokens_out,
            llm_cost_usd=record.llm_cost_usd,
            created_at=record.created_at,
        )
        self.db.add(row)

    async def get_execution(self, execution_id: UUID) -> Optional[WSExecutionRecord]:
        from app.domain.models.ws_metrics import WSExecution

        result = await self.db.execute(
            select(WSExecution).where(WSExecution.id == execution_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_execution(row) if row else None

    async def update_execution(self, execution_id: UUID, **fields) -> None:
        from app.domain.models.ws_metrics import WSExecution

        result = await self.db.execute(
            select(WSExecution).where(WSExecution.id == execution_id)
        )
        row = result.scalar_one_or_none()
        if row:
            for key, value in fields.items():
                setattr(row, key, value)

    async def list_executions(
        self,
        wp_id: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[WSExecutionRecord]:
        from app.domain.models.ws_metrics import WSExecution

        query = select(WSExecution)
        if wp_id is not None:
            query = query.where(WSExecution.wp_id == wp_id)
        if status is not None:
            query = query.where(WSExecution.status == status)
        if since is not None:
            query = query.where(WSExecution.started_at >= since)
        if until is not None:
            query = query.where(WSExecution.started_at <= until)
        query = query.order_by(WSExecution.started_at.desc())

        result = await self.db.execute(query)
        return [self._row_to_execution(r) for r in result.scalars().all()]

    async def insert_bug_fix(self, record: WSBugFixRecord) -> None:
        from app.domain.models.ws_metrics import WSBugFix

        row = WSBugFix(
            id=record.id,
            ws_execution_id=record.ws_execution_id,
            scope_id=record.scope_id,
            description=record.description,
            root_cause=record.root_cause,
            test_name=record.test_name,
            fix_summary=record.fix_summary,
            files_modified=record.files_modified,
            autonomous=record.autonomous,
            created_at=record.created_at,
        )
        self.db.add(row)

    async def get_bug_fixes_for_execution(self, execution_id: UUID) -> List[WSBugFixRecord]:
        from app.domain.models.ws_metrics import WSBugFix

        result = await self.db.execute(
            select(WSBugFix)
            .where(WSBugFix.ws_execution_id == execution_id)
            .order_by(WSBugFix.created_at)
        )
        return [self._row_to_bug_fix(r) for r in result.scalars().all()]

    async def list_bug_fixes(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[WSBugFixRecord]:
        from app.domain.models.ws_metrics import WSBugFix

        query = select(WSBugFix)
        if since is not None:
            query = query.where(WSBugFix.created_at >= since)
        if until is not None:
            query = query.where(WSBugFix.created_at <= until)
        query = query.order_by(WSBugFix.created_at)

        result = await self.db.execute(query)
        return [self._row_to_bug_fix(r) for r in result.scalars().all()]

    def _row_to_execution(self, row) -> WSExecutionRecord:
        return WSExecutionRecord(
            id=row.id,
            ws_id=row.ws_id,
            wp_id=row.wp_id,
            scope_id=row.scope_id,
            executor=row.executor,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            duration_seconds=row.duration_seconds,
            phase_metrics=row.phase_metrics,
            test_metrics=row.test_metrics,
            file_metrics=row.file_metrics,
            rework_cycles=row.rework_cycles or 0,
            llm_calls=row.llm_calls or 0,
            llm_tokens_in=row.llm_tokens_in or 0,
            llm_tokens_out=row.llm_tokens_out or 0,
            llm_cost_usd=row.llm_cost_usd,
            created_at=row.created_at,
        )

    def _row_to_bug_fix(self, row) -> WSBugFixRecord:
        return WSBugFixRecord(
            id=row.id,
            ws_execution_id=row.ws_execution_id,
            scope_id=row.scope_id,
            description=row.description,
            root_cause=row.root_cause,
            test_name=row.test_name,
            fix_summary=row.fix_summary,
            files_modified=row.files_modified,
            autonomous=row.autonomous,
            created_at=row.created_at,
        )
