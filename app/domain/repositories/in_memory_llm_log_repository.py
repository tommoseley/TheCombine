"""
In-memory implementation for Tier-1 tests.

Real storage semantics, queryable, no DB dependency.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import replace

from app.domain.repositories.llm_log_repository import (
    LLMRunRecord,
    LLMContentRecord,
    LLMInputRefRecord,
    LLMOutputRefRecord,
    LLMErrorRecord,
)


class InMemoryLLMLogRepository:
    """
    In-memory repository with real storage semantics.
    
    For Tier-1 tests: verifies persisted, queryable data.
    """
    
    def __init__(self):
        self._runs: Dict[UUID, LLMRunRecord] = {}
        self._content: Dict[UUID, LLMContentRecord] = {}
        self._content_by_hash: Dict[str, UUID] = {}
        self._input_refs: Dict[UUID, List[LLMInputRefRecord]] = {}
        self._output_refs: Dict[UUID, List[LLMOutputRefRecord]] = {}
        self._errors: Dict[UUID, List[LLMErrorRecord]] = {}
        
        self._pending_runs: Dict[UUID, LLMRunRecord] = {}
        self._pending_content: Dict[UUID, LLMContentRecord] = {}
        self._pending_content_hash: Dict[str, UUID] = {}
        self._pending_input_refs: List[LLMInputRefRecord] = []
        self._pending_output_refs: List[LLMOutputRefRecord] = []
        self._pending_errors: List[LLMErrorRecord] = []
        self._pending_run_updates: Dict[UUID, Dict[str, Any]] = {}
        self._pending_content_touches: Dict[UUID, datetime] = {}
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        content_id = self._content_by_hash.get(content_hash)
        if content_id:
            return self._content.get(content_id)
        content_id = self._pending_content_hash.get(content_hash)
        if content_id:
            return self._pending_content.get(content_id)
        return None
    
    async def insert_content(self, record: LLMContentRecord) -> None:
        self._pending_content[record.id] = record
        self._pending_content_hash[record.content_hash] = record.id
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        self._pending_content_touches[content_id] = datetime.now(timezone.utc)
    
    async def insert_run(self, record: LLMRunRecord) -> None:
        self._pending_runs[record.id] = record
    
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
        updates = {'status': status, 'ended_at': ended_at}
        if input_tokens is not None:
            updates['input_tokens'] = input_tokens
        if output_tokens is not None:
            updates['output_tokens'] = output_tokens
        if total_tokens is not None:
            updates['total_tokens'] = total_tokens
        if cost_usd is not None:
            updates['cost_usd'] = cost_usd
        if metadata is not None:
            updates['metadata'] = metadata
        
        if run_id not in self._pending_run_updates:
            self._pending_run_updates[run_id] = {}
        self._pending_run_updates[run_id].update(updates)
    
    async def bump_error_summary(
        self,
        run_id: UUID,
        error_code: Optional[str],
        message: str,
    ) -> None:
        if run_id not in self._pending_run_updates:
            self._pending_run_updates[run_id] = {}
        
        current_run = self._runs.get(run_id) or self._pending_runs.get(run_id)
        current_count = current_run.error_count if current_run else 0
        
        pending = self._pending_run_updates.get(run_id, {})
        if 'error_count' in pending:
            current_count = pending['error_count']
        
        self._pending_run_updates[run_id].update({
            'error_count': current_count + 1,
            'primary_error_code': error_code,
            'primary_error_message': message,
        })
    
    async def get_run(self, run_id: UUID) -> Optional[LLMRunRecord]:
        return self._runs.get(run_id)
    
    async def get_run_by_correlation_id(self, correlation_id: UUID) -> Optional[LLMRunRecord]:
        for run in self._runs.values():
            if run.correlation_id == correlation_id:
                return run
        return None
    
    async def insert_input_ref(self, record: LLMInputRefRecord) -> None:
        self._pending_input_refs.append(record)
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
        self._pending_output_refs.append(record)
    
    async def get_inputs_for_run(self, run_id: UUID) -> List[LLMInputRefRecord]:
        return self._input_refs.get(run_id, [])
    
    async def get_outputs_for_run(self, run_id: UUID) -> List[LLMOutputRefRecord]:
        return self._output_refs.get(run_id, [])
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        committed = len(self._errors.get(run_id, []))
        pending = len([e for e in self._pending_errors if e.llm_run_id == run_id])
        return committed + pending + 1
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        self._pending_errors.append(record)
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        return self._errors.get(run_id, [])
    
    async def commit(self) -> None:
        self._content.update(self._pending_content)
        self._content_by_hash.update(self._pending_content_hash)
        self._pending_content.clear()
        self._pending_content_hash.clear()
        
        for content_id, accessed_at in self._pending_content_touches.items():
            if content_id in self._content:
                self._content[content_id] = replace(self._content[content_id], accessed_at=accessed_at)
        self._pending_content_touches.clear()
        
        self._runs.update(self._pending_runs)
        self._pending_runs.clear()
        
        for run_id, updates in self._pending_run_updates.items():
            if run_id in self._runs:
                self._runs[run_id] = replace(self._runs[run_id], **updates)
        self._pending_run_updates.clear()
        
        for ref in self._pending_input_refs:
            if ref.llm_run_id not in self._input_refs:
                self._input_refs[ref.llm_run_id] = []
            self._input_refs[ref.llm_run_id].append(ref)
        self._pending_input_refs.clear()
        
        for ref in self._pending_output_refs:
            if ref.llm_run_id not in self._output_refs:
                self._output_refs[ref.llm_run_id] = []
            self._output_refs[ref.llm_run_id].append(ref)
        self._pending_output_refs.clear()
        
        for err in self._pending_errors:
            if err.llm_run_id not in self._errors:
                self._errors[err.llm_run_id] = []
            self._errors[err.llm_run_id].append(err)
        self._pending_errors.clear()
    
    async def rollback(self) -> None:
        self._pending_runs.clear()
        self._pending_content.clear()
        self._pending_content_hash.clear()
        self._pending_input_refs.clear()
        self._pending_output_refs.clear()
        self._pending_errors.clear()
        self._pending_run_updates.clear()
        self._pending_content_touches.clear()
    
    def get_content_text(self, content_hash: str) -> Optional[str]:
        content_id = self._content_by_hash.get(content_hash)
        if content_id:
            record = self._content.get(content_id)
            return record.content_text if record else None
        return None
    
    def count_unique_content(self) -> int:
        return len(self._content)
    
    def clear(self) -> None:
        self._runs.clear()
        self._content.clear()
        self._content_by_hash.clear()
        self._input_refs.clear()
        self._output_refs.clear()
        self._errors.clear()
        self._pending_runs.clear()
        self._pending_content.clear()
        self._pending_content_hash.clear()
        self._pending_input_refs.clear()
        self._pending_output_refs.clear()
        self._pending_errors.clear()
        self._pending_run_updates.clear()
        self._pending_content_touches.clear()
