"""Add LLM thread queue tables (ADR-035)

Revision ID: 20260110_001
Revises: 20260108_002_add_document_definitions
Create Date: 2026-01-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260110_001'
down_revision: Union[str, None] = '20260108_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intent container - durable record of user intent
    op.create_table(
        'llm_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('kind', sa.String(100), nullable=False),  # story_generate_epic, story_generate_all, etc.
        sa.Column('space_type', sa.String(50), nullable=False),  # project
        sa.Column('space_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_ref', postgresql.JSONB, nullable=False),  # {doc_type, doc_id, epic_id?}
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),  # open|running|complete|failed|canceled
        sa.Column('parent_thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('llm_threads.id'), nullable=True),
        sa.Column('idempotency_key', sa.String(255), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Execution unit - queue-executed work
    op.create_table(
        'llm_work_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('llm_threads.id'), nullable=False),
        sa.Column('sequence', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),  # queued|claimed|running|applied|failed|dead_letter
        sa.Column('attempt', sa.Integer, nullable=False, server_default='1'),
        sa.Column('lock_scope', sa.String(255), nullable=True),  # project:{id} or epic:{id}
        sa.Column('not_before', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),  # LOCKED|PROVIDER_RATE_LIMIT|PROVIDER_TIMEOUT|SCHEMA_INVALID|MUTATION_CONFLICT|UNKNOWN
        sa.Column('error_message', sa.Text, nullable=True),  # Human-readable summary (informational only)
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('thread_id', 'sequence', name='uq_work_item_thread_sequence'),
    )
    
    # Immutable ledger - what we paid for and received
    op.create_table(
        'llm_ledger_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('llm_threads.id'), nullable=False),
        sa.Column('work_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('llm_work_items.id'), nullable=True),
        sa.Column('entry_type', sa.String(50), nullable=False),  # prompt|response|parse_report|mutation_report|error
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('payload_hash', sa.String(64), nullable=True),  # SHA256 for dedup/verification
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    
    # Indexes
    op.create_index('idx_threads_space', 'llm_threads', ['space_type', 'space_id', 'status'])
    op.create_index('idx_work_items_thread', 'llm_work_items', ['thread_id'])
    op.create_index('idx_work_items_queued', 'llm_work_items', ['status'], postgresql_where=sa.text("status = 'queued'"))
    op.create_index('idx_ledger_thread', 'llm_ledger_entries', ['thread_id'])
    
    # Partial unique index for idempotency (only active threads)
    op.create_index(
        'uq_threads_idempotency_active',
        'llm_threads',
        ['idempotency_key'],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'running')")
    )


def downgrade() -> None:
    op.drop_index('uq_threads_idempotency_active', table_name='llm_threads')
    op.drop_index('idx_ledger_thread', table_name='llm_ledger_entries')
    op.drop_index('idx_work_items_queued', table_name='llm_work_items')
    op.drop_index('idx_work_items_thread', table_name='llm_work_items')
    op.drop_index('idx_threads_space', table_name='llm_threads')
    op.drop_table('llm_ledger_entries')
    op.drop_table('llm_work_items')
    op.drop_table('llm_threads')
