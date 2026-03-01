"""
PostgreSQL implementation via ORM.

IMPORTANT: Does NOT commit. Caller owns transaction.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.domain.repositories.llm_log_repository import (
    LLMRunRecord,
    LLMContentRecord,
    LLMInputRefRecord,
    LLMOutputRefRecord,
    LLMErrorRecord,
)

logger = logging.getLogger(__name__)


class PostgresLLMLogRepository:
    """PostgreSQL repository via ORM. Does NOT commit internally."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def commit(self) -> None:
        logger.info("[ADR-010] PostgresRepo.commit() called")
        await self.db.commit()
        logger.info("[ADR-010] PostgresRepo.commit() completed")
    
    async def rollback(self) -> None:
        await self.db.rollback()
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        from app.api.models.llm_log import LLMContent
        
        result = await self.db.execute(
            select(LLMContent).where(LLMContent.content_hash == content_hash)
        )
        row = result.scalar_one_or_none()
        if row:
            return LLMContentRecord(
                id=row.id,
                content_hash=row.content_hash,
                content_text=row.content_text,
                content_size=row.content_size,
                created_at=row.created_at,
                accessed_at=row.accessed_at,
            )
        return None
    
    async def insert_content(self, record: LLMContentRecord) -> None:
        from app.api.models.llm_log import LLMContent
        
        logger.info(f"[ADR-010] PostgresRepo.insert_content() - hash={record.content_hash[:16]}...")
        content = LLMContent(
            id=record.id,
            content_hash=record.content_hash,
            content_text=record.content_text,
            content_size=record.content_size,
            created_at=record.created_at,
            accessed_at=record.accessed_at,
        )
        self.db.add(content)
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        from app.api.models.llm_log import LLMContent
        
        result = await self.db.execute(
            select(LLMContent).where(LLMContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        if content:
            content.accessed_at = datetime.now(timezone.utc)

    async def insert_run(self, record: LLMRunRecord) -> None:
        from app.api.models.llm_log import LLMRun
        
        logger.info(f"[ADR-010] PostgresRepo.insert_run() - id={record.id}, correlation_id={record.correlation_id}")
        run = LLMRun(
            id=record.id,
            correlation_id=record.correlation_id,
            project_id=record.project_id,
            artifact_type=record.artifact_type,
            role=record.role,
            model_provider=record.model_provider,
            model_name=record.model_name,
            prompt_id=record.prompt_id,
            prompt_version=record.prompt_version,
            effective_prompt_hash=record.effective_prompt_hash,
            schema_version=record.schema_version,
            schema_id=record.schema_id,
            schema_bundle_hash=record.schema_bundle_hash,
            status=record.status,
            started_at=record.started_at,
            error_count=0,
            workflow_execution_id=record.workflow_execution_id,
        )
        self.db.add(run)
    
    async def update_run_completion(
        self,
        run_id: UUID,
        status: str,
        ended_at: datetime,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        from app.api.models.llm_log import LLMRun
        
        result = await self.db.execute(
            select(LLMRun).where(LLMRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = status
            run.ended_at = ended_at
            run.input_tokens = input_tokens
            run.output_tokens = output_tokens
            run.total_tokens = total_tokens
            run.cost_usd = cost_usd
            run.run_metadata = metadata
    
    async def bump_error_summary(
        self,
        run_id: UUID,
        error_code: Optional[str],
        message: str,
    ) -> None:
        from app.api.models.llm_log import LLMRun
        
        result = await self.db.execute(
            select(LLMRun).where(LLMRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            run.error_count = (run.error_count or 0) + 1
            run.primary_error_code = error_code
            run.primary_error_message = message
    
    async def get_run(self, run_id: UUID) -> Optional[LLMRunRecord]:
        from app.api.models.llm_log import LLMRun
        
        result = await self.db.execute(
            select(LLMRun).where(LLMRun.id == run_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_run_record(row) if row else None
    
    async def get_run_by_correlation_id(self, correlation_id: UUID) -> Optional[LLMRunRecord]:
        from app.api.models.llm_log import LLMRun
        
        result = await self.db.execute(
            select(LLMRun).where(LLMRun.correlation_id == correlation_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_run_record(row) if row else None
    
    def _row_to_run_record(self, row) -> LLMRunRecord:
        return LLMRunRecord(
            id=row.id,
            correlation_id=row.correlation_id,
            project_id=row.project_id,
            artifact_type=row.artifact_type,
            role=row.role,
            model_provider=row.model_provider,
            model_name=row.model_name,
            prompt_id=row.prompt_id,
            prompt_version=row.prompt_version,
            effective_prompt_hash=row.effective_prompt_hash,
            schema_version=row.schema_version,
            schema_id=row.schema_id,
            schema_bundle_hash=row.schema_bundle_hash,
            status=row.status,
            started_at=row.started_at,
            ended_at=row.ended_at,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            total_tokens=row.total_tokens,
            cost_usd=row.cost_usd,
            primary_error_code=row.primary_error_code,
            primary_error_message=row.primary_error_message,
            error_count=row.error_count,
            metadata=row.metadata,
        )

    async def insert_input_ref(self, record: LLMInputRefRecord) -> None:
        from app.api.models.llm_log import LLMRunInputRef
        
        logger.info(f"[ADR-010] PostgresRepo.insert_input_ref() - kind={record.kind}, run_id={record.llm_run_id}")
        ref = LLMRunInputRef(
            id=record.id,
            llm_run_id=record.llm_run_id,
            kind=record.kind,
            content_ref=record.content_ref,
            content_hash=record.content_hash,
            content_redacted=record.content_redacted,
            created_at=record.created_at,
        )
        self.db.add(ref)
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
        from app.api.models.llm_log import LLMRunOutputRef
        
        logger.info(f"[ADR-010] PostgresRepo.insert_output_ref() - kind={record.kind}, run_id={record.llm_run_id}")
        ref = LLMRunOutputRef(
            id=record.id,
            llm_run_id=record.llm_run_id,
            kind=record.kind,
            content_ref=record.content_ref,
            content_hash=record.content_hash,
            parse_status=record.parse_status,
            validation_status=record.validation_status,
            created_at=record.created_at,
        )
        self.db.add(ref)
    
    async def get_inputs_for_run(self, run_id: UUID) -> List[LLMInputRefRecord]:
        from app.api.models.llm_log import LLMRunInputRef
        
        result = await self.db.execute(
            select(LLMRunInputRef)
            .where(LLMRunInputRef.llm_run_id == run_id)
            .order_by(LLMRunInputRef.created_at)
        )
        return [
            LLMInputRefRecord(
                id=row.id,
                llm_run_id=row.llm_run_id,
                kind=row.kind,
                content_ref=row.content_ref,
                content_hash=row.content_hash,
                content_redacted=row.content_redacted,
                created_at=row.created_at,
            )
            for row in result.scalars().all()
        ]
    
    async def get_outputs_for_run(self, run_id: UUID) -> List[LLMOutputRefRecord]:
        from app.api.models.llm_log import LLMRunOutputRef
        
        result = await self.db.execute(
            select(LLMRunOutputRef)
            .where(LLMRunOutputRef.llm_run_id == run_id)
            .order_by(LLMRunOutputRef.created_at)
        )
        return [
            LLMOutputRefRecord(
                id=row.id,
                llm_run_id=row.llm_run_id,
                kind=row.kind,
                content_ref=row.content_ref,
                content_hash=row.content_hash,
                parse_status=row.parse_status,
                validation_status=row.validation_status,
                created_at=row.created_at,
            )
            for row in result.scalars().all()
        ]
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        from app.api.models.llm_log import LLMRunError
        
        result = await self.db.execute(
            select(sql_func.coalesce(sql_func.max(LLMRunError.sequence), 0) + 1)
            .where(LLMRunError.llm_run_id == run_id)
        )
        return result.scalar_one()
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        from app.api.models.llm_log import LLMRunError
        
        error = LLMRunError(
            id=record.id,
            llm_run_id=record.llm_run_id,
            sequence=record.sequence,
            stage=record.stage,
            severity=record.severity,
            error_code=record.error_code,
            message=record.message,
            details=record.details,
            created_at=record.created_at,
        )
        self.db.add(error)
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        from app.api.models.llm_log import LLMRunError
        
        result = await self.db.execute(
            select(LLMRunError)
            .where(LLMRunError.llm_run_id == run_id)
            .order_by(LLMRunError.sequence)
        )
        return [
            LLMErrorRecord(
                id=row.id,
                llm_run_id=row.llm_run_id,
                sequence=row.sequence,
                stage=row.stage,
                severity=row.severity,
                error_code=row.error_code,
                message=row.message,
                details=row.details,
                created_at=row.created_at,
            )
            for row in result.scalars().all()
        ]