"""Add archive fields to projects table

Revision ID: 001_add_archive
Revises: <previous_revision>
Create Date: 2025-01-01 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251231_001'
down_revision = None  # Update with your last migration
branch_labels = None
depends_on = None


def upgrade():
    # Add archive columns
    op.add_column('projects', sa.Column('archived_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('projects', sa.Column('archived_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('archived_reason', sa.Text(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_projects_archived_by', 
        'projects', 
        'users', 
        ['archived_by'], 
        ['user_id'],
        ondelete='SET NULL'
    )
    
    # Add partial index for archived projects
    op.create_index(
        'idx_projects_archived', 
        'projects', 
        ['archived_at'],
        unique=False,
        postgresql_where=sa.text('archived_at IS NOT NULL')
    )
    
    # Add comments
    op.execute("""
        COMMENT ON COLUMN projects.archived_at IS 
        'Timestamp when project was archived. NULL = active, NOT NULL = archived.'
    """)
    op.execute("""
        COMMENT ON COLUMN projects.archived_by IS 
        'User who archived the project. NULL for system-initiated archives.'
    """)
    op.execute("""
        COMMENT ON COLUMN projects.archived_reason IS 
        'Current archive reason. Cleared on unarchive; history in project_audit.'
    """)


def downgrade():
    op.drop_index('idx_projects_archived', table_name='projects')
    op.drop_constraint('fk_projects_archived_by', 'projects', type_='foreignkey')
    op.drop_column('projects', 'archived_reason')
    op.drop_column('projects', 'archived_by')
    op.drop_column('projects', 'archived_at')