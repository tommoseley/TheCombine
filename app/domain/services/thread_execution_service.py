"""
Thread Execution Service - ADR-035.

Orchestrates the durable LLM execution lifecycle:
- Thread creation with idempotency
- Work item management
- Ledger entry recording
- Status transitions
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence import (
    LLMThread,
    LLMWorkItem,
    LLMLedgerEntry,
    ThreadStatus,
    LedgerEntryType,
    ErrorCode,
    ThreadRepository,
    WorkItemRepository,
    LedgerRepository,
)


logger = logging.getLogger(__name__)


class ThreadExecutionService:
    """
    Service for managing durable LLM execution threads.
    
    Per ADR-035:
    - Threads are durable containers for user intent
    - Work items are queue-executed units
    - Ledger entries are immutable records of what was paid for
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.thread_repo = ThreadRepository(db)
        self.work_item_repo = WorkItemRepository(db)
        self.ledger_repo = LedgerRepository(db)
    
    # =========================================================================
    # Thread Management
    # =========================================================================
    
    async def get_or_create_thread(
        self,
        kind: str,
        space_type: str,
        space_id: UUID,
        target_ref: Dict[str, Any],
        idempotency_key: str,
        created_by: Optional[str] = None,
        parent_thread_id: Optional[UUID] = None,
    ) -> Tuple[LLMThread, bool]:
        """
        Get existing active thread or create new one.
        
        Returns:
            Tuple of (thread, created) where created is True if new thread was made.
        """
        # Check for existing active thread
        existing = await self.thread_repo.find_by_idempotency_key(idempotency_key)
        if existing:
            logger.info(f"Found existing thread {existing.id} for key {idempotency_key}")
            return existing, False
        
        # Create new thread
        thread = LLMThread.create(
            kind=kind,
            space_type=space_type,
            space_id=space_id,
            target_ref=target_ref,
            idempotency_key=idempotency_key,
            parent_thread_id=parent_thread_id,
            created_by=created_by,
        )
        
        await self.thread_repo.create(thread)
        logger.info(f"Created thread {thread.id} kind={kind}")
        
        return thread, True
    
    async def get_thread(self, thread_id: UUID) -> Optional[LLMThread]:
        """Get thread by ID."""
        return await self.thread_repo.get(thread_id)
    
    async def get_active_threads(
        self,
        space_type: str,
        space_id: UUID,
    ) -> List[LLMThread]:
        """Get all active threads in a space."""
        return await self.thread_repo.find_active_by_space(space_type, space_id)
    
    async def start_thread(self, thread_id: UUID) -> None:
        """Mark thread as running."""
        await self.thread_repo.update_status(thread_id, ThreadStatus.RUNNING)
        logger.info(f"Thread {thread_id} started")
    
    async def complete_thread(self, thread_id: UUID) -> None:
        """Mark thread as complete."""
        await self.thread_repo.update_status(
            thread_id,
            ThreadStatus.COMPLETE,
            closed_at=datetime.now(timezone.utc)
        )
        logger.info(f"Thread {thread_id} completed")
    
    async def fail_thread(self, thread_id: UUID) -> None:
        """Mark thread as failed."""
        await self.thread_repo.update_status(
            thread_id,
            ThreadStatus.FAILED,
            closed_at=datetime.now(timezone.utc)
        )
        logger.info(f"Thread {thread_id} failed")
    
    async def get_child_summary(self, parent_thread_id: UUID) -> Dict[str, int]:
        """Get summary of child thread statuses."""
        return await self.thread_repo.get_child_summary(parent_thread_id)
    
    # =========================================================================
    # Work Item Management
    # =========================================================================
    
    async def create_work_item(
        self,
        thread_id: UUID,
        lock_scope: Optional[str] = None,
    ) -> LLMWorkItem:
        """Create a work item for a thread."""
        # Get current max sequence
        existing = await self.work_item_repo.get_by_thread(thread_id)
        sequence = max([w.sequence for w in existing], default=0) + 1
        
        work_item = LLMWorkItem.create(
            thread_id=thread_id,
            sequence=sequence,
            lock_scope=lock_scope,
        )
        
        await self.work_item_repo.create(work_item)
        logger.info(f"Created work item {work_item.id} for thread {thread_id}")
        
        return work_item
    
    async def get_work_item(self, work_item_id: UUID) -> Optional[LLMWorkItem]:
        """Get work item by ID."""
        return await self.work_item_repo.get(work_item_id)
    
    async def claim_work_item(self, work_item_id: UUID) -> None:
        """Claim work item for processing."""
        work_item = await self.work_item_repo.get(work_item_id)
        if work_item:
            work_item.claim()
            await self.work_item_repo.update(work_item)
            logger.info(f"Work item {work_item_id} claimed")
    
    async def start_work_item(self, work_item_id: UUID) -> None:
        """Mark work item as running."""
        work_item = await self.work_item_repo.get(work_item_id)
        if work_item:
            work_item.start()
            await self.work_item_repo.update(work_item)
            logger.info(f"Work item {work_item_id} running")
    
    async def apply_work_item(self, work_item_id: UUID) -> None:
        """Mark work item as successfully applied."""
        work_item = await self.work_item_repo.get(work_item_id)
        if work_item:
            work_item.apply()
            await self.work_item_repo.update(work_item)
            logger.info(f"Work item {work_item_id} applied")
    
    async def fail_work_item(
        self,
        work_item_id: UUID,
        error_code: ErrorCode,
        error_message: str,
    ) -> None:
        """Mark work item as failed."""
        work_item = await self.work_item_repo.get(work_item_id)
        if work_item:
            work_item.fail(error_code, error_message)
            await self.work_item_repo.update(work_item)
            logger.info(f"Work item {work_item_id} failed: {error_code}")
    
    # =========================================================================
    # Ledger Management
    # =========================================================================
    
    async def record_prompt(
        self,
        thread_id: UUID,
        work_item_id: UUID,
        prompt_data: Dict[str, Any],
    ) -> LLMLedgerEntry:
        """Record prompt sent to LLM."""
        entry = LLMLedgerEntry.create(
            thread_id=thread_id,
            work_item_id=work_item_id,
            entry_type=LedgerEntryType.PROMPT,
            payload=prompt_data,
        )
        await self.ledger_repo.append(entry)
        logger.debug(f"Recorded prompt for work item {work_item_id}")
        return entry
    
    async def record_response(
        self,
        thread_id: UUID,
        work_item_id: UUID,
        response_data: Dict[str, Any],
    ) -> LLMLedgerEntry:
        """Record response from LLM."""
        entry = LLMLedgerEntry.create(
            thread_id=thread_id,
            work_item_id=work_item_id,
            entry_type=LedgerEntryType.RESPONSE,
            payload=response_data,
        )
        await self.ledger_repo.append(entry)
        logger.debug(f"Recorded response for work item {work_item_id}")
        return entry
    
    async def record_parse_report(
        self,
        thread_id: UUID,
        work_item_id: UUID,
        report_data: Dict[str, Any],
    ) -> LLMLedgerEntry:
        """Record parse/validation report."""
        entry = LLMLedgerEntry.create(
            thread_id=thread_id,
            work_item_id=work_item_id,
            entry_type=LedgerEntryType.PARSE_REPORT,
            payload=report_data,
        )
        await self.ledger_repo.append(entry)
        logger.debug(f"Recorded parse report for work item {work_item_id}")
        return entry
    
    async def record_mutation(
        self,
        thread_id: UUID,
        work_item_id: UUID,
        mutation_data: Dict[str, Any],
    ) -> LLMLedgerEntry:
        """Record mutation applied to documents."""
        entry = LLMLedgerEntry.create(
            thread_id=thread_id,
            work_item_id=work_item_id,
            entry_type=LedgerEntryType.MUTATION_REPORT,
            payload=mutation_data,
        )
        await self.ledger_repo.append(entry)
        logger.debug(f"Recorded mutation for work item {work_item_id}")
        return entry
    
    async def record_error(
        self,
        thread_id: UUID,
        work_item_id: Optional[UUID],
        error_data: Dict[str, Any],
    ) -> LLMLedgerEntry:
        """Record error in ledger."""
        entry = LLMLedgerEntry.create(
            thread_id=thread_id,
            work_item_id=work_item_id,
            entry_type=LedgerEntryType.ERROR,
            payload=error_data,
        )
        await self.ledger_repo.append(entry)
        logger.debug(f"Recorded error for thread {thread_id}")
        return entry
    
    async def get_ledger_entries(self, thread_id: UUID) -> List[LLMLedgerEntry]:
        """Get all ledger entries for a thread."""
        return await self.ledger_repo.get_by_thread(thread_id)
    
    # =========================================================================
    # Idempotency Key Generation
    # =========================================================================
    
    @staticmethod
    def make_idempotency_key(
        operation: str,
        space_type: str,
        space_id: UUID,
        target_doc_type: str,
        target_id: str,
    ) -> str:
        """
        Generate idempotency key from semantic identity.
        
        Format: {operation}:{space_type}:{space_id}:{target_doc_type}:{target_id}
        """
        return f"{operation}:{space_type}:{space_id}:{target_doc_type}:{target_id}"
