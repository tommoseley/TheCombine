"""
SQLAlchemy models for LLM Execution Logging (ADR-010).

Domain models for execution telemetry and operational data.
These models mirror the tables created by the Alembic migration.
The LLMExecutionLogger service uses raw SQL, but these models
enable SQLAlchemy's Base.metadata.create_all() to work in tests.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    String,
    Column, String, Integer, Text, DateTime, Boolean,
    ForeignKey, Index, CheckConstraint, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from app.core.database import Base


class LLMContent(Base):
    """
    Content storage table for LLM inputs/outputs.
    
    Stores raw content with deduplication via content_hash.
    Referenced by input_ref and output_ref tables.
    """
    
    __tablename__ = "llm_content"
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    content_hash: Mapped[str] = Column(
        Text,
        nullable=False,
        unique=True,
        doc="SHA-256 hash for deduplication"
    )
    
    content_text: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="Actual content"
    )
    
    content_size: Mapped[int] = Column(
        Integer,
        nullable=False,
        doc="Size in bytes (UTF-8 encoded)"
    )
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    accessed_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Updated on each access for cache metrics"
    )
    
    __table_args__ = (
        Index("idx_llm_content_hash", "content_hash"),
        Index("idx_llm_content_accessed", "accessed_at"),
        {"comment": "Content storage for LLM inputs/outputs (ADR-010)"}
    )


class LLMRun(Base):
    """
    Main execution record for LLM invocations.
    
    One row per LLM call. Tracks model, prompt, status, tokens, cost.
    Links to project (if applicable) and references inputs/outputs.
    """
    
    __tablename__ = "llm_run"
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    correlation_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        doc="Request trace ID (propagated from HTTP layer)"
    )
    
    project_id: Mapped[Optional[UUID]] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        doc="Project this run belongs to (if applicable)"
    )
    
    artifact_type: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="Document type: discovery, epic, architecture, etc."
    )
    
    role: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="Role: PM_MENTOR, BA_MENTOR, ARCHITECT_MENTOR, etc."
    )
    
    model_provider: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="Provider: anthropic, openai"
    )
    
    model_name: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="Exact model: claude-sonnet-4-20250514"
    )
    
    prompt_id: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="Stable identifier from prompt registry (e.g., pm/preliminary)"
    )
    
    prompt_version: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="Human-readable version (e.g., 1.2.3)"
    )
    
    effective_prompt_hash: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="SHA-256 hash of actual prompt sent to LLM"
    )
    
    schema_version: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="Output schema version if applicable"
    )
    
    # ADR-031: Schema Registry tracking
    schema_id: Mapped[Optional[str]] = Column(
        String(100),
        nullable=True,
        doc="Root schema identifier per ADR-031 (e.g., EpicBacklogV2)"
    )
    
    schema_bundle_hash: Mapped[Optional[str]] = Column(
        String(64),
        nullable=True,
        doc="SHA256 hash of resolved schema bundle per ADR-031"
    )
    
    status: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="IN_PROGRESS, SUCCESS, FAILED, PARTIAL, CANCELLED"
    )
    
    started_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False
    )
    
    ended_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    input_tokens: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True
    )
    
    output_tokens: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True
    )
    
    total_tokens: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True
    )
    
    cost_usd: Mapped[Optional[float]] = Column(
        DECIMAL(10, 6),
        nullable=True,
        doc="Computed cost (nullable in MVP)"
    )
    
    primary_error_code: Mapped[Optional[str]] = Column(
        Text,
        nullable=True
    )
    
    primary_error_message: Mapped[Optional[str]] = Column(
        Text,
        nullable=True
    )
    
    error_count: Mapped[int] = Column(
        Integer,
        nullable=False,
        server_default="0"
    )
    
    run_metadata: Mapped[Optional[dict]] = Column(
        "metadata",  # â† Column name in database
        JSONB,
        nullable=True,
        doc="retry_count, is_replay, etc."
    )
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    input_refs: Mapped[list["LLMRunInputRef"]] = relationship(
        "LLMRunInputRef",
        back_populates="llm_run",
        cascade="all, delete-orphan"
    )
    
    output_refs: Mapped[list["LLMRunOutputRef"]] = relationship(
        "LLMRunOutputRef",
        back_populates="llm_run",
        cascade="all, delete-orphan"
    )
    
    errors: Mapped[list["LLMRunError"]] = relationship(
        "LLMRunError",
        back_populates="llm_run",
        cascade="all, delete-orphan"
    )
    
    tool_calls: Mapped[list["LLMRunToolCall"]] = relationship(
        "LLMRunToolCall",
        back_populates="llm_run",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_llm_run_correlation", "correlation_id"),
        Index("idx_llm_run_project_time", "project_id", func.text("started_at DESC"),
              postgresql_where=func.text("project_id IS NOT NULL")),
        Index("idx_llm_run_role_time", "role", func.text("started_at DESC")),
        Index("idx_llm_run_status", "status"),
        Index("idx_llm_run_started", func.text("started_at DESC")),
        {"comment": "LLM execution records (ADR-010)"}
    )


class LLMRunInputRef(Base):
    """
    Input references for LLM runs.
    
    Links to content via content_ref (db://llm_content/{uuid}).
    Multiple inputs per run (role_prompt, user_prompt, context_doc, etc.).
    """
    
    __tablename__ = "llm_run_input_ref"
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    llm_run_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_run.id", ondelete="CASCADE"),
        nullable=False
    )
    
    kind: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="system_prompt, role_prompt, user_prompt, context_doc, schema, tools"
    )
    
    content_ref: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="db://llm_content/{uuid}"
    )
    
    content_hash: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="SHA-256 for verification"
    )
    
    content_redacted: Mapped[bool] = Column(
        Boolean,
        nullable=False,
        server_default="false",
        doc="Manual redaction flag (PII/sensitive data)"
    )
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationship
    llm_run: Mapped["LLMRun"] = relationship(
        "LLMRun",
        back_populates="input_refs"
    )
    
    __table_args__ = (
        Index("idx_llm_input_ref_run", "llm_run_id"),
        Index("idx_llm_input_ref_kind", "llm_run_id", "kind"),
        {"comment": "LLM input references by content_ref (ADR-010)"}
    )


class LLMRunOutputRef(Base):
    """
    Output references for LLM runs.
    
    Links to content via content_ref.
    Tracks parse/validation status.
    """
    
    __tablename__ = "llm_run_output_ref"
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    llm_run_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_run.id", ondelete="CASCADE"),
        nullable=False
    )
    
    kind: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="raw_text, json, tool_calls, qa_report"
    )
    
    content_ref: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="db://llm_content/{uuid}"
    )
    
    content_hash: Mapped[str] = Column(
        Text,
        nullable=False
    )
    
    parse_status: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="PARSED, FAILED"
    )
    
    validation_status: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="PASSED, FAILED"
    )
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationship
    llm_run: Mapped["LLMRun"] = relationship(
        "LLMRun",
        back_populates="output_refs"
    )
    
    __table_args__ = (
        Index("idx_llm_output_ref_run", "llm_run_id"),
        Index("idx_llm_output_ref_kind", "llm_run_id", "kind"),
        {"comment": "LLM output references by content_ref (ADR-010)"}
    )


class LLMRunError(Base):
    """
    Error tracking for LLM runs.
    
    Many-per-run model with sequence numbers.
    Captures stage, severity, and details.
    """
    
    __tablename__ = "llm_run_error"
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    llm_run_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_run.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: Mapped[int] = Column(
        Integer,
        nullable=False,
        doc="Monotonic sequence within run"
    )
    
    stage: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="PROMPT_BUILD, MODEL_CALL, TOOL_CALL, PARSE, VALIDATE, QA_GATE, PERSIST"
    )
    
    severity: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="INFO, WARN, ERROR, FATAL"
    )
    
    error_code: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="Canonical error codes"
    )
    
    message: Mapped[str] = Column(
        Text,
        nullable=False
    )
    
    details: Mapped[Optional[dict]] = Column(
        JSONB,
        nullable=True,
        doc="Stack traces, validation errors, provider IDs"
    )
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationship
    llm_run: Mapped["LLMRun"] = relationship(
        "LLMRun",
        back_populates="errors"
    )
    
    __table_args__ = (
        Index("idx_llm_error_run", "llm_run_id"),
        Index("idx_llm_error_stage", "stage"),
        Index("idx_llm_error_severity", "severity"),
        CheckConstraint("sequence > 0", name="ck_llm_run_error_sequence_positive"),
        {"comment": "LLM execution errors (many-per-run model, ADR-010)"}
    )


class LLMRunToolCall(Base):
    """
    Tool call tracking for LLM runs.
    
    DEFERRED in MVP - table created but unused until tools are added.
    """
    
    __tablename__ = "llm_run_tool_call"
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    llm_run_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_run.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: Mapped[int] = Column(
        Integer,
        nullable=False,
        doc="Order in LLM response"
    )
    
    tool_name: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="web_search, read_document, etc."
    )
    
    started_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False
    )
    
    ended_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    status: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="PENDING, SUCCESS, FAILED"
    )
    
    input_ref: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="db://llm_content/{uuid}"
    )
    
    output_ref: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="db://llm_content/{uuid}"
    )
    
    error_ref: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="db://llm_content/{uuid}"
    )
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationship
    llm_run: Mapped["LLMRun"] = relationship(
        "LLMRun",
        back_populates="tool_calls"
    )
    
    __table_args__ = (
        Index("idx_llm_tool_call_run", "llm_run_id"),
        Index("idx_llm_tool_call_name", "tool_name"),
        Index("idx_llm_tool_call_status", "status"),
        {"comment": "Tool call tracking (ADR-010) - UNUSED IN MVP, reserved for future"}
    )
