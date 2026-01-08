"""Add component_artifacts table for ADR-034 Canonical Components

Revision ID: 20260108_001
Revises: 20260106_003
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260108_001'
down_revision = '20260106_003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'component_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('component_id', sa.String(150), nullable=False, unique=True, comment='Canonical component ID with semver (e.g., component:OpenQuestionV1:1.0.0)'),
        sa.Column('schema_artifact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schema_artifacts.id'), nullable=False, comment='FK to schema_artifacts'),
        sa.Column('schema_id', sa.String(100), nullable=False, comment='Denormalized schema ID for convenience (e.g., schema:OpenQuestionV1)'),
        sa.Column('generation_guidance', postgresql.JSONB, nullable=False, comment='Prompt generation bullets'),
        sa.Column('view_bindings', postgresql.JSONB, nullable=False, comment='Channel-specific fragment bindings'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='Lifecycle status: draft, accepted'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when status changed to accepted'),
        sa.CheckConstraint("status IN ('draft', 'accepted')", name='ck_component_artifacts_status'),
    )
    
    # Index on schema_artifact_id for FK queries
    op.create_index(
        'ix_component_artifacts_schema_artifact_id',
        'component_artifacts',
        ['schema_artifact_id']
    )
    
    # Index on status for filtering
    op.create_index(
        'ix_component_artifacts_status',
        'component_artifacts',
        ['status']
    )
    
    # Index on accepted_at for get_accepted queries (D7)
    op.create_index(
        'ix_component_artifacts_accepted_at',
        'component_artifacts',
        ['accepted_at']
    )


def downgrade() -> None:
    op.drop_index('ix_component_artifacts_accepted_at', table_name='component_artifacts')
    op.drop_index('ix_component_artifacts_status', table_name='component_artifacts')
    op.drop_index('ix_component_artifacts_schema_artifact_id', table_name='component_artifacts')
    op.drop_table('component_artifacts')
