"""Add instance_id to documents for multi-instance document types

Revision ID: 20260216_002
Revises: 20260216_001
Create Date: 2026-02-16

Per WS-INSTANCE-ID-001 Phase 1.

The existing idx_documents_unique_latest constraint enforces one is_latest=TRUE
document per (space_type, space_id, doc_type_id). This blocks multi-instance
types like epic/feature where a project needs multiple latest documents of
the same type.

This migration:
1. Adds instance_id column to documents (stable domain identifier for multi-instance types)
2. Replaces the single unique index with two partial indexes:
   - idx_documents_latest_single: for single-instance types (instance_id IS NULL)
   - idx_documents_latest_multi: for multi-instance types (instance_id IS NOT NULL)
3. Adds cardinality and instance_key columns to document_types
4. Sets cardinality metadata for epic and feature types
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260216_002'
down_revision: Union[str, None] = '20260216_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add instance_id column to documents
    op.add_column('documents', sa.Column('instance_id', sa.String(200), nullable=True))

    # 2. Create index on instance_id for query performance
    op.create_index(
        'idx_documents_instance_id',
        'documents',
        ['instance_id'],
        postgresql_where=sa.text('instance_id IS NOT NULL'),
    )

    # 3. Drop the existing unique index
    op.drop_index('idx_documents_unique_latest', table_name='documents')

    # 4. Create two replacement partial unique indexes
    op.create_index(
        'idx_documents_latest_single',
        'documents',
        ['space_type', 'space_id', 'doc_type_id'],
        unique=True,
        postgresql_where=sa.text('is_latest = true AND instance_id IS NULL'),
    )

    op.create_index(
        'idx_documents_latest_multi',
        'documents',
        ['space_type', 'space_id', 'doc_type_id', 'instance_id'],
        unique=True,
        postgresql_where=sa.text('is_latest = true AND instance_id IS NOT NULL'),
    )

    # 5. Add cardinality and instance_key columns to document_types
    op.add_column('document_types', sa.Column(
        'cardinality', sa.String(20), nullable=False, server_default='single',
    ))
    op.add_column('document_types', sa.Column(
        'instance_key', sa.String(100), nullable=True,
    ))

    # 6. Set cardinality metadata for multi-instance types
    op.execute("""
        UPDATE document_types SET cardinality = 'multi', instance_key = 'epic_id'
        WHERE doc_type_id = 'epic'
    """)
    op.execute("""
        UPDATE document_types SET cardinality = 'multi', instance_key = 'feature_id'
        WHERE doc_type_id = 'feature'
    """)


def downgrade() -> None:
    # 1. Reset cardinality on epic/feature rows
    op.execute("""
        UPDATE document_types SET cardinality = 'single', instance_key = NULL
        WHERE doc_type_id IN ('epic', 'feature')
    """)

    # 2. Drop cardinality and instance_key columns from document_types
    op.drop_column('document_types', 'instance_key')
    op.drop_column('document_types', 'cardinality')

    # 3. Drop new indexes
    op.drop_index('idx_documents_latest_multi', table_name='documents')
    op.drop_index('idx_documents_latest_single', table_name='documents')

    # 4. Recreate original unique index
    op.create_index(
        'idx_documents_unique_latest',
        'documents',
        ['space_type', 'space_id', 'doc_type_id'],
        unique=True,
        postgresql_where=sa.text('is_latest = true'),
    )

    # 5. Drop instance_id index and column
    op.drop_index('idx_documents_instance_id', table_name='documents')
    op.drop_column('documents', 'instance_id')
