"""Document Identity Standard - add display_id to documents, display_prefix to document_types

Revision ID: 20260304_001
Revises: 20260301_001
Create Date: 2026-03-04

Per WS-ID-001 (ADR-055: Document Identity Standard).

This migration:
1. Adds display_id VARCHAR(20) to documents (human-readable identity in {TYPE}-{NNN} format)
2. Adds display_prefix VARCHAR(4) to document_types (authoritative prefix registry)
3. Populates display_prefix for all 14 registered doc types
4. Drops instance_key column from document_types (replaced by display_prefix)
5. Creates idx_documents_latest_display unique index
6. instance_id is NOT modified (different semantic on workflow_instances)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260304_001'
down_revision: Union[str, None] = '20260301_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add display_id to documents (nullable first for existing rows)
    op.add_column('documents', sa.Column('display_id', sa.String(20), nullable=True))

    # 2. Backfill existing rows with temporary values
    op.execute("UPDATE documents SET display_id = 'LEGACY-' || LEFT(id::text, 8) WHERE display_id IS NULL")

    # 3. Make display_id NOT NULL
    op.alter_column('documents', 'display_id', nullable=False)

    # 4. Create unique index for display_id lookups
    op.create_index(
        'idx_documents_latest_display',
        'documents',
        ['space_type', 'space_id', 'doc_type_id', 'display_id'],
        unique=True,
        postgresql_where=sa.text('is_latest = true'),
    )

    # 5. Add display_prefix to document_types (nullable first)
    op.add_column('document_types', sa.Column('display_prefix', sa.String(4), nullable=True))

    # 6. Populate display_prefix for all registered doc types
    prefix_map = {
        'project_discovery': 'PD',
        'technical_architecture': 'TA',
        'implementation_plan': 'IP',
        'implementation_plan_primary': 'IPP',
        'concierge_intake': 'CI',
        'intent_packet': 'INT',
        'execution_plan': 'XP',
        'plan_explanation': 'PX',
        'pipeline_run': 'PR',
        'backlog_item': 'BLI',
        'work_package_candidate': 'WPC',
        'work_package': 'WP',
        'work_statement': 'WS',
        'project_logbook': 'PL',
        'story_backlog': 'SB',
        'epic': 'EP',
        'feature': 'FT',
    }
    for doc_type_id, prefix in prefix_map.items():
        op.execute(
            f"UPDATE document_types SET display_prefix = '{prefix}' "
            f"WHERE doc_type_id = '{doc_type_id}'"
        )

    # 7. Make display_prefix NOT NULL
    op.alter_column('document_types', 'display_prefix', nullable=False)

    # 8. Drop instance_key (replaced by display_prefix)
    op.drop_column('document_types', 'instance_key')


def downgrade() -> None:
    # 1. Add instance_key back
    op.add_column('document_types', sa.Column('instance_key', sa.String(100), nullable=True))

    # 2. Repopulate known instance_key values
    instance_key_map = {
        'epic': 'epic_id',
        'feature': 'feature_id',
        'work_package_candidate': 'wpc_id',
        'work_package': 'wp_id',
        'work_statement': 'ws_id',
    }
    for doc_type_id, key in instance_key_map.items():
        op.execute(
            f"UPDATE document_types SET instance_key = '{key}' "
            f"WHERE doc_type_id = '{doc_type_id}'"
        )

    # 3. Drop display_prefix
    op.drop_column('document_types', 'display_prefix')

    # 4. Drop display_id index
    op.drop_index('idx_documents_latest_display', table_name='documents')

    # 5. Drop display_id column
    op.drop_column('documents', 'display_id')
