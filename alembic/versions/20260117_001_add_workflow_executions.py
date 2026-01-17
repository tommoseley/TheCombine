"""add workflow_executions table

Revision ID: 20260117_001
Revises: 20260114_144631
Create Date: 2026-01-17

Minimal persistence for Document Workflow Engine (ADR-039).
Only stores essential state - everything else derived at runtime.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260117_001'
down_revision = '20260114_144631'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_executions',
        sa.Column('execution_id', sa.String(36), primary_key=True),
        sa.Column('current_node_id', sa.String(100), nullable=False),
        sa.Column('execution_log', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('retry_counts', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('gate_outcome', sa.String(50), nullable=True),
        sa.Column('terminal_outcome', sa.String(50), nullable=True),
    )

    # Index for listing active executions (those without terminal_outcome)
    op.create_index(
        'ix_workflow_executions_active',
        'workflow_executions',
        ['terminal_outcome'],
        postgresql_where=sa.text('terminal_outcome IS NULL')
    )


def downgrade() -> None:
    op.drop_index('ix_workflow_executions_active', table_name='workflow_executions')
    op.drop_table('workflow_executions')
