"""
WorkflowExecution model for The Combine.

Minimal persistence for Document Workflow Engine (ADR-039).
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.core.database import Base


class WorkflowExecution(Base):
    """
    Workflow execution state persistence.
    
    Stores minimal state - everything else derived at runtime.
    """
    
    __tablename__ = "workflow_executions"
    
    # Primary key
    execution_id = Column(String(36), primary_key=True)
    
    # Document reference
    document_id = Column(String(255), nullable=True)
    document_type = Column(String(100), nullable=True)
    workflow_id = Column(String(100), nullable=True)
    
    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    
    # Current state
    current_node_id = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default='running')
    
    # Execution history
    execution_log = Column(JSONB, nullable=False, default=list)
    retry_counts = Column(JSONB, nullable=False, default=dict)
    
    # Outcomes
    gate_outcome = Column(String(50), nullable=True)
    terminal_outcome = Column(String(50), nullable=True)
    
    # Pause state
    pending_user_input = Column(Boolean, nullable=False, default=False)
    pending_user_input_rendered = Column("pending_prompt", Text, nullable=True)  # DB column: pending_prompt
    pending_choices = Column(JSONB, nullable=True)
    pending_user_input_payload = Column(JSONB, nullable=True)
    pending_user_input_schema_ref = Column(String(255), nullable=True)
    
    # Conversation thread
    thread_id = Column(String(36), nullable=True)
    
    # Context state (ADR-040)
    context_state = Column(JSONB, nullable=True)
    
    def to_dict(self):
        return {
            "execution_id": self.execution_id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "workflow_id": self.workflow_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "current_node_id": self.current_node_id,
            "status": self.status,
            "execution_log": self.execution_log,
            "retry_counts": self.retry_counts,
            "gate_outcome": self.gate_outcome,
            "terminal_outcome": self.terminal_outcome,
            "pending_user_input": self.pending_user_input,
            "pending_user_input_rendered": self.pending_user_input_rendered,
            "pending_choices": self.pending_choices,
            "pending_user_input_payload": self.pending_user_input_payload,
            "pending_user_input_schema_ref": self.pending_user_input_schema_ref,
            "thread_id": self.thread_id,
            "context_state": self.context_state,
        }