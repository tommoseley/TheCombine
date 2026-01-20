"""add user_id to workflow_executions and workflow_execution_id to llm_run

Revision ID: 20260118_001
Revises: 20260117_005
Create Date: 2026-01-18

Links LLM runs to their parent workflow execution for bundling.
Tracks user who initiated workflow execution.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260118_001'
down_revision = '20260117_005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id to workflow_executions
    op.add_column(
        'workflow_executions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_workflow_executions_user_id',
        'workflow_executions',
        'users',
        ['user_id'],
        ['user_id'],
        ondelete='SET NULL'
    )

    # Add workflow_execution_id to llm_run for bundling
    op.add_column(
        'llm_run',
        sa.Column('workflow_execution_id', sa.String(36), nullable=True)
    )
    op.create_index(
        'ix_llm_run_workflow_execution_id',
        'llm_run',
        ['workflow_execution_id']
    )


def downgrade() -> None:
    op.drop_index('ix_llm_run_workflow_execution_id', table_name='llm_run')
    op.drop_column('llm_run', 'workflow_execution_id')
    op.drop_constraint('fk_workflow_executions_user_id', 'workflow_executions', type_='foreignkey')
    op.drop_column('workflow_executions', 'user_id')
