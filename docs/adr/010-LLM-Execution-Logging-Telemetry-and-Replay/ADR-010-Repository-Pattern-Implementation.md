# ADR-010: Repository Pattern - Corrected Design

## Test Tiers (Corrected)

| Tier | Purpose | Implementation | Speed |
|------|---------|----------------|-------|
| **Tier-1** | Business logic + persistence semantics | `InMemoryLLMLogRepository` (queryable) | Fast |
| **Tier-2** | Wiring (HTTP → Logger → Repo) | Spy repo that records calls + payloads | Fast |
| **Tier-3** | Dialect/constraints/indexes | `PostgresLLMLogRepository` + real DB | Slow |

**Tier-2 clarification**: Verifies call contracts (right methods called with right payload shapes), NOT SQL string verification.

---

## Key Corrections

### 1. No Commits in Repository

Repository methods do `execute()` only. Commits owned by service layer.

```python
# WRONG - commits inside repo
async def insert_run(self, record: LLMRunRecord) -> None:
    await self.db.execute(...)
    await self.db.commit()  # ❌ Don't do this

# RIGHT - repo just executes
async def insert_run(self, record: LLMRunRecord) -> None:
    await self.db.execute(...)
    # No commit - caller manages transaction
```

### 2. Atomic Error Summary Update

Single method instead of separate increment + update:

```python
# WRONG - separate operations, race-prone
await repo.insert_error(error_record)
await repo.increment_run_error_count(run_id)  # ❌ Remove this
await repo.update_run(run_id, primary_error_code=..., primary_error_message=...)

# RIGHT - single atomic operation
await repo.insert_error(error_record)
await repo.bump_error_summary(run_id, error_code, message)  # ✓ One UPDATE
```

### 3. Correlation ID: UUID Everywhere

- Middleware converts header string → UUID once
- Domain + DB store UUID
- No string/UUID mismatches downstream

---

## Corrected Repository Protocol

```python
# app/domain/repositories/llm_log_repository.py
"""
Repository protocol for LLM execution logging.

Key design rules:
- Repository does NOT commit (caller owns transaction)
- DTOs are dataclasses (no ORM dependency)
- UUID for correlation_id everywhere
"""

from typing import Protocol, Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


# =============================================================================
# DATA TRANSFER OBJECTS
# =============================================================================

@dataclass
class LLMRunRecord:
    """LLM run data."""
    id: UUID
    correlation_id: UUID  # Always UUID, never string
    project_id: Optional[UUID]
    artifact_type: Optional[str]
    role: str
    model_provider: str
    model_name: str
    prompt_id: str
    prompt_version: str
    effective_prompt_hash: str
    schema_version: Optional[str]
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    primary_error_code: Optional[str] = None
    primary_error_message: Optional[str] = None
    error_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMContentRecord:
    """Content storage record."""
    id: UUID
    content_hash: str
    content_text: str
    content_size: int
    created_at: datetime
    accessed_at: datetime


@dataclass
class LLMInputRefRecord:
    """Input reference record."""
    id: UUID
    llm_run_id: UUID
    kind: str
    content_ref: str
    content_hash: str
    content_redacted: bool
    created_at: datetime


@dataclass
class LLMOutputRefRecord:
    """Output reference record."""
    id: UUID
    llm_run_id: UUID
    kind: str
    content_ref: str
    content_hash: str
    parse_status: Optional[str]
    validation_status: Optional[str]
    created_at: datetime


@dataclass
class LLMErrorRecord:
    """Error record."""
    id: UUID
    llm_run_id: UUID
    sequence: int
    stage: str
    severity: str
    error_code: Optional[str]
    message: str
    details: Optional[Dict[str, Any]]
    created_at: datetime


# =============================================================================
# REPOSITORY PROTOCOL
# =============================================================================

class LLMLogRepository(Protocol):
    """
    Repository interface for LLM execution logging.
    
    IMPORTANT: Repository does NOT commit. Caller owns transaction boundaries.
    """
    
    # -------------------------------------------------------------------------
    # Content Storage
    # -------------------------------------------------------------------------
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        """Find content by hash for deduplication."""
        ...
    
    async def insert_content(self, record: LLMContentRecord) -> None:
        """Insert new content record. Does NOT commit."""
        ...
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        """Update accessed_at timestamp. Does NOT commit."""
        ...
    
    # -------------------------------------------------------------------------
    # LLM Run
    # -------------------------------------------------------------------------
    
    async def insert_run(self, record: LLMRunRecord) -> None:
        """Insert new LLM run record. Does NOT commit."""
        ...
    
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
        """Update run with completion data. Does NOT commit."""
        ...
    
    async def bump_error_summary(
        self,
        run_id: UUID,
        error_code: Optional[str],
        message: str,
    ) -> None:
        """
        Atomically increment error_count and set primary_error fields.
        
        Single UPDATE: SET error_count = error_count + 1, 
                           primary_error_code = :code,
                           primary_error_message = :msg
        
        Does NOT commit.
        """
        ...
    
    async def get_run(self, run_id: UUID) -> Optional[LLMRunRecord]:
        """Get run by ID."""
        ...
    
    async def get_run_by_correlation_id(self, correlation_id: UUID) -> Optional[LLMRunRecord]:
        """Get run by correlation ID."""
        ...
    
    # -------------------------------------------------------------------------
    # Input/Output References
    # -------------------------------------------------------------------------
    
    async def insert_input_ref(self, record: LLMInputRefRecord) -> None:
        """Insert input reference. Does NOT commit."""
        ...
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
        """Insert output reference. Does NOT commit."""
        ...
    
    async def get_inputs_for_run(self, run_id: UUID) -> List[LLMInputRefRecord]:
        """Get all input refs for a run."""
        ...
    
    async def get_outputs_for_run(self, run_id: UUID) -> List[LLMOutputRefRecord]:
        """Get all output refs for a run."""
        ...
    
    # -------------------------------------------------------------------------
    # Error Tracking
    # -------------------------------------------------------------------------
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        """Get next sequence number for errors on this run."""
        ...
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        """Insert error record. Does NOT commit."""
        ...
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        """Get all errors for a run."""
        ...
    
    # -------------------------------------------------------------------------
    # Transaction Control (for service layer)
    # -------------------------------------------------------------------------
    
    async def commit(self) -> None:
        """Commit current transaction."""
        ...
    
    async def rollback(self) -> None:
        """Rollback current transaction."""
        ...
```

---

## In-Memory Repository (Tier-1)

```python
# app/domain/repositories/in_memory_llm_log_repository.py
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
        
        # Track uncommitted changes for rollback
        self._pending_runs: Dict[UUID, LLMRunRecord] = {}
        self._pending_content: Dict[UUID, LLMContentRecord] = {}
        self._pending_input_refs: List[LLMInputRefRecord] = []
        self._pending_output_refs: List[LLMOutputRefRecord] = []
        self._pending_errors: List[LLMErrorRecord] = []
        self._pending_run_updates: Dict[UUID, Dict[str, Any]] = {}
    
    # -------------------------------------------------------------------------
    # Content Storage
    # -------------------------------------------------------------------------
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        # Check committed first, then pending
        content_id = self._content_by_hash.get(content_hash)
        if content_id:
            return self._content.get(content_id) or self._pending_content.get(content_id)
        return None
    
    async def insert_content(self, record: LLMContentRecord) -> None:
        self._pending_content[record.id] = record
        self._content_by_hash[record.content_hash] = record.id
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        if content_id in self._content:
            old = self._content[content_id]
            self._content[content_id] = replace(old, accessed_at=datetime.now(timezone.utc))
    
    # -------------------------------------------------------------------------
    # LLM Run
    # -------------------------------------------------------------------------
    
    async def insert_run(self, record: LLMRunRecord) -> None:
        self._pending_runs[record.id] = record
        self._input_refs[record.id] = []
        self._output_refs[record.id] = []
        self._errors[record.id] = []
    
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
        updates = {
            'status': status,
            'ended_at': ended_at,
        }
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
        """Atomic increment + set primary error fields."""
        if run_id not in self._pending_run_updates:
            self._pending_run_updates[run_id] = {}
        
        # Get current error count
        current_run = self._runs.get(run_id) or self._pending_runs.get(run_id)
        current_count = current_run.error_count if current_run else 0
        
        # Apply any pending count increments
        pending = self._pending_run_updates.get(run_id, {})
        if 'error_count' in pending:
            current_count = pending['error_count']
        
        self._pending_run_updates[run_id].update({
            'error_count': current_count + 1,
            'primary_error_code': error_code,
            'primary_error_message': message,
        })
    
    async def get_run(self, run_id: UUID) -> Optional[LLMRunRecord]:
        # Return committed data (pending not visible until commit)
        return self._runs.get(run_id)
    
    async def get_run_by_correlation_id(self, correlation_id: UUID) -> Optional[LLMRunRecord]:
        for run in self._runs.values():
            if run.correlation_id == correlation_id:
                return run
        return None
    
    # -------------------------------------------------------------------------
    # Input/Output References
    # -------------------------------------------------------------------------
    
    async def insert_input_ref(self, record: LLMInputRefRecord) -> None:
        self._pending_input_refs.append(record)
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
        self._pending_output_refs.append(record)
    
    async def get_inputs_for_run(self, run_id: UUID) -> List[LLMInputRefRecord]:
        return self._input_refs.get(run_id, [])
    
    async def get_outputs_for_run(self, run_id: UUID) -> List[LLMOutputRefRecord]:
        return self._output_refs.get(run_id, [])
    
    # -------------------------------------------------------------------------
    # Error Tracking
    # -------------------------------------------------------------------------
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        committed = len(self._errors.get(run_id, []))
        pending = len([e for e in self._pending_errors if e.llm_run_id == run_id])
        return committed + pending + 1
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        self._pending_errors.append(record)
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        return self._errors.get(run_id, [])
    
    # -------------------------------------------------------------------------
    # Transaction Control
    # -------------------------------------------------------------------------
    
    async def commit(self) -> None:
        """Apply all pending changes."""
        # Commit content
        self._content.update(self._pending_content)
        self._pending_content.clear()
        
        # Commit runs
        self._runs.update(self._pending_runs)
        self._pending_runs.clear()
        
        # Apply run updates
        for run_id, updates in self._pending_run_updates.items():
            if run_id in self._runs:
                self._runs[run_id] = replace(self._runs[run_id], **updates)
        self._pending_run_updates.clear()
        
        # Commit refs
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
        
        # Commit errors
        for err in self._pending_errors:
            if err.llm_run_id not in self._errors:
                self._errors[err.llm_run_id] = []
            self._errors[err.llm_run_id].append(err)
        self._pending_errors.clear()
    
    async def rollback(self) -> None:
        """Discard all pending changes."""
        self._pending_runs.clear()
        self._pending_content.clear()
        self._pending_input_refs.clear()
        self._pending_output_refs.clear()
        self._pending_errors.clear()
        self._pending_run_updates.clear()
    
    # -------------------------------------------------------------------------
    # Test Helpers (not in protocol)
    # -------------------------------------------------------------------------
    
    def get_content_text(self, content_hash: str) -> Optional[str]:
        """Retrieve actual content text by hash."""
        content_id = self._content_by_hash.get(content_hash)
        if content_id:
            record = self._content.get(content_id)
            return record.content_text if record else None
        return None
    
    def count_unique_content(self) -> int:
        """Count unique content entries."""
        return len(self._content)
    
    def clear(self) -> None:
        """Reset all storage."""
        self._runs.clear()
        self._content.clear()
        self._content_by_hash.clear()
        self._input_refs.clear()
        self._output_refs.clear()
        self._errors.clear()
        self._pending_runs.clear()
        self._pending_content.clear()
        self._pending_input_refs.clear()
        self._pending_output_refs.clear()
        self._pending_errors.clear()
        self._pending_run_updates.clear()
```

---

## Spy Repository (Tier-2)

```python
# tests/helpers/spy_llm_log_repository.py
"""
Spy repository for Tier-2 wiring tests.

Records all calls + payloads for contract verification.
NOT for SQL string verification.
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
    Does NOT verify SQL strings.
    """
    
    def __init__(self):
        self.calls: List[MethodCall] = []
        self._committed = False
        self._rolled_back = False
    
    def _record(self, method: str, *args, **kwargs):
        self.calls.append(MethodCall(method, args, kwargs))
    
    # -------------------------------------------------------------------------
    # Content Storage
    # -------------------------------------------------------------------------
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        self._record("get_content_by_hash", content_hash)
        return None  # Simulate no existing content
    
    async def insert_content(self, record: LLMContentRecord) -> None:
        self._record("insert_content", record=record)
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        self._record("touch_content_accessed", content_id)
    
    # -------------------------------------------------------------------------
    # LLM Run
    # -------------------------------------------------------------------------
    
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
    
    # -------------------------------------------------------------------------
    # Input/Output References
    # -------------------------------------------------------------------------
    
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
    
    # -------------------------------------------------------------------------
    # Error Tracking
    # -------------------------------------------------------------------------
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        self._record("get_next_error_sequence", run_id)
        return 1
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        self._record("insert_error", record=record)
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        self._record("get_errors_for_run", run_id)
        return []
    
    # -------------------------------------------------------------------------
    # Transaction Control
    # -------------------------------------------------------------------------
    
    async def commit(self) -> None:
        self._record("commit")
        self._committed = True
    
    async def rollback(self) -> None:
        self._record("rollback")
        self._rolled_back = True
    
    # -------------------------------------------------------------------------
    # Assertion Helpers
    # -------------------------------------------------------------------------
    
    def assert_called(self, method: str) -> MethodCall:
        """Assert method was called, return the call for inspection."""
        for call in self.calls:
            if call.method == method:
                return call
        raise AssertionError(f"Method '{method}' was not called. Calls: {[c.method for c in self.calls]}")
    
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
    
    def assert_input_logged(self, kind: str):
        """Assert an input ref was logged with given kind."""
        calls = self.get_calls("insert_input_ref")
        for call in calls:
            record = call.kwargs.get("record")
            if record and record.kind == kind:
                return
        raise AssertionError(f"No insert_input_ref call with kind='{kind}'")
    
    def assert_output_logged(self, kind: str):
        """Assert an output ref was logged with given kind."""
        calls = self.get_calls("insert_output_ref")
        for call in calls:
            record = call.kwargs.get("record")
            if record and record.kind == kind:
                return
        raise AssertionError(f"No insert_output_ref call with kind='{kind}'")
    
    def assert_committed(self):
        """Assert commit was called."""
        if not self._committed:
            raise AssertionError("commit() was not called")
    
    def assert_run_completed_with_status(self, status: str):
        """Assert update_run_completion was called with status."""
        call = self.assert_called("update_run_completion")
        if call.kwargs.get("status") != status:
            raise AssertionError(
                f"Expected status={status}, got {call.kwargs.get('status')}"
            )
```

---

## Refactored LLMExecutionLogger (Service Owns Commit)

```python
# app/domain/services/llm_execution_logger.py
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
    - add_input/add_output: commits after each (or batch in future)
    - log_error: commits after error + summary update
    - complete_run: commits after final update
    """
    
    def __init__(self, repo: LLMLogRepository):
        self.repo = repo
    
    async def start_run(
        self,
        correlation_id: UUID,  # Always UUID, converted at boundary
        project_id: Optional[UUID],
        artifact_type: Optional[str],
        role: str,
        model_provider: str,
        model_name: str,
        prompt_id: str,
        prompt_version: str,
        effective_prompt: str,
        schema_version: Optional[str] = None,
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
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc),
        )
        
        try:
            await self.repo.insert_run(record)
            await self.repo.commit()
            
            logger.info(
                f"Started LLM run {run_id} "
                f"(correlation: {correlation_id}, role: {role}, artifact: {artifact_type})"
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
            
            logger.debug(f"Added input ref (run: {run_id}, kind: {kind})")
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
            
            logger.debug(f"Added output ref (run: {run_id}, kind: {kind})")
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
            
            # Atomic summary update if ERROR or FATAL
            if severity in ("ERROR", "FATAL"):
                await self.repo.bump_error_summary(run_id, error_code, message)
            
            await self.repo.commit()
            
            logger.warning(f"LLM run {run_id} error [{severity}] {stage}: {message}")
            
        except Exception as e:
            await self.repo.rollback()
            logger.error(f"Failed to log error: {e}")
            # Don't re-raise
    
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
            
            logger.info(
                f"Completed LLM run {run_id}: {status} "
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
            logger.debug(f"Content deduplicated (hash: {content_hash[:8]}...)")
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
        logger.debug(f"Content stored (hash: {content_hash[:8]}...)")
        
        return f"db://llm_content/{content_id}", content_hash
```

---

## PostgreSQL Repository (No Commits)

```python
# app/domain/repositories/postgres_llm_log_repository.py
"""
PostgreSQL implementation.

IMPORTANT: Does NOT commit. Caller owns transaction.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
    
    # -------------------------------------------------------------------------
    # Transaction Control
    # -------------------------------------------------------------------------
    
    async def commit(self) -> None:
        await self.db.commit()
    
    async def rollback(self) -> None:
        await self.db.rollback()
    
    # -------------------------------------------------------------------------
    # Content Storage
    # -------------------------------------------------------------------------
    
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
        # NO COMMIT
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        await self.db.execute(
            text("UPDATE llm_content SET accessed_at = :now WHERE id = :id"),
            {"id": content_id, "now": datetime.now()}
        )
        # NO COMMIT
    
    # -------------------------------------------------------------------------
    # LLM Run
    # -------------------------------------------------------------------------
    
    async def insert_run(self, record: LLMRunRecord) -> None:
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
        # NO COMMIT
    
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
        # NO COMMIT
    
    async def bump_error_summary(
        self,
        run_id: UUID,
        error_code: Optional[str],
        message: str,
    ) -> None:
        """Atomic increment + set primary error fields."""
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
        # NO COMMIT
    
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
    
    # -------------------------------------------------------------------------
    # Input/Output References
    # -------------------------------------------------------------------------
    
    async def insert_input_ref(self, record: LLMInputRefRecord) -> None:
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
        # NO COMMIT
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
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
        # NO COMMIT
    
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
    
    # -------------------------------------------------------------------------
    # Error Tracking
    # -------------------------------------------------------------------------
    
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
        # NO COMMIT
    
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
```

---

## Correlation ID Middleware

```python
# app/middleware/correlation.py
"""
Correlation ID middleware.

Converts X-Correlation-ID header (string) to UUID once.
Stores as UUID in request.state for downstream use.
"""

from uuid import UUID, uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Extract or generate correlation ID from request.
    
    - Accepts X-Correlation-ID header as string
    - Converts to UUID (or generates new one)
    - Stores as UUID in request.state.correlation_id
    - Echoes back in response headers
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get header value (string or None)
        header_value = request.headers.get("X-Correlation-ID")
        
        # Convert to UUID
        if header_value:
            try:
                correlation_id = UUID(header_value)
            except ValueError:
                logger.warning(f"Invalid correlation ID format: {header_value}, generating new")
                correlation_id = uuid4()
        else:
            correlation_id = uuid4()
        
        # Store as UUID in request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Echo in response (as string for HTTP header)
        response.headers["X-Correlation-ID"] = str(correlation_id)
        
        return response
```

---

## Summary of Corrections

| Issue | Before | After |
|-------|--------|-------|
| Tier-2 description | "SQL generation verification" | "Call contract verification (methods + payloads)" |
| Repo commits | `commit()` in every method | Repo never commits; service commits at boundaries |
| Error summary update | Separate increment + update (race-prone) | Single `bump_error_summary()` (atomic) |
| Correlation ID | Mixed string/UUID | UUID everywhere; parse once in middleware |