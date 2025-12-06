"""
PipelinePromptUsage model for audit trail of prompt usage.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Integer, Numeric  # Add Integer, Numeric
from sqlalchemy.orm import relationship
from app.orchestrator_api.persistence.database import Base

class PipelinePromptUsage(Base):
    """
    Audit trail of which prompt versions were used in which pipelines.
    
    Tracks prompt usage for compliance, rollback capability,
    and prompt performance analysis.
    """
    __tablename__ = "pipeline_prompt_usage"
    
    id = Column(String(64), primary_key=True)  # Format: ppu_<ulid>
    pipeline_id = Column(String(64), ForeignKey("pipelines.pipeline_id"), nullable=False, index=True)
    prompt_id = Column(String(64), ForeignKey("role_prompts.id"), nullable=False, index=True)
    role_name = Column(String(64), nullable=False)
    phase_name = Column(String(64), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # NEW: Token tracking columns
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 6), default=0.0)
    model = Column(String(64), default="claude-sonnet-4-20250514")
    execution_time_ms = Column(Integer, default=0)

    # Relationships

    pipeline = relationship("Pipeline", back_populates="prompt_usages")
    prompt = relationship("RolePrompt", back_populates="pipeline_usages")
    
    # Composite index for queries by role and phase
    __table_args__ = (
        Index('idx_prompt_usage_role_phase', 'role_name', 'phase_name'),
    )
    
    def __repr__(self):
        return f"<PipelinePromptUsage(pipeline={self.pipeline_id}, role={self.role_name}, phase={self.phase_name})>"