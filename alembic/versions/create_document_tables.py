"""Create documents and document_relations tables

This replaces the old artifacts table with the document-centric model.

Revision ID: create_documents_tables
Revises: refactor_artifacts_uuids
Create Date: 2025-12-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'create_documents_tables'
down_revision: Union[str, None] = 'refactor_artifacts_uuids'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # CREATE DOCUMENTS TABLE
    # =========================================================================
    op.create_table(
        'documents',
        
        # Identity
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        
        # Ownership (which space does this doc live in?)
        sa.Column('space_type', sa.String(50), nullable=False),  # project | organization | team
        sa.Column('space_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Type
        sa.Column('doc_type_id', sa.String(100), nullable=False),
        
        # Versioning
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('revision_hash', sa.String(64), nullable=True),
        sa.Column('is_latest', sa.Boolean, nullable=False, server_default='true'),
        
        # Content
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('content', postgresql.JSONB, nullable=False),
        
        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('is_stale', sa.Boolean, nullable=False, server_default='false'),
        
        # Provenance
        sa.Column('created_by', sa.String(200), nullable=True),
        sa.Column('created_by_type', sa.String(50), nullable=True),  # user | builder | import
        sa.Column('builder_metadata', postgresql.JSONB, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        
        # Search
        sa.Column('search_vector', postgresql.TSVECTOR, nullable=True),
    )
    
    # Indexes for documents
    op.create_index('idx_documents_space', 'documents', ['space_type', 'space_id'])
    op.create_index('idx_documents_type', 'documents', ['doc_type_id'])
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_documents_search', 'documents', ['search_vector'],
                    postgresql_using='gin')
    
    # Unique constraint: one latest doc per type per space
    op.create_index(
        'idx_documents_unique_latest',
        'documents',
        ['space_type', 'space_id', 'doc_type_id'],
        unique=True,
        postgresql_where=sa.text('is_latest = true')
    )
    
    # Foreign key to document_types
    op.create_foreign_key(
        'fk_documents_doc_type',
        'documents',
        'document_types',
        ['doc_type_id'],
        ['doc_type_id'],
        ondelete='RESTRICT'
    )
    
    # =========================================================================
    # CREATE DOCUMENT_RELATIONS TABLE
    # =========================================================================
    op.create_table(
        'document_relations',
        
        # Identity
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        
        # Edge endpoints
        sa.Column('from_document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_document_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Edge type
        sa.Column('relation_type', sa.String(50), nullable=False),
        
        # Version pinning (for cross-space requires)
        sa.Column('pinned_version', sa.Integer, nullable=True),
        sa.Column('pinned_revision', sa.String(64), nullable=True),
        
        # Metadata
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('relation_metadata', postgresql.JSONB, nullable=True),
        
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=True),
    )
    
    # Constraints
    op.create_check_constraint(
        'no_self_reference',
        'document_relations',
        'from_document_id != to_document_id'
    )
    
    op.create_unique_constraint(
        'unique_relation',
        'document_relations',
        ['from_document_id', 'to_document_id', 'relation_type']
    )
    
    # Foreign keys
    op.create_foreign_key(
        'fk_relations_from_doc',
        'document_relations',
        'documents',
        ['from_document_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_relations_to_doc',
        'document_relations',
        'documents',
        ['to_document_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Indexes for relations
    op.create_index('idx_relations_from', 'document_relations', ['from_document_id'])
    op.create_index('idx_relations_to', 'document_relations', ['to_document_id'])
    op.create_index('idx_relations_type', 'document_relations', ['relation_type'])
    
    # =========================================================================
    # DROP OLD ARTIFACTS TABLE (optional - comment out if you want to keep it)
    # =========================================================================
    # op.drop_table('artifacts')


def downgrade() -> None:
    # Drop relations table
    op.drop_index('idx_relations_type', table_name='document_relations')
    op.drop_index('idx_relations_to', table_name='document_relations')
    op.drop_index('idx_relations_from', table_name='document_relations')
    op.drop_constraint('fk_relations_to_doc', 'document_relations', type_='foreignkey')
    op.drop_constraint('fk_relations_from_doc', 'document_relations', type_='foreignkey')
    op.drop_constraint('unique_relation', 'document_relations', type_='unique')
    op.drop_constraint('no_self_reference', 'document_relations', type_='check')
    op.drop_table('document_relations')
    
    # Drop documents table
    op.drop_constraint('fk_documents_doc_type', 'documents', type_='foreignkey')
    op.drop_index('idx_documents_unique_latest', table_name='documents')
    op.drop_index('idx_documents_search', table_name='documents')
    op.drop_index('idx_documents_status', table_name='documents')
    op.drop_index('idx_documents_type', table_name='documents')
    op.drop_index('idx_documents_space', table_name='documents')
    op.drop_table('documents')