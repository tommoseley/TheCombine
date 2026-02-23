"""
SQLAlchemy models for WS Execution Metrics (WS-METRICS-001).

Domain models for Work Statement execution tracking.
These models mirror the tables created by the Alembic migration.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean,
    ForeignKey, Index, CheckConstraint, DECIMAL, text
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from app.core.database import Base


class WSExecution(Base):
    """
    WS execution record.

    One row per Work Statement execution. Tracks phases, tests, files,
    LLM costs, and rework cycles.
    """

    __tablename__ = "ws_executions"

    id: Mapped[str] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )

    ws_id: Mapped[str] = Column(
        String(100),
        nullable=False,
        doc="Work Statement identifier (e.g., WS-DCW-001)"
    )

    wp_id: Mapped[Optional[str]] = Column(
        String(100),
        nullable=True,
        doc="Parent Work Package identifier"
    )

    scope_id: Mapped[Optional[str]] = Column(
        String(100),
        nullable=True,
        doc="Reserved for future tenant/scope isolation (nullable, not enforced in v1)"
    )

    executor: Mapped[str] = Column(
        String(50),
        nullable=False,
        doc="Who executed (claude_code, human, subagent)"
    )

    status: Mapped[str] = Column(
        String(20),
        nullable=False,
        doc="STARTED, COMPLETED, FAILED, HARD_STOP, BLOCKED"
    )

    started_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False
    )

    completed_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    duration_seconds: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True
    )

    phase_metrics: Mapped[Optional[dict]] = Column(
        JSONB,
        nullable=True,
        doc="Per-phase breakdown"
    )

    test_metrics: Mapped[Optional[dict]] = Column(
        JSONB,
        nullable=True,
        doc="Tests written, passing, failing, skipped"
    )

    file_metrics: Mapped[Optional[dict]] = Column(
        JSONB,
        nullable=True,
        doc="Files created, modified, deleted"
    )

    rework_cycles: Mapped[int] = Column(
        Integer,
        nullable=False,
        server_default="0"
    )

    llm_calls: Mapped[int] = Column(
        Integer,
        nullable=False,
        server_default="0"
    )

    llm_tokens_in: Mapped[int] = Column(
        Integer,
        nullable=False,
        server_default="0"
    )

    llm_tokens_out: Mapped[int] = Column(
        Integer,
        nullable=False,
        server_default="0"
    )

    llm_cost_usd: Mapped[Optional[float]] = Column(
        DECIMAL(10, 6),
        nullable=True
    )

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    bug_fixes: Mapped[list["WSBugFix"]] = relationship(
        "WSBugFix",
        back_populates="ws_execution",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_ws_exec_ws_id", "ws_id", text("started_at DESC")),
        Index("idx_ws_exec_wp_id", "wp_id", text("started_at DESC"),
              postgresql_where=text("wp_id IS NOT NULL")),
        Index("idx_ws_exec_status", "status"),
        Index("idx_ws_exec_started", text("started_at DESC")),
        CheckConstraint(
            "status IN ('STARTED', 'COMPLETED', 'FAILED', 'HARD_STOP', 'BLOCKED')",
            name="ck_ws_exec_status"
        ),
        {"comment": "WS execution tracking (WS-METRICS-001)"}
    )


class WSBugFix(Base):
    """
    Bug fix record linked to a WS execution.
    """

    __tablename__ = "ws_bug_fixes"

    id: Mapped[str] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )

    ws_execution_id: Mapped[str] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("ws_executions.id", ondelete="CASCADE"),
        nullable=False
    )

    scope_id: Mapped[Optional[str]] = Column(
        String(100),
        nullable=True,
        doc="Reserved for future tenant/scope isolation (nullable, not enforced in v1)"
    )

    description: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="One-line bug description"
    )

    root_cause: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="One-line root cause"
    )

    test_name: Mapped[str] = Column(
        String(200),
        nullable=False,
        doc="Reproducing test name"
    )

    fix_summary: Mapped[str] = Column(
        Text,
        nullable=False,
        doc="What was changed"
    )

    files_modified: Mapped[Optional[list]] = Column(
        JSONB,
        nullable=True,
        doc="List of files touched"
    )

    autonomous: Mapped[bool] = Column(
        Boolean,
        nullable=False,
        server_default="false",
        doc="True if fixed without human escalation"
    )

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationship
    ws_execution: Mapped["WSExecution"] = relationship(
        "WSExecution",
        back_populates="bug_fixes"
    )

    __table_args__ = (
        Index("idx_ws_bugfix_exec", "ws_execution_id"),
        {"comment": "Bug fix tracking linked to WS executions (WS-METRICS-001)"}
    )
