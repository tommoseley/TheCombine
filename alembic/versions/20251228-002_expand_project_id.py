"""Expand project_id column to VARCHAR(50)

Revision ID: 20251228_expand_project_id
Revises: 20251228_add_project_ownership
Create Date: 2025-12-28 23:10:00

Expand project_id from VARCHAR(8) to VARCHAR(50) to allow for more 
descriptive project identifiers.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251228_002'
down_revision = '20251228_001'  # Update if different
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Expand project_id to VARCHAR(50)."""
    
    # Expand the column
    op.alter_column(
        'projects',
        'project_id',
        type_=sa.String(50),
        existing_type=sa.String(8),
        existing_nullable=True  # Adjust if your column is NOT NULL
    )


def downgrade() -> None:
    """Revert project_id back to VARCHAR(8)."""
    
    # Warning: This will truncate any project_ids longer than 8 characters!
    op.alter_column(
        'projects',
        'project_id',
        type_=sa.String(8),
        existing_type=sa.String(50),
        existing_nullable=True
    )