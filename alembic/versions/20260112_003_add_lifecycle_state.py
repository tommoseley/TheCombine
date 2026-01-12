"""Add lifecycle_state to documents (ADR-036)

Revision ID: 20260112_003
Revises: 20260112_002
Create Date: 2026-01-12

Phase 3 of WS-DOCUMENT-SYSTEM-CLEANUP:
Implements ADR-036 document lifecycle states.

States: generating, partial, complete, stale
(missing is implicit - document doesn't exist)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260112_003'
down_revision = '20260112_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for lifecycle states
    lifecycle_state_enum = postgresql.ENUM(
        'generating', 'partial', 'complete', 'stale',
        name='document_lifecycle_state'
    )
    lifecycle_state_enum.create(op.get_bind())
    
    # Add lifecycle_state column - defaults to 'complete' for existing docs
    op.add_column(
        'documents',
        sa.Column(
            'lifecycle_state',
            lifecycle_state_enum,
            nullable=False,
            server_default='complete',
            comment='ADR-036 lifecycle state: generating, partial, complete, stale'
        )
    )
    
    # Add state_changed_at timestamp
    op.add_column(
        'documents',
        sa.Column(
            'state_changed_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
            comment='Timestamp of last lifecycle state change'
        )
    )
    
    # Index for lifecycle_state queries
    op.create_index(
        'idx_documents_lifecycle_state',
        'documents',
        ['lifecycle_state']
    )
    
    # Backfill: Mark documents with is_stale=True as 'stale' lifecycle_state
    op.execute("""
        UPDATE documents 
        SET lifecycle_state = 'stale'
        WHERE is_stale = true
    """)


def downgrade() -> None:
    op.drop_index('idx_documents_lifecycle_state', table_name='documents')
    op.drop_column('documents', 'state_changed_at')
    op.drop_column('documents', 'lifecycle_state')
    
    # Drop enum type
    lifecycle_state_enum = postgresql.ENUM(
        'generating', 'partial', 'complete', 'stale',
        name='document_lifecycle_state'
    )
    lifecycle_state_enum.drop(op.get_bind())