"""
LLM execution logging service.

Key design:
- Business logic (hashing, dedup) lives here
- Repository handles storage (no commits)
- Service commits at safe boundaries
"""

import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.domain.repositories.llm_log_repository import (
    LLMLogRepository,
    LLMRunRecord,
    LLMContentRecord,
    LLMInputRefRecord,
    LLMOutputRefRecord,
    LLMErrorRecord,
)

logger = logging.getLogger(__name__)


class LLMExecutionLogger:
    """
    Centralized service for LLM execution logging.
    
    Transaction boundaries:
    - start_run: commits after run created
    - add_input/add_output: commits after each
    - log_error: commits after error + summary update
    - complete_run: commits after final update
    """
    
    def __init__(self, repo: LLMLogRepository):
        self.repo = repo
    
    async def start_run(
        self,
        correlation_id: UUID,
        project_id: Optional[UUID],
        artifact_type: Optional[str],
        role: str,
        model_provider: str,
        model_name: str,
        prompt_id: str,
        prompt_version: str,
        effective_prompt: str,
        schema_version: Optional[str] = None,
        schema_id: Optional[str] = None,
        schema_bundle_hash: Optional[str] = None,
        workflow_execution_id: Optional[str] = None,
    ) -> UUID:
        """Create llm_run record. Commits on success."""
        if correlation_id is None:
            raise ValueError("correlation_id cannot be None")
        
        effective_prompt_hash = hashlib.sha256(
            effective_prompt.encode('utf-8')
        ).hexdigest()
        
        run_id = uuid4()
        record = LLMRunRecord(
            id=run_id,
            correlation_id=correlation_id,
            project_id=project_id,
            artifact_type=artifact_type,
            role=role,
            model_provider=model_provider,
            model_name=model_name,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            effective_prompt_hash=effective_prompt_hash,
            schema_version=schema_version,
            schema_id=schema_id,
            schema_bundle_hash=schema_bundle_hash,
            status="IN_PROGRESS",
            workflow_execution_id=workflow_execution_id,
            started_at=datetime.now(timezone.utc),
        )
        
        try:
            await self.repo.insert_run(record)
            await self.repo.commit()
            
            schema_info = f", schema: {schema_id}" if schema_id else ""
            logger.info(f"[ADR-010] Started LLM run {run_id} "
                f"(correlation: {correlation_id}, role: {role}, artifact: {artifact_type}{schema_info})"
            )
            return run_id
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to start LLM run: {e}")
            raise
    
    async def add_input(
        self,
        run_id: UUID,
        kind: str,
        content: str,
        redacted: bool = False
    ) -> None:
        """Store input reference. Commits on success."""
        try:
            content_ref, content_hash = await self._store_content(content)
            
            record = LLMInputRefRecord(
                id=uuid4(),
                llm_run_id=run_id,
                kind=kind,
                content_ref=content_ref,
                content_hash=content_hash,
                content_redacted=redacted,
                created_at=datetime.now(timezone.utc),
            )
            
            await self.repo.insert_input_ref(record)
            await self.repo.commit()
            
            logger.info(f"[ADR-010] Added input ref (run: {run_id}, kind: {kind})")
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to add input ref: {e}")
            raise
    
    async def add_output(
        self,
        run_id: UUID,
        kind: str,
        content: str,
        parse_status: Optional[str] = None,
        validation_status: Optional[str] = None
    ) -> None:
        """Store output reference. Commits on success."""
        try:
            content_ref, content_hash = await self._store_content(content)
            
            record = LLMOutputRefRecord(
                id=uuid4(),
                llm_run_id=run_id,
                kind=kind,
                content_ref=content_ref,
                content_hash=content_hash,
                parse_status=parse_status,
                validation_status=validation_status,
                created_at=datetime.now(timezone.utc),
            )
            
            await self.repo.insert_output_ref(record)
            await self.repo.commit()
            
            logger.info(f"[ADR-010] Added output ref (run: {run_id}, kind: {kind})")
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to add output ref: {e}")
            raise
    
    async def log_error(
        self,
        run_id: UUID,
        stage: str,
        severity: str,
        error_code: Optional[str],
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Append error to run. Commits atomically with summary update.
        
        Does NOT re-raise - logging errors should not block execution.
        """
        try:
            sequence = await self.repo.get_next_error_sequence(run_id)
            
            record = LLMErrorRecord(
                id=uuid4(),
                llm_run_id=run_id,
                sequence=sequence,
                stage=stage,
                severity=severity,
                error_code=error_code,
                message=message,
                details=details,
                created_at=datetime.now(timezone.utc),
            )
            
            await self.repo.insert_error(record)
            
            if severity in ("ERROR", "FATAL"):
                await self.repo.bump_error_summary(run_id, error_code, message)
            
            await self.repo.commit()
            
            logger.warning(f"LLM run {run_id} error [{severity}] {stage}: {message}")
            
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to log error: {e}")
    
    async def complete_run(
        self,
        run_id: UUID,
        status: str,
        usage: Dict[str, int],
        cost_usd: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Finalize run with metrics. Commits on success."""
        try:
            # Auto-calculate cost if not provided
            if cost_usd is None:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                if input_tokens > 0 or output_tokens > 0:
                    from app.domain.utils.pricing import calculate_cost
                    cost_usd = Decimal(str(calculate_cost(input_tokens, output_tokens)))
            
            await self.repo.update_run_completion(
                run_id=run_id,
                status=status,
                ended_at=datetime.now(timezone.utc),
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                total_tokens=usage.get("total_tokens"),
                cost_usd=cost_usd,
                metadata=metadata,
            )
            await self.repo.commit()
            
            logger.info(f"[ADR-010] Completed LLM run {run_id}: {status} "
                f"({usage.get('total_tokens', 0)} tokens)"
            )
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to complete run: {e}")
            raise
    
    async def _store_content(self, content: str) -> tuple[str, str]:
        """
        Store content with deduplication. Does NOT commit (caller commits).
        
        Returns (content_ref, content_hash).
        """
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        existing = await self.repo.get_content_by_hash(content_hash)
        
        if existing:
            await self.repo.touch_content_accessed(existing.id)
            logger.info(f"[ADR-010] Content deduplicated (hash: {content_hash[:8]}...)")
            return f"db://llm_content/{existing.id}", content_hash
        
        content_id = uuid4()
        record = LLMContentRecord(
            id=content_id,
            content_hash=content_hash,
            content_text=content,
            content_size=len(content.encode('utf-8')),
            created_at=datetime.now(timezone.utc),
            accessed_at=datetime.now(timezone.utc),
        )
        
        await self.repo.insert_content(record)
        logger.info(f"[ADR-010] Content stored (hash: {content_hash[:8]}...)")
        
        return f"db://llm_content/{content_id}", content_hash


