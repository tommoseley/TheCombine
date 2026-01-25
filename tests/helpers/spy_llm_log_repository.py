"""
Spy repository for Tier-2 wiring tests.

Records all calls + payloads for contract verification.
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field

from app.domain.repositories.llm_log_repository import (
    LLMRunRecord,
    LLMContentRecord,
    LLMInputRefRecord,
    LLMOutputRefRecord,
    LLMErrorRecord,
)


@dataclass
class MethodCall:
    """Record of a method call."""
    method: str
    args: Tuple
    kwargs: Dict[str, Any]


class SpyLLMLogRepository:
    """
    Spy repository that records all method calls.
    
    For Tier-2 tests: verifies call contracts (methods + payload shapes).
    """
    
    def __init__(self):
        self.calls: List[MethodCall] = []
        self._committed = False
        self._rolled_back = False
    
    def _record(self, method: str, *args, **kwargs):
        self.calls.append(MethodCall(method, args, kwargs))
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        self._record("get_content_by_hash", content_hash)
        return None
    
    async def insert_content(self, record: LLMContentRecord) -> None:
        self._record("insert_content", record=record)
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        self._record("touch_content_accessed", content_id)
    
    async def insert_run(self, record: LLMRunRecord) -> None:
        self._record("insert_run", record=record)
    
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
        self._record(
            "update_run_completion",
            run_id=run_id,
            status=status,
            ended_at=ended_at,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            metadata=metadata,
        )
    
    async def bump_error_summary(
        self,
        run_id: UUID,
        error_code: Optional[str],
        message: str,
    ) -> None:
        self._record("bump_error_summary", run_id=run_id, error_code=error_code, message=message)
    
    async def get_run(self, run_id: UUID) -> Optional[LLMRunRecord]:
        self._record("get_run", run_id)
        return None
    
    async def get_run_by_correlation_id(self, correlation_id: UUID) -> Optional[LLMRunRecord]:
        self._record("get_run_by_correlation_id", correlation_id)
        return None
    
    async def insert_input_ref(self, record: LLMInputRefRecord) -> None:
        self._record("insert_input_ref", record=record)
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
        self._record("insert_output_ref", record=record)
    
    async def get_inputs_for_run(self, run_id: UUID) -> List[LLMInputRefRecord]:
        self._record("get_inputs_for_run", run_id)
        return []
    
    async def get_outputs_for_run(self, run_id: UUID) -> List[LLMOutputRefRecord]:
        self._record("get_outputs_for_run", run_id)
        return []
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        self._record("get_next_error_sequence", run_id)
        return 1
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        self._record("insert_error", record=record)
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        self._record("get_errors_for_run", run_id)
        return []
    
    async def commit(self) -> None:
        self._record("commit")
        self._committed = True
    
    async def rollback(self) -> None:
        self._record("rollback")
        self._rolled_back = True
    
    def assert_called(self, method: str) -> MethodCall:
        """Assert method was called, return the call."""
        for call in self.calls:
            if call.method == method:
                return call
        raise AssertionError(f"Method '{method}' not called. Calls: {[c.method for c in self.calls]}")
    
    def assert_called_with(self, method: str, **expected_kwargs):
        """Assert method was called with specific kwargs."""
        call = self.assert_called(method)
        for key, expected in expected_kwargs.items():
            actual = call.kwargs.get(key)
            if actual != expected:
                raise AssertionError(f"{method}() expected {key}={expected}, got {actual}")
    
    def get_calls(self, method: str) -> List[MethodCall]:
        """Get all calls to a method."""
        return [c for c in self.calls if c.method == method]
    
    def assert_insert_run_has_correlation_id(self, correlation_id: UUID):
        """Assert insert_run was called with specific correlation_id."""
        call = self.assert_called("insert_run")
        record = call.kwargs.get("record")
        if record.correlation_id != correlation_id:
            raise AssertionError(
                f"insert_run correlation_id mismatch: expected {correlation_id}, got {record.correlation_id}"
            )
    
    def assert_insert_run_has_workflow_execution_id(self, workflow_execution_id: str):
        """Assert insert_run was called with specific workflow_execution_id."""
        call = self.assert_called("insert_run")
        record = call.kwargs.get("record")
        if record.workflow_execution_id != workflow_execution_id:
            raise AssertionError(
                f"insert_run workflow_execution_id mismatch: expected {workflow_execution_id}, got {record.workflow_execution_id}"
            )
    
    def get_insert_run_record(self) -> Optional[LLMRunRecord]:
        """Get the LLMRunRecord from insert_run call."""
        call = self.assert_called("insert_run")
        return call.kwargs.get("record")
    
    def assert_input_logged(self, kind: str):
        """Assert an input ref was logged with given kind."""
        for call in self.get_calls("insert_input_ref"):
            record = call.kwargs.get("record")
            if record and record.kind == kind:
                return
        raise AssertionError(f"No insert_input_ref with kind='{kind}'")
    
    def assert_output_logged(self, kind: str):
        """Assert an output ref was logged with given kind."""
        for call in self.get_calls("insert_output_ref"):
            record = call.kwargs.get("record")
            if record and record.kind == kind:
                return
        raise AssertionError(f"No insert_output_ref with kind='{kind}'")
    
    def assert_committed(self):
        """Assert commit was called."""
        if not self._committed:
            raise AssertionError("commit() was not called")
    
    def assert_run_completed_with_status(self, status: str):
        """Assert update_run_completion was called with status."""
        call = self.assert_called("update_run_completion")
        if call.kwargs.get("status") != status:
            raise AssertionError(f"Expected status={status}, got {call.kwargs.get('status')}")
