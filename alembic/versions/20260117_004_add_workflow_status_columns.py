"""add status and pause columns to workflow_executions

Revision ID: 20260117_004
Revises: 20260117_003
Create Date: 2026-01-17

The original minimal persistence design derived status from
terminal_outcome/gate_outcome, but this fails for PAUSED state
during concierge conversations (before any gate is reached).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260117_004'
down_revision = '20260117_003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column (default to 'running' for existing rows)
    op.add_column(
        'workflow_executions',
        sa.Column('status', sa.String(20), nullable=False, server_default='running')
    )

    # Add pause state columns
    op.add_column(
        'workflow_executions',
        sa.Column('pending_user_input', sa.Boolean, nullable=False, server_default='false')
    )
    op.add_column(
        'workflow_executions',
        sa.Column('pending_prompt', sa.Text, nullable=True)
    )
    op.add_column(
        'workflow_executions',
        sa.Column('pending_choices', postgresql.JSONB, nullable=True)
    )

    # Add thread_id for conversation persistence
    op.add_column(
        'workflow_executions',
        sa.Column('thread_id', sa.String(36), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('workflow_executions', 'thread_id')
    op.drop_column('workflow_executions', 'pending_choices')
    op.drop_column('workflow_executions', 'pending_prompt')
    op.drop_column('workflow_executions', 'pending_user_input')
    op.drop_column('workflow_executions', 'status')
