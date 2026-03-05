"""Drop legacy instance_id-based unique indexes superseded by idx_documents_latest_display

Revision ID: 20260305_001
Revises: 20260304_001
Create Date: 2026-03-05

Migration 20260216_002 created two partial unique indexes:
- idx_documents_latest_single: (space_type, space_id, doc_type_id) WHERE is_latest AND instance_id IS NULL
- idx_documents_latest_multi: (space_type, space_id, doc_type_id, instance_id) WHERE is_latest AND instance_id IS NOT NULL

Migration 20260304_001 (ADR-055) created idx_documents_latest_display:
- (space_type, space_id, doc_type_id, display_id) WHERE is_latest = true

The new display_id index fully supersedes both legacy indexes. The legacy indexes
now cause IntegrityError on multi-instance doc types (e.g., work_package_candidate)
when instance_id is NULL (because WB creation paths no longer set instance_id).
"""

import sqlalchemy as sa
from alembic import op

revision = '20260305_001'
down_revision = '20260304_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('idx_documents_latest_single', table_name='documents')
    op.drop_index('idx_documents_latest_multi', table_name='documents')


def downgrade() -> None:
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
