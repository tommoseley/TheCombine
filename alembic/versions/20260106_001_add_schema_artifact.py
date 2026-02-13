"""Add schema_artifact table for ADR-031 Schema Registry

Revision ID: 20260106_001
Revises: 20260105_001_add_parent_document_id
Create Date: 2026-01-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260106_001'
down_revision = '20260105_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'schema_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('schema_id', sa.String(100), nullable=False, comment='Canonical schema identifier (e.g., OpenQuestionV1)'),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0', comment='Schema version'),
        sa.Column('kind', sa.String(20), nullable=False, comment='Schema kind: type, document, envelope'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='Lifecycle status: draft, accepted, deprecated'),
        sa.Column('schema_json', postgresql.JSONB, nullable=False, comment='The canonical JSON Schema'),
        sa.Column('sha256', sa.String(64), nullable=False, comment='SHA256 hash of schema_json'),
        sa.Column('governance_refs', postgresql.JSONB, nullable=True, comment='References to governing ADRs and policies'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        sa.CheckConstraint("kind IN ('type', 'document', 'envelope')", name='ck_schema_artifacts_kind'),
        sa.CheckConstraint("status IN ('draft', 'accepted', 'deprecated')", name='ck_schema_artifacts_status'),
    )
    
    # Unique constraint on (schema_id, version)
    op.create_index(
        'ix_schema_artifacts_schema_id_version',
        'schema_artifacts',
        ['schema_id', 'version'],
        unique=True
    )
    
    # Index on status for filtering
    op.create_index(
        'ix_schema_artifacts_status',
        'schema_artifacts',
        ['status']
    )
    
    # Index on kind for filtering
    op.create_index(
        'ix_schema_artifacts_kind',
        'schema_artifacts',
        ['kind']
    )


def downgrade() -> None:
    op.drop_index('ix_schema_artifacts_kind', table_name='schema_artifacts')
    op.drop_index('ix_schema_artifacts_status', table_name='schema_artifacts')
    op.drop_index('ix_schema_artifacts_schema_id_version', table_name='schema_artifacts')
    op.drop_table('schema_artifacts')