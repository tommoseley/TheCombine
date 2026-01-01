"""Backfill project_audit with CREATED events

Revision ID: 003_backfill_audit
Revises: 002_create_audit
Create Date: 2025-01-01 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20251231_004'
down_revision = '20251231_003'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # Content Storage Table
    # ========================================================================
    op.create_table(
        'llm_content',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('content_hash', sa.Text(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('content_size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('accessed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_hash'),
        comment='Content storage for LLM inputs/outputs (ADR-010)'
    )
    op.create_index('idx_llm_content_hash', 'llm_content', ['content_hash'])
    op.create_index('idx_llm_content_accessed', 'llm_content', ['accessed_at'])
    
    # ========================================================================
    # Main Execution Record
    # ========================================================================
    op.create_table(
        'llm_run',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('artifact_type', sa.Text(), nullable=True),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('model_provider', sa.Text(), nullable=False),
        sa.Column('model_name', sa.Text(), nullable=False),
        sa.Column('prompt_id', sa.Text(), nullable=False),
        sa.Column('prompt_version', sa.Text(), nullable=False),
        sa.Column('effective_prompt_hash', sa.Text(), nullable=False),
        sa.Column('schema_version', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('primary_error_code', sa.Text(), nullable=True),
        sa.Column('primary_error_message', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='LLM execution records (ADR-010)'
    )
    op.create_index('idx_llm_run_correlation', 'llm_run', ['correlation_id'])
    op.create_index('idx_llm_run_project_time', 'llm_run', ['project_id', sa.text('started_at DESC')], 
                    postgresql_where=sa.text('project_id IS NOT NULL'))
    op.create_index('idx_llm_run_role_time', 'llm_run', ['role', sa.text('started_at DESC')])
    op.create_index('idx_llm_run_status', 'llm_run', ['status'])
    op.create_index('idx_llm_run_started', 'llm_run', [sa.text('started_at DESC')])
    
    # ========================================================================
    # Input References
    # ========================================================================
    op.create_table(
        'llm_run_input_ref',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('llm_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('content_ref', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.Text(), nullable=False),
        sa.Column('content_redacted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['llm_run_id'], ['llm_run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='LLM input references by content_ref (ADR-010)'
    )
    op.create_index('idx_llm_input_ref_run', 'llm_run_input_ref', ['llm_run_id'])
    op.create_index('idx_llm_input_ref_kind', 'llm_run_input_ref', ['llm_run_id', 'kind'])
    
    # ========================================================================
    # Output References
    # ========================================================================
    op.create_table(
        'llm_run_output_ref',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('llm_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('content_ref', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.Text(), nullable=False),
        sa.Column('parse_status', sa.Text(), nullable=True),
        sa.Column('validation_status', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['llm_run_id'], ['llm_run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='LLM output references by content_ref (ADR-010)'
    )
    op.create_index('idx_llm_output_ref_run', 'llm_run_output_ref', ['llm_run_id'])
    op.create_index('idx_llm_output_ref_kind', 'llm_run_output_ref', ['llm_run_id', 'kind'])
    
    # ========================================================================
    # Error Tracking
    # ========================================================================
    op.create_table(
        'llm_run_error',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('llm_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('stage', sa.Text(), nullable=False),
        sa.Column('severity', sa.Text(), nullable=False),
        sa.Column('error_code', sa.Text(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['llm_run_id'], ['llm_run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('llm_run_id', 'sequence', name='uq_llm_run_error_sequence'),
        comment='LLM execution errors (many-per-run model, ADR-010)'
    )
    op.create_index('idx_llm_error_run', 'llm_run_error', ['llm_run_id'])
    op.create_index('idx_llm_error_stage', 'llm_run_error', ['stage'])
    op.create_index('idx_llm_error_severity', 'llm_run_error', ['severity'])
    
    # ========================================================================
    # Tool Call Tracking (DEFERRED - created but unused in MVP)
    # ========================================================================
    op.create_table(
        'llm_run_tool_call',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('llm_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('tool_name', sa.Text(), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('input_ref', sa.Text(), nullable=False),
        sa.Column('output_ref', sa.Text(), nullable=True),
        sa.Column('error_ref', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['llm_run_id'], ['llm_run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('llm_run_id', 'sequence', name='uq_llm_run_tool_call_sequence'),
        comment='Tool call tracking (ADR-010) - UNUSED IN MVP, reserved for future'
    )
    op.create_index('idx_llm_tool_call_run', 'llm_run_tool_call', ['llm_run_id'])
    op.create_index('idx_llm_tool_call_name', 'llm_run_tool_call', ['tool_name'])
    op.create_index('idx_llm_tool_call_status', 'llm_run_tool_call', ['status'])


def downgrade():
    # Drop in reverse order (children before parents)
    op.drop_table('llm_run_tool_call')
    op.drop_table('llm_run_error')
    op.drop_table('llm_run_output_ref')
    op.drop_table('llm_run_input_ref')
    op.drop_table('llm_run')
    op.drop_table('llm_content')