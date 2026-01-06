"""Add schema_id and schema_bundle_hash to llm_run for ADR-031

Revision ID: 20260106_002
Revises: 20260106_001
Create Date: 2026-01-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260106_002'
down_revision = '20260106_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add schema_id column (root schema identifier)
    op.add_column(
        'llm_run',
        sa.Column(
            'schema_id',
            sa.String(100),
            nullable=True,
            comment='Root schema identifier per ADR-031 (e.g., EpicBacklogV2)'
        )
    )
    
    # Add schema_bundle_hash column (resolved bundle SHA256)
    op.add_column(
        'llm_run',
        sa.Column(
            'schema_bundle_hash',
            sa.String(64),
            nullable=True,
            comment='SHA256 hash of resolved schema bundle per ADR-031'
        )
    )
    
    # Index for schema usage analysis
    op.create_index(
        'ix_llm_run_schema_id',
        'llm_run',
        ['schema_id'],
        postgresql_where=sa.text("schema_id IS NOT NULL")
    )


def downgrade() -> None:
    op.drop_index('ix_llm_run_schema_id', table_name='llm_run')
    op.drop_column('llm_run', 'schema_bundle_hash')
    op.drop_column('llm_run', 'schema_id')