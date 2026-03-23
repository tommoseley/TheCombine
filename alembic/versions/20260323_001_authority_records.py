"""Create authority_records table (ADR-064)

Revision ID: 20260323_001
Revises: 20260321_001
Create Date: 2026-03-23

Durable authority records for PGC answers that persist across
pipeline rewinds and regenerations. Authority is project-scoped,
path-aware, and type-scoped for supersession.

ADR-064: Durable Authority Context
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '20260323_001'
down_revision = '20260321_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'authority_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('authority_type', sa.String(50), nullable=False),
        sa.Column('stage', sa.String(20), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', JSONB, nullable=False),
        sa.Column('source_execution_id', UUID(as_uuid=True), nullable=False),
        sa.Column('lineage_path_id', UUID(as_uuid=True), nullable=False),
        sa.Column('actor', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='current'),
        sa.Column('superseded_by', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Index: current authority resolution by project
    op.create_index(
        'idx_authority_project_status',
        'authority_records',
        ['project_id', 'status'],
    )

    # Index: type-scoped supersession lookup
    op.create_index(
        'idx_authority_supersession',
        'authority_records',
        ['project_id', 'authority_type', 'key', 'status'],
    )

    # Index: path-historical bulk updates
    op.create_index(
        'idx_authority_lineage_path',
        'authority_records',
        ['lineage_path_id'],
    )


def downgrade() -> None:
    op.drop_index('idx_authority_lineage_path', table_name='authority_records')
    op.drop_index('idx_authority_supersession', table_name='authority_records')
    op.drop_index('idx_authority_project_status', table_name='authority_records')
    op.drop_table('authority_records')
