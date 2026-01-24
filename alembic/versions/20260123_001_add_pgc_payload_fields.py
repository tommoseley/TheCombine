"""add pgc payload fields to workflow execution

Revision ID: add_pgc_payload_fields
Revises: 
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260123_001'
down_revision: Union[str, None] = '20260121_004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('workflow_executions', sa.Column('pending_user_input_payload', postgresql.JSONB(), nullable=True))
    op.add_column('workflow_executions', sa.Column('pending_user_input_schema_ref', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('workflow_executions', 'pending_user_input_schema_ref')
    op.drop_column('workflow_executions', 'pending_user_input_payload')