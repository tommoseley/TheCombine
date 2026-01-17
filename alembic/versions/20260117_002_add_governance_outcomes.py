"""Add governance_outcomes table (ADR-037)

Revision ID: 20260117_002
Revises: 20260117_001
Create Date: 2026-01-17

Records governance layer outcomes for Intake Gate and other gates.
Separate from workflow_executions to maintain governance/execution separation.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260117_002'
down_revision = '20260117_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'governance_outcomes',
        # Identity
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),

        # References
        sa.Column('execution_id', sa.String(36), nullable=False,
                  comment='Reference to workflow_executions.execution_id'),
        sa.Column('document_id', sa.String(100), nullable=False,
                  comment='Document being governed'),
        sa.Column('document_type', sa.String(100), nullable=False,
                  comment='Type of document'),
        sa.Column('workflow_id', sa.String(100), nullable=False,
                  comment='Workflow plan that produced this outcome'),
        sa.Column('thread_id', sa.String(36), nullable=True,
                  comment='Reference to llm_threads.id if applicable'),

        # Governance outcome (ADR-025 vocabulary)
        sa.Column('gate_type', sa.String(50), nullable=False,
                  comment='Type of gate (intake_gate, qa_gate, etc.)'),
        sa.Column('gate_outcome', sa.String(50), nullable=False,
                  comment='Governance outcome (qualified, not_ready, out_of_scope, redirect)'),

        # Execution outcome (ADR-039 vocabulary)
        sa.Column('terminal_outcome', sa.String(50), nullable=False,
                  comment='Execution outcome (stabilized, blocked, abandoned)'),

        # Routing decision
        sa.Column('ready_for', sa.String(100), nullable=True,
                  comment='Next station if qualified (pm_discovery, etc.)'),
        sa.Column('routing_rationale', sa.Text, nullable=True,
                  comment='Explanation for the routing decision'),

        # Audit metadata
        sa.Column('options_offered', postgresql.JSONB, nullable=True,
                  comment='Snapshot of available_options[] at decision time (ADR-037)'),
        sa.Column('option_selected', sa.String(100), nullable=True,
                  comment='The option_id that was selected'),
        sa.Column('selection_method', sa.String(50), nullable=True,
                  comment='auto, recommended, user_confirmed'),

        # Context snapshot
        sa.Column('retry_count', sa.Integer, nullable=True,
                  comment='Retry count at time of outcome'),
        sa.Column('circuit_breaker_active', sa.Boolean, nullable=False,
                  server_default='false',
                  comment='Whether circuit breaker was active'),

        # Timestamps
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()'),
                  comment='When this outcome was recorded'),

        # Audit fields
        sa.Column('recorded_by', sa.String(100), nullable=True,
                  comment='Who/what recorded this outcome'),
    )

    # Index for looking up outcomes by execution
    op.create_index(
        'ix_governance_outcomes_execution',
        'governance_outcomes',
        ['execution_id']
    )

    # Index for looking up outcomes by document
    op.create_index(
        'ix_governance_outcomes_document',
        'governance_outcomes',
        ['document_type', 'document_id']
    )

    # Index for filtering by gate type and outcome
    op.create_index(
        'ix_governance_outcomes_gate',
        'governance_outcomes',
        ['gate_type', 'gate_outcome']
    )


def downgrade() -> None:
    op.drop_index('ix_governance_outcomes_gate', table_name='governance_outcomes')
    op.drop_index('ix_governance_outcomes_document', table_name='governance_outcomes')
    op.drop_index('ix_governance_outcomes_execution', table_name='governance_outcomes')
    op.drop_table('governance_outcomes')
