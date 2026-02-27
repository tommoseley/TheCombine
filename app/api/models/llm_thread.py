"""
LLM Thread Queue Models - ADR-035 Durable LLM Execution.

Three tables for durable LLM work:
- llm_threads: Intent containers (user request)
- llm_work_items: Execution units (queue work)
- llm_ledger_entries: Immutable interaction records
"""

from datetime import datetime
from typing import Optional, Dict
from uuid import UUID

from sqlalchemy import (
    Column, String, Integer, Text, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from app.core.database import Base


class LLMThreadModel(Base):
    """
    Intent container - durable record of user intent.
    
    A Thread represents one semantic user intent (e.g., "Generate stories for Epic X").
    Threads are operation-scoped, not conversational.
    """
    
    __tablename__ = "llm_threads"
    
    # Identity
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Classification
    kind: Mapped[str] = Column(String(100), nullable=False)  # story_generate_epic, story_generate_all
    space_type: Mapped[str] = Column(String(50), nullable=False)  # project
    space_id: Mapped[UUID] = Column(PG_UUID(as_uuid=True), nullable=False)
    target_ref: Mapped[Dict] = Column(JSONB, nullable=False)  # {doc_type, doc_id, epic_id?}
    
    # Status
    status: Mapped[str] = Column(String(20), nullable=False, default="open")  # open|running|complete|failed|canceled
    
    # Orchestration
    parent_thread_id: Mapped[Optional[UUID]] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_threads.id"),
        nullable=True,
    )
    
    # Idempotency
    idempotency_key: Mapped[Optional[str]] = Column(String(255), nullable=True)
    
    # Audit
    created_by: Mapped[Optional[str]] = Column(String(100), nullable=True)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    closed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    parent_thread = relationship("LLMThreadModel", remote_side=[id], backref="child_threads")
    work_items = relationship("LLMWorkItemModel", back_populates="thread", lazy="dynamic")
    ledger_entries = relationship("LLMLedgerEntryModel", back_populates="thread", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<LLMThread {self.id} kind={self.kind} status={self.status}>"


class LLMWorkItemModel(Base):
    """
    Execution unit - queue-executed work.
    
    A Work Item is a single executable unit, typically one LLM call
    followed by validation and a lock-safe mutation.
    """
    
    __tablename__ = "llm_work_items"
    
    # Identity
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Thread association
    thread_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_threads.id"),
        nullable=False,
    )
    sequence: Mapped[int] = Column(Integer, nullable=False, default=1)
    
    # Status
    status: Mapped[str] = Column(String(20), nullable=False, default="queued")  # queued|claimed|running|applied|failed|dead_letter
    attempt: Mapped[int] = Column(Integer, nullable=False, default=1)
    
    # Locking
    lock_scope: Mapped[Optional[str]] = Column(String(255), nullable=True)  # project:{id} or epic:{id}
    not_before: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking (informational only - authoritative context in ledger)
    error_code: Mapped[Optional[str]] = Column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    thread = relationship("LLMThreadModel", back_populates="work_items")
    ledger_entries = relationship("LLMLedgerEntryModel", back_populates="work_item", lazy="dynamic")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("thread_id", "sequence", name="uq_work_item_thread_sequence"),
    )
    
    def __repr__(self) -> str:
        return f"<LLMWorkItem {self.id} thread={self.thread_id} status={self.status}>"


class LLMLedgerEntryModel(Base):
    """
    Immutable ledger - what we paid for and received.
    
    A Ledger Entry records what the system paid for and received.
    Ledger entries are immutable and append-only.
    """
    
    __tablename__ = "llm_ledger_entries"
    
    # Identity
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Associations
    thread_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_threads.id"),
        nullable=False,
    )
    work_item_id: Mapped[Optional[UUID]] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_work_items.id"),
        nullable=True,
    )
    
    # Content
    entry_type: Mapped[str] = Column(String(50), nullable=False)  # prompt|response|parse_report|mutation_report|error
    payload: Mapped[Dict] = Column(JSONB, nullable=False)
    payload_hash: Mapped[Optional[str]] = Column(String(64), nullable=True)  # SHA256
    
    # Timestamp
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    # Relationships
    thread = relationship("LLMThreadModel", back_populates="ledger_entries")
    work_item = relationship("LLMWorkItemModel", back_populates="ledger_entries")
    
    def __repr__(self) -> str:
        return f"<LLMLedgerEntry {self.id} type={self.entry_type}>"
