"""
LLM execution logging models for The Combine (ADR-010).

Content storage, execution records, input/output refs, and errors.
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Numeric, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.core.database import Base


class LLMContent(Base):
    """Content storage for LLM inputs/outputs (ADR-010)."""
    
    __tablename__ = "llm_content"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_hash = Column(Text, nullable=False, unique=True, index=True)
    content_text = Column(Text, nullable=False)
    content_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    accessed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LLMRun(Base):
    """LLM execution records (ADR-010)."""
    
    __tablename__ = "llm_run"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correlation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    artifact_type = Column(Text, nullable=True)
    role = Column(Text, nullable=False)
    model_provider = Column(Text, nullable=False)
    model_name = Column(Text, nullable=False)
    prompt_id = Column(Text, nullable=False)
    prompt_version = Column(Text, nullable=False)
    effective_prompt_hash = Column(Text, nullable=False)
    schema_version = Column(Text, nullable=True)
    schema_id = Column(Text, nullable=True)
    schema_bundle_hash = Column(Text, nullable=True)
    status = Column(Text, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(precision=10, scale=6), nullable=True)
    primary_error_code = Column(Text, nullable=True)
    primary_error_message = Column(Text, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    run_metadata = Column("metadata", JSONB, nullable=True)  # "metadata" is reserved in SQLAlchemy
    workflow_execution_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LLMRunInputRef(Base):
    """LLM input references by content_ref (ADR-010)."""
    
    __tablename__ = "llm_run_input_ref"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    llm_run_id = Column(UUID(as_uuid=True), ForeignKey('llm_run.id', ondelete='CASCADE'), nullable=False, index=True)
    kind = Column(Text, nullable=False)
    content_ref = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    content_redacted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LLMRunOutputRef(Base):
    """LLM output references by content_ref (ADR-010)."""
    
    __tablename__ = "llm_run_output_ref"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    llm_run_id = Column(UUID(as_uuid=True), ForeignKey('llm_run.id', ondelete='CASCADE'), nullable=False, index=True)
    kind = Column(Text, nullable=False)
    content_ref = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    parse_status = Column(Text, nullable=True)
    validation_status = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LLMRunError(Base):
    """LLM execution errors (ADR-010)."""
    
    __tablename__ = "llm_run_error"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    llm_run_id = Column(UUID(as_uuid=True), ForeignKey('llm_run.id', ondelete='CASCADE'), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    stage = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    error_code = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())