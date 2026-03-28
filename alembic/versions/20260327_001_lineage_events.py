"""Create lineage_events table (ADR-063).

Revision ID: 20260327_001
Revises: 20260323_001
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "20260327_001"
down_revision = "20260323_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lineage_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("rewind_to_stage", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("affected_document_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("regeneration_event_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_index("idx_lineage_project", "lineage_events", ["project_id"])
    op.create_index("idx_lineage_project_type", "lineage_events", ["project_id", "event_type"])


def downgrade() -> None:
    op.drop_index("idx_lineage_project_type", table_name="lineage_events")
    op.drop_index("idx_lineage_project", table_name="lineage_events")
    op.drop_table("lineage_events")
