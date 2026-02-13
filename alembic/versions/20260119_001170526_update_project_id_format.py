"""Update project_id format to support LIR-001 pattern.

Revision ID: update_project_id_format
Revises: 
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260119_001' 
down_revision = '20260118_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the constraint first (before changing column type)
    op.drop_constraint('projects_project_id_format', 'projects', type_='check')
    
    # Increase column width to 20 to handle any existing data
    op.alter_column('projects', 'project_id',
                    existing_type=sa.String(8),
                    type_=sa.String(20),
                    existing_nullable=False)
    
    # Note: Not adding the new constraint yet because existing data may not match
    # The application code will enforce the new format for new projects
    # A separate data migration can clean up old projects if needed


def downgrade() -> None:
    # Revert column width - this may fail if data exceeds 8 chars
    op.alter_column('projects', 'project_id',
                    existing_type=sa.String(20),
                    type_=sa.String(8),
                    existing_nullable=False)
    
    # Re-add old constraint
    op.create_check_constraint(
        'projects_project_id_format',
        'projects',
        "project_id ~ '^[A-Z]{2,8}$'"
    )
