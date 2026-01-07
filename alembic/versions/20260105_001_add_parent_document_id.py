"""Add parent_document_id for document ownership (ADR-011-Part-2)

Revision ID: 20260105_001
Revises: 20251231_004_add_llm_execution_logging
Create Date: 2026-01-05

Implements ADR-011-Part-2 document ownership model:
- Adds parent_document_id column for ownership hierarchy
- ON DELETE RESTRICT prevents orphaning
- Partial index for efficient child queries
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260105_001'
down_revision = '20251231_004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add parent_document_id column (nullable for existing/root documents)
    op.add_column(
        'documents',
        sa.Column(
            'parent_document_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Parent document for ownership hierarchy (ADR-011-Part-2)'
        )
    )
    
    # Add foreign key with RESTRICT to prevent orphaning
    op.create_foreign_key(
        'fk_documents_parent',
        'documents',
        'documents',
        ['parent_document_id'],
        ['id'],
        ondelete='RESTRICT'
    )
    
    # Partial index for efficient child queries (only index non-null values)
    op.create_index(
        'idx_documents_parent',
        'documents',
        ['parent_document_id'],
        postgresql_where=sa.text('parent_document_id IS NOT NULL')
    )


def downgrade() -> None:
    op.drop_index('idx_documents_parent', table_name='documents')
    op.drop_constraint('fk_documents_parent', 'documents', type_='foreignkey')
    op.drop_column('documents', 'parent_document_id')