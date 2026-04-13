"""Create project_artifacts table (ADR-068).

Revision ID: 20260402_001
Revises: 20260327_002
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "20260402_001"
down_revision = "20260327_002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False, server_default="mockup"),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("file_content", sa.LargeBinary, nullable=False),
        sa.Column("thumbnail_content", sa.LargeBinary, nullable=True),
        sa.Column("uploaded_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
    )
    op.create_index("ix_project_artifacts_type", "project_artifacts", ["artifact_type"])


def downgrade():
    op.drop_index("ix_project_artifacts_type")
    op.drop_table("project_artifacts")
