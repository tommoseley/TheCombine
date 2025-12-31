"""Create project_audit table

Revision ID: 002_create_audit
Revises: 001_add_archive
Create Date: 2025-01-01 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20251231_002'
down_revision = '20251231_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create project_audit table
    op.create_table(
        'project_audit',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Foreign keys
        sa.ForeignKeyConstraint(
            ['project_id'], 
            ['projects.id'], 
            name='fk_project_audit_project',
            ondelete='RESTRICT'
        ),
        sa.ForeignKeyConstraint(
            ['actor_user_id'], 
            ['users.user_id'], 
            name='fk_project_audit_actor',
            ondelete='SET NULL'
        ),
        
        # Check constraint for valid actions
        sa.CheckConstraint(
            "action IN ('CREATED', 'UPDATED', 'ARCHIVED', 'UNARCHIVED', 'EDIT_BLOCKED_ARCHIVED')",
            name='chk_project_audit_action'
        )
    )
    
    # Create indexes
    op.create_index('idx_project_audit_project_created', 'project_audit', ['project_id', sa.text('created_at DESC')])
    op.create_index('idx_project_audit_actor_created', 'project_audit', ['actor_user_id', sa.text('created_at DESC')])
    op.create_index('idx_project_audit_action_created', 'project_audit', ['action', sa.text('created_at DESC')])
    
    # Add table comment
    op.execute("""
        COMMENT ON TABLE project_audit IS 
        'Append-only audit log for project lifecycle events. Immutable.'
    """)
    op.execute("""
        COMMENT ON COLUMN project_audit.actor_user_id IS 
        'User who performed action. NULL for system/agent actions.'
    """)
    op.execute("""
        COMMENT ON COLUMN project_audit.metadata IS 
        'Structured audit context: client, correlation_id, changed_fields, before/after, etc.'
    """)


def downgrade():
    op.drop_table('project_audit')