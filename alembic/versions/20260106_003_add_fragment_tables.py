"""Add fragment_artifacts and fragment_bindings tables for ADR-032

Revision ID: 20260106_003
Revises: 20260106_002
Create Date: 2026-01-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260106_003'
down_revision = '20260106_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fragment artifacts table
    op.create_table(
        'fragment_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('fragment_id', sa.String(100), nullable=False, comment='Fragment identifier (e.g., OpenQuestionV1Fragment)'),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0', comment='Fragment version'),
        sa.Column('schema_type_id', sa.String(100), nullable=False, comment='Canonical schema type this fragment renders'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='Lifecycle status: draft, accepted, deprecated'),
        sa.Column('fragment_markup', sa.Text, nullable=False, comment='HTML/Jinja2 template content'),
        sa.Column('sha256', sa.String(64), nullable=False, comment='SHA256 hash of fragment_markup'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        sa.CheckConstraint("status IN ('draft', 'accepted', 'deprecated')", name='ck_fragment_artifacts_status'),
    )
    
    # Indexes for fragment_artifacts
    op.create_index(
        'ix_fragment_artifacts_fragment_id_version',
        'fragment_artifacts',
        ['fragment_id', 'version'],
        unique=True
    )
    op.create_index(
        'ix_fragment_artifacts_schema_type_id',
        'fragment_artifacts',
        ['schema_type_id']
    )
    op.create_index(
        'ix_fragment_artifacts_status',
        'fragment_artifacts',
        ['status']
    )
    
    # Fragment bindings table
    op.create_table(
        'fragment_bindings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('schema_type_id', sa.String(100), nullable=False, comment='Canonical schema type ID'),
        sa.Column('fragment_id', sa.String(100), nullable=False, comment='Bound fragment ID'),
        sa.Column('fragment_version', sa.String(20), nullable=False, comment='Bound fragment version'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='false', comment='Whether this binding is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(100), nullable=True),
    )
    
    # Unique constraint: only one active binding per schema_type_id
    op.create_index(
        'ix_fragment_bindings_unique_active',
        'fragment_bindings',
        ['schema_type_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true')
    )
    op.create_index(
        'ix_fragment_bindings_fragment_id',
        'fragment_bindings',
        ['fragment_id']
    )


def downgrade() -> None:
    op.drop_index('ix_fragment_bindings_fragment_id', table_name='fragment_bindings')
    op.drop_index('ix_fragment_bindings_unique_active', table_name='fragment_bindings')
    op.drop_table('fragment_bindings')
    
    op.drop_index('ix_fragment_artifacts_status', table_name='fragment_artifacts')
    op.drop_index('ix_fragment_artifacts_schema_type_id', table_name='fragment_artifacts')
    op.drop_index('ix_fragment_artifacts_fragment_id_version', table_name='fragment_artifacts')
    op.drop_table('fragment_artifacts')