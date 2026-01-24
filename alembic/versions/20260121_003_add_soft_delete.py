"""Add soft delete columns to projects table.

Revision ID: 20260121_003
Revises: 20260121_002
Create Date: 2026-01-21

WS-SOFT-DELETE-001: Soft delete for archived projects.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '20260121_003'
down_revision = '20260121_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add soft delete columns."""
    op.add_column('projects', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('projects', sa.Column('deleted_by', UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('deleted_reason', sa.Text(), nullable=True))
    
    # Index for filtering deleted projects
    op.create_index('idx_projects_deleted_at', 'projects', ['deleted_at'])


def downgrade() -> None:
    """Remove soft delete columns."""
    op.drop_index('idx_projects_deleted_at', table_name='projects')
    op.drop_column('projects', 'deleted_reason')
    op.drop_column('projects', 'deleted_by')
    op.drop_column('projects', 'deleted_at')