"""add project_id to workflow_executions

Revision ID: 20260126_001
Revises: 20260124_001
Create Date: 2026-01-26

Adds project_id for efficient querying of interrupts and production line status.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_001'
down_revision = '20260124_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'workflow_executions',
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_workflow_executions_project_id',
        'workflow_executions',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='CASCADE'
    )
    # Index for project-scoped queries (interrupts, production status)
    op.create_index(
        'ix_workflow_executions_project_id',
        'workflow_executions',
        ['project_id']
    )


def downgrade() -> None:
    op.drop_index('ix_workflow_executions_project_id', table_name='workflow_executions')
    op.drop_constraint('fk_workflow_executions_project_id', 'workflow_executions', type_='foreignkey')
    op.drop_column('workflow_executions', 'project_id')
