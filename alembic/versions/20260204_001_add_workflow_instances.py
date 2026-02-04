"""add workflow_instances and workflow_instance_history tables

Revision ID: 20260204_001
Revises: 20260126_001
Create Date: 2026-02-04

Per WS-ADR-046-001 Phase 1.
Database-backed storage for project-scoped POW instances with
append-only audit trail. Implements ADR-046.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260204_001'
down_revision: Union[str, None] = '20260126_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workflow_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('projects.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),
        sa.Column('base_workflow_ref', postgresql.JSONB(), nullable=False),
        sa.Column('effective_workflow', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_workflow_instances_project_id', 'workflow_instances', ['project_id'], unique=True)
    op.create_index('idx_workflow_instances_status', 'workflow_instances', ['status'])

    op.create_table(
        'workflow_instance_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'instance_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('workflow_instances.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('change_type', sa.String(50), nullable=False),
        sa.Column('change_detail', postgresql.JSONB()),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('changed_by', sa.String(100)),
    )
    op.create_index('idx_workflow_instance_history_instance_id', 'workflow_instance_history', ['instance_id'])
    op.create_index('idx_workflow_instance_history_changed_at', 'workflow_instance_history', ['changed_at'])


def downgrade() -> None:
    op.drop_index('idx_workflow_instance_history_changed_at', table_name='workflow_instance_history')
    op.drop_index('idx_workflow_instance_history_instance_id', table_name='workflow_instance_history')
    op.drop_table('workflow_instance_history')
    op.drop_index('idx_workflow_instances_status', table_name='workflow_instances')
    op.drop_index('idx_workflow_instances_project_id', table_name='workflow_instances')
    op.drop_table('workflow_instances')
