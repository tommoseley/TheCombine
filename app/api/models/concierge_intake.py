"""
Concierge Intake models for The Combine.

Implements CONCIERGE_PROJECT_INGESTION_CONTRACT v1.0 section 5.1
Storage model for intake sessions and events.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timedelta

from app.core.database import Base


class ConciergeIntakeSession(Base):
    """
    Concierge Intake Session - bounded interaction for project ingestion.
    
    Each session captures user intent through phased conversation (A-F),
    stores all interactions as append-only events, and produces a handoff
    contract that initiates Project Discovery.
    
    Sessions expire after 24 hours and cannot create projects without
    explicit user consent at the consent gate (Phase E).
    """
    
    __tablename__ = "concierge_intake_session"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User (required in v1 - no anonymous sessions)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # State machine (9 states per contract section 6.1)
    state = Column(String(50), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Origin tracking
    origin_route = Column(String(255), nullable=True)
    
    # Project (set only after consent)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    
    # Contract version
    version = Column(String(20), nullable=False, default="1.0")
    
    # Relationships
    events = relationship(
        "ConciergeIntakeEvent",
        back_populates="session",
        order_by="ConciergeIntakeEvent.seq",
        cascade="all, delete-orphan"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default expiry to 24 hours from creation
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "state": self.state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "origin_route": self.origin_route,
            "project_id": str(self.project_id) if self.project_id else None,
            "version": self.version,
            "is_expired": self.is_expired(),
        }
    
    def __repr__(self):
        return f"<ConciergeIntakeSession(id='{self.id}', state='{self.state}', user_id='{self.user_id}')>"


class ConciergeIntakeEvent(Base):
    """
    Concierge Intake Event - append-only event log for session interactions.
    
    Each event captures a single interaction or state change with:
    - Monotonic sequence number (starting at 1)
    - Event type (15 types per contract section 8.1)
    - Structured JSON payload (schemas per contract section 8.2)
    
    Events are immutable after creation and provide complete audit trail.
    """
    
    __tablename__ = "concierge_intake_event"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session reference (cascade delete)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("concierge_intake_session.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Sequence (monotonic, unique per session)
    seq = Column(Integer, nullable=False)
    
    # Event type (from contract enum)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Structured payload (contract-defined schemas)
    payload_json = Column(JSONB, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    session = relationship("ConciergeIntakeSession", back_populates="events")
    
    # Unique constraint on (session_id, seq)
    __table_args__ = (
        Index('idx_concierge_event_session_seq', 'session_id', 'seq', unique=True),
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "seq": self.seq,
            "event_type": self.event_type,
            "payload": self.payload_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<ConciergeIntakeEvent(session_id='{self.session_id}', seq={self.seq}, type='{self.event_type}')>"

