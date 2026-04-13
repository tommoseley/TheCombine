"""Create repair_proposals table (ADR-065).

Revision ID: 20260327_002
Revises: 20260327_001
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "20260327_002"
down_revision = "20260327_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "repair_proposals" in inspect(bind).get_table_names():
        return

    op.create_table(
        "repair_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("component_identifier", sa.String(255), nullable=False),
        sa.Column("trigger_finding", JSONB, nullable=False),
        sa.Column("proposed_payload", JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_by", sa.String(100), nullable=True),
    )

    op.create_index("idx_repair_artifact", "repair_proposals",
                     ["artifact_id", "artifact_type"])
    op.create_index("idx_repair_artifact_status", "repair_proposals",
                     ["artifact_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_repair_artifact_status", table_name="repair_proposals")
    op.drop_index("idx_repair_artifact", table_name="repair_proposals")
    op.drop_table("repair_proposals")
