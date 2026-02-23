"""Add WS execution metrics tables

Revision ID: 20260223_001
Revises: 20260221_001
Create Date: 2026-02-23

WS-METRICS-001: ws_executions and ws_bug_fixes tables for
Work Statement execution tracking and metrics collection.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "20260223_001"
down_revision = "20260221_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ws_executions table
    op.create_table(
        "ws_executions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("ws_id", sa.String(100), nullable=False),
        sa.Column("wp_id", sa.String(100), nullable=True),
        sa.Column("scope_id", sa.String(100), nullable=True),
        sa.Column("executor", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("phase_metrics", JSONB, nullable=True),
        sa.Column("test_metrics", JSONB, nullable=True),
        sa.Column("file_metrics", JSONB, nullable=True),
        sa.Column("rework_cycles", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_tokens_in", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_tokens_out", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_cost_usd", sa.DECIMAL(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('STARTED', 'COMPLETED', 'FAILED', 'HARD_STOP', 'BLOCKED')",
            name="ck_ws_exec_status"
        ),
        comment="WS execution tracking (WS-METRICS-001)",
    )

    op.create_index("idx_ws_exec_ws_id", "ws_executions", ["ws_id", sa.text("started_at DESC")])
    op.create_index(
        "idx_ws_exec_wp_id", "ws_executions", ["wp_id", sa.text("started_at DESC")],
        postgresql_where=sa.text("wp_id IS NOT NULL")
    )
    op.create_index("idx_ws_exec_status", "ws_executions", ["status"])
    op.create_index("idx_ws_exec_started", "ws_executions", [sa.text("started_at DESC")])

    # ws_bug_fixes table
    op.create_table(
        "ws_bug_fixes",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("ws_execution_id", UUID(as_uuid=True), sa.ForeignKey("ws_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_id", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("root_cause", sa.Text, nullable=False),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("fix_summary", sa.Text, nullable=False),
        sa.Column("files_modified", JSONB, nullable=True),
        sa.Column("autonomous", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        comment="Bug fix tracking linked to WS executions (WS-METRICS-001)",
    )

    op.create_index("idx_ws_bugfix_exec", "ws_bug_fixes", ["ws_execution_id"])


def downgrade() -> None:
    op.drop_table("ws_bug_fixes")
    op.drop_table("ws_executions")
