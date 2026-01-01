"""
PostgreSQL implementation.

IMPORTANT: Does NOT commit. Caller owns transaction.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

from app.domain.repositories.llm_log_repository import (
    LLMRunRecord,
    LLMContentRecord,
    LLMInputRefRecord,
    LLMOutputRefRecord,
    LLMErrorRecord,
)


class PostgresLLMLogRepository:
    """PostgreSQL repository. Does NOT commit internally."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def commit(self) -> None:
        logger.info("[ADR-010] PostgresRepo.commit() called")
        await self.db.commit()
        logger.info("[ADR-010] PostgresRepo.commit() completed")
    
    async def rollback(self) -> None:
        await self.db.rollback()
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        result = await self.db.execute(
            text("""
                SELECT id, content_hash, content_text, content_size, created_at, accessed_at 
                FROM llm_content WHERE content_hash = :hash
            """),
            {"hash": content_hash}
        )
        row = result.fetchone()
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
        logger.info(f"[ADR-010] PostgresRepo.insert_content() - hash={record.content_hash[:16]}...")
        await self.db.execute(
            text("""
                INSERT INTO llm_content (id, content_hash, content_text, content_size, created_at, accessed_at)
                VALUES (:id, :hash, :text, :size, :created, :accessed)
            """),
            {
                "id": record.id,
                "hash": record.content_hash,
                "text": record.content_text,
                "size": record.content_size,
                "created": record.created_at,
                "accessed": record.accessed_at,
            }
        )
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        await self.db.execute(
            text("UPDATE llm_content SET accessed_at = :now WHERE id = :id"),
            {"id": content_id, "now": datetime.now(timezone.utc)}
        )
    
    async def insert_run(self, record: LLMRunRecord) -> None:
        logger.info(f"[ADR-010] PostgresRepo.insert_run() - id={record.id}, correlation_id={record.correlation_id}")
        await self.db.execute(
            text("""
                INSERT INTO llm_run (
                    id, correlation_id, project_id, artifact_type, role,
                    model_provider, model_name, prompt_id, prompt_version,
                    effective_prompt_hash, schema_version, status, started_at,
                    error_count
                )
                VALUES (
                    :id, :correlation_id, :project_id, :artifact_type, :role,
                    :model_provider, :model_name, :prompt_id, :prompt_version,
                    :effective_prompt_hash, :schema_version, :status, :started_at,
                    0
                )
            """),
            {
                "id": record.id,
                "correlation_id": record.correlation_id,
                "project_id": record.project_id,
                "artifact_type": record.artifact_type,
                "role": record.role,
                "model_provider": record.model_provider,
                "model_name": record.model_name,
                "prompt_id": record.prompt_id,
                "prompt_version": record.prompt_version,
                "effective_prompt_hash": record.effective_prompt_hash,
                "schema_version": record.schema_version,
                "status": record.status,
                "started_at": record.started_at,
            }
        )
    
    async def update_run_completion(
        self,
        run_id: UUID,
        status: str,
        ended_at: datetime,
        # Logging added below in method body
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        await self.db.execute(
            text("""
                UPDATE llm_run SET
                    status = :status,
                    ended_at = :ended_at,
                    input_tokens = :input_tokens,
                    output_tokens = :output_tokens,
                    total_tokens = :total_tokens,
                    cost_usd = :cost_usd,
                    metadata = :metadata
                WHERE id = :id
            """),
            {
                "id": run_id,
                "status": status,
                "ended_at": ended_at,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "metadata": json.dumps(metadata) if metadata else None,
            }
        )
    
    async def bump_error_summary(
        self,
        run_id: UUID,
        error_code: Optional[str],
        message: str,
    ) -> None:
        await self.db.execute(
            text("""
                UPDATE llm_run SET
                    error_count = error_count + 1,
                    primary_error_code = :code,
                    primary_error_message = :msg
                WHERE id = :id
            """),
            {"id": run_id, "code": error_code, "msg": message}
        )
    
    async def get_run(self, run_id: UUID) -> Optional[LLMRunRecord]:
        result = await self.db.execute(
            text("SELECT * FROM llm_run WHERE id = :id"),
            {"id": run_id}
        )
        row = result.fetchone()
        return self._row_to_run_record(row) if row else None
    
    async def get_run_by_correlation_id(self, correlation_id: UUID) -> Optional[LLMRunRecord]:
        result = await self.db.execute(
            text("SELECT * FROM llm_run WHERE correlation_id = :cid"),
            {"cid": correlation_id}
        )
        row = result.fetchone()
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
        logger.info(f"[ADR-010] PostgresRepo.insert_input_ref() - kind={record.kind}, run_id={record.llm_run_id}")
        await self.db.execute(
            text("""
                INSERT INTO llm_run_input_ref 
                    (id, llm_run_id, kind, content_ref, content_hash, content_redacted, created_at)
                VALUES (:id, :run_id, :kind, :ref, :hash, :redacted, :created)
            """),
            {
                "id": record.id,
                "run_id": record.llm_run_id,
                "kind": record.kind,
                "ref": record.content_ref,
                "hash": record.content_hash,
                "redacted": record.content_redacted,
                "created": record.created_at,
            }
        )
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
        logger.info(f"[ADR-010] PostgresRepo.insert_output_ref() - kind={record.kind}, run_id={record.llm_run_id}")
        await self.db.execute(
            text("""
                INSERT INTO llm_run_output_ref 
                    (id, llm_run_id, kind, content_ref, content_hash, parse_status, validation_status, created_at)
                VALUES (:id, :run_id, :kind, :ref, :hash, :parse, :valid, :created)
            """),
            {
                "id": record.id,
                "run_id": record.llm_run_id,
                "kind": record.kind,
                "ref": record.content_ref,
                "hash": record.content_hash,
                "parse": record.parse_status,
                "valid": record.validation_status,
                "created": record.created_at,
            }
        )
    
    async def get_inputs_for_run(self, run_id: UUID) -> List[LLMInputRefRecord]:
        result = await self.db.execute(
            text("SELECT * FROM llm_run_input_ref WHERE llm_run_id = :id ORDER BY created_at"),
            {"id": run_id}
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
            for row in result.fetchall()
        ]
    
    async def get_outputs_for_run(self, run_id: UUID) -> List[LLMOutputRefRecord]:
        result = await self.db.execute(
            text("SELECT * FROM llm_run_output_ref WHERE llm_run_id = :id ORDER BY created_at"),
            {"id": run_id}
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
            for row in result.fetchall()
        ]
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        result = await self.db.execute(
            text("SELECT COALESCE(MAX(sequence), 0) + 1 FROM llm_run_error WHERE llm_run_id = :id"),
            {"id": run_id}
        )
        return result.scalar_one()
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        await self.db.execute(
            text("""
                INSERT INTO llm_run_error 
                    (id, llm_run_id, sequence, stage, severity, error_code, message, details, created_at)
                VALUES (:id, :run_id, :seq, :stage, :sev, :code, :msg, :details, :created)
            """),
            {
                "id": record.id,
                "run_id": record.llm_run_id,
                "seq": record.sequence,
                "stage": record.stage,
                "sev": record.severity,
                "code": record.error_code,
                "msg": record.message,
                "details": json.dumps(record.details) if record.details else None,
                "created": record.created_at,
            }
        )
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        result = await self.db.execute(
            text("SELECT * FROM llm_run_error WHERE llm_run_id = :id ORDER BY sequence"),
            {"id": run_id}
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
            for row in result.fetchall()
        ]
