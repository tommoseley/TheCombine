"""Add schema_bundle_sha256 to documents

Revision ID: 20260112_002
Revises: 20260112_001
Create Date: 2026-01-12

Phase 2 of WS-DOCUMENT-SYSTEM-CLEANUP:
Adds schema_bundle_sha256 column to documents table so documents
preserve the schema version they were generated with. Viewer
resolves by hash, not "latest" schema.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260112_002'
down_revision = '20260112_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add schema_bundle_sha256 column - stores the hash of schema bundle at generation time
    # e.g., 'sha256:abc123...'
    op.add_column(
        'documents',
        sa.Column('schema_bundle_sha256', sa.String(100), nullable=True,
                  comment='Schema bundle hash at generation time (e.g., sha256:abc123...)')
    )
    
    # Index for schema_bundle_sha256 lookups (useful for finding docs by schema version)
    op.create_index(
        'idx_documents_schema_bundle',
        'documents',
        ['schema_bundle_sha256'],
        postgresql_where=sa.text("schema_bundle_sha256 IS NOT NULL")
    )


def downgrade() -> None:
    op.drop_index('idx_documents_schema_bundle', table_name='documents')
    op.drop_column('documents', 'schema_bundle_sha256')