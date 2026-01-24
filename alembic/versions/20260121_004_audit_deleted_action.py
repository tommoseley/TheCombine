"""Add DELETED to project_audit action check constraint.

Revision ID: 20260121_004
Revises: 20260121_003
Create Date: 2026-01-21

WS-SOFT-DELETE-001: Allow DELETED action in audit log.
"""
from alembic import op

revision = '20260121_004'
down_revision = '20260121_003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update check constraint to include DELETED."""
    # Drop old constraint
    op.drop_constraint('chk_project_audit_action', 'project_audit', type_='check')
    
    # Create new constraint with DELETED
    op.create_check_constraint(
        'chk_project_audit_action',
        'project_audit',
        "action IN ('CREATED', 'UPDATED', 'ARCHIVED', 'UNARCHIVED', 'DELETED', 'EDIT_BLOCKED_ARCHIVED')"
    )


def downgrade() -> None:
    """Revert to original constraint (will fail if DELETED rows exist)."""
    op.drop_constraint('chk_project_audit_action', 'project_audit', type_='check')
    
    op.create_check_constraint(
        'chk_project_audit_action',
        'project_audit',
        "action IN ('CREATED', 'UPDATED', 'ARCHIVED', 'UNARCHIVED', 'EDIT_BLOCKED_ARCHIVED')"
    )