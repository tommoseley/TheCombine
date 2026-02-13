"""add concierge intake tables

Revision ID: 20260114_144631
Revises: (will be filled by alembic)
Create Date: 2026-01-14 14:46:31

Implements: CONCIERGE_PROJECT_INGESTION_CONTRACT v1.0 section 5.1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260114_144631'
down_revision = '20260113_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create concierge_intake_session table
    op.create_table(
        'concierge_intake_session',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('origin_route', sa.String(255), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0'),
    )
    
    # Create indexes for concierge_intake_session
    op.create_index('idx_concierge_session_user', 'concierge_intake_session', ['user_id'])
    op.create_index('idx_concierge_session_state', 'concierge_intake_session', ['state'])
    op.create_index('idx_concierge_session_project', 'concierge_intake_session', ['project_id'])
    
    # Create concierge_intake_event table
    op.create_table(
        'concierge_intake_event',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('concierge_intake_session.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seq', sa.Integer, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload_json', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Create indexes for concierge_intake_event
    op.create_index('idx_concierge_event_session_seq', 'concierge_intake_event', ['session_id', 'seq'], unique=True)
    op.create_index('idx_concierge_event_type', 'concierge_intake_event', ['event_type'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_concierge_event_type', table_name='concierge_intake_event')
    op.drop_index('idx_concierge_event_session_seq', table_name='concierge_intake_event')
    op.drop_index('idx_concierge_session_project', table_name='concierge_intake_session')
    op.drop_index('idx_concierge_session_state', table_name='concierge_intake_session')
    op.drop_index('idx_concierge_session_user', table_name='concierge_intake_session')
    
    # Drop tables
    op.drop_table('concierge_intake_event')
    op.drop_table('concierge_intake_session')

