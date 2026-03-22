"""Add versioned document support for pipeline rewind (ADR-063)

Revision ID: 20260321_001
Revises: 20260305_001
Create Date: 2026-03-21

Adds version-aware unique indexes to support multiple document versions
per display_id while maintaining exactly one is_latest per display_id.

The existing idx_documents_latest_display constraint is PRESERVED —
it correctly enforces one latest doc per (space, type, display_id).

New indexes:
- idx_documents_version_unique: prevents duplicate version numbers
  per (space, type, display_id)
- idx_documents_status: optimizes status-based queries for rewind

ADR-063: Pipeline Rewind, Invalidation, and Regeneration Semantics
"""

from alembic import op

revision = '20260321_001'
down_revision = '20260305_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add version uniqueness index
    # Ensures no two documents share the same version for a given display_id
    op.create_index(
        'idx_documents_version_unique',
        'documents',
        ['space_type', 'space_id', 'doc_type_id', 'display_id', 'version'],
        unique=True,
    )

    # 2. Add status index for efficient rewind queries
    # Used when finding current/stale/superseded documents by type
    op.create_index(
        'idx_documents_status',
        'documents',
        ['space_type', 'space_id', 'doc_type_id', 'status'],
    )

    # 3. Add lifecycle_state index for stale artifact filtering
    op.create_index(
        'idx_documents_lifecycle',
        'documents',
        ['lifecycle_state'],
        postgresql_where="lifecycle_state = 'stale'",
    )


def downgrade() -> None:
    op.drop_index('idx_documents_lifecycle', table_name='documents')
    op.drop_index('idx_documents_status', table_name='documents')
    op.drop_index('idx_documents_version_unique', table_name='documents')
