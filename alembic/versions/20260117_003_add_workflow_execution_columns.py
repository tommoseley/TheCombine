"""add document_id, document_type, workflow_id to workflow_executions

Revision ID: 20260117_003
Revises: 20260117_002
Create Date: 2026-01-17

These columns were previously derived from execution_log metadata,
but that fails when execution_log is empty (initial save).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260117_003'
down_revision = '20260117_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns with defaults for existing rows
    op.add_column(
        'workflow_executions',
        sa.Column('document_id', sa.String(255), nullable=True)
    )
    op.add_column(
        'workflow_executions',
        sa.Column('document_type', sa.String(100), nullable=True)
    )
    op.add_column(
        'workflow_executions',
        sa.Column('workflow_id', sa.String(100), nullable=True)
    )

    # Add index for document lookup
    op.create_index(
        'ix_workflow_executions_document',
        'workflow_executions',
        ['document_id', 'workflow_id']
    )


def downgrade() -> None:
    op.drop_index('ix_workflow_executions_document', table_name='workflow_executions')
    op.drop_column('workflow_executions', 'workflow_id')
    op.drop_column('workflow_executions', 'document_type')
    op.drop_column('workflow_executions', 'document_id')
