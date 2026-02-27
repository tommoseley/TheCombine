"""
LLM Thread Queue Repositories - ADR-035.

Repository layer for durable LLM execution:
- ThreadRepository: CRUD + find by idempotency key
- WorkItemRepository: CRUD + claim next + update status
- LedgerRepository: Append-only writes
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import (
    LLMThread,
    LLMWorkItem,
    LLMLedgerEntry,
    ThreadStatus,
    WorkItemStatus,
    LedgerEntryType,
    ErrorCode,
)
from app.api.models.llm_thread import (
    LLMThreadModel,
    LLMWorkItemModel,
    LLMLedgerEntryModel,
)


# =============================================================================
# Converters: ORM <-> Domain
# =============================================================================

def _orm_to_thread(orm: LLMThreadModel) -> LLMThread:
    """Convert ORM model to domain model."""
    return LLMThread(
        id=orm.id,
        kind=orm.kind,
        space_type=orm.space_type,
        space_id=orm.space_id,
        target_ref=orm.target_ref,
        status=ThreadStatus(orm.status),
        parent_thread_id=orm.parent_thread_id,
        idempotency_key=orm.idempotency_key,
        created_by=orm.created_by,
        created_at=orm.created_at,
        closed_at=orm.closed_at,
    )


def _thread_to_orm(domain: LLMThread, orm: Optional[LLMThreadModel] = None) -> LLMThreadModel:
    """Convert domain model to ORM model."""
    if orm is None:
        orm = LLMThreadModel()
    
    orm.id = domain.id
    orm.kind = domain.kind
    orm.space_type = domain.space_type
    orm.space_id = domain.space_id
    orm.target_ref = domain.target_ref
    orm.status = domain.status.value
    orm.parent_thread_id = domain.parent_thread_id
    orm.idempotency_key = domain.idempotency_key
    orm.created_by = domain.created_by
    orm.created_at = domain.created_at
    orm.closed_at = domain.closed_at
    
    return orm


def _orm_to_work_item(orm: LLMWorkItemModel) -> LLMWorkItem:
    """Convert ORM model to domain model."""
    return LLMWorkItem(
        id=orm.id,
        thread_id=orm.thread_id,
        sequence=orm.sequence,
        status=WorkItemStatus(orm.status),
        attempt=orm.attempt,
        lock_scope=orm.lock_scope,
        not_before=orm.not_before,
        error_code=ErrorCode(orm.error_code) if orm.error_code else None,
        error_message=orm.error_message,
        created_at=orm.created_at,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
    )


def _work_item_to_orm(domain: LLMWorkItem, orm: Optional[LLMWorkItemModel] = None) -> LLMWorkItemModel:
    """Convert domain model to ORM model."""
    if orm is None:
        orm = LLMWorkItemModel()
    
    orm.id = domain.id
    orm.thread_id = domain.thread_id
    orm.sequence = domain.sequence
    orm.status = domain.status.value
    orm.attempt = domain.attempt
    orm.lock_scope = domain.lock_scope
    orm.not_before = domain.not_before
    orm.error_code = domain.error_code.value if domain.error_code else None
    orm.error_message = domain.error_message
    orm.created_at = domain.created_at
    orm.started_at = domain.started_at
    orm.finished_at = domain.finished_at
    
    return orm


def _orm_to_ledger_entry(orm: LLMLedgerEntryModel) -> LLMLedgerEntry:
    """Convert ORM model to domain model."""
    return LLMLedgerEntry(
        id=orm.id,
        thread_id=orm.thread_id,
        work_item_id=orm.work_item_id,
        entry_type=LedgerEntryType(orm.entry_type),
        payload=orm.payload,
        payload_hash=orm.payload_hash,
        created_at=orm.created_at,
    )


def _ledger_entry_to_orm(domain: LLMLedgerEntry) -> LLMLedgerEntryModel:
    """Convert domain model to ORM model."""
    orm = LLMLedgerEntryModel()
    orm.id = domain.id
    orm.thread_id = domain.thread_id
    orm.work_item_id = domain.work_item_id
    orm.entry_type = domain.entry_type.value
    orm.payload = domain.payload
    orm.payload_hash = domain.payload_hash
    orm.created_at = domain.created_at
    return orm


# =============================================================================
# Thread Repository
# =============================================================================

class ThreadRepository:
    """Repository for LLM threads."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, thread: LLMThread) -> LLMThread:
        """Create a new thread."""
        orm = _thread_to_orm(thread)
        self.db.add(orm)
        await self.db.flush()
        return thread
    
    async def get(self, thread_id: UUID) -> Optional[LLMThread]:
        """Get thread by ID."""
        stmt = select(LLMThreadModel).where(LLMThreadModel.id == thread_id)
        result = await self.db.execute(stmt)
        orm = result.scalar_one_or_none()
        return _orm_to_thread(orm) if orm else None
    
    async def find_by_idempotency_key(self, key: str) -> Optional[LLMThread]:
        """Find active thread by idempotency key."""
        stmt = select(LLMThreadModel).where(
            and_(
                LLMThreadModel.idempotency_key == key,
                LLMThreadModel.status.in_(["open", "running"])
            )
        )
        result = await self.db.execute(stmt)
        orm = result.scalar_one_or_none()
        return _orm_to_thread(orm) if orm else None
    
    async def find_active_by_space(
        self,
        space_type: str,
        space_id: UUID,
    ) -> List[LLMThread]:
        """Find all active threads in a space."""
        stmt = select(LLMThreadModel).where(
            and_(
                LLMThreadModel.space_type == space_type,
                LLMThreadModel.space_id == space_id,
                LLMThreadModel.status.in_(["open", "running"])
            )
        ).order_by(LLMThreadModel.created_at.desc())
        
        result = await self.db.execute(stmt)
        return [_orm_to_thread(orm) for orm in result.scalars().all()]
    
    async def update_status(
        self,
        thread_id: UUID,
        status: ThreadStatus,
        closed_at: Optional[datetime] = None,
    ) -> None:
        """Update thread status."""
        values = {"status": status.value}
        if closed_at:
            values["closed_at"] = closed_at
        
        stmt = update(LLMThreadModel).where(
            LLMThreadModel.id == thread_id
        ).values(**values)
        
        await self.db.execute(stmt)
    
    async def get_child_summary(self, parent_thread_id: UUID) -> Dict[str, int]:
        """Get summary of child thread statuses."""
        stmt = select(LLMThreadModel.status).where(
            LLMThreadModel.parent_thread_id == parent_thread_id
        )
        result = await self.db.execute(stmt)
        
        summary = {}
        for status in result.scalars().all():
            summary[status] = summary.get(status, 0) + 1
        
        return summary


# =============================================================================
# Work Item Repository
# =============================================================================

class WorkItemRepository:
    """Repository for LLM work items."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, work_item: LLMWorkItem) -> LLMWorkItem:
        """Create a new work item."""
        orm = _work_item_to_orm(work_item)
        self.db.add(orm)
        await self.db.flush()
        return work_item
    
    async def get(self, work_item_id: UUID) -> Optional[LLMWorkItem]:
        """Get work item by ID."""
        stmt = select(LLMWorkItemModel).where(LLMWorkItemModel.id == work_item_id)
        result = await self.db.execute(stmt)
        orm = result.scalar_one_or_none()
        return _orm_to_work_item(orm) if orm else None
    
    async def get_by_thread(self, thread_id: UUID) -> List[LLMWorkItem]:
        """Get all work items for a thread."""
        stmt = select(LLMWorkItemModel).where(
            LLMWorkItemModel.thread_id == thread_id
        ).order_by(LLMWorkItemModel.sequence)
        
        result = await self.db.execute(stmt)
        return [_orm_to_work_item(orm) for orm in result.scalars().all()]
    
    async def update(self, work_item: LLMWorkItem) -> None:
        """Update work item."""
        stmt = update(LLMWorkItemModel).where(
            LLMWorkItemModel.id == work_item.id
        ).values(
            status=work_item.status.value,
            attempt=work_item.attempt,
            error_code=work_item.error_code.value if work_item.error_code else None,
            error_message=work_item.error_message,
            started_at=work_item.started_at,
            finished_at=work_item.finished_at,
        )
        await self.db.execute(stmt)


# =============================================================================
# Ledger Repository
# =============================================================================

class LedgerRepository:
    """Repository for LLM ledger entries (append-only)."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def append(self, entry: LLMLedgerEntry) -> LLMLedgerEntry:
        """Append a new ledger entry (immutable)."""
        # Compute hash if not provided
        if not entry.payload_hash:
            payload_json = json.dumps(entry.payload, sort_keys=True)
            entry.payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        
        orm = _ledger_entry_to_orm(entry)
        self.db.add(orm)
        await self.db.flush()
        return entry
    
    async def get_by_thread(self, thread_id: UUID) -> List[LLMLedgerEntry]:
        """Get all ledger entries for a thread."""
        stmt = select(LLMLedgerEntryModel).where(
            LLMLedgerEntryModel.thread_id == thread_id
        ).order_by(LLMLedgerEntryModel.created_at)
        
        result = await self.db.execute(stmt)
        return [_orm_to_ledger_entry(orm) for orm in result.scalars().all()]
    
    async def get_by_work_item(self, work_item_id: UUID) -> List[LLMLedgerEntry]:
        """Get all ledger entries for a work item."""
        stmt = select(LLMLedgerEntryModel).where(
            LLMLedgerEntryModel.work_item_id == work_item_id
        ).order_by(LLMLedgerEntryModel.created_at)
        
        result = await self.db.execute(stmt)
        return [_orm_to_ledger_entry(orm) for orm in result.scalars().all()]
