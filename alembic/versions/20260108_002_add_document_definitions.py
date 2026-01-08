"""Add document_definitions table for ADR-034 Document Composition Manifest

Revision ID: 20260108_002
Revises: 20260108_001
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260108_002'
down_revision = '20260108_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'document_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_def_id', sa.String(150), nullable=False, unique=True, comment='Canonical docdef ID with semver (e.g., docdef:EpicBacklog:1.0.0)'),
        sa.Column('document_schema_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schema_artifacts.id'), nullable=True, comment='Optional FK to document schema (nullable for MVP)'),
        sa.Column('prompt_header', postgresql.JSONB, nullable=False, comment='Role and constraints for prompt generation'),
        sa.Column('sections', postgresql.JSONB, nullable=False, comment='Section definitions with component bindings'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='Lifecycle status: draft, accepted'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when status changed to accepted'),
        sa.CheckConstraint("status IN ('draft', 'accepted')", name='ck_document_definitions_status'),
    )
    
    # Index on status for filtering
    op.create_index(
        'ix_document_definitions_status',
        'document_definitions',
        ['status']
    )
    
    # Index on accepted_at for get_accepted queries (D7)
    op.create_index(
        'ix_document_definitions_accepted_at',
        'document_definitions',
        ['accepted_at']
    )


def downgrade() -> None:
    op.drop_index('ix_document_definitions_accepted_at', table_name='document_definitions')
    op.drop_index('ix_document_definitions_status', table_name='document_definitions')
    op.drop_table('document_definitions')
