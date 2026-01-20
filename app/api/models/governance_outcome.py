"""
GovernanceOutcome model for The Combine.

Records governance layer outcomes for Intake Gate and other gates.
Separate from workflow_executions to maintain governance/execution separation.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class GovernanceOutcome(Base):
    """
    Records governance outcomes for audit (ADR-037).
    
    Maintains separation between governance (qualified, not_ready, etc.)
    and execution (stabilized, blocked, abandoned) vocabularies.
    """
    
    __tablename__ = "governance_outcomes"
    
    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    execution_id = Column(String(36), nullable=False, index=True)
    document_id = Column(String(100), nullable=False)
    document_type = Column(String(100), nullable=False)
    workflow_id = Column(String(100), nullable=False)
    thread_id = Column(String(36), nullable=True)
    
    # Governance outcome (ADR-025 vocabulary)
    gate_type = Column(String(50), nullable=False)
    gate_outcome = Column(String(50), nullable=False)
    
    # Execution outcome (ADR-039 vocabulary)
    terminal_outcome = Column(String(50), nullable=False)
    
    # Routing decision
    ready_for = Column(String(100), nullable=True)
    routing_rationale = Column(Text, nullable=True)
    
    # Audit metadata
    options_offered = Column(JSONB, nullable=True)
    option_selected = Column(String(100), nullable=True)
    selection_method = Column(String(50), nullable=True)
    
    # Context snapshot
    retry_count = Column(Integer, nullable=True)
    circuit_breaker_active = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Audit fields
    recorded_by = Column(String(100), nullable=True)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "execution_id": self.execution_id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "workflow_id": self.workflow_id,
            "thread_id": self.thread_id,
            "gate_type": self.gate_type,
            "gate_outcome": self.gate_outcome,
            "terminal_outcome": self.terminal_outcome,
            "ready_for": self.ready_for,
            "routing_rationale": self.routing_rationale,
            "options_offered": self.options_offered,
            "option_selected": self.option_selected,
            "selection_method": self.selection_method,
            "retry_count": self.retry_count,
            "circuit_breaker_active": self.circuit_breaker_active,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "recorded_by": self.recorded_by,
        }