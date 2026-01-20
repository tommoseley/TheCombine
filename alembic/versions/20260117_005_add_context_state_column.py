"""Add context_state column to workflow_executions (ADR-040).

Revision ID: 20260117_005
Revises: 20260117_004
Create Date: 2026-01-17

Per ADR-040: context_state is the ONLY source of continuity for LLM invocations.
It contains structured, governed data derived from prior turns — NOT transcripts.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260117_005'
down_revision = '20260117_004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add context_state column for structured workflow memory (ADR-040)
    op.add_column('workflow_executions',
        sa.Column('context_state', postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('workflow_executions', 'context_state')
