"""create pgc_answers table

Revision ID: 20260124_001
Revises: 20260123_001
Create Date: 2026-01-24

Per WS-PGC-VALIDATION-001 Phase 2.
Stores PGC answers as first-class documents with full provenance.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260124_001'
down_revision: Union[str, None] = '20260123_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pgc_answers',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('execution_id', sa.String(36), nullable=False, index=True),
        sa.Column('workflow_id', sa.String(100), nullable=False),
        sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('pgc_node_id', sa.String(100), nullable=False),
        sa.Column('schema_ref', sa.String(255), nullable=False),
        sa.Column('questions', postgresql.JSONB(), nullable=False),
        sa.Column('answers', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('pgc_answers')
